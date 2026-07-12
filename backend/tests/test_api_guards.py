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
    got = client.get(f"/v1/subscriptions/{tok}")
    assert got.status_code == 200 and got.json()["corridor_ids"] == ["i80"]


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
