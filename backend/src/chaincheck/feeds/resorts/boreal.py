"""Boreal via the POWDR day-of-resort API.

Lift status is solid year-round. Snow totals have no confirmed endpoint yet
(the sensors feed is empty off-season); the adapter reports lifts and leaves
snow fields None with a note until the in-season recheck.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from chaincheck.feeds.resorts.base import ResortAdapter, ResortReport, headers

LIFTS_URL = "https://api.rideboreal.com/api/v1/dor/drupal/lifts"


def parse_lifts(payload: list) -> tuple[int, int, datetime | None]:
    total = len(payload)
    open_count = sum(1 for lift in payload if str(lift.get("status", "")).lower() == "open")
    newest = None
    for lift in payload:
        updated = lift.get("updated")
        if isinstance(updated, int | float) and updated > 0:
            when = datetime.fromtimestamp(updated, tz=UTC)
            newest = max(newest, when) if newest else when
    return open_count, total, newest


class BorealAdapter(ResortAdapter):
    id = "boreal"
    name = "Boreal"

    async def fetch(self, client: httpx.AsyncClient) -> ResortReport:
        report = ResortReport(resort_id=self.id, name=self.name, source_url=LIFTS_URL)
        resp = await client.get(LIFTS_URL, headers=headers(), timeout=25.0)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, list):
            raise ValueError("unexpected lifts payload shape")
        report.lifts_open, report.lifts_total, report.updated_at = parse_lifts(payload)
        report.notes.append("snow totals not yet available from this source")
        return report
