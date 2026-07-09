"""AI trip brief: Claude Haiku narrates the assembled facts.

Hard rules, enforced structurally:
- The model sees ONLY the structured facts (facts.render_plain output plus
  the facts JSON) - it has no tools and no other context, so it cannot know
  road states we didn't give it.
- The vehicle ruling is appended verbatim after generation; the model is
  told not to restate it, and whatever it says can't replace the ruling.
- No key / API failure -> the deterministic plain rendering ships instead.
- Cached per (corridor, origin, departure-hour, vehicle) for an hour.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass

from ca_roads.cache import TTLCache

from chaincheck.brief import facts as facts_mod
from chaincheck.brief import validate
from chaincheck.brief.facts import TripFacts

logger = logging.getLogger(__name__)

MODEL = os.environ.get("BRIEF_MODEL", "claude-haiku-4-5-20251001")
CACHE_TTL = 60 * 60
CACHE_MAX_SERVE = 4 * 60 * 60
MAX_TOKENS = 700

SYSTEM_PROMPT = """\
You write short pre-drive briefs for winter Sierra trips. You are given a
set of verified facts about one route. Rules, absolute:
- Use ONLY the facts provided. Never invent, guess, or soften a road state,
  control level, closure, or forecast. If a fact isn't listed, don't mention it.
- The first sentence must name the origin and state the current control level
  by its exact label from the facts (R0, R1, R2, R3, or Closed).
- Never mention a control level that does not appear in the facts - not even
  hypothetically ("could go to R2") or as an explanation of the scale.
- Every active chain control point and every listed closure MUST appear in
  the brief by its exact location name - do not summarize closures into a
  count or "several construction zones". Name weather alerts exactly as given.
- Never suggest the driver will be fine without chains or that conditions are
  safe. Requirements and conditions only; the decision is the driver's.
- Plain prose only: no markdown, no headers, no bold, no bullet lists.
  120-220 words, ordered: the answer right now, what changes during their
  drive window, what to bring/do.
- End with: verify before driving (511 or quickmap.dot.ca.gov).
"""


@dataclass
class BriefResult:
    text: str
    ai: bool
    model: str | None
    cached: bool
    facts: TripFacts


class TripBriefer:
    def __init__(self) -> None:
        self._cache = TTLCache()
        self._client = None

    def _anthropic(self):
        if self._client is None:
            import anthropic

            # Secret-manager/console-pasted keys often carry a trailing
            # newline, which corrupts the auth header; strip defensively.
            self._client = anthropic.AsyncAnthropic(
                api_key=os.environ["ANTHROPIC_API_KEY"].strip()
            )
        return self._client

    def available(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())

    async def narrate(self, facts: TripFacts) -> BriefResult:
        plain = facts_mod.render_plain(facts)
        if not self.available():
            return BriefResult(text=plain, ai=False, model=None, cached=False, facts=facts)

        # The key carries a digest of every fact that must survive into the
        # narration; if controls, closures, or alerts change mid-hour the
        # cache misses instead of serving a brief about the old facts.
        material = "|".join(
            (
                facts.tier_label,
                *facts.active_controls,
                *facts.closures[: facts_mod.CLOSURE_MENTION_CAP],
                *facts.alerts,
            )
        )
        key = (
            facts.corridor_id,
            facts.origin.lower().strip(),
            facts.departure.strftime("%Y-%m-%dT%H"),
            facts.ruling.requirement.value if facts.ruling else None,
            hashlib.sha256(material.encode()).hexdigest()[:16],
        )

        user_prompt = (
            "Facts for this brief (the only truth you have):\n\n"
            f"{plain}\n\n"
            "Write the brief. Do not restate the vehicle-requirement "
            "sentence verbatim; it will be appended after your text."
        )

        async def generate(messages: list[dict]) -> str:
            message = await self._anthropic().messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
            return "".join(
                block.text for block in message.content if block.type == "text"
            ).strip()

        async def fetch() -> str:
            """Validated narration, retried once with feedback. Returns ""
            (cached) when both drafts fail validation, so a bad-narration
            hour serves the plain rendering without regenerating per request.
            Only validated text or that empty marker ever enters the cache."""
            draft = await generate([{"role": "user", "content": user_prompt}])
            found = validate.problems(draft, facts)
            if not found:
                return draft
            retry = await generate(
                [
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": draft},
                    {
                        "role": "user",
                        "content": (
                            "That draft fails these checks:\n- "
                            + "\n- ".join(found)
                            + "\nRewrite the full brief fixing every one of them."
                        ),
                    },
                ]
            )
            found = validate.problems(retry, facts)
            if not found:
                return retry
            logger.warning(
                "trip brief for %s failed validation twice, using plain "
                "rendering: %s",
                facts.corridor_id,
                "; ".join(found),
            )
            return ""

        outcome = await self._cache.get(key, CACHE_TTL, CACHE_MAX_SERVE, fetch)
        if not outcome.served or not outcome.value:
            if outcome.error:
                logger.warning(
                    "trip brief narration failed for %s, using plain rendering: %s",
                    facts.corridor_id,
                    outcome.error,
                )
            return BriefResult(text=plain, ai=False, model=None, cached=False, facts=facts)

        text = str(outcome.value)
        # Safety net: even a cache hit must validate against the facts being
        # answered right now (cheap and deterministic).
        leftover = validate.problems(text, facts)
        if leftover:
            logger.warning(
                "cached trip brief for %s no longer matches current facts, "
                "using plain rendering: %s",
                facts.corridor_id,
                "; ".join(leftover),
            )
            return BriefResult(text=plain, ai=False, model=None, cached=False, facts=facts)
        if facts.ruling is not None:
            text = f"{text}\n\nYour vehicle: {facts.ruling.reason}"
        from datetime import UTC, datetime

        age = (
            (datetime.now(UTC) - outcome.fetched_at).total_seconds()
            if outcome.fetched_at
            else 0.0
        )
        return BriefResult(
            text=text,
            ai=True,
            model=MODEL,
            cached=age > 5.0,
            facts=facts,
        )
