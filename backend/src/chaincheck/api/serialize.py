"""Plain-dict serialization for API responses.

Every payload that reflects feed data carries ``as_of``/``stale`` so clients
can show honest timestamps when mountain connectivity leaves them on cached
state.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ca_roads.models import ChainControl, ChpIncident, LaneClosure

from chaincheck.feeds.nws import ForecastPeriod, PassForecast, WinterAlert
from chaincheck.feeds.openmeteo import SnowOutlook
from chaincheck.feeds.resorts.base import ResortReport
from chaincheck.feeds.roads import CorridorRoads, SierraSnapshot
from chaincheck.passes import MountainPass
from chaincheck.tiers import TIER_MEANING, control_tier, tier_label


def _iso(dt: datetime | None) -> str | None:
    return dt.astimezone(UTC).isoformat() if dt else None


def control_dict(c: ChainControl) -> dict:
    tier = control_tier(c)
    return {
        "route": c.route,
        "direction": c.direction,
        "location": c.location_name,
        "nearby": c.nearby_place,
        "lat": c.lat,
        "lon": c.lon,
        "status": c.status,
        "tier": int(tier),
        "tier_label": tier_label(tier),
        "description": c.status_description,
        "updated_at": _iso(c.status_updated_at),
    }


def closure_dict(c: LaneClosure) -> dict:
    return {
        "route": c.route,
        "direction": c.direction,
        "location": c.location_name,
        "nearby": c.nearby_place,
        "type": c.type_of_closure,
        "work": c.type_of_work,
        "lanes_closed": c.lanes_closed,
        "total_lanes": c.total_lanes,
        "delay_minutes": c.estimated_delay_minutes,
        "begin": {"lat": c.begin_lat, "lon": c.begin_lon},
        "end": {"lat": c.end_lat, "lon": c.end_lon},
    }


def incident_dict(i: ChpIncident) -> dict:
    return {
        "id": i.id,
        "type": i.log_type,
        "location": i.location,
        "area": i.area,
        "lat": i.lat,
        "lon": i.lon,
        "reported_at": _iso(i.reported_at),
    }


def corridor_summary(roads: CorridorRoads) -> dict:
    return {
        "id": roads.corridor.id,
        "name": roads.corridor.name,
        "route": roads.corridor.display_route,
        "description": roads.corridor.description,
        "tier": int(roads.tier),
        "tier_label": tier_label(roads.tier),
        "tier_meaning": TIER_MEANING[roads.tier],
        "controls": len([c for c in roads.controls if control_tier(c) > 0]),
        "closures": len(roads.closures),
        "incidents": len(roads.incidents),
    }


def corridor_detail(roads: CorridorRoads) -> dict:
    payload = corridor_summary(roads)
    payload["control_points"] = [control_dict(c) for c in roads.controls]
    payload["closure_list"] = [closure_dict(c) for c in roads.closures]
    payload["incident_list"] = [incident_dict(i) for i in roads.incidents]
    return payload


# Raw feed errors embed upstream URLs, library exception types, and (from a
# hostile upstream) reflected text. Clients only need to know a source is
# degraded, so we publish the source label and a generic status, never the
# detail. The detail stays in server logs.
def _public_note(note: str) -> str:
    source = note.split(":", 1)[0].strip()
    return f"{source}: temporarily unavailable" if source else "a feed is temporarily unavailable"


def snapshot_health(snapshot: SierraSnapshot) -> dict:
    return {
        "ok": snapshot.ok,
        "stale": snapshot.stale,
        "as_of": _iso(snapshot.data_as_of),
        "notes": [_public_note(n) for n in snapshot.notes],
    }


def period_dict(p: ForecastPeriod) -> dict:
    return {
        "name": p.name,
        "start": _iso(p.start),
        "end": _iso(p.end),
        "is_daytime": p.is_daytime,
        "temperature_f": p.temperature_f,
        "wind": p.wind,
        "short": p.short,
        "detailed": p.detailed,
        "precip_chance": p.precip_chance,
    }


def alert_dict(a: WinterAlert) -> dict:
    return {
        "id": a.id,
        "event": a.event,
        "severity": a.severity,
        "headline": a.headline,
        "onset": _iso(a.onset),
        "ends": _iso(a.ends),
    }


def resort_dict(r: ResortReport) -> dict:
    return {
        "id": r.resort_id,
        "name": r.name,
        "snow_24h_in": r.snow_24h_in,
        "snow_48h_in": r.snow_48h_in,
        "snow_overnight_in": r.snow_overnight_in,
        "storm_total_in": r.storm_total_in,
        "base_depth_in": r.base_depth_in,
        "base_depth_max_in": r.base_depth_max_in,
        "season_total_in": r.season_total_in,
        "lifts_open": r.lifts_open,
        "lifts_total": r.lifts_total,
        "updated_at": _iso(r.updated_at),
        "ok": r.ok,
        "stale": r.stale,
        "error": "unavailable" if r.error else None,
        "notes": [_public_note(n) for n in r.notes],
    }


def pass_summary(
    mtn_pass: MountainPass,
    forecast: PassForecast | None,
    outlook: SnowOutlook | None,
) -> dict:
    payload: dict = {
        "id": mtn_pass.id,
        "name": mtn_pass.name,
        "route": mtn_pass.route,
        "state": mtn_pass.state,
        "elevation_ft": mtn_pass.elevation_ft,
        "corridor_id": mtn_pass.corridor_id,
        "lat": mtn_pass.lat,
        "lon": mtn_pass.lon,
    }
    if forecast is not None:
        payload["alerts"] = [alert_dict(a) for a in forecast.alerts]
        payload["forecast_ok"] = forecast.ok
        payload["forecast_stale"] = forecast.stale
        payload["forecast_as_of"] = _iso(forecast.data_as_of)
        if forecast.periods:
            payload["next_period"] = period_dict(forecast.periods[0])
    if outlook is not None and outlook.ok:
        payload["snow_next_24h_cm"] = outlook.accumulation_cm(24)
        payload["snow_next_48h_cm"] = outlook.accumulation_cm(48)
        payload["snow_next_72h_cm"] = outlook.accumulation_cm(72)
        storm = outlook.storm_start()
        payload["storm_start"] = _iso(storm)
    return payload


def tier_label_for(tier) -> str:
    """Stable alias used by the map payload."""
    return tier_label(tier)
