"""Palisades Tahoe via the MtnPowder feed (the platform behind their own site).

No auth. Snow numbers live in SnowReport.MidMountainArea (strings, "--" when
unreported); lifts are nested per MountainAreas[].Lifts with a StatusEnglish
slug.
"""

from __future__ import annotations

from datetime import datetime

import httpx

from chaincheck.feeds.resorts.base import ResortAdapter, ResortReport, headers, parse_inches

FEED_URL = "https://mtnpowder.com/feed"

_OPEN_STATUSES = {"open", "scheduled"}


def parse_feed(payload: dict, resort_id: str, name: str) -> ResortReport:
    report = ResortReport(resort_id=resort_id, name=name, source_url=FEED_URL)
    snow = payload.get("SnowReport", {})
    mid = snow.get("MidMountainArea", {}) or snow.get("BaseArea", {})
    report.snow_24h_in = parse_inches(mid.get("Last24HoursIn"))
    report.snow_48h_in = parse_inches(mid.get("Last48HoursIn"))
    report.base_depth_in = parse_inches(mid.get("BaseIn"))
    report.storm_total_in = parse_inches(snow.get("StormTotalIn"))
    report.season_total_in = parse_inches(snow.get("SeasonTotalIn"))

    lifts_total = 0
    lifts_open = 0
    for area in payload.get("MountainAreas", []):
        for lift in area.get("Lifts", []):
            lifts_total += 1
            if str(lift.get("StatusEnglish", "")).lower() in _OPEN_STATUSES:
                lifts_open += 1
    if lifts_total:
        report.lifts_total = lifts_total
        report.lifts_open = lifts_open

    raw_update = snow.get("LastUpdate") or payload.get("LastUpdate")
    if raw_update:
        try:
            report.updated_at = datetime.fromisoformat(str(raw_update))
        except ValueError:
            report.notes.append(f"unparsed LastUpdate: {raw_update}")
    return report


class PalisadesAdapter(ResortAdapter):
    id = "palisades"
    name = "Palisades Tahoe"
    mtnpowder_resort_id = "61"

    async def fetch(self, client: httpx.AsyncClient) -> ResortReport:
        resp = await client.get(
            FEED_URL,
            params={"resortId": self.mtnpowder_resort_id},
            headers=headers(),
            timeout=25.0,
        )
        resp.raise_for_status()
        return parse_feed(resp.json(), self.id, self.name)
