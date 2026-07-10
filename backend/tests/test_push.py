from tests.test_differ import snapshot_with

from chaincheck.feeds.nws import WinterAlert
from chaincheck.push import dispatch
from chaincheck.push.fcm import RecordingSender
from chaincheck.push.subscriptions import InMemorySubscriptionStore, validate_corridors
from chaincheck.tiers import Tier
from chaincheck.watcher import differ


def make_alert(alert_id: str, event: str = "Winter Storm Warning") -> WinterAlert:
    return WinterAlert(
        id=alert_id,
        event=event,
        severity="Severe",
        headline=f"{event} in effect",
        onset=None,
        ends=None,
        description="",
    )


def test_validate_corridors():
    assert validate_corridors(["i80", "nope", "US50", "i80", " sr88 "]) == [
        "i80",
        "us50",
        "sr88",
    ]


async def test_subscription_store_roundtrip():
    store = InMemorySubscriptionStore()
    await store.upsert("tok1", ["i80", "us50"])
    await store.upsert("tok2", ["us50"])

    sub = await store.get("tok1")
    assert sub is not None and sub.corridor_ids == ["i80", "us50"]
    assert await store.tokens_for_corridor("us50") == ["tok1", "tok2"]
    assert await store.tokens_for_corridor("i80") == ["tok1"]
    assert await store.delete("tok1")
    assert not await store.delete("tok1")
    assert await store.tokens_for_corridor("i80") == []


async def test_dispatch_matches_watched_corridor_only():
    store = InMemorySubscriptionStore()
    sender = RecordingSender()
    await store.upsert("i80-watcher", ["i80"])
    await store.upsert("us50-watcher", ["us50"])

    _, state = differ.diff(differ.WatchState.empty(), snapshot_with({"i80": Tier.R0}))
    events, _ = differ.diff(state, snapshot_with({"i80": Tier.R2}))
    sent = await dispatch.dispatch(events, store, sender)

    assert sent == 1
    assert len(sender.sent) == 1
    token, message = sender.sent[0]
    assert token == "i80-watcher"
    assert message.kind == "tier_change"
    assert "R2" in message.body and "I-80" in message.body


async def test_storm_warning_diff_and_dispatch():
    store = InMemorySubscriptionStore()
    sender = RecordingSender()
    await store.upsert("donner-driver", ["i80"])

    state = differ.WatchState.empty()
    # First sight of the pass establishes baseline, no event.
    events, state = differ.diff_alerts(state, {"donner": []})
    assert events == []
    events, state = differ.diff_alerts(state, {"donner": [make_alert("a1")]})
    assert len(events) == 1
    assert "Winter Storm Warning" in events[0].summary()
    assert "Donner" in events[0].summary()

    sent = await dispatch.dispatch(events, store, sender)
    assert sent == 1
    assert sender.sent[0][1].kind == "storm_warning"

    # Same alert again: no repeat notification.
    events, state = differ.diff_alerts(state, {"donner": [make_alert("a1")]})
    assert events == []


async def test_dispatch_no_subscribers_sends_nothing():
    store = InMemorySubscriptionStore()
    sender = RecordingSender()
    _, state = differ.diff(differ.WatchState.empty(), snapshot_with({"us50": Tier.R0}))
    events, _ = differ.diff(state, snapshot_with({"us50": Tier.R1}))
    sent = await dispatch.dispatch(events, store, sender)
    assert sent == 0
    assert sender.sent == []


async def test_dispatch_prunes_dead_tokens():
    from chaincheck.push.fcm import PushMessage, SendReport

    store = InMemorySubscriptionStore()
    await store.upsert("live-token", ["i80"])
    await store.upsert("dead-token", ["i80"])

    class DeadTokenSender:
        async def send(self, tokens: list[str], message: PushMessage) -> SendReport:
            return SendReport(
                sent=len(tokens) - 1, dead_tokens=["dead-token"]
            )

    _, state = differ.diff(differ.WatchState.empty(), snapshot_with({"i80": Tier.R0}))
    events, _ = differ.diff(state, snapshot_with({"i80": Tier.R2}))
    sent = await dispatch.dispatch(events, store, DeadTokenSender())

    assert sent == 1
    # The uninstalled device is gone; the live one remains.
    assert await store.get("dead-token") is None
    assert await store.tokens_for_corridor("i80") == ["live-token"]
