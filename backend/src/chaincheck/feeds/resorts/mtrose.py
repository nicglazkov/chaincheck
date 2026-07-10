"""Mt Rose Ski Tahoe: .fx-card blocks (value in header, label in footer).

Base depth arrives as a range ("30-44\""); the report keeps both ends. Lift
status icons are lazy-loaded placeholders in raw HTML, so lift counts come
from the lift-name rows only when a real status can be read.
"""

from __future__ import annotations

import re

import httpx

from chaincheck.feeds.resorts.base import (
    ResortAdapter,
    ResortReport,
    get_page_text,
    parse_inches,
    parse_range_inches,
    strip_tags,
)

PAGE_URL = "https://skirose.com/snow-report/"

_CARD_RE = re.compile(
    r"fx-card-header[^>]*>(.*?)</[^>]+>.*?fx-card-footer[^>]*>(.*?)</", re.S
)
_LIFT_NAME_RE = re.compile(r"rose-name[^>]*>(.*?)</", re.S)


def parse_page(html: str) -> ResortReport:
    report = ResortReport(resort_id="mtrose", name="Mt Rose", source_url=PAGE_URL)
    cards: dict[str, str] = {}
    for value, label in _CARD_RE.findall(html):
        cards[strip_tags(label).lower()] = strip_tags(value)
    if not cards:
        raise ValueError("fx-card blocks not found")

    report.snow_24h_in = parse_inches(cards.get("new snow"))
    lo, hi = parse_range_inches(cards.get("base depth"))
    if lo is not None:
        report.base_depth_in = lo
        report.base_depth_max_in = hi
    season_lo, season_hi = parse_range_inches(cards.get("season total"))
    report.season_total_in = season_hi or season_lo

    names = [strip_tags(n) for n in _LIFT_NAME_RE.findall(html)]
    names = [n for n in names if n]
    if names:
        report.lifts_total = len(names)
        report.notes.append("lift status icons are lazy-loaded; open count unavailable")
    return report


class MtRoseAdapter(ResortAdapter):
    id = "mtrose"
    name = "Mt Rose"

    async def fetch(self, client: httpx.AsyncClient) -> ResortReport:
        return parse_page(await get_page_text(client, PAGE_URL))
