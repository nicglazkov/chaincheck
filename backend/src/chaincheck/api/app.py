"""ChainCheck HTTP API.

Client-agnostic JSON: the mobile apps, the future web page, and evals all
consume the same endpoints. ``POST /internal/poll`` is the watcher tick,
fired by Cloud Scheduler and guarded by a shared token.
"""

from __future__ import annotations

import asyncio
import hmac
import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI, Header, HTTPException, Path, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from chaincheck import __version__, rules
from chaincheck.api import security, serialize
from chaincheck.brief import facts as brief_facts
from chaincheck.brief.tripbrief import TripBriefer
from chaincheck.feeds.nws import NwsSource
from chaincheck.feeds.openmeteo import OpenMeteoSource
from chaincheck.feeds.resorts import ResortRegistry
from chaincheck.feeds.roads import SierraRoads
from chaincheck.passes import PASSES, PASSES_BY_ID
from chaincheck.push import dispatch as push_dispatch
from chaincheck.push.fcm import build_sender
from chaincheck.push.subscriptions import (
    FirestoreSubscriptionStore,
    InMemorySubscriptionStore,
    validate_corridors,
)
from chaincheck.tiers import Tier
from chaincheck.watcher import differ, poller

DISCLAIMER = (
    "ChainCheck reports official Caltrans/CHP/NWS data but is not affiliated with "
    "any government agency. Conditions change fast; verify before you drive "
    "(dial 511 or quickmap.dot.ca.gov). Whether it is safe to drive is always "
    "your decision."
)


class AppState:
    def __init__(self) -> None:
        self.client = httpx.AsyncClient(follow_redirects=True)
        self.roads = SierraRoads(self.client)
        self.nws = NwsSource(self.client)
        self.snow = OpenMeteoSource(self.client)
        self.resorts = ResortRegistry(self.client)
        self.watch_state = differ.WatchState.empty()
        self.cadence = poller.CadenceState()
        self.recent_events: list[dict] = []
        if os.environ.get("SUBSCRIPTIONS_BACKEND", "memory") == "firestore":
            self.subscriptions = FirestoreSubscriptionStore(
                project=os.environ.get("GOOGLE_CLOUD_PROJECT")
            )
        else:
            self.subscriptions = InMemorySubscriptionStore()
        self.push_sender = build_sender()
        self.briefer = TripBriefer()


state: AppState | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global state
    state = AppState()
    try:
        yield
    finally:
        await state.client.aclose()
        state = None


logger = logging.getLogger(__name__)

# Interactive docs advertise every route (including /internal/poll) to anyone.
# Off by default; opt in with CHAINCHECK_DOCS=1 for local exploration.
_docs_on = os.environ.get("CHAINCHECK_DOCS") == "1"
app = FastAPI(
    title="ChainCheck API",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs" if _docs_on else None,
    redoc_url="/redoc" if _docs_on else None,
    openapi_url="/openapi.json" if _docs_on else None,
)

# A generous global ceiling: real clients poll a handful of times a minute;
# this only bites scrapers and crude floods. Per trusted IP, per instance.
_request_limiter = security.RateLimiter(limit=120, window_seconds=60.0)
# Anonymous Firestore writes get their own tighter budget so nobody can
# spray junk subscriptions into the database.
_subscription_limiter = security.RateLimiter(limit=20, window_seconds=3600.0)

# Paths exempt from the global limit: health must never be throttled (uptime
# checks) and the scheduler tick authenticates with its own token.
_UNLIMITED_PATHS = frozenset({"/health", "/healthz", "/internal/poll"})


def _caller(request: Request) -> str | None:
    return security.trusted_client_ip(
        request.headers.get("x-forwarded-for"),
        request.client.host if request.client else None,
    )


@app.middleware("http")
async def _guard(request: Request, call_next):
    # Reject oversized bodies before FastAPI buffers or parses them.
    length = request.headers.get("content-length")
    if length is not None:
        try:
            if int(length) > security.MAX_REQUEST_BYTES:
                return JSONResponse(status_code=413, content={"detail": "request too large"})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "bad content-length"})

    if request.url.path not in _UNLIMITED_PATHS and not _request_limiter.allow(
        _caller(request)
    ):
        return JSONResponse(status_code=429, content={"detail": "slow down"})

    response = await call_next(request)
    # Defense-in-depth headers; the API returns JSON, never HTML, but these
    # cost nothing and close off content-sniffing and framing.
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    # Log the detail server-side; never return it. FastAPI's default already
    # hides tracebacks, but this guarantees a stable, quiet error shape.
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal error"})


