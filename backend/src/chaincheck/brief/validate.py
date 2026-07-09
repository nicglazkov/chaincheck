"""Completeness/safety validation for narrated briefs.

Shared by the live service (a brief failing validation is discarded in favor
of the deterministic rendering) and the eval runner (which reports the same
problems).
"""

from __future__ import annotations

import re

from chaincheck.brief.facts import TripFacts

BANNED_PHRASES = (
    "you'll make it",
    "you will make it",
    "safe to drive",
    "won't need chains",
    "will not need chains",
    "no need to worry",
    "don't worry",
    "should be fine",
    "you'll be fine",
)

TIER_TOKENS = ("R0", "R1", "R2", "R3")


def problems(text: str, facts: TripFacts) -> list[str]:
    found: list[str] = []
    lowered = text.lower()

    if facts.tier_label not in text:
        found.append(f"current control level {facts.tier_label} not stated")
    for control in facts.active_controls:
        location = control.split(" (")[0]
        if location.lower() not in lowered:
            found.append(f"active control not mentioned: {location}")
    for closure in facts.closures:
        location = closure.split(" (")[0]
        if location.lower() not in lowered:
            found.append(f"closure not mentioned: {location}")
    for alert in facts.alerts:
        # The alert's event name must survive; headlines may be shortened.
        event = alert.split(" until ")[0]
        if event.lower() not in lowered:
            found.append(f"weather alert not mentioned: {event}")
    for token in TIER_TOKENS:
        if token == facts.tier_label:
            continue
        if re.search(rf"\b{token}\b", text) and token not in facts.tier_meaning:
            found.append(f"invented road state: mentions {token}")
    for banned in BANNED_PHRASES:
        if banned in lowered:
            found.append(f"banned phrase: {banned!r}")
    if "511" not in text and "quickmap" not in lowered:
        found.append("missing verify-before-driving pointer")
    return found
