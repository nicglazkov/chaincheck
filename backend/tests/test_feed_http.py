"""Size-bounded outbound fetch: a hostile or MITM'd upstream cannot OOM the
instance with a giant streamed body."""

import httpx
import pytest

from chaincheck.feeds import _http


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_returns_normal_body():
    async with _client(lambda req: httpx.Response(200, content=b'{"ok": true}')) as c:
        assert await _http.fetch_json_capped(c, "https://x/") == {"ok": True}


async def test_rejects_oversized_declared_length():
    def handler(req):
        return httpx.Response(
            200,
            headers={"content-length": str(_http.MAX_FEED_BYTES + 1)},
            content=b"x",
        )

    async with _client(handler) as c:
        with pytest.raises(_http.FeedTooLarge):
            await _http.fetch_capped(c, "https://x/")


async def test_rejects_oversized_streamed_body_without_declared_length():
    # No content-length; the cap must trip on the streamed bytes themselves.
    big = b"x" * (_http.MAX_FEED_BYTES + 1024)
    async with _client(lambda req: httpx.Response(200, content=big)) as c:
        with pytest.raises(_http.FeedTooLarge):
            await _http.fetch_capped(c, "https://x/", max_bytes=1024)


async def test_propagates_http_errors_for_fallback_logic():
    async with _client(lambda req: httpx.Response(403, content=b"nope")) as c:
        with pytest.raises(httpx.HTTPStatusError):
            await _http.fetch_text_capped(c, "https://x/")
