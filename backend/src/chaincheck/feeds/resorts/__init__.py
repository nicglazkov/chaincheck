"""Resort adapter registry.

One TTL-cached, stale-serving entry per resort; a failing or blocked resort
degrades alone. Disable any adapter without a deploy via the
``RESORTS_DISABLED`` env var (comma-separated adapter ids).
"""

from __future__ import annotations

import asyncio
import os

import httpx
from ca_roads.cache import TTLCache

from chaincheck.feeds.resorts.base import ResortAdapter, ResortReport
from chaincheck.feeds.resorts.boreal import BorealAdapter
from chaincheck.feeds.resorts.diamondpeak import DiamondPeakAdapter
from chaincheck.feeds.resorts.donner import DonnerSkiRanchAdapter
from chaincheck.feeds.resorts.homewood import HomewoodAdapter
from chaincheck.feeds.resorts.mtnpowder import PalisadesAdapter
from chaincheck.feeds.resorts.mtrose import MtRoseAdapter
from chaincheck.feeds.resorts.sierra import SierraAtTahoeAdapter
from chaincheck.feeds.resorts.sugarbowl import SugarBowlAdapter
from chaincheck.feeds.resorts.vail import heavenly, kirkwood, northstar

TTL_SECONDS = 30 * 60
MAX_SERVE_SECONDS = 12 * 60 * 60

# Base-area coordinates for the map (static; not worth an adapter field).
RESORT_COORDS: dict[str, tuple[float, float]] = {
    "palisades": (39.1969, -120.2358),
    "heavenly": (38.9351, -119.9400),
    "northstar": (39.2746, -120.1211),
    "kirkwood": (38.6850, -120.0654),
    "sugarbowl": (39.3043, -120.3336),
    "sierra": (38.7990, -120.0803),
    "homewood": (39.0857, -120.1600),
    "diamondpeak": (39.2542, -119.9218),
    "mtrose": (39.3287, -119.8854),
    "boreal": (39.3365, -120.3499),
    "donner": (39.3172, -120.3306),
}


def all_adapters() -> list[ResortAdapter]:
    return [
        PalisadesAdapter(),
        heavenly(),
        northstar(),
        kirkwood(),
        SugarBowlAdapter(),
        SierraAtTahoeAdapter(),
        HomewoodAdapter(),
        DiamondPeakAdapter(),
        MtRoseAdapter(),
        BorealAdapter(),
        DonnerSkiRanchAdapter(),
    ]


def disabled_ids() -> set[str]:
    raw = os.environ.get("RESORTS_DISABLED", "")
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


class ResortRegistry:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._cache = TTLCache()
        self._adapters = {a.id: a for a in all_adapters()}

    @property
    def adapters(self) -> dict[str, ResortAdapter]:
        return self._adapters

    async def report(self, resort_id: str) -> ResortReport | None:
        adapter = self._adapters.get(resort_id)
        if adapter is None or adapter.id in disabled_ids():
            return None
        outcome = await self._cache.get(
            adapter.id,
            TTL_SECONDS,
            MAX_SERVE_SECONDS,
            lambda: adapter.fetch(self._client),
        )
        if outcome.served:
            report: ResortReport = outcome.value  # type: ignore[assignment]
            report.stale = outcome.stale
            if outcome.stale and outcome.error:
                report.error = outcome.error
            return report
        return ResortReport(
            resort_id=adapter.id,
            name=adapter.name,
            ok=False,
            error=outcome.error,
        )

    async def all_reports(self) -> list[ResortReport]:
        enabled = [a for a in self._adapters.values() if a.id not in disabled_ids()]
        reports = await asyncio.gather(*(self.report(a.id) for a in enabled))
        return [r for r in reports if r is not None]
