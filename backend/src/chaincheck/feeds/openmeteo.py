"""Hourly snow accumulation for the passes via Open-Meteo (free, no key)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx
from ca_roads.cache import TTLCache

from chaincheck import USER_AGENT
from chaincheck.feeds._http import fetch_json_capped
from chaincheck.passes import MountainPass

API_URL = "https://api.open-meteo.com/v1/forecast"
TTL = 30 * 60
MAX_SERVE = 6 * 60 * 60

_HOURLY_VARS = "snowfall,snow_depth,temperature_2m,wind_speed_10m,freezing_level_height"


@dataclass(frozen=True)
class SnowHour:
    time: datetime
    snowfall_cm: float
    snow_depth_m: float | None
    temperature_c: float | None
    wind_kmh: float | None
    freezing_level_m: float | None


@dataclass
class SnowOutlook:
    pass_id: str
    hours: list[SnowHour] = field(default_factory=list)
    data_as_of: datetime | None = None
    ok: bool = True
    stale: bool = False
    error: str | None = None

    def accumulation_cm(self, window_hours: int, now: datetime | None = None) -> float:
        """Forecast snowfall total over the next ``window_hours`` from ``now``."""
        now = now or datetime.now(UTC)
        horizon = [
            h for h in self.hours
            if h.time >= now and (h.time - now).total_seconds() <= window_hours * 3600
        ]
        return round(sum(h.snowfall_cm for h in horizon), 1)

    def storm_start(self, threshold_cm_per_hr: float = 0.5,
                    now: datetime | None = None) -> datetime | None:
        """First upcoming hour with meaningful snowfall, if any."""
        now = now or datetime.now(UTC)
        for hour in self.hours:
            if hour.time >= now and hour.snowfall_cm >= threshold_cm_per_hr:
                return hour.time
        return None


def parse_hours(payload: dict) -> list[SnowHour]:
    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    snowfall = hourly.get("snowfall", [])
    depth = hourly.get("snow_depth", [])
    temp = hourly.get("temperature_2m", [])
    wind = hourly.get("wind_speed_10m", [])
    freezing = hourly.get("freezing_level_height", [])

    def _at(series: list, i: int) -> float | None:
        return series[i] if i < len(series) else None

    hours = []
    for i, raw in enumerate(times):
        try:
            when = datetime.fromisoformat(raw).replace(tzinfo=UTC)
        except ValueError:
            continue
        hours.append(
            SnowHour(
                time=when,
                snowfall_cm=float(_at(snowfall, i) or 0.0),
                snow_depth_m=_at(depth, i),
                temperature_c=_at(temp, i),
                wind_kmh=_at(wind, i),
                freezing_level_m=_at(freezing, i),
            )
        )
    return hours


class OpenMeteoSource:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._cache = TTLCache()

    async def outlook(self, mtn_pass: MountainPass, days: int = 7) -> SnowOutlook:
        result = SnowOutlook(pass_id=mtn_pass.id)

        async def fetch() -> list[SnowHour]:
            payload = await fetch_json_capped(
                self._client,
                API_URL,
                params={
                    "latitude": f"{mtn_pass.lat:.4f}",
                    "longitude": f"{mtn_pass.lon:.4f}",
                    "hourly": _HOURLY_VARS,
                    "forecast_days": str(days),
                    "timezone": "UTC",
                },
                headers={"User-Agent": USER_AGENT},
                timeout=20.0,
            )
            return parse_hours(payload)

        outcome = await self._cache.get(("snow", mtn_pass.id, days), TTL, MAX_SERVE, fetch)
        if outcome.served:
            result.hours = outcome.value  # type: ignore[assignment]
            result.data_as_of = outcome.fetched_at
        result.ok = outcome.served
        result.stale = outcome.stale
        result.error = outcome.error
        return result
