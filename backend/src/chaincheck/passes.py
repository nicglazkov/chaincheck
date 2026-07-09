"""Sierra pass definitions used for forecasts and route grouping.

Coordinates are the highway summit points (close enough for NWS gridpoint and
Open-Meteo point forecasts). NV-side passes get forecasts but have no Caltrans
chain feed; their chain status comes from whatever corridor data exists.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MountainPass:
    id: str
    name: str
    route: str  # highway designation as displayed ("I-80", "US-50", "SR-88")
    route_number: str  # bare route number as it appears in Caltrans feeds
    state: str  # "CA" | "NV"
    lat: float
    lon: float
    elevation_ft: int
    corridor_id: str


PASSES: tuple[MountainPass, ...] = (
    MountainPass(
        id="donner",
        name="Donner Summit",
        route="I-80",
        route_number="80",
        state="CA",
        lat=39.3417,
        lon=-120.3465,
        elevation_ft=7239,
        corridor_id="i80",
    ),
    MountainPass(
        id="echo",
        name="Echo Summit",
        route="US-50",
        route_number="50",
        state="CA",
        lat=38.8146,
        lon=-120.0359,
        elevation_ft=7382,
        corridor_id="us50",
    ),
    MountainPass(
        id="carson",
        name="Carson Pass",
        route="SR-88",
        route_number="88",
        state="CA",
        lat=38.6946,
        lon=-119.9890,
        elevation_ft=8574,
        corridor_id="sr88",
    ),
    MountainPass(
        id="luther",
        name="Luther Pass",
        route="SR-89",
        route_number="89",
        state="CA",
        lat=38.7868,
        lon=-119.9505,
        elevation_ft=7740,
        corridor_id="sr89",
    ),
    MountainPass(
        id="monitor",
        name="Monitor Pass",
        route="SR-89",
        route_number="89",
        state="CA",
        lat=38.6743,
        lon=-119.6157,
        elevation_ft=8314,
        corridor_id="sr89",
    ),
    MountainPass(
        id="brockway",
        name="Brockway Summit",
        route="SR-267",
        route_number="267",
        state="CA",
        lat=39.2620,
        lon=-120.0669,
        elevation_ft=7179,
        corridor_id="sr267",
    ),
    MountainPass(
        id="mtrose",
        name="Mt Rose Summit",
        route="SR-431",
        route_number="431",
        state="NV",
        lat=39.3145,
        lon=-119.8977,
        elevation_ft=8911,
        corridor_id="sr431",
    ),
    MountainPass(
        id="spooner",
        name="Spooner Summit",
        route="US-50",
        route_number="50",
        state="NV",
        lat=39.1043,
        lon=-119.8955,
        elevation_ft=7146,
        corridor_id="us50",
    ),
)

PASSES_BY_ID: dict[str, MountainPass] = {p.id: p for p in PASSES}
