import json

import httpx
import respx

from chaincheck.feeds import resorts
from chaincheck.feeds.resorts import (
    base,
    boreal,
    diamondpeak,
    donner,
    homewood,
    mtnpowder,
    mtrose,
    sugarbowl,
    vail,
)


def test_parse_inches():
    assert base.parse_inches('12"') == 12.0
    assert base.parse_inches("0.0 in") == 0.0
    assert base.parse_inches("--") is None
    assert base.parse_inches(None) is None
    assert base.parse_inches(7) == 7.0


def test_parse_range():
    assert base.parse_range_inches('30-44"') == (30.0, 44.0)
    assert base.parse_range_inches('38"') == (38.0, 38.0)
    assert base.parse_range_inches("--") == (None, None)


def test_mtnpowder_parse(fixture_bytes):
    payload = json.loads(fixture_bytes("mtnpowder_sample.json"))
    report = mtnpowder.parse_feed(payload, "palisades", "Palisades Tahoe")
    assert report.snow_24h_in == 11.0
    assert report.snow_48h_in is None  # "--" means unreported, not zero
    assert report.base_depth_in == 48.0
    assert report.storm_total_in == 18.0
    assert report.season_total_in == 142.0
    assert report.lifts_total == 4
    assert report.lifts_open == 2  # open + scheduled
    assert report.updated_at is not None


def test_sugarbowl_parse(fixture_bytes):
    payload = json.loads(fixture_bytes("sugarbowl_sample.json"))
    report = sugarbowl.parse_feed(payload)
    assert report.snow_24h_in == 9.0
    assert report.base_depth_in == 61.0
    assert report.season_total_in == 188.0
    assert report.lifts_open == 7
    assert report.lifts_total == 11
    assert report.updated_at is not None


def test_vail_terrain_parse(fixture_bytes):
    html = fixture_bytes("vail_terrain_sample.html").decode()
    lifts_open, lifts_total = vail.parse_terrain_feed(html)
    assert lifts_total == 5
    assert lifts_open == 3  # two open + one scheduled


def test_vail_block_page_raises():
    try:
        vail.parse_terrain_feed("<html>Access Denied</html>")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_diamondpeak_parse(fixture_bytes):
    report = diamondpeak.parse_page(fixture_bytes("diamondpeak_sample.html").decode())
    assert report.snow_overnight_in == 3.0
    assert report.snow_24h_in == 7.0
    assert report.storm_total_in == 15.0
    assert report.base_depth_in == 38.0
    assert report.season_total_in == 178.0
    assert report.lifts_total == 6


def test_mtrose_parse(fixture_bytes):
    report = mtrose.parse_page(fixture_bytes("mtrose_sample.html").decode())
    assert report.snow_24h_in == 5.0
    assert report.base_depth_in == 30.0
    assert report.base_depth_max_in == 44.0
    assert report.season_total_in == 284.0
    assert report.lifts_total == 7


def test_homewood_parse_winter(fixture_bytes):
    report = homewood.parse_page(fixture_bytes("homewood_sample.html").decode())
    assert report.snow_24h_in == 9.0  # Summit row wins
    assert report.snow_overnight_in == 4.0
    assert report.base_depth_in == 17.0
    assert report.season_total_in == 245.0
    assert report.lifts_open == 4


def test_homewood_summer_layout_degrades():
    html = (
        '<table class="weather-table"><tr>'
        '<td data-label="Zone">Summit</td>'
        '<td data-label="Temperature">57.2 F</td></tr></table>'
    )
    report = homewood.parse_page(html)
    assert report.snow_24h_in is None
    assert any("off-season" in n for n in report.notes)


def test_sierra_lifts_parse(fixture_bytes):
    from chaincheck.feeds.resorts import sierra
    from chaincheck.feeds.resorts.base import ResortReport

    report = ResortReport(resort_id="sierra", name="Sierra-at-Tahoe")
    sierra.parse_lifts_page(fixture_bytes("sierra_lifts_sample.html").decode(), report)
    assert report.lifts_total == 4
    assert report.lifts_open == 2


def test_donner_parse(fixture_bytes):
    payload = json.loads(fixture_bytes("donner_sample.json"))
    report = donner.parse_page_json(payload)
    assert report.lifts_total == 6
    assert report.lifts_open == 2  # chairs 1 and 4
    assert report.updated_at is not None
    assert report.snow_24h_in is None


def test_boreal_parse():
    payload = [
        {"name": "Accelerator", "status": "open", "updated": 1765555200},
        {"name": "Castle Peak", "status": "closed", "updated": 1765555100},
        {"name": "Cedar", "status": "open", "updated": 0},
    ]
    lifts_open, lifts_total, newest = boreal.parse_lifts(payload)
    assert (lifts_open, lifts_total) == (2, 3)
    assert newest is not None


@respx.mock
async def test_registry_isolates_failures(fixture_bytes, monkeypatch):
    monkeypatch.delenv("RESORTS_DISABLED", raising=False)
    respx.get(url__regex=r".*mtnpowder\.com.*").mock(
        return_value=httpx.Response(
            200, content=fixture_bytes("mtnpowder_sample.json")
        )
    )
    # Everything else fails hard.
    respx.get(url__regex=r".*").mock(return_value=httpx.Response(503))

    async with httpx.AsyncClient() as client:
        registry = resorts.ResortRegistry(client)
        reports = await registry.all_reports()

    by_id = {r.resort_id: r for r in reports}
    assert len(by_id) == 11
    assert by_id["palisades"].ok and by_id["palisades"].snow_24h_in == 11.0
    assert not by_id["heavenly"].ok and by_id["heavenly"].error


async def test_registry_disable_env(monkeypatch):
    monkeypatch.setenv("RESORTS_DISABLED", "heavenly, donner")
    async with httpx.AsyncClient() as client:
        registry = resorts.ResortRegistry(client)
        assert await registry.report("heavenly") is None
        assert await registry.report("donner") is None


_VAIL_SNOW_JSON = json.dumps({
    "OverallSnowConditions": "Powder",
    "OvernightSnowfall": {"Inches": "4", "Centimeters": "10"},
    "TwentyFourHourSnowfall": {"Inches": "9", "Centimeters": "23"},
    "FortyEightHourSnowfall": {"Inches": "15", "Centimeters": "38"},
    "SevenDaySnowfall": {"Inches": "31", "Centimeters": "79"},
    "BaseDepth": {"Inches": "52", "Centimeters": "132"},
    "CurrentSeason": {"Inches": "220", "Centimeters": "558"},
    "LastUpdatedText": "Updated",
})
VAIL_SNOW_HTML = f"<script>FR.snowReportData = {_VAIL_SNOW_JSON};</script>"


def test_vail_snow_report_parse():
    snow = vail.parse_snow_report(VAIL_SNOW_HTML)
    assert snow["snow_overnight_in"] == 4.0
    assert snow["snow_24h_in"] == 9.0
    assert snow["snow_48h_in"] == 15.0
    assert snow["base_depth_in"] == 52.0
    assert snow["season_total_in"] == 220.0


def test_vail_empty_lift_list_is_offseason_not_error():
    html = "<script>FR.TerrainStatusFeed = {\"Lifts\":[]};</script>"
    assert vail.parse_terrain_feed(html) == (0, 0)
