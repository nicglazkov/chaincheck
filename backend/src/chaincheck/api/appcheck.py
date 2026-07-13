"""Firebase App Check: attest that a request came from the genuine ChainCheck
app on a real device.

Rolled out monitoring-first. Every request's attestation state is recorded,
but nothing is rejected until ``APP_CHECK_ENFORCE=1``. Enforcement is planned
for the Play Store release, when Play Integrity attestation is fully
meaningful for a store-distributed app; enforcing it against the current
sideload channel would either lock out testers or give false confidence.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections import Counter

logger = logging.getLogger(__name__)

# Header the app sends its App Check token in (Firebase's convention).
HEADER = "x-firebase-appcheck"

# When enforcing, only these app-only endpoints require a valid token. Reads
# stay open for the future web page and evals; the abuse-prone writes are what
# attestation protects.
PROTECTED_PATHS = frozenset(
    {
        "/v1/tripbrief",
        "/v1/subscriptions",
        "/v1/subscriptions/delete",
        "/v1/subscriptions/query",
    }
)


class AppCheckMonitor:
    """Counts attestation outcomes so the real attested-traffic rate is
    visible before enforcement is turned on."""

    def __init__(self) -> None:
        self._counts: Counter[str] = Counter()

    def record(self, result: str) -> None:
        self._counts[result] += 1

    def snapshot(self) -> dict:
        total = sum(self._counts.values())
        attested = self._counts.get("valid", 0)
        return {
            "total": total,
            "valid": attested,
            "missing": self._counts.get("missing", 0),
            "invalid": self._counts.get("invalid", 0),
            "attested_pct": round(100 * attested / total, 1) if total else None,
            "enforcing": enforcing(),
        }


async def verify(token: str | None) -> str:
    """Classify a request's App Check token as 'valid', 'missing', or
    'invalid'. Never raises: a verification failure is just 'invalid'.

    Short-circuits when no token is present, so there is zero verification
    overhead until the app actually starts sending tokens.
    """
    if not token:
        return "missing"
    try:
        from firebase_admin import app_check

        await asyncio.to_thread(app_check.verify_token, token)
        return "valid"
    except Exception as exc:  # noqa: BLE001 - any failure is a non-attested request
        logger.debug("app check verification failed: %s", exc)
        return "invalid"


def enforcing() -> bool:
    return os.environ.get("APP_CHECK_ENFORCE") == "1"
