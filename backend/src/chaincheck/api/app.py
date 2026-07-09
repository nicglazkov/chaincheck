"""ChainCheck HTTP API.

Client-agnostic JSON: the mobile apps, the future web page, and evals all
consume the same endpoints. ``POST /internal/poll`` is the watcher tick,
fired by Cloud Scheduler and guarded by a shared token.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from chaincheck import __version__, rules
from chaincheck.api import serialize
from chaincheck.feeds.nws import NwsSource
from chaincheck.feeds.openmeteo import OpenMeteoSource
from chaincheck.feeds.resorts import ResortRegistry
from chaincheck.feeds.roads import SierraRoads
from chaincheck.passes import PASSES, PASSES_BY_ID
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


app = FastAPI(title="ChainCheck API", version=__version__, lifespan=lifespan)


def _state() -> AppState:
    if state is None:  # pragma: no cover - lifespan guarantees this
        raise HTTPException(503, "starting up")
    return state


@app.get("/healthz")
async def healthz() -> dict:
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
async def route_detail(corridor_id: str) -> dict:
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
async def pass_detail(pass_id: str) -> dict:
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


@app.get("/v1/resorts")
async def resorts() -> dict:
    reports = await _state().resorts.all_reports()
    reports.sort(key=lambda r: (r.snow_24h_in or 0.0), reverse=True)
    return {"resorts": [serialize.resort_dict(r) for r in reports]}


@app.get("/v1/resorts/{resort_id}")
async def resort_detail(resort_id: str) -> dict:
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


@app.post("/internal/poll")
async def poll_tick(x_poll_token: str | None = Header(default=None)) -> dict:
    expected = os.environ.get("POLL_TOKEN")
    if expected and x_poll_token != expected:
        raise HTTPException(403, "bad poll token")
    st = _state()
    now = datetime.now(UTC)
    if not poller.should_poll(st.cadence, now):
        return {"polled": False, "active": st.cadence.active}

    snapshot = await st.roads.snapshot()
    events, st.watch_state = differ.diff(st.watch_state, snapshot)

    alerts = []
    for p in PASSES:
        forecast = await st.nws.forecast(p)
        alerts.extend(forecast.alerts)
    st.cadence.active = poller.is_active_weather(snapshot, alerts, now)
    st.cadence.last_poll_at = now

    event_payloads = [
        {"summary": e.summary(), "corridor_id": e.corridor_id, "at": now.isoformat()}
        for e in events
    ]
    st.recent_events = (event_payloads + st.recent_events)[:100]
    return {
        "polled": True,
        "active": st.cadence.active,
        "events": event_payloads,
        "feed": serialize.snapshot_health(snapshot),
    }


@app.get("/v1/events")
async def recent_events() -> dict:
    """Recent tier/closure change events (debug/dev; push lands in M2)."""
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
