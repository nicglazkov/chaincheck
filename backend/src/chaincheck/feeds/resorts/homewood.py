"""Homewood: weather-table with data-label cells.

In season the table carries snow columns (data-labels containing "12 hr",
"24 hr", "Current Depth", "Season Total"); off-season it degrades to
temperature/wind only, and this adapter reports None rather than zero.
Homewood's operating status has been in flux - verify each season the report
is actually maintained.
"""

from __future__ import annotations

import re

import httpx

from chaincheck.feeds.resorts.base import (
    ResortAdapter,
    ResortReport,
    headers,
    parse_inches,
    strip_tags,
)

PAGE_URL = "https://skihomewood.com/snowreport/"

_CELL_RE = re.compile(r'<td[^>]*data-label="([^"]*)"[^>]*>(.*?)</td>', re.S)
_OPEN_LIFTS_RE = re.compile(r"Open\s+Lifts[^0-9]{0,40}(\d+)", re.I | re.S)


def parse_page(html: str) -> ResortReport:
    report = ResortReport(resort_id="homewood", name="Homewood", source_url=PAGE_URL)
    cells = _CELL_RE.findall(html)
    if not cells and "weather-table" not in html:
        raise ValueError("weather table not found")

    # First matching cell wins: the Summit row comes before Base.
    def first(label_fragment: str) -> str | None:
        for label, value in cells:
            if label_fragment.lower() in strip_tags(label).lower():
                return strip_tags(value)
        return None

    report.snow_24h_in = parse_inches(first("24 hr"))
    report.snow_overnight_in = parse_inches(first("12 hr"))
    report.base_depth_in = parse_inches(first("current depth"))
    report.season_total_in = parse_inches(first("season total"))
    if report.snow_24h_in is None and report.base_depth_in is None:
        report.notes.append("no snow columns on page (off-season layout)")

    open_match = _OPEN_LIFTS_RE.search(html)
    if open_match:
        report.lifts_open = int(open_match.group(1))
    return report


class HomewoodAdapter(ResortAdapter):
    id = "homewood"
    name = "Homewood"

    async def fetch(self, client: httpx.AsyncClient) -> ResortReport:
        resp = await client.get(PAGE_URL, headers=headers(), timeout=30.0)
        resp.raise_for_status()
        return parse_page(resp.text)
