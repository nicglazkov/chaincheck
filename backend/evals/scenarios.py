"""Trip-brief eval scenarios: structured inputs -> facts every brief must
carry (and things no brief may ever say).

Used two ways: offline (render_plain must contain every expected fact) and
against the live model (evals/run_tripbrief.py) where the narrated brief is
checked for the same facts, for invented road states, and for banned safety
promises.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from ca_roads.models import ChainControl, LaneClosure

from chaincheck import rules
from chaincheck.brief import facts as brief_facts
from chaincheck.corridors import CORRIDORS
from chaincheck.feeds.nws import ForecastPeriod, PassForecast, WinterAlert
from chaincheck.feeds.openmeteo import SnowHour, SnowOutlook
from chaincheck.feeds.roads import CorridorRoads, SierraSnapshot
from chaincheck.tiers import Tier

NOW = datetime(2026, 12, 12, 8, 0, tzinfo=UTC)

# Re-exported for the offline tests; the live service enforces the same lists.
from chaincheck.brief.validate import BANNED_PHRASES, TIER_TOKENS  # noqa: E402, F401


@dataclass
class Scenario:
    id: str
    corridor_id: str
    tier: Tier
    controls: list[tuple[str, str]] = field(default_factory=list)  # (location, status)
    closures: list[str] = field(default_factory=list)  # locations
    alert: str | None = None
    snow_start_hour: int | None = None  # hours from NOW; None = dry
    departure_offset_h: int = 6
    origin: str = "Sacramento"
    vehicle: rules.Vehicle | None = None
    expect_substrings: list[str] = field(default_factory=list)


def _control(location: str, status: str) -> ChainControl:
    return ChainControl(
        index=f"3-{location}",
        district=3,
        route="80",
        county="Placer",
        direction="East",
        location_name=location,
        nearby_place="",
        lat=39.3,
        lon=-120.4,
        in_service=True,
        status=status,
        status_description="",
        status_updated_at=NOW,
    )


def _closure(location: str) -> LaneClosure:
    return LaneClosure(
        index=f"C-{location}",
        district=3,
        route="80",
        county="Placer",
        direction="East",
        location_name=location,
        nearby_place="",
        type_of_closure="Full",
        facility="",
        type_of_work="spinout recovery",
        lanes_closed="all",
        total_lanes=2,
        estimated_delay_minutes=45,
        duration="",
        begin_lat=39.3,
        begin_lon=-120.4,
        end_lat=39.31,
        end_lon=-120.39,
        begin_milepost=None,
        end_milepost=None,
        start_epoch=0,
        end_epoch=0,
        indefinite_end=False,
        is_1097=True,
        is_1098=False,
        is_1022=False,
        epoch_1097=0,
    )


def build_facts(s: Scenario) -> brief_facts.TripFacts:
    corridors_map = {
        c.id: CorridorRoads(corridor=c, tier=Tier.R0) for c in CORRIDORS
    }
    roads = corridors_map[s.corridor_id]
    roads.tier = s.tier
    roads.controls = [_control(loc, status) for loc, status in s.controls]
    roads.closures = [_closure(loc) for loc in s.closures]
    snapshot = SierraSnapshot(
        corridors=corridors_map, data_as_of=NOW, ok=True, stale=False
    )

    departure = NOW + timedelta(hours=s.departure_offset_h)
    forecast = None
    if s.alert is not None or s.snow_start_hour is not None:
        forecast = PassForecast(
            pass_id="donner",
            periods=[
                ForecastPeriod(
                    name="Today",
                    start=departure - timedelta(hours=1),
                    end=departure + timedelta(hours=8),
                    is_daytime=True,
                    temperature_f=24,
                    wind="25 to 40 mph SW",
                    short="Snow" if s.snow_start_hour is not None else "Partly Cloudy",
                    detailed="",
                    precip_chance=90 if s.snow_start_hour is not None else 10,
                )
            ],
            alerts=(
                [
                    WinterAlert(
                        id="a1",
                        event=s.alert,
                        severity="Severe",
                        headline=s.alert,
                        onset=NOW,
                        ends=departure + timedelta(hours=12),
                        description="",
                    )
                ]
                if s.alert
                else []
            ),
        )

    outlook = None
    if s.snow_start_hour is not None:
        outlook = SnowOutlook(
            pass_id="donner",
            hours=[
                SnowHour(
                    time=NOW + timedelta(hours=i),
                    snowfall_cm=2.5 if i >= s.snow_start_hour else 0.0,
                    snow_depth_m=None,
                    temperature_c=-3.0,
                    wind_kmh=45.0,
                    freezing_level_m=1300.0,
                )
                for i in range(48)
            ],
        )

    return brief_facts.assemble(
        corridor_id=s.corridor_id,
        origin=s.origin,
        departure=departure,
        snapshot=snapshot,
        forecast=forecast,
        outlook=outlook,
        vehicle=s.vehicle,
        now=NOW,
    )


AWD_SNOW = rules.Vehicle(rules.Drivetrain.FOUR_WHEEL, rules.Tires.SNOW_ALL_FOUR)
AWD_BALD = rules.Vehicle(rules.Drivetrain.FOUR_WHEEL, rules.Tires.NO_SNOW)
FWD_SNOW = rules.Vehicle(rules.Drivetrain.TWO_WHEEL, rules.Tires.SNOW_DRIVE_AXLE)
FWD_BALD = rules.Vehicle(rules.Drivetrain.TWO_WHEEL, rules.Tires.NO_SNOW)
TOWING = rules.Vehicle(rules.Drivetrain.FOUR_WHEEL, rules.Tires.SNOW_ALL_FOUR, towing=True)
HEAVY = rules.Vehicle(
    rules.Drivetrain.TWO_WHEEL, rules.Tires.SNOW_DRIVE_AXLE, over_6000_lbs=True
)


SCENARIOS: list[Scenario] = [
    # --- quiet days ---
    Scenario(id="r0-i80-dry", corridor_id="i80", tier=Tier.R0,
             expect_substrings=["R0", "No chain controls"]),
    Scenario(id="r0-us50-dry-awd", corridor_id="us50", tier=Tier.R0, vehicle=AWD_SNOW,
             expect_substrings=["R0", "No chain controls"]),
    Scenario(id="r0-sr88-alert-preStorm", corridor_id="sr88", tier=Tier.R0,
             alert="Winter Storm Watch", snow_start_hour=10,
             expect_substrings=["R0", "Winter Storm Watch"]),
    # --- R1 ---
    Scenario(id="r1-i80-fwd-snowtires", corridor_id="i80", tier=Tier.R1,
             controls=[("Kingvale", "R-1")], vehicle=FWD_SNOW,
             expect_substrings=["R1", "Kingvale", "carry"]),
    Scenario(id="r1-i80-fwd-bald", corridor_id="i80", tier=Tier.R1,
             controls=[("Kingvale", "R-1")], vehicle=FWD_BALD,
             expect_substrings=["R1", "Kingvale", "install"]),
    Scenario(id="r1-us50-awd", corridor_id="us50", tier=Tier.R1,
             controls=[("Twin Bridges", "R-1")], vehicle=AWD_BALD,
             expect_substrings=["R1", "Twin Bridges", "carry"]),
    Scenario(id="r1-heavy-truck", corridor_id="i80", tier=Tier.R1,
             controls=[("Baxter", "R-1")], vehicle=HEAVY,
             expect_substrings=["R1", "Baxter", "6,000"]),
    Scenario(id="r1-towing", corridor_id="sr88", tier=Tier.R1,
             controls=[("Carson Spur", "R-1")], vehicle=TOWING,
             expect_substrings=["R1", "Carson Spur", "drive axle"]),
    # --- R2 ---
    Scenario(id="r2-i80-storm-awd", corridor_id="i80", tier=Tier.R2,
             controls=[("Kingvale", "R-2"), ("Baxter", "R-2")],
             alert="Winter Storm Warning", snow_start_hour=2, vehicle=AWD_SNOW,
             expect_substrings=["R2", "Kingvale", "Baxter", "Winter Storm Warning",
                                "carry"]),
    Scenario(id="r2-i80-storm-fwd", corridor_id="i80", tier=Tier.R2,
             controls=[("Kingvale", "R-2")], alert="Winter Storm Warning",
             snow_start_hour=2, vehicle=FWD_SNOW,
             expect_substrings=["R2", "Kingvale", "regardless of tires"]),
    Scenario(id="r2-us50-two-points", corridor_id="us50", tier=Tier.R2,
             controls=[("Twin Bridges", "R-2"), ("Meyers", "R-1")],
             expect_substrings=["R2", "Twin Bridges", "Meyers"]),
    Scenario(id="r2-awd-bald-tires", corridor_id="i80", tier=Tier.R2,
             controls=[("Kingvale", "R-2")], vehicle=AWD_BALD,
             expect_substrings=["R2", "install"]),
    Scenario(id="r2-towing-awd", corridor_id="i80", tier=Tier.R2,
             controls=[("Kingvale", "R-2")], vehicle=TOWING,
             expect_substrings=["R2", "drive axle"]),
    Scenario(id="r2-with-closure", corridor_id="i80", tier=Tier.R2,
             controls=[("Kingvale", "R-2")], closures=["Donner Lake Interchange"],
             expect_substrings=["R2", "Kingvale", "Donner Lake Interchange"]),
    Scenario(id="r2-sr267", corridor_id="sr267", tier=Tier.R2,
             controls=[("Brockway Summit", "R-2")],
             expect_substrings=["R2", "Brockway Summit"]),
    Scenario(id="r2-sr89", corridor_id="sr89", tier=Tier.R2,
             controls=[("Luther Pass", "R-2")],
             expect_substrings=["R2", "Luther Pass"]),
    # --- R3 / closed ---
    Scenario(id="r3-i80", corridor_id="i80", tier=Tier.R3,
             controls=[("Kingvale", "R-3")], alert="Blizzard Warning",
             snow_start_hour=0, vehicle=AWD_SNOW,
             expect_substrings=["R3", "no exceptions", "Blizzard Warning"]),
    Scenario(id="closed-i80", corridor_id="i80", tier=Tier.CLOSED,
             controls=[("Kingvale", "RC")], alert="Blizzard Warning",
             expect_substrings=["Closed", "closed"]),
    Scenario(id="closed-us50", corridor_id="us50", tier=Tier.CLOSED,
             controls=[("Echo Summit", "Road Closed")],
             expect_substrings=["Closed"]),
    # --- storm-timing emphasis ---
    Scenario(id="storm-arrives-during-drive", corridor_id="i80", tier=Tier.R0,
             alert="Winter Storm Warning", snow_start_hour=7, departure_offset_h=6,
             expect_substrings=["R0", "Winter Storm Warning"]),
    Scenario(id="storm-before-departure", corridor_id="us50", tier=Tier.R1,
             controls=[("Twin Bridges", "R-1")], alert="Winter Storm Warning",
             snow_start_hour=1, departure_offset_h=8,
             expect_substrings=["R1", "Winter Storm Warning"]),
    Scenario(id="evening-departure", corridor_id="i80", tier=Tier.R2,
             controls=[("Kingvale", "R-2")], snow_start_hour=4, departure_offset_h=12,
             expect_substrings=["R2", "Kingvale"]),
    # --- other corridors / origins ---
    Scenario(id="reno-origin", corridor_id="i80", tier=Tier.R1,
             controls=[("Floriston", "R-1")], origin="Reno",
             expect_substrings=["R1", "Reno", "Floriston"]),
    Scenario(id="bay-area-origin", corridor_id="us50", tier=Tier.R2,
             controls=[("Twin Bridges", "R-2")], origin="San Jose",
             expect_substrings=["R2", "San Jose", "Twin Bridges"]),
    Scenario(id="sr88-kirkwood-day", corridor_id="sr88", tier=Tier.R2,
             controls=[("Carson Spur", "R-2")], alert="Winter Weather Advisory",
             snow_start_hour=3, vehicle=FWD_SNOW,
             expect_substrings=["R2", "Carson Spur", "Winter Weather Advisory"]),
]
