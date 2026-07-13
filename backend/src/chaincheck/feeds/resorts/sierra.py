"""Sierra-at-Tahoe: server-rendered WordPress pages, no JSON route.

Snow numbers come from the weather/snow report page (labels like "24 Hour
Snowfall"); lift status rows live under [data-panel="lift-status"] as h4
names each followed by a status element.
"""

from __future__ import annotations

import re

import httpx

from chaincheck.feeds.resorts.base import (
    ResortAdapter,
    ResortReport,
    fetch_text_capped,
    headers,
    strip_tags,
)

SNOW_URL = "https://sierraattahoe.com/weather-snow-report/"
LIFTS_URL = "https://sierraattahoe.com/lifts-trails-grooming/"

_LABEL_VALUE_RE = re.compile(
    r"(24 Hour Snowfall|48 Hour Snowfall|Storm Total|Base Depth|Season Total)"
    r"(.{0,400}?)(-?\d+(?:\.\d+)?)\s*(?:&quot;|\"|&#8243;|in\b|”)",
    re.S | re.I,
)
# Each lift is a WP custom post: <li class="wp-block-post ... sierra_lift ...">
_LIFT_LI_RE = re.compile(r'<li[^>]*\bsierra_lift\b[^>]*>(.*?)</li>', re.S)
_STATUS_WORD_RE = re.compile(r"\b(open|closed|on hold|hold|scheduled|standby)\b", re.I)


def parse_snow_page(html: str, report: ResortReport) -> None:
    found: dict[str, float] = {}
    for label, _, number in _LABEL_VALUE_RE.findall(html):
        key = label.lower()
        if key not in found:
            found[key] = float(number)
    report.snow_24h_in = found.get("24 hour snowfall")
    report.snow_48h_in = found.get("48 hour snowfall")
    report.storm_total_in = found.get("storm total")
    report.base_depth_in = found.get("base depth")
    report.season_total_in = found.get("season total")
    if not found:
        report.notes.append("no snow figures found on report page")


def parse_lifts_page(html: str, report: ResortReport) -> None:
    statuses = []
    for block in _LIFT_LI_RE.findall(html):
        text = strip_tags(block)
        match = _STATUS_WORD_RE.search(text)
        statuses.append(match.group(1).lower() if match else "unknown")
    if statuses:
        report.lifts_total = len(statuses)
        report.lifts_open = sum(1 for s in statuses if s == "open")


class SierraAtTahoeAdapter(ResortAdapter):
    id = "sierra"
    name = "Sierra-at-Tahoe"

    async def fetch(self, client: httpx.AsyncClient) -> ResortReport:
        report = ResortReport(resort_id=self.id, name=self.name, source_url=SNOW_URL)
        snow_html = await fetch_text_capped(client, SNOW_URL, headers=headers(), timeout=30.0)
        parse_snow_page(snow_html, report)
        try:
            lifts_html = await fetch_text_capped(client, LIFTS_URL, headers=headers(), timeout=30.0)
            parse_lifts_page(lifts_html, report)
        except httpx.HTTPError as exc:
            report.notes.append(f"lifts page unavailable: {type(exc).__name__}")
        return report
