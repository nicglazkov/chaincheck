"""Resort adapter contract and shared parsing helpers.

Adapter discipline: each resort is one isolated adapter that can fail or be
disabled (env ``RESORTS_DISABLED``) without touching the others. Adapters use
an honest User-Agent, are polled at a gentle cadence (the registry caches
30 min), and report what they couldn't parse instead of inventing zeros:
``None`` means "not reported", ``0.0`` means the resort said zero.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

import httpx


@dataclass
class ResortReport:
    resort_id: str
    name: str
    snow_24h_in: float | None = None
    snow_48h_in: float | None = None
    snow_overnight_in: float | None = None
    storm_total_in: float | None = None
    base_depth_in: float | None = None  # midpoint when the resort reports a range
    base_depth_max_in: float | None = None
    season_total_in: float | None = None
    lifts_open: int | None = None
    lifts_total: int | None = None
    updated_at: datetime | None = None
    source_url: str = ""
    ok: bool = True
    stale: bool = False
    error: str | None = None
    notes: list[str] = field(default_factory=list)


class ResortAdapter(ABC):
    id: str
    name: str

    @abstractmethod
    async def fetch(self, client: httpx.AsyncClient) -> ResortReport:
        """One live pull. Raise on failure; the registry handles stale-serve."""


# Several WordPress resort sites 403 anything that doesn't look like a
# browser. This UA stays honest (names the bot and links the project) while
# using the conventional "compatible" form those filters accept.
SCRAPER_USER_AGENT = (
    "Mozilla/5.0 (compatible; ChainCheck/0.1; +https://github.com/nicglazkov/chaincheck)"
)


def headers() -> dict[str, str]:
    return {"User-Agent": SCRAPER_USER_AGENT}


_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def parse_inches(raw: object) -> float | None:
    """First number in a resort-formatted value ('12\"', '0.0 in', '--' -> None)."""
    if raw is None:
        return None
    if isinstance(raw, int | float):
        return float(raw)
    text = str(raw).strip()
    match = _NUM.search(text)
    return float(match.group(0)) if match else None


_UNSIGNED_NUM = re.compile(r"\d+(?:\.\d+)?")


def parse_range_inches(raw: object) -> tuple[float | None, float | None]:
    """A value like '30-44\"' -> (30.0, 44.0); single values -> (v, v).

    Depths are never negative, so the hyphen is always a range separator here.
    """
    if raw is None:
        return None, None
    nums = _UNSIGNED_NUM.findall(str(raw))
    if not nums:
        return None, None
    lo = float(nums[0])
    hi = float(nums[1]) if len(nums) > 1 else lo
    return lo, hi


def strip_tags(html: str) -> str:
    """Tags out, entities decoded, whitespace collapsed."""
    import html as html_mod

    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html_mod.unescape(text)).strip()