def _state() -> AppState:
    if state is None:  # pragma: no cover - lifespan guarantees this
        raise HTTPException(503, "starting up")
    return state


# Note: Cloud Run's frontend intercepts /healthz on run.app domains, so the
# health endpoint is /health (the old path stays for local tooling).
@app.get("/health")
@app.get("/healthz")
async def health() -> dict:
    return {"ok": True, "version": __version__}


@app.get("/v1/summary")
async def summary() -> dict:
    st = _state()
    snapshot = await st.roads.snapshot()
    pass_payloads = await asyncio.gather(
        *(_pass_payload(st, p.id) for p in PASSES)
    )
    return {
        "corridors": [
            serialize.corridor_summary(snapshot.corridors[c_id])
            for c_id in sorted(snapshot.corridors)
        ],
        "passes": list(pass_payloads),
        "feed": serialize.snapshot_health(snapshot),
        "disclaimer": DISCLAIMER,
    }


@app.get("/v1/routes")
async def routes() -> dict:
    st = _state()
    snapshot = await st.roads.snapshot()
    return {
        "corridors": [
            serialize.corridor_summary(snapshot.corridors[c_id])
            for c_id in sorted(snapshot.corridors)
        ],
        "feed": serialize.snapshot_health(snapshot),
    }


@app.get("/v1/routes/{corridor_id}")
async def route_detail(corridor_id: str = Path(max_length=64)) -> dict:
    st = _state()
    snapshot = await st.roads.snapshot()
    roads = snapshot.corridors.get(corridor_id)
    if roads is None:
        raise HTTPException(404, f"unknown corridor '{corridor_id}'")
    payload = serialize.corridor_detail(roads)
    payload["feed"] = serialize.snapshot_health(snapshot)
    return payload


async def _pass_payload(st: AppState, pass_id: str) -> dict:
    mtn_pass = PASSES_BY_ID[pass_id]
    forecast, outlook = await asyncio.gather(
        st.nws.forecast(mtn_pass), st.snow.outlook(mtn_pass)
    )
    return serialize.pass_summary(mtn_pass, forecast, outlook)


@app.get("/v1/passes")
async def passes() -> dict:
    st = _state()
    payloads = await asyncio.gather(*(_pass_payload(st, p.id) for p in PASSES))
    return {"passes": list(payloads)}


@app.get("/v1/passes/{pass_id}")
async def pass_detail(pass_id: str = Path(max_length=64)) -> dict:
    st = _state()
    mtn_pass = PASSES_BY_ID.get(pass_id)
    if mtn_pass is None:
        raise HTTPException(404, f"unknown pass '{pass_id}'")
    forecast, outlook = await asyncio.gather(
        st.nws.forecast(mtn_pass), st.snow.outlook(mtn_pass)
    )
    payload = serialize.pass_summary(mtn_pass, forecast, outlook)
    payload["periods"] = [serialize.period_dict(p) for p in forecast.periods]
    return payload


@app.get("/v1/map")
async def map_data() -> dict:
    """Everything plottable in one payload: controls, closures, incidents,
    webcams, passes, resorts. Point data only - the client draws the map."""
    from chaincheck.feeds.resorts import RESORT_COORDS

    st = _state()
    snapshot, cams, resort_reports = await asyncio.gather(
        st.roads.snapshot(), st.roads.webcams(), st.resorts.all_reports()
    )

    controls = []
    closures = []
    incidents = []
    for roads in snapshot.corridors.values():
        for c in roads.controls:
            payload = serialize.control_dict(c)
            payload["corridor_id"] = roads.corridor.id
            controls.append(payload)
        for c in roads.closures:
            payload = serialize.closure_dict(c)
            payload["corridor_id"] = roads.corridor.id
            closures.append(payload)
        for i in roads.incidents:
            payload = serialize.incident_dict(i)
            payload["corridor_id"] = roads.corridor.id
            incidents.append(payload)

    corridor_lines = [
        {
            "id": roads.corridor.id,
            "route": roads.corridor.display_route,
            "name": roads.corridor.name,
            "tier": int(roads.tier),
            "tier_label": serialize.tier_label_for(roads.tier),
            "segments": [
                [{"lat": lat, "lon": lon} for lat, lon in segment]
                for segment in roads.corridor.segments
            ],
        }
        for roads in snapshot.corridors.values()
        if roads.corridor.segments
    ]

    return {
        "corridors": corridor_lines,
        "controls": controls,
        "closures": closures,
        "incidents": incidents,
        "webcams": [
            {
                "id": w.id,
                "name": w.name,
                "route": w.route,
                "direction": w.direction,
                "nearby": w.nearby,
                "lat": w.lat,
                "lon": w.lon,
                "image_url": w.image_url,
            }
            for w in cams.webcams
        ],
        "webcams_attribution": "Camera images: Caltrans",
        "passes": [
            {
                "id": p.id,
                "name": p.name,
                "route": p.route,
                "state": p.state,
                "elevation_ft": p.elevation_ft,
                "corridor_id": p.corridor_id,
                "lat": p.lat,
                "lon": p.lon,
            }
            for p in PASSES
        ],
        "resorts": [
            {
                **serialize.resort_dict(r),
                "lat": RESORT_COORDS[r.resort_id][0],
                "lon": RESORT_COORDS[r.resort_id][1],
            }
            for r in resort_reports
            if r.resort_id in RESORT_COORDS
        ],
        "feed": serialize.snapshot_health(snapshot),
        "disclaimer": DISCLAIMER,
    }


