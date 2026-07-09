from chaincheck.tiers import Tier, parse_tier, tier_label


def test_core_statuses():
    assert parse_tier("R-0") is Tier.R0
    assert parse_tier("R-1") is Tier.R1
    assert parse_tier("R-2") is Tier.R2
    assert parse_tier("R-3") is Tier.R3


def test_tolerates_case_and_whitespace():
    assert parse_tier("  r-2 ") is Tier.R2
    assert parse_tier("R2") is Tier.R2


def test_composite_status_takes_strictest_tier():
    assert parse_tier("R-2 / TS") is Tier.R2
    assert parse_tier("R-1 R-2") is Tier.R2


def test_closed():
    assert parse_tier("RC") is Tier.CLOSED
    assert parse_tier("Road Closed") is Tier.CLOSED


def test_unrecognized_is_unknown_not_r0():
    assert parse_tier("") is Tier.UNKNOWN
    assert parse_tier(None) is Tier.UNKNOWN
    assert parse_tier("TS") is Tier.UNKNOWN
    assert parse_tier("garbled") is Tier.UNKNOWN


def test_ordering():
    assert Tier.CLOSED > Tier.R3 > Tier.R2 > Tier.R1 > Tier.R0 > Tier.UNKNOWN


def test_labels():
    assert tier_label(Tier.R2) == "R2"
    assert tier_label(Tier.CLOSED) == "Closed"
    assert tier_label(Tier.UNKNOWN) == "Unknown"
