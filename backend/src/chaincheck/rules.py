"""Vehicle chain-requirement rules for each control tier.

Encodes the published Caltrans requirements as structured logic. Sources,
both retrieved 2026-07-09:

- Caltrans "Chain Controls / Chain Installation"
  (dot.ca.gov/travel/winter-driving-tips/chain-controls):
  R-1: "Chains are required on all vehicles except passenger vehicles and
  light-duty trucks under 6,000 pounds gross weight and equipped with snow
  tires on at least two drive wheels." Vehicles using snow tires must carry
  chains; vehicles towing trailers must have chains on one drive axle.
  R-2: "Chains or traction devices are required on all vehicles except
  four-wheel/all-wheel drive vehicles with snow-tread tires on all four
  wheels." 4WD/AWD must still carry traction devices.
  R-3: "Chains or traction devices are required on all vehicles, no
  exceptions."
- Caltrans chain control status chart
  (cwwp2.dot.ca.gov/documentation/cc/cc-chart.htm) for feed-status semantics,
  including the R-1 four-wheel-drive drive-axle exemption.

Additional notes from the Caltrans "Chain Requirements" diagram (rev 10/16):
all vehicles, including 4WD/AWD, must carry chains upon entering a chain
control area; "chains" means any tire traction device meeting CVC section
605; minimum legal mud-and-snow tread depth is 6/32 inch.

This module is the single source of truth for what a given vehicle must do
under a given tier. The AI trip brief presents this output; it never
computes or alters it. Answers are requirements, not driving advice: whether
conditions are safe is always the driver's call.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from chaincheck.tiers import Tier


class Drivetrain(Enum):
    TWO_WHEEL = "2wd"
    FOUR_WHEEL = "4wd_awd"


class Tires(Enum):
    """Snow-rated (M+S, at least 6/32" tread) tire fitment."""

    NO_SNOW = "no_snow"
    SNOW_DRIVE_AXLE = "snow_drive_axle"
    SNOW_ALL_FOUR = "snow_all_four"


class Requirement(Enum):
    NONE = "none"
    CARRY = "carry_chains"
    INSTALL = "install_chains"
    CLOSED = "road_closed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Vehicle:
    drivetrain: Drivetrain
    tires: Tires
    over_6000_lbs: bool = False
    towing: bool = False


@dataclass(frozen=True)
class Ruling:
    requirement: Requirement
    reason: str


_CARRY_NOTE = (
    "All vehicles, including four-wheel/all-wheel drive, must carry chains when "
    "entering a chain control area."
)


def evaluate(tier: Tier, vehicle: Vehicle) -> Ruling:
    """What this vehicle must do under this tier, per published Caltrans rules."""
    if tier is Tier.CLOSED:
        return Ruling(Requirement.CLOSED, "The road is closed to all traffic.")
    if tier is Tier.UNKNOWN:
        return Ruling(
            Requirement.UNKNOWN,
            "Control status is unknown. Carry chains and check Caltrans (dial 511 or "
            "quickmap.dot.ca.gov) before driving.",
        )
    if tier is Tier.R0:
        return Ruling(Requirement.NONE, "No chain controls are in effect on this stretch.")

    if vehicle.towing:
        # No towing exemption at any tier: chains go on one drive axle, and
        # trailers with brakes need chains on one axle too.
        return Ruling(
            Requirement.INSTALL,
            "Vehicles towing trailers must have chains on one drive axle at any chain "
            "control level, including four-wheel/all-wheel drive. Trailers with brakes "
            "need chains on one trailer axle.",
        )

    if tier is Tier.R1:
        if vehicle.drivetrain is Drivetrain.FOUR_WHEEL:
            return Ruling(
                Requirement.CARRY,
                "R1: four-wheel/all-wheel drive vehicles are exempt from installing "
                f"chains. {_CARRY_NOTE}",
            )
        if (
            not vehicle.over_6000_lbs
            and vehicle.tires in (Tires.SNOW_DRIVE_AXLE, Tires.SNOW_ALL_FOUR)
        ):
            return Ruling(
                Requirement.CARRY,
                "R1: passenger vehicles and light-duty trucks under 6,000 lbs gross "
                "weight with snow tires on at least two drive wheels are exempt from "
                f"installing chains. {_CARRY_NOTE}",
            )
        if vehicle.over_6000_lbs:
            return Ruling(
                Requirement.INSTALL,
                "R1: the snow-tire exemption only covers vehicles under 6,000 lbs gross "
                "weight. Install chains or traction devices on the drive axle.",
            )
        return Ruling(
            Requirement.INSTALL,
            "R1: without snow-rated (M+S) tires on the drive wheels, chains or "
            "traction devices must be installed on the drive axle.",
        )

    if tier is Tier.R2:
        if (
            vehicle.drivetrain is Drivetrain.FOUR_WHEEL
            and vehicle.tires is Tires.SNOW_ALL_FOUR
        ):
            return Ruling(
                Requirement.CARRY,
                "R2: four-wheel/all-wheel drive vehicles with snow-tread tires on all "
                f"four wheels are exempt from installing chains. {_CARRY_NOTE}",
            )
        if vehicle.drivetrain is Drivetrain.FOUR_WHEEL:
            return Ruling(
                Requirement.INSTALL,
                "R2: the four-wheel/all-wheel drive exemption requires snow-tread tires "
                "on all four wheels. Without them, chains or traction devices must be "
                "installed.",
            )
        return Ruling(
            Requirement.INSTALL,
            "R2: chains or traction devices are required on all two-wheel drive "
            "vehicles regardless of tires.",
        )

    # Tier.R3
    return Ruling(
        Requirement.INSTALL,
        "R3: chains or traction devices are required on all vehicles. No exceptions.",
    )
