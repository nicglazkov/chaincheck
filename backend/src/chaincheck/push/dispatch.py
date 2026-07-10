"""Match watcher events to subscriptions and send pushes."""

from __future__ import annotations

import logging

from chaincheck.push.fcm import PushMessage, PushSender
from chaincheck.push.subscriptions import SubscriptionStore
from chaincheck.watcher.differ import ClosureChange, StormWarning, TierChange

logger = logging.getLogger(__name__)

APP_TITLE = "ChainCheck"


def message_for(event: object) -> PushMessage | None:
    if isinstance(event, TierChange):
        return PushMessage(
            title=APP_TITLE, body=event.summary(),
            corridor_id=event.corridor_id, kind="tier_change",
        )
    if isinstance(event, ClosureChange):
        return PushMessage(
            title=APP_TITLE, body=event.summary(),
            corridor_id=event.corridor_id, kind="closure",
        )
    if isinstance(event, StormWarning):
        return PushMessage(
            title=APP_TITLE, body=event.summary(),
            corridor_id=event.corridor_id, kind="storm_warning",
        )
    return None


async def dispatch(
    events: list[object], store: SubscriptionStore, sender: PushSender
) -> int:
    """Send each event to the tokens watching its corridor. Returns sends."""
    sent = 0
    for event in events:
        message = message_for(event)
        if message is None:
            continue
        try:
            tokens = await store.tokens_for_corridor(message.corridor_id)
        except Exception:
            logger.exception("subscription lookup failed for %s", message.corridor_id)
            continue
        if not tokens:
            continue
        try:
            report = await sender.send(tokens, message)
        except Exception:
            logger.exception("push send failed for %s", message.corridor_id)
            continue
        sent += report.sent
        for token in report.dead_tokens:
            try:
                await store.delete(token)
            except Exception:
                logger.exception("failed to prune dead token %s...", token[:12])
        if report.dead_tokens:
            logger.info("pruned %d dead subscriptions", len(report.dead_tokens))
    return sent
