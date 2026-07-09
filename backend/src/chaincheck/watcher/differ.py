"""Turns consecutive Sierra snapshots into events worth telling someone about.

The differ is pure: state in, state out, no I/O. Corridor-level tier changes
are the headline events ("R2 went up on I-80 over Donner Summit"); closure
appear/clear events ride along. Checkpoint-level changes below the corridor
max are intentionally not events - they'd be noise.
"""

from __future__ import annotations

from dataclasses import dataclass

from chaincheck.corridors import CORRIDORS_BY_ID
from chaincheck.feeds.roads import SierraSnapshot
from chaincheck.tiers import Tier, tier_label


@dataclass(frozen=True)
class TierChange:
    corridor_id: str
    old: Tier
    new: Tier

    @property
    def went_up(self) -> bool:
        return self.new > self.old

    def summary(self) -> str:
        corridor = CORRIDORS_BY_ID[self.corridor_id]
        if self.new is Tier.CLOSED:
            return f"{corridor.display_route} closed ({corridor.name})"
        if self.old is Tier.CLOSED:
            return (
                f"{corridor.display_route} reopened at {tier_label(self.new)} "
                f"({corridor.name})"
            )
        if self.new is Tier.R0:
            return f"Chain controls lifted on {corridor.display_route} ({corridor.name})"
        direction = "up" if self.went_up else "down"
        return (
            f"{tier_label(self.new)} just went {direction} on "
            f"{corridor.display_route} ({corridor.name}), was {tier_label(self.old)}"
        )


@dataclass(frozen=True)
class ClosureChange:
    corridor_id: str
    closure_index: str
    appeared: bool  # False = cleared
    location: str

    def summary(self) -> str:
        corridor = CORRIDORS_BY_ID[self.corridor_id]
        verb = "New closure" if self.appeared else "Closure cleared"
        where = f" at {self.location}" if self.location else ""
        return f"{verb} on {corridor.display_route}{where}"


@dataclass(frozen=True)
class WatchState:
    """Last-known per-corridor state, serializable for external storage."""

    tiers: dict[str, int]
    closure_keys: dict[str, tuple[str, ...]]

    @classmethod
    def empty(cls) -> WatchState:
        return cls(tiers={}, closure_keys={})


def diff(prev: WatchState, snapshot: SierraSnapshot) -> tuple[list[object], WatchState]:
    """Events since ``prev``, plus the new state to persist.

    A stale snapshot produces no events and does not advance state: reporting
    a "change" off cached data would fire alerts on feed hiccups.
    """
    if not snapshot.ok or snapshot.stale:
        return [], prev

    events: list[object] = []
    new_tiers: dict[str, int] = {}
    new_closures: dict[str, tuple[str, ...]] = {}

    for corridor_id, roads in snapshot.corridors.items():
        if roads.tier is Tier.UNKNOWN and corridor_id in prev.tiers:
            # Keep the last known tier through a blind spell so recovery to the
            # same tier doesn't fire a phantom change.
            new_tiers[corridor_id] = prev.tiers[corridor_id]
        else:
            new_tiers[corridor_id] = int(roads.tier)
        keys = tuple(sorted(c.index for c in roads.closures))
        new_closures[corridor_id] = keys

        if corridor_id in prev.tiers:
            old_tier = Tier(prev.tiers[corridor_id])
            if (
                roads.tier is not Tier.UNKNOWN
                and old_tier is not Tier.UNKNOWN
                and roads.tier is not old_tier
            ):
                events.append(TierChange(corridor_id, old_tier, roads.tier))

        prev_keys = set(prev.closure_keys.get(corridor_id, ()))
        curr_keys = set(keys)
        locations = {c.index: c.location_name for c in roads.closures}
        for idx in sorted(curr_keys - prev_keys):
            events.append(ClosureChange(corridor_id, idx, True, locations.get(idx, "")))
        if corridor_id in prev.closure_keys:
            for idx in sorted(prev_keys - curr_keys):
                events.append(ClosureChange(corridor_id, idx, False, ""))

    return events, WatchState(tiers=new_tiers, closure_keys=new_closures)
