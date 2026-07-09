"""End-to-end: real Caltrans feed XML through ca_roads into a SierraSnapshot."""

import httpx
import respx
from ca_roads.feeds import chains, chp, lcs

from chaincheck.corridors import SIERRA_DISTRICTS
from chaincheck.feeds.roads import SierraRoads
from chaincheck.tiers import Tier


@respx.mock
async def test_snapshot_from_fixture_feeds(fixture_bytes):
    for district in SIERRA_DISTRICTS:
        respx.get(chains.feed_url(district)).mock(
            return_value=httpx.Response(
                200 if district == 3 else 404,
                content=fixture_bytes("cc_sample.xml") if district == 3 else b"",
            )
        )
        respx.get(lcs.feed_url(district)).mock(
            return_value=httpx.Response(
                200 if district == 3 else 404,
                content=fixture_bytes("lcs_sample.xml") if district == 3 else b"",
            )
        )
    respx.get(chp.CHP_URL).mock(
        return_value=httpx.Response(200, content=fixture_bytes("chp_sample.xml"))
    )

    roads = SierraRoads()
    try:
        snapshot = await roads.snapshot()
    finally:
        await roads.aclose()

    assert snapshot.ok
    # cc_sample has US-50 at R-2 and SR-89 at R-0 (district 3 records).
    assert snapshot.corridors["us50"].tier is Tier.R2
    assert snapshot.corridors["sr89"].tier is Tier.R0
    # Corridors with no checkpoint reporting still affirm R0 when the feed is up.
    assert snapshot.corridors["i80"].tier is Tier.R0
    assert snapshot.data_as_of is not None
