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
    # Hand-traced highway waypoints for map polylines, coarse on purpose:
    # accurate at the regional zooms the app uses, not survey data. A corridor
    # can have several disjoint segments (SR-89 exists in three pieces here).
    segments: tuple[tuple[tuple[float, float], ...], ...] = ()


CORRIDORS: tuple[Corridor, ...] = (
    Corridor(
        id="i80",
        name="I-80 Donner Summit",
        route_number="80",
        display_route="I-80",
        description="Sacramento to Truckee/Reno over Donner Summit",
        segments=(((38.8966, -121.0769), (39.01, -120.96), (39.1007, -120.9533), (39.145, -120.86), (39.205, -120.77), (39.247, -120.728), (39.2986, -120.6664), (39.3168, -120.6014), (39.3138, -120.5461), (39.3161, -120.4439), (39.3239, -120.38), (39.3417, -120.3465), (39.3239, -120.265), (39.328, -120.1833), (39.352, -120.115), (39.3947, -120.0219), (39.44, -120.009), (39.4986, -120.0027),),),  # noqa: E501
    ),
    Corridor(
        id="us50",
        name="US-50 Echo Summit",
        route_number="50",
        display_route="US-50",
        description="Sacramento to South Lake Tahoe over Echo Summit",
        segments=(((38.7296, -120.7985), (38.7452, -120.6721), (38.7621, -120.586), (38.766, -120.462), (38.7773, -120.2955), (38.8034, -120.124), (38.8146, -120.0359), (38.8574, -119.9962), (38.899, -119.989), (38.9399, -119.9772), (38.9609, -119.9391), (39.0446, -119.949), (39.101, -119.892),),),  # noqa: E501
    ),
    Corridor(
        id="sr88",
        name="SR-88 Carson Pass",
        route_number="88",
        display_route="SR-88",
        description="Jackson to Kirkwood over Carson Pass",
        segments=(((38.3488, -120.7741), (38.4135, -120.659), (38.4322, -120.5715), (38.477, -120.3737), (38.55, -120.26), (38.63, -120.18), (38.6683, -120.1206), (38.685, -120.0654), (38.6946, -119.989), (38.73, -119.95), (38.7724, -119.9046), (38.7777, -119.8324),),),  # noqa: E501
    ),
    Corridor(
        id="sr89",
        name="SR-89 Luther / Monitor",
        route_number="89",
        display_route="SR-89",
        description="Tahoe west shore, Luther Pass and Monitor Pass",
        segments=(((38.7724, -119.9046), (38.7868, -119.9505), (38.82, -119.98), (38.8574, -119.9962),), ((38.9312, -120.0058), (38.953, -120.11), (39.0, -120.12), (39.0857, -120.16), (39.14, -120.155), (39.1677, -120.1436), (39.199, -120.205), (39.26, -120.198), (39.327, -120.207),), ((38.7724, -119.9046), (38.6944, -119.7787), (38.6743, -119.6157), (38.6079, -119.5443),),),  # noqa: E501
    ),
    Corridor(
        id="sr267",
        name="SR-267 Brockway Summit",
        route_number="267",
        display_route="SR-267",
        description="Truckee to Kings Beach over Brockway Summit",
        segments=(((39.3239, -120.145), (39.3, -120.115), (39.262, -120.0669), (39.238, -120.0264),),),  # noqa: E501
    ),
    Corridor(
        id="sr28",
        name="SR-28 North Shore",
        route_number="28",
        display_route="SR-28",
        description="Tahoe City to Crystal Bay along the north shore",
        segments=(((39.1677, -120.1436), (39.2263, -120.081), (39.238, -120.0264), (39.2337, -120.002),),),  # noqa: E501
    ),
    Corridor(
        id="sr20",
        name="SR-20 Yuba Pass",
        route_number="20",
        display_route="SR-20",
        description="Grass Valley to I-80 at Yuba Gap",
        segments=(((39.2191, -121.0608), (39.2616, -121.0161), (39.3, -120.86), (39.3242, -120.6535),),),  # noqa: E501
    ),
)

def _load_snapped_geometry() -> None:
    """Replace hand-traced segments with road-snapped geometry when the baked
    data file is present (generated once via OSRM; see docs in repo)."""
    global CORRIDORS
    import json
    from importlib import resources

    try:
        raw = (
            resources.files("chaincheck").joinpath("data/corridor_geometry.json").read_text()
        )
    except (FileNotFoundError, ModuleNotFoundError):
        return
    geometry = json.loads(raw)
    updated = []
    for corridor in CORRIDORS:
        segs = geometry.get(corridor.id)
        if segs:
            corridor = Corridor(
                id=corridor.id,
                name=corridor.name,
                route_number=corridor.route_number,
                display_route=corridor.display_route,
                description=corridor.description,
                segments=tuple(
                    tuple((lat, lon) for lat, lon in seg) for seg in segs
                ),
            )
        updated.append(corridor)
    CORRIDORS = tuple(updated)


_load_snapped_geometry()

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
