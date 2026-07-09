from ca_roads.models import ChainControl

from chaincheck.corridors import CORRIDORS
from chaincheck.feeds.roads import CorridorRoads, SierraSnapshot
from chaincheck.tiers import Tier
from chaincheck.watcher import differ


def make_control(route: str, status: str, lat: float = 39.34, lon: float = -120.35):
    return ChainControl(
        index=f"{route}-{status}",
        district=3,
        route=route,
        county="Placer",
        direction="East",
        location_name="Donner Summit",
        nearby_place="Truckee",
        lat=lat,
        lon=lon,
        in_service=True,
        status=status,
        status_description="",
        status_updated_at=None,
    )


def snapshot_with(tier_by_corridor: dict[str, Tier], ok=True, stale=False) -> SierraSnapshot:
    corridors_map = {}
    for c in CORRIDORS:
        roads = CorridorRoads(corridor=c, tier=tier_by_corridor.get(c.id, Tier.R0))
        corridors_map[c.id] = roads
    return SierraSnapshot(
        corridors=corridors_map, data_as_of=None, ok=ok, stale=stale
    )


def test_first_snapshot_produces_no_events():
    events, state = differ.diff(differ.WatchState.empty(), snapshot_with({"i80": Tier.R2}))
    assert events == []
    assert state.tiers["i80"] == int(Tier.R2)


def test_tier_up_fires_event_with_plain_language_summary():
    _, state = differ.diff(differ.WatchState.empty(), snapshot_with({"i80": Tier.R0}))
    events, _ = differ.diff(state, snapshot_with({"i80": Tier.R2}))
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, differ.TierChange)
    assert event.went_up
    assert "R2" in event.summary()
    assert "I-80" in event.summary()


def test_tier_lift_summary():
    _, state = differ.diff(differ.WatchState.empty(), snapshot_with({"us50": Tier.R2}))
    events, _ = differ.diff(state, snapshot_with({"us50": Tier.R0}))
    assert len(events) == 1
    assert "lifted" in events[0].summary()


def test_no_event_when_nothing_changed():
    snap = snapshot_with({"i80": Tier.R1})
    _, state = differ.diff(differ.WatchState.empty(), snap)
    events, _ = differ.diff(state, snap)
    assert events == []


def test_stale_snapshot_neither_fires_nor_advances_state():
    _, state = differ.diff(differ.WatchState.empty(), snapshot_with({"i80": Tier.R0}))
    events, state2 = differ.diff(state, snapshot_with({"i80": Tier.R3}, stale=True))
    assert events == []
    assert state2 is state


def test_unknown_gap_does_not_fire_phantom_change():
    _, state = differ.diff(differ.WatchState.empty(), snapshot_with({"i80": Tier.R2}))
    # Feed goes blind for a poll...
    events, state = differ.diff(state, snapshot_with({"i80": Tier.UNKNOWN}))
    assert events == []
    # ...then recovers at the same tier: still no event.
    events, _ = differ.diff(state, snapshot_with({"i80": Tier.R2}))
    assert events == []


def test_closure_appears_and_clears():
    snap_with_closure = snapshot_with({})
    from ca_roads.models import LaneClosure

    closure = LaneClosure(
        index="C123",
        district=3,
        route="80",
        county="Placer",
        direction="East",
        location_name="Kingvale",
        nearby_place="",
        type_of_closure="Full",
        facility="",
        type_of_work="spinout",
        lanes_closed="all",
        total_lanes=2,
        estimated_delay_minutes=None,
        duration="",
        begin_lat=39.31,
        begin_lon=-120.44,
        end_lat=39.32,
        end_lon=-120.40,
        begin_milepost=None,
        end_milepost=None,
        start_epoch=0,
        end_epoch=0,
        indefinite_end=False,
        is_1097=True,
        is_1098=False,
        is_1022=False,
        epoch_1097=0,
    )
    snap_with_closure.corridors["i80"].closures.append(closure)

    _, state = differ.diff(differ.WatchState.empty(), snapshot_with({}))
    events, state = differ.diff(state, snap_with_closure)
    assert any(
        isinstance(e, differ.ClosureChange) and e.appeared and "Kingvale" in e.summary()
        for e in events
    )
    events, _ = differ.diff(state, snapshot_with({}))
    assert any(isinstance(e, differ.ClosureChange) and not e.appeared for e in events)
