"""Run the trip-brief eval set against the live model.

Usage: ANTHROPIC_API_KEY=... python -m evals.run_tripbrief [--limit N]

The service itself validates every narrated brief (completeness, no invented
road states, no banned phrases) and falls back to the deterministic rendering
on any problem - so what this eval measures is:
- expected key facts present in whatever text would actually ship,
- how often the model's narration fails validation (fallback rate).

Exit nonzero when a shipped brief misses an expected fact or the fallback
rate exceeds MAX_FALLBACKS.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from chaincheck.brief.tripbrief import TripBriefer
from evals.scenarios import SCENARIOS, build_facts

MAX_FALLBACKS = 3


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    briefer = TripBriefer()
    if not briefer.available():
        print("ANTHROPIC_API_KEY not set; cannot run live evals.")
        return 2

    scenarios = SCENARIOS[: args.limit] if args.limit else SCENARIOS
    failures = 0
    fallbacks = 0
    for scenario in scenarios:
        facts = build_facts(scenario)
        result = await briefer.narrate(facts)
        problems = []
        lowered = result.text.lower()
        for expected in scenario.expect_substrings:
            if expected.lower() not in lowered:
                problems.append(f"missing expected fact: {expected!r}")
        if not result.ai:
            fallbacks += 1
            status = "FALLBACK" if not problems else "FAIL"
        else:
            status = "PASS" if not problems else "FAIL"
        if problems:
            failures += 1
        print(f"[{status}] {scenario.id}")
        for problem in problems:
            print(f"    - {problem}")

    narrated = len(scenarios) - fallbacks
    print(
        f"\n{len(scenarios) - failures}/{len(scenarios)} shippable briefs carried all "
        f"expected facts; {narrated} AI-narrated, {fallbacks} fell back to plain."
    )
    if fallbacks > MAX_FALLBACKS:
        print(f"Fallback rate too high (> {MAX_FALLBACKS}).")
        return 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
