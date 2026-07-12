"""NWS point forecasts and winter alerts for the Sierra passes.

api.weather.gov, free, no key. NWS asks for an identifying User-Agent, which
every request sends. Gridpoint metadata is resolved once per pass and cached
for the process lifetime; forecasts and alerts use TTL caches with
stale-serve (via ca_roads.cache.TTLCache).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse

import httpx
from ca_roads.cache import TTLCache

from chaincheck import USER_AGENT
from chaincheck.passes import MountainPass

API_BASE = "https://api.weather.gov"
_API_HOST = urlparse(API_BASE).hostname or "api.weather.gov"
FORECAST_TTL = 15 * 60
FORECAST_MAX_SERVE = 3 * 60 * 60
ALERTS_TTL = 5 * 60
ALERTS_MAX_SERVE = 60 * 60

_WINTER_EVENTS = (
    "winter storm",
    "winter weather",
    "blizzard",
    "snow",
    "ice storm",
    "freezing rain",
    "high wind",
    "wind chill",
    "avalanche",
    "frost",
    "freeze",
)


@dataclass(frozen=True)
class ForecastPeriod:
    name: str
    start: datetime | None
    end: datetime | None
    is_daytime: bool
    temperature_f: int | None
    wind: str
    short: str
    detailed: str
    precip_chance: int | None


@dataclass(frozen=True)
class WinterAlert:
    id: str
    event: str
    severity: str
    headline: str
    onset: datetime | None
    ends: datetime | None
    description: str


@dataclass
class PassForecast:
    pass_id: str
    periods: list[ForecastPeriod] = field(default_factory=list)
    alerts: list[WinterAlert] = field(default_factory=list)
    data_as_of: datetime | None = None
    ok: bool = True
    stale: bool = False
    error: str | None = None


def _parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def parse_forecast(payload: dict) -> list[ForecastPeriod]:
    periods = []
    for p in payload.get("properties", {}).get("periods", []):
        chance = (p.get("probabilityOfPrecipitation") or {}).get("value")
        periods.append(
            ForecastPeriod(
                name=p.get("name", ""),
                start=_parse_dt(p.get("startTime")),
                end=_parse_dt(p.get("endTime")),
                is_daytime=bool(p.get("isDaytime", True)),
                temperature_f=p.get("temperature"),
                wind=f"{p.get('windSpeed', '')} {p.get('windDirection', '')}".strip(),
                short=p.get("shortForecast", ""),
                detailed=p.get("detailedForecast", ""),
                precip_chance=int(chance) if chance is not None else None,
            )
        )
    return periods


def is_winter_event(event: str) -> bool:
    lowered = event.lower()
    return any(w in lowered for w in _WINTER_EVENTS)


def parse_alerts(payload: dict) -> list[WinterAlert]:
    alerts = []
    for feature in payload.get("features", []):
        props = feature.get("properties", {})
        event = props.get("event", "")
        if not is_winter_event(event):
            continue
        alerts.append(
            WinterAlert(
                id=props.get("id", feature.get("id", "")),
                event=event,
                severity=props.get("severity", ""),
                headline=props.get("headline", ""),
                onset=_parse_dt(props.get("onset")),
                ends=_parse_dt(props.get("ends") or props.get("expires")),
                description=props.get("description", ""),
            )
        )
    return alerts


class NwsSource:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._cache = TTLCache()
        self._forecast_urls: dict[str, str] = {}

    async def _get_json(self, url: str, params: dict | None = None) -> dict:
        resp = await self._client.get(
            url,
            params=params,
            headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"},
            timeout=20.0,
        )
        resp.raise_for_status()
        return resp.json()

    async def _forecast_url(self, mtn_pass: MountainPass) -> str:
        url = self._forecast_urls.get(mtn_pass.id)
        if url:
            return url
        meta = await self._get_json(f"{API_BASE}/points/{mtn_pass.lat:.4f},{mtn_pass.lon:.4f}")
        url = meta["properties"]["forecast"]
        # This URL comes from the upstream response and is then fetched, so it
        # is an SSRF surface if the points endpoint is ever compromised or
        # spoofed. Only follow it when it stays on the NWS API host.
        host = urlparse(url).hostname or ""
        if host != _API_HOST and not host.endswith("." + _API_HOST):
            raise ValueError(f"refusing off-host forecast url: {host!r}")
        self._forecast_urls[mtn_pass.id] = url
        return url

    async def forecast(self, mtn_pass: MountainPass) -> PassForecast:
        result = PassForecast(pass_id=mtn_pass.id)

        async def fetch_periods() -> list[ForecastPeriod]:
            url = await self._forecast_url(mtn_pass)
            return parse_forecast(await self._get_json(url))

        async def fetch_alerts() -> list[WinterAlert]:
            payload = await self._get_json(
                f"{API_BASE}/alerts/active",
                params={"point": f"{mtn_pass.lat:.4f},{mtn_pass.lon:.4f}"},
            )
            return parse_alerts(payload)

        periods = await self._cache.get(
            ("forecast", mtn_pass.id), FORECAST_TTL, FORECAST_MAX_SERVE, fetch_periods
        )
        alerts = await self._cache.get(
            ("alerts", mtn_pass.id), ALERTS_TTL, ALERTS_MAX_SERVE, fetch_alerts
        )

        if periods.served:
            result.periods = periods.value  # type: ignore[assignment]
            result.data_as_of = periods.fetched_at
        if alerts.served:
            result.alerts = alerts.value  # type: ignore[assignment]
        result.stale = periods.stale or alerts.stale
        result.ok = periods.served
        result.error = periods.error or alerts.error
        return result
