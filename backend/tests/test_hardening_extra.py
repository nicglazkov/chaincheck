"""Fold-in hardening from the independent audit: no upstream detail leaks to
clients, feed text can't bloat the prompt, the trip-brief cache is bounded,
off-host forecast URLs are refused, and docs are off by default."""

import pytest

from chaincheck.api import serialize
from chaincheck.brief import facts as facts_mod
from chaincheck.brief.tripbrief import MAX_CACHE_KEYS, TripBriefer


def test_public_note_strips_urls_and_exception_detail():
    raw = "roads: ConnectError: failed to GET https://cwwp2.dot.ca.gov/secret?x=1"
    scrubbed = serialize._public_note(raw)
    assert "https://" not in scrubbed
    assert "ConnectError" not in scrubbed
    assert scrubbed.startswith("roads:")
    assert "unavailable" in scrubbed


def test_feed_strings_capped_before_the_prompt():
    assert facts_mod._cap("x" * 10_000) == "x" * facts_mod._FEED_STR_CAP
    assert facts_mod._cap("Donner Summit") == "Donner Summit"


def test_trip_brief_cache_is_bounded():
    briefer = TripBriefer()
    # Simulate a flood of distinct keys reaching the underlying cache.
    for i in range(MAX_CACHE_KEYS + 50):
        briefer._cache._entries[f"k{i}"] = object()
    # Next access flushes wholesale instead of growing without bound.
    assert len(briefer._bounded_cache()._entries) == 0


def test_docs_are_disabled_by_default():
    from fastapi.testclient import TestClient

    from chaincheck.api import app as app_module
    from chaincheck.api import security

    # Fresh limiter so leftover state from other tests can't turn these into
    # 429s before routing.
    app_module._request_limiter = security.RateLimiter(120, 60.0)
    with TestClient(app_module.app) as c:
        assert c.get("/docs").status_code == 404
        assert c.get("/openapi.json").status_code == 404


class _FakePass:
    def __init__(self, lat, lon):
        self.id = "p1"
        self.lat = lat
        self.lon = lon


async def test_forecast_url_refuses_off_host(monkeypatch):
    from chaincheck.feeds import nws

    src = nws.NwsSource(client=object())

    async def fake_get_json(url, params=None):
        return {"properties": {"forecast": "https://evil.example.com/steal"}}

    src._get_json = fake_get_json
    with pytest.raises(ValueError, match="off-host"):
        await src._forecast_url(_FakePass(39.0, -120.0))


async def test_forecast_url_allows_nws_host(monkeypatch):
    from chaincheck.feeds import nws

    src = nws.NwsSource(client=object())

    async def fake_get_json(url, params=None):
        return {"properties": {"forecast": "https://api.weather.gov/gridpoints/x/1,2/forecast"}}

    src._get_json = fake_get_json
    url = await src._forecast_url(_FakePass(39.0, -120.0))
    assert url.startswith("https://api.weather.gov/")
