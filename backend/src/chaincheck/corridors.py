"""Sierra corridor definitions and record filtering.

A corridor is one drivable mountain crossing (I-80 over Donner, US-50 over
Echo, ...). Feed records are matched by route number plus a Sierra bounding
box rather than by Caltrans district lists: districts 3, 9, and 10 all touch
the Tahoe area and box-matching survives district boundary quirks.
"""

from __future__ import annotations

from dataclasses import dataclass

from ca_roads.models import ChainControl, ChpIncident, LaneClosure

# Lat/lon box that covers the Tahoe Sierra crossings from Yuba Gap to Monitor
# Pass. Deliberately generous: corridor route numbers do the fine filtering.
SIERRA_BOX = (38.2, -121.2, 39.8, -119.4)  # (south, west, north, east)

# Caltrans districts whose feeds can carry Sierra records.
SIERRA_DISTRICTS = (3, 9, 10)


@dataclass(frozen=True)
class Corridor:
    id: str
    name: str
    route_number: str  # as it appears in feed ``route`` fields
    display_route: str
    description: str


CORRIDORS: tuple[Corridor, ...] = (
    Corridor(
        id="i80",
        name="I-80 Donner Summit",
        route_number="80",
        display_route="I-80",
        description="Sacramento to Truckee/Reno over Donner Summit",
    ),
    Corridor(
        id="us50",
        name="US-50 Echo Summit",
        route_number="50",
        display_route="US-50",
        description="Sacramento to South Lake Tahoe over Echo Summit",
    ),
    Corridor(
        id="sr88",
        name="SR-88 Carson Pass",
        route_number="88",
        display_route="SR-88",
        description="Jackson to Kirkwood over Carson Pass",
    ),
    Corridor(
        id="sr89",
        name="SR-89 Luther / Monitor",
        route_number="89",
        display_route="SR-89",
        description="Tahoe west shore, Luther Pass and Monitor Pass",
    ),
    Corridor(
        id="sr267",
        name="SR-267 Brockway Summit",
        route_number="267",
        display_route="SR-267",
        description="Truckee to Kings Beach over Brockway Summit",
    ),
    Corridor(
        id="sr28",
        name="SR-28 North Shore",
        route_number="28",
        display_route="SR-28",
        description="Tahoe City to Crystal Bay along the north shore",
    ),
    Corridor(
        id="sr20",
        name="SR-20 Yuba Pass",
        route_number="20",
        display_route="SR-20",
        description="Grass Valley to I-80 at Yuba Gap",
    ),
)

CORRIDORS_BY_ID: dict[str, Corridor] = {c.id: c for c in CORRIDORS}
_ROUTE_TO_CORRIDOR: dict[str, Corridor] = {c.route_number: c for c in CORRIDORS}


def _in_box(lat: float, lon: float) -> bool:
    south, west, north, east = SIERRA_BOX
    return south <= lat <= north and west <= lon <= east


def _route_number(raw: str) -> str:
    """Normalize feed route strings ("SR-89", "US 50", "I-80", "80") to digits."""
    return "".join(ch for ch in raw if ch.isdigit()).lstrip("0") or raw.strip()


def corridor_for(route: str, lat: float, lon: float) -> Corridor | None:
    """Corridor owning a feed record, or None when out of scope."""
    if not _in_box(lat, lon):
        return None
    return _ROUTE_TO_CORRIDOR.get(_route_number(route))


def match_control(record: ChainControl) -> Corridor | None:
    return corridor_for(record.route, record.lat, record.lon)


def match_closure(record: LaneClosure) -> Corridor | None:
    return corridor_for(record.route, record.begin_lat, record.begin_lon)


def match_incident(record: ChpIncident) -> Corridor | None:
    """CHP incidents carry a free-text location, not a route field, so they are
    matched to the nearest corridor only when they sit inside the Sierra box
    and mention the route in the location text."""
    if not _in_box(record.lat, record.lon):
        return None
    text = f"{record.location} {record.area}".upper()
    for corridor in CORRIDORS:
        needles = (
            f"I{corridor.route_number} ",
            f"I-{corridor.route_number}",
            f"US{corridor.route_number}",
            f"US-{corridor.route_number}",
            f"SR{corridor.route_number}",
            f"SR-{corridor.route_number}",
            f"HWY {corridor.route_number}",
            f"HWY{corridor.route_number}",
            f"RT {corridor.route_number}",
        )
        if any(n in text for n in needles):
            return corridor
    return None
