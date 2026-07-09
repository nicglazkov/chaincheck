from datetime import UTC, datetime, timedelta

from ca_roads.models import ChainControl
from tests.test_differ import snapshot_with

from chaincheck import rules
from chaincheck.brief import facts as brief_facts
from chaincheck.feeds.nws import ForecastPeriod, PassForecast, WinterAlert
from chaincheck.feeds.openmeteo import SnowHour, SnowOutlook
from chaincheck.tiers import Tier

NOW = datetime(2026, 12, 12, 8, 0, tzinfo=UTC)
DEPARTURE = datetime(2026, 12, 12, 14, 0, tzinfo=UTC)  # 6am PST Saturday


def make_control(status: str, location: str = "Kingvale") -> ChainControl:
    return ChainControl(
        index=f"3-{location}",
        district=3,
        route="80",
        county="Placer",
        direction="East",
        location_name=location,
        nearby_place="Truckee",
        lat=39.32,
        lon=-120.44,
        in_service=True,
        status=status,
        status_description="Chains or traction devices required",
        status_updated_at=NOW,
    )


def storm_setup():
    snapshot = snapshot_with({"i80": Tier.R2})
    snapshot.corridors["i80"].controls.append(make_control("R-2"))
    snapshot.corridors["i80"].controls.append(make_control("R-1", "Baxter"))
    forecast = PassForecast(
        pass_id="donner",
        periods=[
            ForecastPeriod(
                name="Saturday",
                start=DEPARTURE - timedelta(hours=2),
                end=DEPARTURE + timedelta(hours=10),
                is_daytime=True,
                temperature_f=25,
                wind="30 to 45 mph SW",
                short="Heavy Snow",
                detailed="Heavy snow, 12 to 18 inches.",
                precip_chance=95,
            )
        ],
        alerts=[
            WinterAlert(
                id="a1",
                event="Winter Storm Warning",
                severity="Severe",
                headline="Winter Storm Warning until Sunday 4 AM",
                onset=NOW,
                ends=DEPARTURE + timedelta(hours=14),
                description="",
            )
        ],
    )
    hours = [
        SnowHour(
            time=NOW + timedelta(hours=i),
            snowfall_cm=2.0 if i >= 4 else 0.0,
            snow_depth_m=None,
            temperature_c=-4.0,
            wind_kmh=40.0,
            freezing_level_m=1200.0,
        )
        for i in range(24)
    ]
    outlook = SnowOutlook(pass_id="donner", hours=hours)
    return snapshot, forecast, outlook


def assemble(vehicle=None):
    snapshot, forecast, outlook = storm_setup()
    return brief_facts.assemble(
        corridor_id="i80",
        origin="Sacramento",
        departure=DEPARTURE,
        snapshot=snapshot,
        forecast=forecast,
        outlook=outlook,
        vehicle=vehicle,
        now=NOW,
    )


def test_facts_capture_controls_and_alerts():
    facts = assemble()
    assert facts.tier == 2
    assert facts.tier_label == "R2"
    assert len(facts.active_controls) == 2
    assert any("Kingvale" in c for c in facts.active_controls)
    assert facts.alerts == ("Winter Storm Warning until Sunday 4 AM",)
    assert facts.forecast_window  # Saturday period overlaps the drive
    assert facts.pass_name == "Donner Summit"


def test_snow_split_before_and_during_drive():
    facts = assemble()
    # Snow starts 4h from now; departure is 6h out. The departure-boundary
    # hour counts as "before" (inclusive window): hours 4, 5, 6.
    assert facts.snow_before_arrival_cm == 6.0
    # 4-hour drive window -> hours 7-10 -> 8 cm during
    assert facts.snow_during_window_cm == 8.0
    assert facts.storm_start == NOW + timedelta(hours=4)


def test_ruling_included_when_vehicle_given():
    vehicle = rules.Vehicle(rules.Drivetrain.TWO_WHEEL, rules.Tires.NO_SNOW)
    facts = assemble(vehicle)
    assert facts.ruling is not None
    assert facts.ruling.requirement is rules.Requirement.INSTALL


def test_render_plain_contains_required_facts():
    vehicle = rules.Vehicle(rules.Drivetrain.FOUR_WHEEL, rules.Tires.SNOW_ALL_FOUR)
    text = brief_facts.render_plain(assemble(vehicle))
    assert "R2" in text
    assert "Kingvale" in text and "Baxter" in text
    assert "Winter Storm Warning" in text
    assert "Sacramento" in text
    assert "511" in text
    assert "exempt from installing" in text  # the ruling rides along verbatim


def test_render_plain_never_promises_safety():
    text = brief_facts.render_plain(assemble()).lower()
    for banned in ("you'll make it", "safe to drive", "won't need chains", "no need to worry"):
        assert banned not in text


def test_quiet_day_renders_r0():
    snapshot = snapshot_with({"us50": Tier.R0})
    facts = brief_facts.assemble(
        corridor_id="us50",
        origin="Sacramento",
        departure=DEPARTURE,
        snapshot=snapshot,
        forecast=None,
        outlook=None,
        vehicle=None,
        now=NOW,
    )
    text = brief_facts.render_plain(facts)
    assert "R0" in text
    assert "No chain controls" in text
