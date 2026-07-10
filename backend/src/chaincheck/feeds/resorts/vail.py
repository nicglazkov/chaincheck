"""Heavenly, Northstar, and Kirkwood (Vail Resorts, shared platform).

The terrain-status page embeds ``FR.TerrainStatusFeed = {...}`` with a Lifts
array whose integer Status indexes ['closed','open','hold','scheduled'].
Vail fronts these sites with bot protection that tends to block datacenter
IPs, so this adapter is built to degrade: any block or parse failure surfaces
as a per-resort error, never as invented data.
"""

from __future__ import annotations

import json
import re

import httpx

from chaincheck.feeds.resorts.base import ResortAdapter, ResortReport, headers

_STATUSES = ("closed", "open", "hold", "scheduled")
_OPEN = {"open", "scheduled"}
_FEED_RE = re.compile(r"FR\.TerrainStatusFeed\s*=\s*(\{.*?\})\s*;", re.S)
_SNOW_RE = re.compile(r"FR\.snowReportData\s*=\s*(\{.*?\})\s*;", re.S)

TERRAIN_PATH = "/the-mountain/mountain-conditions/terrain-and-lift-status.aspx"
SNOW_PATH = "/the-mountain/mountain-conditions/snow-and-weather-report.aspx"


def parse_snow_report(html: str) -> dict:
    """Snowfall/base figures from the embedded FR.snowReportData object."""
    match = _SNOW_RE.search(html)
    if not match:
        raise ValueError("snowReportData not found in page")
    data = json.loads(match.group(1))

    def inches(key: str) -> float | None:
        raw = (data.get(key) or {}).get("Inches")
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    return {
        "snow_overnight_in": inches("OvernightSnowfall"),
        "snow_24h_in": inches("TwentyFourHourSnowfall"),
        "snow_48h_in": inches("FortyEightHourSnowfall"),
        "base_depth_in": inches("BaseDepth"),
        "season_total_in": inches("CurrentSeason"),
    }


def parse_terrain_feed(html: str) -> tuple[int, int]:
    """(lifts_open, lifts_total) from the embedded terrain feed object.

    An empty lift list is valid data (the resort de-lists lifts off-season),
    distinct from the feed object missing entirely (bot wall / page change).
    """
    match = _FEED_RE.search(html)
    if not match:
        raise ValueError("TerrainStatusFeed not found in page")
    feed = json.loads(match.group(1))
    lifts = feed.get("Lifts", [])
    total = len(lifts)
    open_count = 0
    for lift in lifts:
        status = lift.get("Status")
        if isinstance(status, int) and 0 <= status < len(_STATUSES):
            if _STATUSES[status] in _OPEN:
                open_count += 1
        elif str(status).lower() in _OPEN:
            open_count += 1
    return open_count, total


class VailAdapter(ResortAdapter):
    def __init__(self, resort_id: str, name: str, host: str) -> None:
        self.id = resort_id
        self.name = name
        self.host = host

    async def fetch(self, client: httpx.AsyncClient) -> ResortReport:
        url = f"https://{self.host}{TERRAIN_PATH}"
        report = ResortReport(resort_id=self.id, name=self.name, source_url=url)
        resp = await client.get(
            url,
            headers={
                **headers(),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        if "TerrainStatusFeed" not in resp.text:
            # Bot wall serves an interstitial with a 200; treat it as a failure
            # so the registry stale-serves instead of reporting zeros.
            raise ValueError("blocked or unexpected page (no terrain feed present)")
        report.lifts_open, report.lifts_total = parse_terrain_feed(resp.text)
        if report.lifts_total == 0:
            report.notes.append("no lifts listed (off-season)")

        try:
            snow_resp = await client.get(
                f"https://{self.host}{SNOW_PATH}",
                headers={
                    **headers(),
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                timeout=30.0,
            )
            snow_resp.raise_for_status()
            snow = parse_snow_report(snow_resp.text)
            report.snow_overnight_in = snow["snow_overnight_in"]
            report.snow_24h_in = snow["snow_24h_in"]
            report.snow_48h_in = snow["snow_48h_in"]
            report.base_depth_in = snow["base_depth_in"]
            report.season_total_in = snow["season_total_in"]
        except Exception as exc:  # noqa: BLE001 - snow is best-effort extra
            report.notes.append(f"snow report unavailable: {type(exc).__name__}")
        return report


def heavenly() -> VailAdapter:
    return VailAdapter("heavenly", "Heavenly", "www.skiheavenly.com")


def northstar() -> VailAdapter:
    return VailAdapter("northstar", "Northstar California", "www.northstarcalifornia.com")


def kirkwood() -> VailAdapter:
    return VailAdapter("kirkwood", "Kirkwood", "www.kirkwood.com")
