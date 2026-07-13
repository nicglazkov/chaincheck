"""Size-bounded outbound fetch.

httpx's plain ``client.get()`` reads the whole body into memory before it
returns, so a compromised or MITM'd upstream that streams a multi-gigabyte
response could OOM the instance before any post-hoc check runs. These helpers
stream instead and abort once the response passes a generous ceiling that no
real feed approaches.
"""

from __future__ import annotations

import json as _json

import httpx

# Every real feed we consume is well under a megabyte; 8 MB is comfortable
# headroom while still bounding a hostile response.
MAX_FEED_BYTES = 8 * 1024 * 1024


class FeedTooLarge(Exception):
    """An upstream response exceeded the size ceiling and was abandoned."""


async def fetch_capped(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict | None = None,
    params: dict | None = None,
    timeout: float = 30.0,
    max_bytes: int = MAX_FEED_BYTES,
) -> bytes:
    """GET ``url`` and return the body, aborting past ``max_bytes``.

    Raises the usual ``httpx.HTTPStatusError`` on a 4xx/5xx (so existing
    fallback logic keeps working) and ``FeedTooLarge`` on an oversized body.
    """
    async with client.stream(
        "GET", url, headers=headers, params=params, timeout=timeout
    ) as resp:
        resp.raise_for_status()
        declared = resp.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > max_bytes:
            raise FeedTooLarge(f"declared {declared} bytes exceeds {max_bytes}")
        chunks: list[bytes] = []
        total = 0
        async for chunk in resp.aiter_bytes():
            total += len(chunk)
            if total > max_bytes:
                raise FeedTooLarge(f"body exceeds {max_bytes} bytes")
            chunks.append(chunk)
        return b"".join(chunks)


async def fetch_json_capped(client: httpx.AsyncClient, url: str, **kw) -> object:
    return _json.loads(await fetch_capped(client, url, **kw))


async def fetch_text_capped(client: httpx.AsyncClient, url: str, **kw) -> str:
    return (await fetch_capped(client, url, **kw)).decode("utf-8", errors="replace")
