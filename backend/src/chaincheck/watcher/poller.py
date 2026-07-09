"""Adaptive polling cadence.

Cloud Scheduler fires a tick every 2 minutes; this module decides whether a
tick should actually hit the feeds. During active weather (any control up,
any closure, or a winter alert in effect or imminent) every tick polls;
otherwise polling relaxes to the quiet interval. Caltrans refreshes chain
data about once a minute, so the active cadence keeps worst-case
control-change-to-poll latency around the tick interval.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from chaincheck.feeds.nws import WinterAlert
from chaincheck.feeds.roads import SierraSnapshot
from chaincheck.tiers import Tier

ACTIVE_INTERVAL = timedelta(minutes=2)
QUIET_INTERVAL = timedelta(minutes=15)
ALERT_LOOKAHEAD = timedelta(hours=12)


def is_active_weather(
    snapshot: SierraSnapshot | None,
    alerts: list[WinterAlert],
    now: datetime | None = None,
) -> bool:
    now = now or datetime.now(UTC)
    if snapshot is not None:
        for roads in snapshot.corridors.values():
            if roads.tier > Tier.R0 or roads.closures:
                return True
    for alert in alerts:
        started = alert.onset is None or alert.onset <= now + ALERT_LOOKAHEAD
        ended = alert.ends is not None and alert.ends < now
        if started and not ended:
            return True
    return False


@dataclass
class CadenceState:
    last_poll_at: datetime | None = None
    active: bool = True  # start eager: first tick always polls


def should_poll(state: CadenceState, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    if state.last_poll_at is None:
        return True
    interval = ACTIVE_INTERVAL if state.active else QUIET_INTERVAL
    # Small grace so a scheduler tick landing seconds early still counts.
    return now - state.last_poll_at >= interval - timedelta(seconds=15)
