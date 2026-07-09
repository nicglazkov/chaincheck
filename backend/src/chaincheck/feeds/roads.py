"""Sierra view over the ca_roads feed layer.

Wraps :class:`ca_roads.roaddata.RoadData` and reduces statewide feeds to the
Tahoe corridors. Chain controls are fetched with ``active_only=False`` so a
corridor can affirmatively report "R0, no controls" instead of going silent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import httpx
from ca_roads.models import ChainControl, ChpIncident, LaneClosure
from ca_roads.roaddata import RoadData

from chaincheck import corridors
from chaincheck.corridors import Corridor
from chaincheck.tiers import Tier, control_tier


@dataclass
class CorridorRoads:
    """Everything road-related happening on one corridor right now."""

    corridor: Corridor
    tier: Tier = Tier.UNKNOWN
    controls: list[ChainControl] = field(default_factory=list)
    closures: list[LaneClosure] = field(default_factory=list)
    incidents: list[ChpIncident] = field(default_factory=list)


@dataclass
class SierraSnapshot:
    """One coherent pull of all Sierra road state, plus feed health."""

    corridors: dict[str, CorridorRoads]
    data_as_of: datetime | None
    ok: bool
    stale: bool
    notes: list[str] = field(default_factory=list)


class SierraRoads:
    """Filters statewide ca_roads feeds down to the Sierra corridors."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._roads = RoadData(client)

    @property
    def client(self) -> httpx.AsyncClient:
        return self._roads.client

    async def aclose(self) -> None:
        await self._roads.aclose()

    async def snapshot(self) -> SierraSnapshot:
        by_id = {c.id: CorridorRoads(corridor=c) for c in corridors.CORRIDORS}
        notes: list[str] = []
        stale = False
        newest: datetime | None = None

        controls = await self._roads.chain_controls(
            districts=corridors.SIERRA_DISTRICTS, active_only=False
        )
        closures = await self._roads.lane_closures(
            districts=corridors.SIERRA_DISTRICTS, active_only=True
        )
        incidents = await self._roads.incidents()

        any_ok = False
        for result in (controls, closures, incidents):
            notes.extend(f"{result.source}: {n}" for n in result.notes)
            if result.error:
                notes.append(f"{result.source}: {result.error}")
            stale = stale or result.stale
            any_ok = any_ok or result.ok
            if result.ok and result.data_as_of:
                newest = max(newest, result.data_as_of) if newest else result.data_as_of

        if controls.ok:
            for control in controls.records:
                corridor = corridors.match_control(control)
                if corridor and control.in_service:
                    by_id[corridor.id].controls.append(control)
        if closures.ok:
            for closure in closures.records:
                corridor = corridors.match_closure(closure)
                if corridor:
                    by_id[corridor.id].closures.append(closure)
        if incidents.ok:
            for incident in incidents.records:
                corridor = corridors.match_incident(incident)
                if corridor:
                    by_id[corridor.id].incidents.append(incident)

        for roads in by_id.values():
            roads.controls.sort(key=lambda c: c.lat, reverse=True)
            if controls.ok and roads.controls:
                roads.tier = max(control_tier(c) for c in roads.controls)
            elif controls.ok:
                # Feed healthy and no checkpoint reporting on this corridor:
                # that is an affirmative "no controls".
                roads.tier = Tier.R0

        return SierraSnapshot(
            corridors=by_id,
            data_as_of=newest,
            ok=any_ok,
            stale=stale,
            notes=notes,
        )
