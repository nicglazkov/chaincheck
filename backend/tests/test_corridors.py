from ca_roads.models import ChainControl, ChpIncident

from chaincheck import corridors


def make_control(route: str, lat: float, lon: float) -> ChainControl:
    return ChainControl(
        index="x",
        district=3,
        route=route,
        county="Placer",
        direction="East",
        location_name="somewhere",
        nearby_place="Truckee",
        lat=lat,
        lon=lon,
        in_service=True,
        status="R-1",
        status_description="",
        status_updated_at=None,
    )


def test_route_formats_normalize_to_same_corridor():
    donner = (39.34, -120.35)
    for route in ("I-80", "80", "I 80", "SR-80"):
        c = corridors.match_control(make_control(route, *donner))
        assert c is not None and c.id == "i80"


def test_sr89_matches():
    c = corridors.match_control(make_control("SR-89", 38.79, -119.95))
    assert c is not None and c.id == "sr89"


def test_outside_sierra_box_is_ignored():
    # I-80 in the Bay Area is not the Donner corridor.
    assert corridors.match_control(make_control("I-80", 37.82, -122.30)) is None


def test_unlisted_route_is_ignored():
    assert corridors.match_control(make_control("SR-49", 39.2, -120.9)) is None


def make_incident(location: str, area: str, lat: float, lon: float) -> ChpIncident:
    return ChpIncident(
        id="1",
        log_type="Trfc Collision-No Inj",
        location=location,
        area=area,
        lat=lat,
        lon=lon,
        reported_at=None,
    )


def test_incident_matched_by_location_text():
    inc = make_incident("I80 E / Donner Pass Rd", "Truckee", 39.32, -120.32)
    c = corridors.match_incident(inc)
    assert c is not None and c.id == "i80"


def test_incident_without_route_mention_is_unmatched():
    inc = make_incident("Main St / 2nd Ave", "Truckee", 39.32, -120.18)
    assert corridors.match_incident(inc) is None


def test_incident_outside_box_is_unmatched():
    inc = make_incident("I80 E / University Ave", "Berkeley", 37.87, -122.30)
    assert corridors.match_incident(inc) is None