@app.get("/v1/resorts")
async def resorts() -> dict:
    from chaincheck.feeds.resorts import RESORT_COORDS

    reports = await _state().resorts.all_reports()
    reports.sort(key=lambda r: (r.snow_24h_in or 0.0), reverse=True)
    payloads = []
    for r in reports:
        payload = serialize.resort_dict(r)
        coords = RESORT_COORDS.get(r.resort_id)
        if coords:
            payload["lat"], payload["lon"] = coords
        payloads.append(payload)
    return {"resorts": payloads}


@app.get("/v1/resorts/{resort_id}")
async def resort_detail(resort_id: str = Path(max_length=64)) -> dict:
    report = await _state().resorts.report(resort_id)
    if report is None:
        raise HTTPException(404, f"unknown or disabled resort '{resort_id}'")
    return serialize.resort_dict(report)


class VehicleQuery(BaseModel):
    tier: int
    drivetrain: rules.Drivetrain
    tires: rules.Tires
    over_6000_lbs: bool = False
    towing: bool = False


@app.post("/v1/rules/evaluate")
async def evaluate_rules(query: VehicleQuery) -> dict:
    try:
        tier = Tier(query.tier)
    except ValueError as exc:
        raise HTTPException(422, f"invalid tier {query.tier}") from exc
    ruling = rules.evaluate(
        tier,
        rules.Vehicle(
            drivetrain=query.drivetrain,
            tires=query.tires,
            over_6000_lbs=query.over_6000_lbs,
            towing=query.towing,
        ),
    )
    return {
        "requirement": ruling.requirement.value,
        "reason": ruling.reason,
        "disclaimer": DISCLAIMER,
    }


class TripBriefQuery(BaseModel):
    corridor_id: str = Field(max_length=32)
    origin: str = Field(default="Sacramento", max_length=200)
    departure_time: datetime | None = None
    drivetrain: rules.Drivetrain | None = None
    tires: rules.Tires | None = None
    over_6000_lbs: bool = False
    towing: bool = False


# A departure only makes sense within the forecast horizon; anything outside
# this window is clamped so it cannot drive a pathological accumulation loop
# or a garbage cache key.
_MAX_DEPARTURE_AHEAD = timedelta(days=7)


@app.post("/v1/tripbrief")
async def trip_brief(query: TripBriefQuery, request: Request) -> dict:
    st = _state()
    if query.corridor_id not in {p.corridor_id for p in PASSES}:
        raise HTTPException(422, f"no pass forecast for corridor '{query.corridor_id}'")
    now = datetime.now(UTC)
    departure = query.departure_time or now
    if departure.tzinfo is None:
        departure = departure.replace(tzinfo=UTC)
    departure = min(max(departure, now), now + _MAX_DEPARTURE_AHEAD)
    origin = security.sanitize_origin(query.origin)

    snapshot = await st.roads.snapshot()
    mtn_pass = next(p for p in PASSES if p.corridor_id == query.corridor_id)
    forecast, outlook = await asyncio.gather(
        st.nws.forecast(mtn_pass), st.snow.outlook(mtn_pass)
    )
    vehicle = None
    if query.drivetrain is not None and query.tires is not None:
        vehicle = rules.Vehicle(
            drivetrain=query.drivetrain,
            tires=query.tires,
            over_6000_lbs=query.over_6000_lbs,
            towing=query.towing,
        )
    facts = brief_facts.assemble(
        corridor_id=query.corridor_id,
        origin=origin,
        departure=departure,
        snapshot=snapshot,
        forecast=forecast,
        outlook=outlook,
        vehicle=vehicle,
    )
    result = await st.briefer.narrate(facts, client=_caller(request))
    return {
        "brief": result.text,
        "ai": result.ai,
        "model": result.model,
        "cached": result.cached,
        "tier": facts.tier,
        "tier_label": facts.tier_label,
        "as_of": facts.data_as_of.isoformat() if facts.data_as_of else None,
        "stale": facts.stale,
        "disclaimer": DISCLAIMER,
    }


