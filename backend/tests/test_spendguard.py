"""Spend guard: the ceilings that protect the Anthropic budget once the
API is public, and the narrate() degradation path when a ceiling is hit."""

from evals.scenarios import SCENARIOS, build_facts

from chaincheck.brief import facts as brief_facts
from chaincheck.brief.spendguard import SpendGuard
from chaincheck.brief.tripbrief import TripBriefer


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def make_guard(clock, per_client=3, global_daily=10):
    return SpendGuard(
        per_client_hourly=per_client, global_daily=global_daily, clock=clock
    )


def test_per_client_ceiling_and_hourly_window():
    clock = Clock()
    guard = make_guard(clock)
    assert all(guard.allow("1.2.3.4") for _ in range(3))
    assert not guard.allow("1.2.3.4")
    # Another client is unaffected.
    assert guard.allow("5.6.7.8")
    # The window slides: an hour later the first client may generate again.
    clock.now += 3600.0
    assert guard.allow("1.2.3.4")


def test_global_daily_ceiling_blocks_everyone():
    clock = Clock()
    guard = make_guard(clock, per_client=100, global_daily=5)
    assert all(guard.allow(f"10.0.0.{i}") for i in range(5))
    assert not guard.allow("10.0.0.99")
    # A day later the budget refills.
    clock.now += 24 * 3600.0
    assert guard.allow("10.0.0.99")


def test_unknown_clients_share_one_allowance():
    clock = Clock()
    guard = make_guard(clock, per_client=2)
    assert guard.allow(None)
    assert guard.allow(None)
    assert not guard.allow(None)


def test_denied_attempts_consume_nothing():
    clock = Clock()
    guard = make_guard(clock, per_client=1, global_daily=2)
    assert guard.allow("a")
    for _ in range(10):
        assert not guard.allow("a")
    # The global budget still has room for another client.
    assert guard.allow("b")


def test_client_table_sweep_bounds_memory():
    clock = Clock()
    guard = make_guard(clock, per_client=1, global_daily=10**9)
    import chaincheck.brief.spendguard as sg

    for i in range(sg._SWEEP_THRESHOLD + 10):
        guard.allow(f"client-{i}")
    clock.now += 3600.0
    # Every entry is now stale; the next new client triggers the sweep.
    guard.allow("fresh")
    assert len(guard._clients) <= 2


async def test_narrate_degrades_to_plain_when_budget_exhausted(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    clock = Clock()
    briefer = TripBriefer(guard=make_guard(clock, per_client=0, global_daily=0))

    def boom(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("model called despite exhausted budget")

    briefer._anthropic = boom
    facts = build_facts(SCENARIOS[0])
    result = await briefer.narrate(facts, client="1.2.3.4")
    assert result.ai is False
    assert result.text == brief_facts.render_plain(facts)


async def test_cache_hit_is_free_after_budget_exhausted(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    clock = Clock()
    briefer = TripBriefer(guard=make_guard(clock, per_client=1, global_daily=1))
    facts = build_facts(SCENARIOS[0])
    valid_text = brief_facts.render_plain(facts)

    calls = {"n": 0}

    class FakeMessages:
        async def create(self, **kwargs):
            calls["n"] += 1

            class Block:
                type = "text"
                text = valid_text

            class Msg:
                content = [Block()]

            return Msg()

    class FakeClient:
        messages = FakeMessages()

    briefer._client = FakeClient()

    first = await briefer.narrate(facts, client="1.2.3.4")
    assert first.ai is True and calls["n"] == 1
    # Budget is now exhausted, but the cached brief still serves as AI.
    second = await briefer.narrate(facts, client="1.2.3.4")
    assert second.ai is True and calls["n"] == 1
