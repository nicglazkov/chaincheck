"""Chain-control tier parsing and ordering.

Caltrans district cc feeds report a checkpoint ``status`` string. The core
tiers are R-0 through R-3; feeds occasionally carry operational codes
(escorts, truck screening, closures) documented in the Caltrans chain control
status chart (cwwp2.dot.ca.gov/documentation/cc/cc-chart.htm).
"""

from __future__ import annotations

from enum import IntEnum

from ca_roads.models import ChainControl


class Tier(IntEnum):
    """Chain requirement tier, ordered by severity so tiers compare directly.

    CLOSED sorts above R3: a closed road is stricter than any requirement.
    UNKNOWN sorts below R0 so it never masks a real control.
    """

    UNKNOWN = -1
    R0 = 0
    R1 = 1
    R2 = 2
    R3 = 3
    CLOSED = 4


_STATUS_TO_TIER = {
    "R-0": Tier.R0,
    "R0": Tier.R0,
    "R-1": Tier.R1,
    "R1": Tier.R1,
    "R-2": Tier.R2,
    "R2": Tier.R2,
    "R-3": Tier.R3,
    "R3": Tier.R3,
    "RC": Tier.CLOSED,
    "ROAD CLOSED": Tier.CLOSED,
    "CLOSED": Tier.CLOSED,
}

# Operational codes that can ride along in a status string. They modify how a
# control point operates but do not change the requirement tier.
_OPERATIONAL_CODES = ("ESC", "TS", "TTA", "TTS", "TTSD", "VM", "W")

TIER_MEANING = {
    Tier.UNKNOWN: "Status unknown - check quickmap.dot.ca.gov or dial 511 before driving.",
    Tier.R0: "No chain controls in effect.",
    Tier.R1: (
        "Chains, traction devices or snow tires are required on the drive axle of all "
        "vehicles except four-wheel/all-wheel drive."
    ),
    Tier.R2: (
        "Chains or traction devices are required on all vehicles except four-wheel/"
        "all-wheel drive with snow-tread tires on all four wheels."
    ),
    Tier.R3: "Chains or traction devices are required on all vehicles. No exceptions.",
    Tier.CLOSED: "Road closed to traffic.",
}


def parse_tier(status: str | None) -> Tier:
    """Map a raw feed status string to a :class:`Tier`.

    Tolerates whitespace, case, and trailing operational codes ("R-2 / TS").
    Anything unrecognized is UNKNOWN, never silently R0.
    """
    if not status:
        return Tier.UNKNOWN
    text = status.strip().upper()
    if text in _STATUS_TO_TIER:
        return _STATUS_TO_TIER[text]
    # Composite strings: find the strictest tier token present.
    found = [
        tier
        for token, tier in _STATUS_TO_TIER.items()
        if token in text
    ]
    if found:
        return max(found)
    if any(code in text.split() for code in _OPERATIONAL_CODES):
        # Purely operational status (e.g. truck screening) with no tier given.
        return Tier.UNKNOWN
    return Tier.UNKNOWN


def control_tier(control: ChainControl) -> Tier:
    """Tier for one feed record. Out-of-service checkpoints report nothing."""
    if not control.in_service:
        return Tier.UNKNOWN
    return parse_tier(control.status)


def tier_label(tier: Tier) -> str:
    """Short display label ("R2", "Closed")."""
    if tier is Tier.CLOSED:
        return "Closed"
    if tier is Tier.UNKNOWN:
        return "Unknown"
    return f"R{int(tier)}"
