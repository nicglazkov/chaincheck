from datetime import UTC, datetime, timedelta

from tests.test_differ import snapshot_with

from chaincheck.feeds.nws import WinterAlert
from chaincheck.feeds.roads import SierraSnapshot
from chaincheck.tiers import Tier
from chaincheck.watcher import poller

NOW = datetime(2026, 12, 12, 15, 0, tzinfo=UTC)


def quiet_snapshot() -> SierraSnapshot:
    return snapshot_with({})


def alert(onset_offset_hours: float | None, ends_offset_hours: float | None) -> WinterAlert:
    return WinterAlert(
        id="a1",
        event="Winter Storm Warning",
        severity="Severe",
        headline="Winter Storm Warning",
        onset=NOW + timedelta(hours=onset_offset_hours) if onset_offset_hours is not None else None,
        ends=NOW + timedelta(hours=ends_offset_hours) if ends_offset_hours is not None else None,
        description="",
    )


def test_quiet_conditions_are_not_active():
    assert not poller.is_active_weather(quiet_snapshot(), [], NOW)


def test_any_control_makes_it_active():
    assert poller.is_active_weather(snapshot_with({"i80": Tier.R1}), [], NOW)


def test_alert_in_effect_makes_it_active():
    assert poller.is_active_weather(quiet_snapshot(), [alert(-2, 6)], NOW)


def test_alert_starting_within_lookahead_makes_it_active():
    assert poller.is_active_weather(quiet_snapshot(), [alert(8, 20)], NOW)


def test_alert_far_out_is_not_active():
    assert not poller.is_active_weather(quiet_snapshot(), [alert(36, 48)], NOW)


def test_expired_alert_is_not_active():
    assert not poller.is_active_weather(quiet_snapshot(), [alert(-30, -10)], NOW)


def test_first_tick_always_polls():
    assert poller.should_poll(poller.CadenceState(), NOW)


def test_active_cadence_polls_every_tick():
    state = poller.CadenceState(last_poll_at=NOW - timedelta(minutes=2), active=True)
    assert poller.should_poll(state, NOW)


def test_quiet_cadence_skips_early_ticks():
    state = poller.CadenceState(last_poll_at=NOW - timedelta(minutes=4), active=False)
    assert not poller.should_poll(state, NOW)
    state = poller.CadenceState(last_poll_at=NOW - timedelta(minutes=15), active=False)
    assert poller.should_poll(state, NOW)
