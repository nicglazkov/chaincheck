"""Diamond Peak: server-rendered snow drawer on every page.

Two <dl class="snow-report-drawer__list"> lists of <dt>value</dt><dd>label</dd>
pairs: Overnight / 24HR / Storm Total, then Base / Peak / Season Total.
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

PAGE_URL = "https://www.diamondpeak.com/the-mountain/mountain-report/"

_PAIR_RE = re.compile(r"<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>", re.S)
# Primary: the lift-header class the status section uses; fallback: h3 names.
_LIFT_CLASS_RE = re.compile(r'class="[^"]*lift-header[^"]*"[^>]*>(.*?)<', re.S)
_LIFT_HEADER_RE = re.compile(r"<h3[^>]*>([^<]*(?:Lift|Chair)[^<]*)</h3>")


def parse_page(html: str) -> ResortReport:
    report = ResortReport(resort_id="diamondpeak", name="Diamond Peak", source_url=PAGE_URL)
    drawer_match = re.search(r"snow-report-drawer.*?</div>\s*</div>", html, re.S)
    scope = drawer_match.group(0) if drawer_match else html

    values: dict[str, str] = {}
    for value, label in _PAIR_RE.findall(scope):
        values[strip_tags(label).lower()] = strip_tags(value)
    if not values:
        raise ValueError("snow drawer not found")

    report.snow_overnight_in = parse_inches(values.get("overnight"))
    report.snow_24h_in = parse_inches(values.get("24hr"))
    report.storm_total_in = parse_inches(values.get("storm total"))
    report.base_depth_in = parse_inches(values.get("base"))
    report.season_total_in = parse_inches(values.get("season total"))

    lifts = _LIFT_CLASS_RE.findall(html) or _LIFT_HEADER_RE.findall(html)
    if lifts:
        report.lifts_total = len(lifts)
        report.notes.append("per-lift status parsing not wired; totals only")
    return report


class DiamondPeakAdapter(ResortAdapter):
    id = "diamondpeak"
    name = "Diamond Peak"

    async def fetch(self, client: httpx.AsyncClient) -> ResortReport:
        resp = await client.get(PAGE_URL, headers=headers(), timeout=30.0)
        resp.raise_for_status()
        return parse_page(resp.text)
