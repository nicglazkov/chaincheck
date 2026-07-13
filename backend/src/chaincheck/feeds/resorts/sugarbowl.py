"""Sugar Bowl via their first-party conditions JSON (no auth)."""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from chaincheck.feeds.resorts.base import (
    ResortAdapter,
    ResortReport,
    fetch_json_capped,
    headers,
    parse_inches,
)

FEED_URL = "https://sugarbowl.com/services_json/update.json"
_PACIFIC = ZoneInfo("America/Los_Angeles")
_LIFT_STATUS_KEY = re.compile(r"^lift_\d+_status_text$")


def parse_feed(payload: dict) -> ResortReport:
    report = ResortReport(resort_id="sugarbowl", name="Sugar Bowl", source_url=FEED_URL)
    report.snow_24h_in = parse_inches(payload.get("conditions_snow_24hr_summit"))
    report.snow_overnight_in = parse_inches(payload.get("conditions_snow_overnight_summit"))
    report.storm_total_in = parse_inches(payload.get("conditions_storm_total_summit"))
    report.base_depth_in = parse_inches(payload.get("conditions_snowdepth_summit"))
    report.season_total_in = parse_inches(payload.get("conditions_snow_ytd_summit"))
    report.lifts_open = (
        int(v) if (v := parse_inches(payload.get("conditions_number_openlifts"))) is not None
        else None
    )

    lift_keys = [k for k in payload if _LIFT_STATUS_KEY.match(k)]
    if lift_keys:
        report.lifts_total = len(lift_keys)

    raw_update = payload.get("conditions_last_update")
    if raw_update:
        try:
            report.updated_at = datetime.strptime(
                str(raw_update), "%m/%d/%Y %I:%M %p"
            ).replace(tzinfo=_PACIFIC)
        except ValueError:
            report.notes.append(f"unparsed last update: {raw_update}")
    return report


class SugarBowlAdapter(ResortAdapter):
    id = "sugarbowl"
    name = "Sugar Bowl"

    async def fetch(self, client: httpx.AsyncClient) -> ResortReport:
        payload = await fetch_json_capped(client, FEED_URL, headers=headers(), timeout=25.0)
        return parse_feed(payload)
