"""Completeness/safety validation for narrated briefs.

Shared by the live service (a brief failing validation is discarded in favor
of the deterministic rendering) and the eval runner (which reports the same
problems).
"""

from __future__ import annotations

import re

from chaincheck.brief.facts import CLOSURE_MENTION_CAP, TripFacts

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


# Caltrans feeds abbreviate road suffixes; the model tends to write them out
# ("Drum Forebay Rd" -> "Drum Forebay Road"). Both spellings name the same
# place, so both sides are canonicalized before comparing.
_ROAD_SUFFIXES = {
    "rd": "road",
    "st": "street",
    "ave": "avenue",
    "blvd": "boulevard",
    "hwy": "highway",
    "dr": "drive",
    "ln": "lane",
    "ct": "court",
    "pkwy": "parkway",
}
_SUFFIX_RE = re.compile(
    r"\b(" + "|".join(_ROAD_SUFFIXES) + r")\b\.?", flags=re.IGNORECASE
)


def _canonical(text: str) -> str:
    expanded = _SUFFIX_RE.sub(lambda m: _ROAD_SUFFIXES[m.group(1).lower()], text)
    return re.sub(r"\s+", " ", expanded.lower())


def _mentions(lowered_text: str, location: str) -> bool:
    """Whether a location is named, tolerating slash/whitespace reformatting
    and abbreviation expansion.

    "Five Mile Rd / Paul Bunyon Rd" counts as mentioned when each component
    name appears, so "Five Mile Road/Paul Bunyon Rd" and reordered forms pass;
    a brief that names neither road still fails.
    """
    squeezed = _canonical(lowered_text)
    for part in location.split("/"):
        part = _canonical(part).strip()
        if part and part not in squeezed:
            return False
    return True


def problems(text: str, facts: TripFacts) -> list[str]:
    found: list[str] = []
    lowered = text.lower()

    if facts.tier_label not in text:
        found.append(f"current control level {facts.tier_label} not stated")
    for control in facts.active_controls:
        location = control.split(" (")[0]
        if not _mentions(lowered, location):
            found.append(f"active control not mentioned: {location}")
    # Only the closures the model was actually shown (render_plain caps the
    # list); requiring the ones it never saw guarantees failure.
    for closure in facts.closures[:CLOSURE_MENTION_CAP]:
        location = closure.split(" (")[0]
        if not _mentions(lowered, location):
            found.append(f"closure not mentioned: {location}")
    for alert in facts.alerts:
        # The alert's event name must survive; headlines may be shortened.
        event = alert.split(" until ")[0]
        if event.lower() not in lowered:
            found.append(f"weather alert not mentioned: {event}")
    # A tier token is legitimate when it appears anywhere in the facts the
    # model was given - e.g. a corridor at R2 whose Meyers checkpoint reads
    # R-1. Only tokens absent from the whole facts corpus are "invented".
    corpus = " ".join((facts.tier_label, facts.tier_meaning, *facts.active_controls))
    for token in TIER_TOKENS:
        legitimate = token in corpus or token.replace("R", "R-") in corpus
        if not legitimate and re.search(rf"\b{token}\b", text):
            found.append(f"invented road state: mentions {token}")
    for banned in BANNED_PHRASES:
        if banned in lowered:
            found.append(f"banned phrase: {banned!r}")
    if "511" not in text and "quickmap" not in lowered:
        found.append("missing verify-before-driving pointer")
    return found
