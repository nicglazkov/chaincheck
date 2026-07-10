<div align="center">
  <img src="docs/logo.svg" width="110" alt="ChainCheck logo: a map pin holding a Sierra ridgeline">
  <h1>ChainCheck</h1>
  <p><b>Tahoe winter driving in one app: live chain controls, closures, storm timing, and resort snow.</b></p>

[![CI](https://github.com/nicglazkov/chaincheck/actions/workflows/ci.yml/badge.svg)](https://github.com/nicglazkov/chaincheck/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](backend/pyproject.toml)
[![Kotlin Multiplatform](https://img.shields.io/badge/Kotlin-Multiplatform-7F52FF?logo=kotlin&logoColor=white)](composeApp/build.gradle.kts)

</div>

Every Sierra storm, the same question hits every ski group chat: do we need chains?
Answering it today means juggling QuickMap, a weather app, resort sites, and CHP logs.
ChainCheck puts the whole picture on one screen and pushes you an alert the moment it changes.

## Screenshots

<p align="center">
  <img src="docs/screenshots/home-light.png" width="19%" alt="Home screen, light theme: destination chips and the R0 tier ring">
  <img src="docs/screenshots/home-dark.png" width="19%" alt="Home screen, dark theme: glowing tier ring on a night gradient">
  <img src="docs/screenshots/map.png" width="19%" alt="Map: route lines colored by tier, webcams, closures, resorts">
  <img src="docs/screenshots/brief.png" width="19%" alt="AI trip brief summarizing live road and weather data">
  <img src="docs/screenshots/guide.png" width="19%" alt="Interactive guide explaining what R0 through R3 mean">
</p>

## What it does

- **The answer, first.** Open the app and your route's chain status is right there:
  R0 through R3 or Closed, with what that means for your exact car.
- **A real map.** Every Sierra crossing drawn on its actual highway geometry and
  colored by its current control level. 80 live Caltrans cameras, closures, CHP
  incidents, resorts, and passes. Tap anything anywhere in the app to see it here.
- **Push alerts.** Watch a route and get a notification the minute a control tier
  changes, a closure goes up, or a winter storm warning lands on your pass.
  Nothing promotional, ever.
- **Storm timing.** NWS pass forecasts plus hourly snow accumulation, split into
  "before you leave" and "while you are driving".
- **Resort snow.** 24 hour totals, base depth, and lifts open across 11 Tahoe
  resorts, with honest off-season labeling instead of fake zeros.
- **AI trip brief.** Pick a route, origin, and your car. A language model writes the
  summary, but it can only narrate verified facts: every brief is validated so no
  active control is dropped and no road state is invented. If validation fails, a
  deterministic plain-text brief ships instead.
- **Built for the mountains.** Offline caching with honest "as of" timestamps for
  dead zones, glove-sized touch targets, and a 60 second interactive guide for
  people who have never seen a chain checkpoint.

## The chain rules

R1, R2, and R3 vehicle requirements are encoded as structured logic from the
published Caltrans definitions and covered by exhaustive unit tests. The app tells
you what the rules require for your drivetrain, tires, weight, and trailer. It never
tells you conditions are safe. That call is yours.

## How it works

```
Caltrans district feeds ─┐
CHP dispatch XML ────────┤   ┌─────────────┐    ┌──────────────────┐
NWS + Open-Meteo ────────┼──▶│  FastAPI on  │───▶│ Compose          │
11 resort adapters ──────┘   │  Cloud Run   │    │ Multiplatform    │
                             │              │    │ app (Android,    │
Cloud Scheduler ──▶ poll ──▶ │ differ ──▶ FCM ──▶ iOS in progress) │
                             └─────────────┘    └──────────────────┘
```

- `backend/` is Python 3.12 with FastAPI. Road data comes from the
  [ca_roads](https://github.com/nicglazkov/ca-roads-mcp) feed layer, which parses
  the public Caltrans and CHP feeds with per-district caching and stale-serve.
  Forecasts come from api.weather.gov and Open-Meteo. Resort conditions come from
  public JSON feeds where resorts have them and light per-resort scrapers where
  they do not; each adapter fails alone and can be disabled by config.
- Polling is adaptive: every 2 minutes during active weather, every 15 otherwise.
  A pure differ turns snapshots into events (tier changes, closures, storm
  warnings), which fan out to watching devices over FCM. Subscriptions are
  anonymous device tokens in Firestore.
- Route lines on the map are extracted once from OpenStreetMap way data and baked
  into the package, so they sit on the real pavement with no runtime routing cost.
- `composeApp/` is Kotlin with Compose Multiplatform. Android ships first; the
  shared code already declares iOS targets.

## Run it locally

Backend (Python 3.12+, [uv](https://github.com/astral-sh/uv) recommended):

```bash
cd backend
uv venv && uv pip install -e ".[dev]"
uv run uvicorn chaincheck.api.app:app --reload
```

The API is keyless by default. All core feeds are free and public. Optional:
set `ANTHROPIC_API_KEY` to enable AI-narrated trip briefs (plain-text briefs
work without it).

Android (JDK 17+, Android SDK):

```bash
./gradlew :composeApp:installDebug -PchaincheckBaseUrl=http://10.0.2.2:8000
```

Maps need a Google Maps Android key in `local.properties` as
`MAPS_API_KEY=...` (restrict it to your package and signing certificate).
Push needs a Firebase project and its `google-services.json` in `composeApp/`.
Both files are gitignored; the app builds and runs without them, minus those
two features.

## Tests

```bash
cd backend && uv run pytest        # 150 tests: feeds, rules table, differ, briefs
./gradlew :composeApp:testDebugUnitTest
```

The trip brief has its own eval set: 25 scenarios checked offline in CI against
the deterministic rendering, and runnable against the live model with
`uv run python -m evals.run_tripbrief`. A brief that drops an active control or
invents a road state never ships.

## Roadmap

- iOS build (shared code is ready, Xcode project in progress)
- Read-only web page for sharing route status with people without the app
- Store releases ahead of the first Sierra storms

## Data sources and thanks

- Chain controls, lane closures, cameras: [Caltrans](https://dot.ca.gov) public district feeds
- Incidents: [CHP](https://www.chp.ca.gov) dispatch feed
- Forecasts and winter alerts: [National Weather Service](https://www.weather.gov)
- Hourly snow: [Open-Meteo](https://open-meteo.com)
- Route geometry: [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors
- Resort conditions: each resort's public snow report, fetched gently and attributed in-app

ChainCheck is not affiliated with Caltrans, the CHP, the NWS, or any resort.
Conditions change faster than any app. Verify before you drive: dial 511 or check
[quickmap.dot.ca.gov](https://quickmap.dot.ca.gov). Whether it is safe to drive is
always your decision.

## License

MIT. See [LICENSE](LICENSE).
