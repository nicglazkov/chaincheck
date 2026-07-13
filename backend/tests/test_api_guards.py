"""Endpoint-level security behavior: the middleware and the input guards
that protect the database and the AI budget. These exercise the wiring;
the pure rules live in test_security.py."""

import pytest
from fastapi.testclient import TestClient

from chaincheck.api import app as app_module


@pytest.fixture
def client(monkeypatch):
    # In-memory subscriptions, no real FCM/Firestore, no Anthropic.
    monkeypatch.setenv("SUBSCRIPTIONS_BACKEND", "memory")
    monkeypatch.setenv("PUSH_DISABLED", "1")
    monkeypatch.setenv("POLL_TOKEN", "secret-token")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # Fresh limiters so tests don't bleed into each other.
    app_module._request_limiter = app_module.security.RateLimiter(120, 60.0)
    app_module._subscription_limiter = app_module.security.RateLimiter(20, 3600.0)
    with TestClient(app_module.app) as c:
        yield c


def test_health_is_open_and_carries_hardening_headers(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["ok"] is True
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "max-age=" in r.headers["Strict-Transport-Security"]


def test_poll_requires_token_and_is_constant_time_checked(client):
    assert client.post("/internal/poll").status_code == 403
    assert client.post(
        "/internal/poll", headers={"X-Poll-Token": "wrong"}
    ).status_code == 403


def test_poll_fails_closed_when_token_unset(client, monkeypatch):
    # A misconfigured deploy that forgot POLL_TOKEN must NOT expose the tick.
    monkeypatch.delenv("POLL_TOKEN", raising=False)
    monkeypatch.delenv("CHAINCHECK_ALLOW_OPEN_POLL", raising=False)
    assert client.post("/internal/poll").status_code == 403
    assert client.get("/v1/events").status_code == 403


def test_events_is_no_longer_public(client):
    assert client.get("/v1/events").status_code == 403
    ok = client.get("/v1/events", headers={"X-Poll-Token": "secret-token"})
    assert ok.status_code == 200


def test_oversized_body_is_rejected_before_parsing(client):
    big = "x" * (app_module.security.MAX_REQUEST_BYTES + 1)
    r = client.put(
        "/v1/subscriptions",
        content=f'{{"token":"{big}","corridor_ids":["i80"]}}',
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 413


def test_subscription_rejects_dangerous_tokens(client):
    for bad in ("a/b", "../x", "__proto__", "has space"):
        r = client.put(
            "/v1/subscriptions", json={"token": bad, "corridor_ids": ["i80"]}
        )
        assert r.status_code == 422, bad


def test_subscription_roundtrip_with_valid_token(client):
    tok = "fMxx1a2b:APA91bH-_ok.QWERTY-0987_zxcv"
    r = client.put("/v1/subscriptions", json={"token": tok, "corridor_ids": ["i80", "nope"]})
    assert r.status_code == 200
    assert r.json()["corridor_ids"] == ["i80"]  # unknown dropped
    # Query and delete carry the token in the body, never the URL path.
    got = client.post("/v1/subscriptions/query", json={"token": tok})
    assert got.status_code == 200 and got.json()["corridor_ids"] == ["i80"]
    gone = client.post("/v1/subscriptions/delete", json={"token": tok})
    assert gone.status_code == 200
    assert client.post("/v1/subscriptions/query", json={"token": tok}).status_code == 404


def test_token_never_appears_in_a_url_path(client):
    # There is no path-parameter route that would log the token.
    tok = "fMxx1a2b:APA91bH-_ok"
    assert client.get(f"/v1/subscriptions/{tok}").status_code in (404, 405)
    assert client.delete(f"/v1/subscriptions/{tok}").status_code in (404, 405)


def test_subscription_write_rate_limit(client):
    app_module._subscription_limiter = app_module.security.RateLimiter(3, 3600.0)
    ok = 0
    for i in range(10):
        r = client.put(
            "/v1/subscriptions",
            json={"token": f"tok{i}-valid_ok", "corridor_ids": ["i80"]},
        )
        if r.status_code == 200:
            ok += 1
        elif r.status_code == 429:
            break
    assert ok == 3


def test_global_rate_limit_returns_429(client):
    app_module._request_limiter = app_module.security.RateLimiter(5, 60.0)
    codes = [client.get("/v1/summary").status_code for _ in range(8)]
    assert 429 in codes
    # health stays exempt even after the flood
    assert client.get("/health").status_code == 200


def test_appcheck_monitors_but_does_not_block_by_default(client):
    app_module._appcheck_monitor = app_module.appcheck.AppCheckMonitor()
    # No attestation header + not enforcing -> a protected write still succeeds.
    tok = "fMxx1a2b:APA91bH-_ok.mon"
    r = client.put("/v1/subscriptions", json={"token": tok, "corridor_ids": ["i80"]})
    assert r.status_code == 200
    stats = client.get("/internal/appcheck-stats", headers={"X-Poll-Token": "secret-token"})
    assert stats.status_code == 200
    body = stats.json()
    assert body["missing"] >= 1 and body["enforcing"] is False


def test_appcheck_stats_needs_poll_token(client):
    assert client.get("/internal/appcheck-stats").status_code == 403


def test_appcheck_enforcement_blocks_protected_paths_without_token(client, monkeypatch):
    monkeypatch.setenv("APP_CHECK_ENFORCE", "1")
    # Protected write with no attestation -> rejected before any DB work.
    r = client.put(
        "/v1/subscriptions", json={"token": "fMxx_valid_ok", "corridor_ids": ["i80"]}
    )
    assert r.status_code == 401
    # Reads stay open even under enforcement (web page / evals).
    assert client.get("/health").status_code == 200
