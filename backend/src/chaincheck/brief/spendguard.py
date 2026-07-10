"""Spend guard for the AI trip brief.

``POST /v1/tripbrief`` is the only endpoint where an anonymous request turns
into Anthropic spend, so generations get two ceilings: a per-client hourly
allowance and a global daily budget. Only real model generations count; cache
hits and stale-serves are free. When a ceiling is hit the brief degrades to
the deterministic plain rendering, never an error.

Counters are per-process. With N Cloud Run instances the effective ceiling is
up to N times the configured value; keep maxScale in mind when tuning.
"""

from __future__ import annotations

import os
import time
from collections import deque
from collections.abc import Callable

HOUR = 60.0 * 60.0
DAY = 24.0 * HOUR

# Sweep the per-client table when it grows past this many entries, so an
# address-spraying abuser can't grow the process heap without bound.
_SWEEP_THRESHOLD = 4096


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


class BudgetExceeded(Exception):
    """A generation was requested past a spend ceiling."""


class SpendGuard:
    """Sliding-window generation limiter. ``allow`` checks and consumes."""

    def __init__(
        self,
        per_client_hourly: int | None = None,
        global_daily: int | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if per_client_hourly is None:
            per_client_hourly = _int_env("BRIEF_CLIENT_HOURLY", 6)
        if global_daily is None:
            global_daily = _int_env("BRIEF_GLOBAL_DAILY", 300)
        self.per_client_hourly = per_client_hourly
        self.global_daily = global_daily
        self._clock = clock
        self._global: deque[float] = deque()
        self._clients: dict[str, deque[float]] = {}

    @staticmethod
    def _prune(stamps: deque[float], horizon: float, now: float) -> None:
        while stamps and now - stamps[0] >= horizon:
            stamps.popleft()

    def _sweep(self, now: float) -> None:
        if len(self._clients) <= _SWEEP_THRESHOLD:
            return
        for key, stamps in list(self._clients.items()):
            self._prune(stamps, HOUR, now)
            if not stamps:
                del self._clients[key]

    def allow(self, client: str | None) -> bool:
        """True (and one generation consumed) if ``client`` may generate now.

        Requests with no derivable address share one "unknown" allowance
        rather than bypassing the per-client ceiling.
        """
        now = self._clock()
        self._prune(self._global, DAY, now)
        if len(self._global) >= self.global_daily:
            return False
        key = client or "unknown"
        stamps = self._clients.get(key)
        if stamps is None:
            self._sweep(now)
            stamps = self._clients[key] = deque()
        self._prune(stamps, HOUR, now)
        if len(stamps) >= self.per_client_hourly:
            return False
        stamps.append(now)
        self._global.append(now)
        return True
