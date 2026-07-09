"""FCM dispatch behind a small interface.

Notification discipline (product rule): pushes go only to tokens watching the
affected corridor, only for tier changes, closures, and storm warnings.
Nothing promotional, ever.

Local dev and tests use the recording sender; production initializes
firebase-admin from Cloud Run's default credentials. firebase-admin's send is
blocking, so it runs in a thread.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PushMessage:
    title: str
    body: str
    corridor_id: str
    kind: str  # "tier_change" | "closure" | "storm_warning"


class PushSender(Protocol):
    async def send(self, tokens: list[str], message: PushMessage) -> int:
        """Send to tokens; returns the number of successful sends."""
        ...


@dataclass
class RecordingSender:
    """Dev/test sender: records instead of sending."""

    sent: list[tuple[str, PushMessage]] = field(default_factory=list)

    async def send(self, tokens: list[str], message: PushMessage) -> int:
        self.sent.extend((t, message) for t in tokens)
        logger.info("push (dry-run) to %d tokens: %s", len(tokens), message.title)
        return len(tokens)


class FcmSender:
    def __init__(self, project: str | None = None) -> None:
        import firebase_admin

        if not firebase_admin._apps:
            options = {"projectId": project} if project else None
            firebase_admin.initialize_app(options=options)

    async def send(self, tokens: list[str], message: PushMessage) -> int:
        if not tokens:
            return 0
        from firebase_admin import messaging

        def _send() -> int:
            multicast = messaging.MulticastMessage(
                tokens=tokens,
                notification=messaging.Notification(
                    title=message.title, body=message.body
                ),
                data={"corridor_id": message.corridor_id, "kind": message.kind},
                android=messaging.AndroidConfig(priority="high"),
            )
            response = messaging.send_each_for_multicast(multicast)
            for token, result in zip(tokens, response.responses, strict=True):
                if result.exception:
                    logger.warning(
                        "push failed for token %s...: %s", token[:12], result.exception
                    )
            return response.success_count

        return await asyncio.to_thread(_send)


def build_sender() -> PushSender:
    """FCM when credentials are available, recording otherwise."""
    import os

    if os.environ.get("PUSH_DISABLED"):
        return RecordingSender()
    try:
        return FcmSender(project=os.environ.get("GOOGLE_CLOUD_PROJECT"))
    except Exception as exc:  # pragma: no cover - env-dependent
        logger.warning("FCM unavailable, using dry-run sender: %s", exc)
        return RecordingSender()
