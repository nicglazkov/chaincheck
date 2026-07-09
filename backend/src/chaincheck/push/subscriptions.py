"""Device subscriptions: which corridors each push token watches.

Anonymous by design - a subscription is just an FCM token plus corridor ids,
no accounts, nothing personal. Firestore in production, in-memory for tests
and local dev.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from chaincheck.corridors import CORRIDORS_BY_ID

COLLECTION = "subscriptions"


@dataclass
class Subscription:
    token: str
    corridor_ids: list[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None


def validate_corridors(corridor_ids: list[str]) -> list[str]:
    """Keep known corridor ids, preserve order, drop duplicates."""
    seen: list[str] = []
    for cid in corridor_ids:
        cid = cid.strip().lower()
        if cid in CORRIDORS_BY_ID and cid not in seen:
            seen.append(cid)
    return seen


class SubscriptionStore(Protocol):
    async def upsert(self, token: str, corridor_ids: list[str]) -> Subscription: ...

    async def get(self, token: str) -> Subscription | None: ...

    async def delete(self, token: str) -> bool: ...

    async def tokens_for_corridor(self, corridor_id: str) -> list[str]: ...


class InMemorySubscriptionStore:
    def __init__(self) -> None:
        self._subs: dict[str, Subscription] = {}

    async def upsert(self, token: str, corridor_ids: list[str]) -> Subscription:
        now = datetime.now(UTC)
        existing = self._subs.get(token)
        sub = Subscription(
            token=token,
            corridor_ids=corridor_ids,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        self._subs[token] = sub
        return sub

    async def get(self, token: str) -> Subscription | None:
        return self._subs.get(token)

    async def delete(self, token: str) -> bool:
        return self._subs.pop(token, None) is not None

    async def tokens_for_corridor(self, corridor_id: str) -> list[str]:
        return [
            sub.token for sub in self._subs.values() if corridor_id in sub.corridor_ids
        ]


@dataclass
class FirestoreSubscriptionStore:
    """Firestore-backed store (google-cloud-firestore AsyncClient)."""

    project: str | None = None
    _client: object = field(default=None, repr=False)

    def _db(self):
        if self._client is None:
            from google.cloud import firestore

            self._client = firestore.AsyncClient(project=self.project)
        return self._client

    async def upsert(self, token: str, corridor_ids: list[str]) -> Subscription:
        now = datetime.now(UTC)
        doc = self._db().collection(COLLECTION).document(token)
        snapshot = await doc.get()
        created = now
        if snapshot.exists:
            created = (snapshot.to_dict() or {}).get("created_at", now)
        await doc.set(
            {
                "corridor_ids": corridor_ids,
                "created_at": created,
                "updated_at": now,
            }
        )
        return Subscription(token, corridor_ids, created, now)

    async def get(self, token: str) -> Subscription | None:
        snapshot = await self._db().collection(COLLECTION).document(token).get()
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        return Subscription(
            token=token,
            corridor_ids=list(data.get("corridor_ids", [])),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    async def delete(self, token: str) -> bool:
        doc = self._db().collection(COLLECTION).document(token)
        snapshot = await doc.get()
        if not snapshot.exists:
            return False
        await doc.delete()
        return True

    async def tokens_for_corridor(self, corridor_id: str) -> list[str]:
        query = (
            self._db()
            .collection(COLLECTION)
            .where("corridor_ids", "array_contains", corridor_id)
        )
        return [doc.id async for doc in query.stream()]
