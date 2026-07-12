"""Structured facts for a trip brief.

Everything the AI is allowed to say comes from here. The assembly is pure
and unit-testable; the narration layer (tripbrief.py) formats or paraphrases
these facts but can neither add road states nor alter the vehicle ruling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from chaincheck import rules
from chaincheck.corridors import CORRIDORS_BY_ID
from chaincheck.feeds.nws import PassForecast
from chaincheck.feeds.openmeteo import SnowOutlook
from chaincheck.feeds.roads import SierraSnapshot
from chaincheck.passes import PASSES
from chaincheck.tiers import TIER_MEANING, Tier, control_tier, tier_label


@dataclass(frozen=True)
class TripFacts:
    corridor_id: str
    corridor_name: str
    route: str
    origin: str
    departure: datetime
    tier: int
    tier_label: str
    tier_meaning: str
    active_controls: tuple[str, ...]
    closures: tuple[str, ...]
    incident_count: int
    pass_name: str
    alerts: tuple[str, ...]
    forecast_window: tuple[str, ...]
    snow_before_arrival_cm: float | None
    snow_during_window_cm: float | None
    storm_start: datetime | None
    ruling: rules.Ruling | None
    data_as_of: datetime | None
    stale: bool
    notes: tuple[str, ...] = field(default=())


DRIVE_WINDOW_HOURS = 4  # Sacramento-to-Tahoe scale drive
PACIFIC = ZoneInfo("America/Los_Angeles")  # drivers read Pacific, not UTC

# Feed-derived text flows verbatim into the model prompt. The strong
# fact-only design already blocks the model from acting on injected text, but
# capping length keeps a compromised upstream from bloating the prompt or
# smuggling a wall of instructions.
_FEED_STR_CAP = 160


def _cap(value: str) -> str:
    return value[:_FEED_STR_CAP]

# The brief names at most this many closures; the model only sees (and
# validation only requires) these, plus an honest "...and N more" tail.
CLOSURE_MENTION_CAP = 5


def assemble(
    corridor_id: str,
    origin: str,
    departure: datetime,
    snapshot: SierraSnapshot,
    forecast: PassForecast | None,
    outlook: SnowOutlook | None,
    vehicle: rules.Vehicle | None,
    now: datetime | None = None,
) -> TripFacts:
    now = now or datetime.now(UTC)
    corridor = CORRIDORS_BY_ID[corridor_id]
    roads = snapshot.corridors[corridor_id]

    controls = tuple(
        _cap(
            f"{c.location_name} ({c.direction}): {c.status} - {c.status_description}".strip(" -")
        )
        for c in roads.controls
        if control_tier(c) > Tier.R0
    )
    closures = tuple(
        _cap(
            f"{c.location_name} ({c.direction}): {c.type_of_closure} {c.type_of_work}".strip()
        )
        for c in roads.closures
    )

    mtn_pass = next((p for p in PASSES if p.corridor_id == corridor_id), None)
    alerts: tuple[str, ...] = ()
    window_periods: tuple[str, ...] = ()
    if forecast is not None:
        alerts = tuple(_cap(a.headline or a.event) for a in forecast.alerts)
        window_end = departure + timedelta(hours=DRIVE_WINDOW_HOURS)
        window_periods = tuple(
            f"{p.name}: {p.short}, {p.temperature_f} F, wind {p.wind}"
            for p in forecast.periods
            if p.start and p.end and p.start < window_end and p.end > departure
        )[:4]

    snow_before = None
    snow_during = None
    storm_start = None
    if outlook is not None and outlook.ok:
        hours_until_departure = max(
            0.0, (departure - now).total_seconds() / 3600
        )
        snow_before = outlook.accumulation_cm(int(hours_until_departure), now=now)
        snow_during = round(
            outlook.accumulation_cm(
                int(hours_until_departure) + DRIVE_WINDOW_HOURS, now=now
            )
            - snow_before,
            1,
        )
        storm_start = outlook.storm_start(now=now)

    ruling = rules.evaluate(roads.tier, vehicle) if vehicle is not None else None

    return TripFacts(
        corridor_id=corridor_id,
        corridor_name=corridor.name,
        route=corridor.display_route,
        origin=origin,
        departure=departure,
        tier=int(roads.tier),
        tier_label=tier_label(roads.tier),
        tier_meaning=TIER_MEANING[roads.tier],
        active_controls=controls,
        closures=closures,
        incident_count=len(roads.incidents),
        pass_name=mtn_pass.name if mtn_pass else "",
        alerts=alerts,
        forecast_window=window_periods,
        snow_before_arrival_cm=snow_before,
        snow_during_window_cm=snow_during,
        storm_start=storm_start,
        ruling=ruling,
        data_as_of=snapshot.data_as_of,
        stale=snapshot.stale,
        notes=tuple(snapshot.notes[:3]),
    )


def _pacific_clock(when: datetime) -> str:
    """'Sat 6:00 AM Pacific' - the clock a Sierra driver actually reads."""
    local = when.astimezone(PACIFIC)
    hour = local.strftime("%I").lstrip("0") or "12"
    return f"{local.strftime('%a')} {hour}:{local.strftime('%M %p')} Pacific"


def render_plain(facts: TripFacts) -> str:
    """Deterministic no-AI fallback brief, and the factual skeleton evals
    check against."""
    lines = [
        f"{facts.route} ({facts.corridor_name}), leaving {facts.origin} "
        f"{_pacific_clock(facts.departure)}.",
        f"Chain controls: {facts.tier_label}. {facts.tier_meaning}",
    ]
    if facts.active_controls:
        lines.append("Active control points:")
        lines.extend(f"- {c}" for c in facts.active_controls)
    if facts.closures:
        lines.append(f"Closures ({len(facts.closures)}):")
        lines.extend(f"- {c}" for c in facts.closures[:CLOSURE_MENTION_CAP])
        remaining = len(facts.closures) - CLOSURE_MENTION_CAP
        if remaining > 0:
            lines.append(f"- ...and {remaining} more closures")
    if facts.alerts:
        lines.append("Weather alerts: " + "; ".join(facts.alerts))
    if facts.forecast_window:
        lines.append("Forecast around your drive:")
        lines.extend(f"- {p}" for p in facts.forecast_window)
    if facts.snow_during_window_cm is not None and facts.snow_during_window_cm > 0:
        lines.append(
            f"Forecast snow during your drive window: "
            f"{facts.snow_during_window_cm:.0f} cm at {facts.pass_name}."
        )
    if facts.ruling is not None:
        lines.append(f"Your vehicle: {facts.ruling.reason}")
    when = _pacific_clock(facts.data_as_of) if facts.data_as_of else "unknown"
    suffix = " (cached)" if facts.stale else ""
    lines.append(f"Road data as of {when}{suffix}. Verify before you drive: 511 or "
                 "quickmap.dot.ca.gov.")
    return "\n".join(lines)
