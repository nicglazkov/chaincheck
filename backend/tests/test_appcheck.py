"""App Check verification classification and the monitoring counter."""

from chaincheck.api import appcheck


async def test_missing_token_short_circuits():
    assert await appcheck.verify(None) == "missing"
    assert await appcheck.verify("") == "missing"


async def test_bad_token_is_invalid_not_an_error():
    # No initialized Firebase app / bogus token -> classified, never raised.
    assert await appcheck.verify("not.a.real.token") == "invalid"


def test_monitor_snapshot_computes_attested_rate():
    m = appcheck.AppCheckMonitor()
    for r in ["valid", "valid", "valid", "missing"]:
        m.record(r)
    snap = m.snapshot()
    assert snap["total"] == 4
    assert snap["valid"] == 3
    assert snap["attested_pct"] == 75.0


def test_monitor_empty_snapshot():
    snap = appcheck.AppCheckMonitor().snapshot()
    assert snap["total"] == 0 and snap["attested_pct"] is None
