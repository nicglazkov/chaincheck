"""Request-safety helpers: trusted client IP, generic rate limiting, and
input validation. Kept out of the endpoint module so each rule is unit
testable in isolation.

None of this is a substitute for the platform controls (Cloud Run instance
cap, Firestore rules, Secret Manager); it is the in-process layer that keeps
a single caller from turning a public endpoint into a cost or abuse vector.
"""

from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
import time
from collections import deque
from collections.abc import Callable

import httpx

MAX_REQUEST_BYTES = 16 * 1024  # our largest legitimate body is a few hundred
# Firestore document ids cap at 1500 bytes and real FCM tokens are ~150-350
# chars; keep well under the former so an oversized token is a clean 422 at
# the edge rather than a 500 from deep in the store.
MAX_TOKEN_LEN = 1024
MAX_ORIGIN_LEN = 64
MAX_CORRIDOR_IDS = 64


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def trusted_client_ip(xff: str | None, peer: str | None) -> str | None:
    """The real caller address, resistant to X-Forwarded-For spoofing.

    A client can send its own X-Forwarded-For; Cloud Run appends the true
    connecting address as the LAST entry, so earlier entries are hostile
    input. Take the last well-formed IP and fall back to the socket peer.
    Using the leftmost value (the common mistake) lets an attacker mint a
    fresh identity per request and walk through any per-IP limit.
    """
    if xff:
        for part in reversed([p.strip() for p in xff.split(",")]):
            if _is_ip(part):
                return part
    if peer and _is_ip(peer):
        return peer
    return None


class RateLimiter:
    """Per-key sliding-window limiter with bounded memory.

    Counters are per-process; with N Cloud Run instances the effective
    limit is up to N times the configured value. The key-table is capped so
    an address-spraying caller cannot grow the heap without bound.
    """

    def __init__(
        self,
        limit: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = 8192,
    ) -> None:
        self.limit = limit
        self.window = window_seconds
        self._clock = clock
        self._max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}

    def _prune(self, hits: deque[float], now: float) -> None:
        while hits and now - hits[0] >= self.window:
            hits.popleft()

    def _sweep(self, now: float) -> None:
        for key, hits in list(self._hits.items()):
            self._prune(hits, now)
            if not hits:
                del self._hits[key]
        # If everything is still live, evict the arbitrary-oldest entry so
        # the table stays bounded even under a distinct-key flood.
        while len(self._hits) >= self._max_keys:
            self._hits.pop(next(iter(self._hits)))

    def allow(self, key: str | None) -> bool:
        """True (and one hit consumed) if ``key`` is under its limit.

        A missing key shares one "unknown" bucket rather than bypassing the
        limit entirely.
        """
        now = self._clock()
        bucket = key or "unknown"
        hits = self._hits.get(bucket)
        if hits is None:
            if len(self._hits) >= self._max_keys:
                self._sweep(now)
            hits = self._hits[bucket] = deque()
        self._prune(hits, now)
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True


# FCM registration tokens are URL-safe-ish: letters, digits, and a small set
# of punctuation. Never a slash (Firestore reads it as a path separator),
# never the reserved __...__ document-id form, never a dot-segment.
_TOKEN_RE = re.compile(r"\A[A-Za-z0-9_:.\-]+\Z")


def is_valid_push_token(token: str) -> bool:
    if not token or len(token) > MAX_TOKEN_LEN:
        return False
    if "." * 2 in token:
        return False
    if token.startswith("__") and token.endswith("__"):
        return False
    return bool(_TOKEN_RE.match(token))


# Place names only need letters, digits, spaces, and a little punctuation.
# Stripping everything else removes newlines (log/prompt injection) and caps
# the value so it cannot be used to inflate the model's input tokens.
_ORIGIN_STRIP = re.compile(r"[^A-Za-z0-9 ,.'\-/]")


def sanitize_origin(origin: str, max_len: int = MAX_ORIGIN_LEN) -> str:
    cleaned = _ORIGIN_STRIP.sub("", origin or "").strip()
    return cleaned[:max_len] or "Sacramento"


class BlockedHostError(httpx.RequestError):
    """An outbound request (or a redirect) targeted a non-public address."""


async def _resolves_to_non_public(host: str) -> bool:
    """True if ``host`` resolves to any non-global address (private, loopback,
    link-local incl. the cloud metadata IP, reserved, etc.)."""
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, None)
    except (socket.gaierror, UnicodeError):
        return False  # let the normal connect path surface a DNS failure
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if not ip.is_global:
            return True
    return False


async def forbid_internal_hosts(request: httpx.Request) -> None:
    """httpx request hook: abort any request whose target resolves to a
    non-public address. Runs on the initial request AND every redirect, so a
    compromised upstream cannot 3xx the shared client into the VPC or the
    cloud metadata server. Legitimate public redirects are unaffected.
    """
    if await _resolves_to_non_public(request.url.host):
        raise BlockedHostError(
            f"blocked non-public host: {request.url.host}", request=request
        )
