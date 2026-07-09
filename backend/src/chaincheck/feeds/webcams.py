"""Sierra roadside webcams from the Caltrans CCTV feed.

Official snapshot URLs are linked with attribution, never rehosted. The feed
flags in-service cameras but some still serve an offline placeholder; the
client treats a failed image load as "camera offline".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ca_roads.models import Camera

from chaincheck import corridors


@dataclass(frozen=True)
class Webcam:
    id: str
    name: str
    route: str
    direction: str
    nearby: str
    lat: float
    lon: float
    image_url: str


def sierra_webcams(cameras: list[Camera]) -> list[Webcam]:
    """In-box cameras with usable coordinates and snapshot URLs."""
    webcams = []
    seen: set[str] = set()
    for cam in cameras:
        if cam.lat is None or cam.lon is None or not cam.image_url:
            continue
        south, west, north, east = corridors.SIERRA_BOX
        if not (south <= cam.lat <= north and west <= cam.lon <= east):
            continue
        key = cam.image_url
        if key in seen:
            continue
        seen.add(key)
        webcams.append(
            Webcam(
                id=cam.index or key,
                name=cam.location_name or cam.nearby_place or cam.route,
                route=cam.route,
                direction=cam.direction,
                nearby=cam.nearby_place,
                lat=cam.lat,
                lon=cam.lon,
                image_url=cam.image_url,
            )
        )
    return webcams


@dataclass
class WebcamsResult:
    webcams: list[Webcam]
    data_as_of: datetime | None
    ok: bool
    stale: bool
