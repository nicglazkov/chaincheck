from datetime import UTC, datetime

import httpx
import respx

from chaincheck.feeds import openmeteo
from chaincheck.passes import PASSES_BY_ID

PAYLOAD = {
    "hourly": {
        "time": [
            "2026-12-12T00:00",
            "2026-12-12T01:00",
            "2026-12-12T02:00",
            "2026-12-13T05:00",
        ],
        "snowfall": [0.0, 2.5, 4.0, 1.5],
        "snow_depth": [0.5, 0.52, 0.56, 0.6],
        "temperature_2m": [-2.0, -3.0, -3.5, -1.0],
        "wind_speed_10m": [20.0, 35.0, 40.0, 10.0],
        "freezing_level_height": [1500, 1400, 1300, 1800],
    }
}

NOW = datetime(2026, 12, 11, 23, 0, tzinfo=UTC)


def test_parse_hours():
    hours = openmeteo.parse_hours(PAYLOAD)
    assert len(hours) == 4
    assert hours[1].snowfall_cm == 2.5
    assert hours[1].time == datetime(2026, 12, 12, 1, 0, tzinfo=UTC)


def test_accumulation_windows():
    outlook = openmeteo.SnowOutlook(pass_id="donner", hours=openmeteo.parse_hours(PAYLOAD))
    assert outlook.accumulation_cm(24, now=NOW) == 6.5  # first three hours
    assert outlook.accumulation_cm(48, now=NOW) == 8.0  # includes next-day hour


def test_storm_start():
    outlook = openmeteo.SnowOutlook(pass_id="donner", hours=openmeteo.parse_hours(PAYLOAD))
    assert outlook.storm_start(now=NOW) == datetime(2026, 12, 12, 1, 0, tzinfo=UTC)


def test_no_storm_when_dry():
    dry = {
        "hourly": {
            "time": ["2026-12-12T00:00"],
            "snowfall": [0.0],
        }
    }
    outlook = openmeteo.SnowOutlook(pass_id="donner", hours=openmeteo.parse_hours(dry))
    assert outlook.storm_start(now=NOW) is None


@respx.mock
async def test_outlook_end_to_end():
    respx.get(url__regex=r".*api\.open-meteo\.com.*").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    async with httpx.AsyncClient() as client:
        source = openmeteo.OpenMeteoSource(client)
        outlook = await source.outlook(PASSES_BY_ID["echo"])
        assert outlook.ok
        assert len(outlook.hours) == 4
