"""Exhaustive checks of the chain-requirement rules against the published
Caltrans definitions (see chaincheck.rules docstring for sources)."""

import itertools

import pytest

from chaincheck.rules import Drivetrain, Requirement, Ruling, Tires, Vehicle, evaluate
from chaincheck.tiers import Tier

ALL_VEHICLES = [
    Vehicle(drivetrain=d, tires=t, over_6000_lbs=w, towing=tow)
    for d, t, w, tow in itertools.product(
        Drivetrain, Tires, (False, True), (False, True)
    )
]


def req(tier: Tier, vehicle: Vehicle) -> Requirement:
    return evaluate(tier, vehicle).requirement


def test_r0_never_requires_anything():
    for v in ALL_VEHICLES:
        assert req(Tier.R0, v) is Requirement.NONE


def test_r3_requires_install_for_every_vehicle():
    """R-3: chains on all vehicles, no exceptions."""
    for v in ALL_VEHICLES:
        assert req(Tier.R3, v) is Requirement.INSTALL


def test_closed_and_unknown():
    for v in ALL_VEHICLES:
        assert req(Tier.CLOSED, v) is Requirement.CLOSED
        assert req(Tier.UNKNOWN, v) is Requirement.UNKNOWN


def test_towing_always_installs_at_r1_and_r2():
    """No towing exemption at any tier, including 4WD/AWD."""
    for v in ALL_VEHICLES:
        if v.towing:
            assert req(Tier.R1, v) is Requirement.INSTALL
            assert req(Tier.R2, v) is Requirement.INSTALL


# R-1: "Chains are required on all vehicles except passenger vehicles and
# light-duty trucks under 6,000 pounds gross weight and equipped with snow
# tires on at least two drive wheels." Feed chart additionally exempts
# 4WD/AWD from the drive-axle requirement at R-1.
R1_CASES = [
    # (drivetrain, tires, over6k, towing) -> requirement
    ((Drivetrain.TWO_WHEEL, Tires.NO_SNOW, False, False), Requirement.INSTALL),
    ((Drivetrain.TWO_WHEEL, Tires.SNOW_DRIVE_AXLE, False, False), Requirement.CARRY),
    ((Drivetrain.TWO_WHEEL, Tires.SNOW_ALL_FOUR, False, False), Requirement.CARRY),
    ((Drivetrain.TWO_WHEEL, Tires.SNOW_DRIVE_AXLE, True, False), Requirement.INSTALL),
    ((Drivetrain.TWO_WHEEL, Tires.SNOW_ALL_FOUR, True, False), Requirement.INSTALL),
    ((Drivetrain.TWO_WHEEL, Tires.NO_SNOW, True, False), Requirement.INSTALL),
    ((Drivetrain.FOUR_WHEEL, Tires.NO_SNOW, False, False), Requirement.CARRY),
    ((Drivetrain.FOUR_WHEEL, Tires.SNOW_ALL_FOUR, False, False), Requirement.CARRY),
    ((Drivetrain.FOUR_WHEEL, Tires.SNOW_ALL_FOUR, True, False), Requirement.CARRY),
    ((Drivetrain.FOUR_WHEEL, Tires.NO_SNOW, False, True), Requirement.INSTALL),
    ((Drivetrain.TWO_WHEEL, Tires.SNOW_DRIVE_AXLE, False, True), Requirement.INSTALL),
]


@pytest.mark.parametrize(("combo", "expected"), R1_CASES)
def test_r1_table(combo, expected):
    d, t, w, tow = combo
    assert req(Tier.R1, Vehicle(d, t, w, tow)) is expected


# R-2: "Chains or traction devices are required on all vehicles except
# four-wheel/all-wheel drive vehicles with snow-tread tires on all four
# wheels." (Those still must carry.)
R2_CASES = [
    ((Drivetrain.FOUR_WHEEL, Tires.SNOW_ALL_FOUR, False, False), Requirement.CARRY),
    ((Drivetrain.FOUR_WHEEL, Tires.SNOW_ALL_FOUR, True, False), Requirement.CARRY),
    ((Drivetrain.FOUR_WHEEL, Tires.SNOW_DRIVE_AXLE, False, False), Requirement.INSTALL),
    ((Drivetrain.FOUR_WHEEL, Tires.NO_SNOW, False, False), Requirement.INSTALL),
    ((Drivetrain.TWO_WHEEL, Tires.SNOW_ALL_FOUR, False, False), Requirement.INSTALL),
    ((Drivetrain.TWO_WHEEL, Tires.SNOW_DRIVE_AXLE, False, False), Requirement.INSTALL),
    ((Drivetrain.TWO_WHEEL, Tires.NO_SNOW, False, False), Requirement.INSTALL),
    ((Drivetrain.FOUR_WHEEL, Tires.SNOW_ALL_FOUR, False, True), Requirement.INSTALL),
]


@pytest.mark.parametrize(("combo", "expected"), R2_CASES)
def test_r2_table(combo, expected):
    d, t, w, tow = combo
    assert req(Tier.R2, Vehicle(d, t, w, tow)) is expected


def test_every_combination_yields_a_ruling_with_reason():
    for tier in Tier:
        for v in ALL_VEHICLES:
            ruling = evaluate(tier, v)
            assert isinstance(ruling, Ruling)
            assert ruling.reason


def test_no_ruling_ever_promises_safety():
    """Safety tone rule: requirements only, never 'you'll be fine'."""
    banned = ("you'll make it", "you will make it", "safe to drive", "no need to worry")
    for tier in Tier:
        for v in ALL_VEHICLES:
            reason = evaluate(tier, v).reason.lower()
            assert not any(b in reason for b in banned)
