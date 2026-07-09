"""Offline half of the trip-brief evals: the deterministic rendering must
already carry every expected fact, so the AI layer starts from complete
truth. Also pins the scenario count the brief calls for."""

import pytest
from evals.scenarios import BANNED_PHRASES, SCENARIOS, build_facts

from chaincheck.brief import facts as brief_facts


def test_scenario_set_is_full_size():
    assert len(SCENARIOS) >= 25


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.id)
def test_plain_rendering_contains_expected_facts(scenario):
    facts = build_facts(scenario)
    text = brief_facts.render_plain(facts)
    lowered = text.lower()
    for expected in scenario.expect_substrings:
        assert expected.lower() in lowered, f"missing {expected!r} in:\n{text}"
    for location, _ in scenario.controls:
        assert location.lower() in lowered, f"control {location} missing in:\n{text}"
    for banned in BANNED_PHRASES:
        assert banned not in lowered
    assert "511" in text


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.id)
def test_facts_tier_matches_scenario(scenario):
    facts = build_facts(scenario)
    assert facts.tier == int(scenario.tier)