class SubscriptionBody(BaseModel):
    token: str = Field(max_length=security.MAX_TOKEN_LEN)
    corridor_ids: list[str] = Field(max_length=security.MAX_CORRIDOR_IDS)


@app.put("/v1/subscriptions")
async def upsert_subscription(body: SubscriptionBody, request: Request) -> dict:
    if not security.is_valid_push_token(body.token):
        raise HTTPException(422, "invalid token")
    if not _subscription_limiter.allow(_caller(request)):
        raise HTTPException(429, "too many subscription changes")
    corridor_ids = validate_corridors(body.corridor_ids)
    if not corridor_ids:
        raise HTTPException(422, "no valid corridor ids")
    sub = await _state().subscriptions.upsert(body.token, corridor_ids)
    return {"token": sub.token, "corridor_ids": sub.corridor_ids}


class TokenBody(BaseModel):
    token: str = Field(max_length=security.MAX_TOKEN_LEN)


# The token is a device secret, so it travels in the request body, never the
# URL path where it would land in access logs and proxy history.
@app.post("/v1/subscriptions/query")
async def query_subscription(body: TokenBody) -> dict:
    if not security.is_valid_push_token(body.token):
        raise HTTPException(404, "unknown token")
    sub = await _state().subscriptions.get(body.token)
    if sub is None:
        raise HTTPException(404, "unknown token")
    return {"token": sub.token, "corridor_ids": sub.corridor_ids}


@app.post("/v1/subscriptions/delete")
async def delete_subscription(body: TokenBody) -> dict:
    if not security.is_valid_push_token(body.token):
        raise HTTPException(404, "unknown token")
    removed = await _state().subscriptions.delete(body.token)
    if not removed:
        raise HTTPException(404, "unknown token")
    return {"deleted": True}


def _poll_authorized(supplied: str | None) -> bool:
    expected = os.environ.get("POLL_TOKEN")
    if not expected:
        # Fail closed: a production deploy always sets POLL_TOKEN. Only an
        # explicit local-dev opt-in leaves this internal endpoint open.
        return os.environ.get("CHAINCHECK_ALLOW_OPEN_POLL") == "1"
    if not supplied:
        return False
    return hmac.compare_digest(supplied, expected)


@app.post("/internal/poll")
async def poll_tick(x_poll_token: str | None = Header(default=None)) -> dict:
    if not _poll_authorized(x_poll_token):
        raise HTTPException(403, "bad poll token")
    st = _state()
    now = datetime.now(UTC)
    if not poller.should_poll(st.cadence, now):
        return {"polled": False, "active": st.cadence.active}

    snapshot = await st.roads.snapshot()
    events, st.watch_state = differ.diff(st.watch_state, snapshot)

    alerts_by_pass: dict[str, list] = {}
    for p in PASSES:
        forecast = await st.nws.forecast(p)
        if forecast.ok:
            alerts_by_pass[p.id] = forecast.alerts
    storm_events, st.watch_state = differ.diff_alerts(st.watch_state, alerts_by_pass)
    events = list(events) + list(storm_events)

    all_alerts = [a for alerts in alerts_by_pass.values() for a in alerts]
    st.cadence.active = poller.is_active_weather(snapshot, all_alerts, now)
    st.cadence.last_poll_at = now

    pushes_sent = await push_dispatch.dispatch(events, st.subscriptions, st.push_sender)

    event_payloads = [
        {"summary": e.summary(), "corridor_id": e.corridor_id, "at": now.isoformat()}
        for e in events
    ]
    st.recent_events = (event_payloads + st.recent_events)[:100]
    return {
        "polled": True,
        "active": st.cadence.active,
        "events": event_payloads,
        "pushes_sent": pushes_sent,
        "feed": serialize.snapshot_health(snapshot),
    }


@app.get("/v1/events")
async def recent_events(x_poll_token: str | None = Header(default=None)) -> dict:
    """Recent tier/closure change events. Operational/debug only, so it
    rides behind the same token as the poll tick rather than being public."""
    if not _poll_authorized(x_poll_token):
        raise HTTPException(403, "bad poll token")
    return {"events": _state().recent_events}


def main() -> None:
    import uvicorn

    uvicorn.run(
        "chaincheck.api.app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8080")),
    )


if __name__ == "__main__":
    main()
