from ca_roads.models import Camera

from chaincheck.feeds import webcams


def make_camera(index: str, lat, lon, image_url="https://cwwp2.dot.ca.gov/x.jpg"):
    return Camera(
        index=index,
        district=3,
        route="I-80",
        county="Placer",
        nearby_place="Truckee",
        location_name="Donner Summit",
        direction="West",
        lat=lat,
        lon=lon,
        image_url=image_url,
        stream_url="",
    )


def test_sierra_filter_and_dedupe():
    cams = [
        make_camera("1", 39.34, -120.35),
        make_camera("2", 37.80, -122.30),  # Bay Area: out of box
        make_camera("3", 39.34, -120.35),  # duplicate image URL
        make_camera("4", None, -120.35),  # no coords
        make_camera("5", 39.10, -119.90, image_url=""),  # no image
        make_camera("6", 38.80, -120.03, image_url="https://cwwp2.dot.ca.gov/echo.jpg"),
    ]
    result = webcams.sierra_webcams(cams)
    assert [w.id for w in result] == ["1", "6"]
    assert result[0].name == "Donner Summit"
    assert result[0].image_url.startswith("https://cwwp2.dot.ca.gov/")
