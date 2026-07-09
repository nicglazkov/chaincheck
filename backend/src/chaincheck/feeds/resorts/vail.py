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

TERRAIN_PATH = "/the-mountain/mountain-conditions/terrain-and-lift-status.aspx"


def parse_terrain_feed(html: str) -> tuple[int, int]:
    """(lifts_open, lifts_total) from the embedded terrain feed object."""
    match = _FEED_RE.search(html)
    if not match:
        raise ValueError("TerrainStatusFeed not found in page")
    feed = json.loads(match.group(1))
    lifts = feed.get("Lifts", [])
    if not lifts:
        raise ValueError("TerrainStatusFeed has no lifts")
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
        report.notes.append("snow totals not yet wired for Vail resorts")
        return report


def heavenly() -> VailAdapter:
    return VailAdapter("heavenly", "Heavenly", "www.skiheavenly.com")


def northstar() -> VailAdapter:
    return VailAdapter("northstar", "Northstar California", "www.northstarcalifornia.com")


def kirkwood() -> VailAdapter:
    return VailAdapter("kirkwood", "Kirkwood", "www.kirkwood.com")
