import httpx
import respx

from chaincheck.feeds import nws
from chaincheck.passes import PASSES_BY_ID

POINTS_PAYLOAD = {
    "properties": {"forecast": "https://api.weather.gov/gridpoints/REV/33,87/forecast"}
}

FORECAST_PAYLOAD = {
    "properties": {
        "periods": [
            {
                "name": "Tonight",
                "startTime": "2026-12-11T18:00:00-08:00",
                "endTime": "2026-12-12T06:00:00-08:00",
                "isDaytime": False,
                "temperature": 22,
                "windSpeed": "25 to 35 mph",
                "windDirection": "SW",
                "shortForecast": "Heavy Snow",
                "detailedForecast": "Heavy snow. Total accumulation 12 to 18 inches.",
                "probabilityOfPrecipitation": {"value": 95},
            }
        ]
    }
}

ALERTS_PAYLOAD = {
    "features": [
        {
            "id": "urn:x:1",
            "properties": {
                "id": "urn:x:1",
                "event": "Winter Storm Warning",
                "severity": "Severe",
                "headline": "Winter Storm Warning until Saturday 10 AM",
                "onset": "2026-12-11T22:00:00-08:00",
                "ends": "2026-12-12T10:00:00-08:00",
                "description": "Heavy snow above 6000 feet.",
            },
        },
        {
            "id": "urn:x:2",
            "properties": {
                "id": "urn:x:2",
                "event": "Air Quality Alert",
                "severity": "Minor",
                "headline": "Air Quality Alert",
                "description": "",
            },
        },
    ]
}


def test_parse_forecast_periods():
    periods = nws.parse_forecast(FORECAST_PAYLOAD)
    assert len(periods) == 1
    p = periods[0]
    assert p.name == "Tonight"
    assert p.temperature_f == 22
    assert p.precip_chance == 95
    assert "Heavy" in p.short


def test_parse_alerts_keeps_winter_only():
    alerts = nws.parse_alerts(ALERTS_PAYLOAD)
    assert len(alerts) == 1
    assert alerts[0].event == "Winter Storm Warning"
    assert alerts[0].onset is not None


@respx.mock
async def test_forecast_end_to_end_and_cached():
    donner = PASSES_BY_ID["donner"]
    points = respx.get(url__regex=r".*api\.weather\.gov/points/.*").mock(
        return_value=httpx.Response(200, json=POINTS_PAYLOAD)
    )
    respx.get("https://api.weather.gov/gridpoints/REV/33,87/forecast").mock(
        return_value=httpx.Response(200, json=FORECAST_PAYLOAD)
    )
    respx.get(url__regex=r".*api\.weather\.gov/alerts/active.*").mock(
        return_value=httpx.Response(200, json=ALERTS_PAYLOAD)
    )

    async with httpx.AsyncClient() as client:
        source = nws.NwsSource(client)
        result = await source.forecast(donner)
        assert result.ok and not result.stale
        assert result.periods[0].short == "Heavy Snow"
        assert len(result.alerts) == 1

        # Second call is served from cache: no new points request.
        calls_before = points.call_count
        again = await source.forecast(donner)
        assert again.ok
        assert points.call_count == calls_before


@respx.mock
async def test_forecast_failure_reports_not_ok():
    donner = PASSES_BY_ID["donner"]
    respx.get(url__regex=r".*api\.weather\.gov.*").mock(
        return_value=httpx.Response(500)
    )
    async with httpx.AsyncClient() as client:
        source = nws.NwsSource(client)
        result = await source.forecast(donner)
        assert not result.ok
        assert result.error
