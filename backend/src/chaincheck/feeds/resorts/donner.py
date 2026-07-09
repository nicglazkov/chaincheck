"""Donner Ski Ranch: manually written lift status prose on Squarespace.

``?format=json`` returns the page JSON; chair statuses are regexed out of the
content HTML ("Chair 1: CLOSED FOR THE SEASON"). No structured snow data
exists on the site. Their robots.txt blocks AI-crawler user agents; this is a
conventional low-frequency conditions fetcher with an honest UA, polled at
the registry's gentle cadence, and easy to disable via RESORTS_DISABLED.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

import httpx

from chaincheck.feeds.resorts.base import ResortAdapter, ResortReport, headers, strip_tags

PAGE_URL = "https://www.donnerskiranch.com/liftstatus"
TOTAL_CHAIRS = 6

# Status capture stops before the next "Chair N" clause so one long line
# doesn't swallow the chairs that follow it.
_CHAIR_RE = re.compile(
    r"Chairs?\s+([\d,\s]+(?:and\s+\d+)?)\s*:?\s*((?:(?!Chairs?\s+\d)[^.<\n]){0,80})",
    re.I,
)


def parse_page_json(payload: dict) -> ResortReport:
    report = ResortReport(
        resort_id="donner", name="Donner Ski Ranch", source_url=PAGE_URL
    )
    content = str(payload.get("mainContent", ""))
    text = strip_tags(content)
    if not text:
        raise ValueError("empty mainContent")

    statuses: dict[int, str] = {}
    for numbers, status in _CHAIR_RE.findall(text):
        chairs = [int(n) for n in re.findall(r"\d+", numbers)]
        for chair in chairs:
            if 1 <= chair <= TOTAL_CHAIRS and chair not in statuses:
                statuses[chair] = status.strip().lower()
    if statuses:
        report.lifts_total = TOTAL_CHAIRS
        report.lifts_open = sum(
            1 for s in statuses.values() if "open" in s and "not open" not in s
        )
    else:
        report.notes.append("no chair statuses found in page text")

    updated = payload.get("item", {}).get("updatedOn") or payload.get("updatedOn")
    if isinstance(updated, int | float) and updated > 0:
        report.updated_at = datetime.fromtimestamp(updated / 1000, tz=UTC)
    report.notes.append("resort publishes no structured snow totals")
    return report


class DonnerSkiRanchAdapter(ResortAdapter):
    id = "donner"
    name = "Donner Ski Ranch"

    async def fetch(self, client: httpx.AsyncClient) -> ResortReport:
        resp = await client.get(
            PAGE_URL, params={"format": "json"}, headers=headers(), timeout=30.0
        )
        resp.raise_for_status()
        return parse_page_json(resp.json())
