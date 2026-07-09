# ChainCheck

**Tahoe winter driving in one app: live chain controls, closures, storm timing, and resort snow.**

[![CI](https://github.com/nicglazkov/chaincheck/actions/workflows/ci.yml/badge.svg)](https://github.com/nicglazkov/chaincheck/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Every storm cycle, the same question hits every ski group chat: do we need
chains? Answering it today means juggling QuickMap, a forecast app, resort
sites, and CHP logs. ChainCheck puts the whole picture on one screen and
pushes you the moment it changes.

## What it does

- **The answer, first.** Open the app and your route's chain status is right
  there: R0 through R3 or Closed, with what that actually means for your car.
- **Route view.** Every Sierra crossing (I-80 Donner, US-50 Echo, SR-88
  Carson, SR-89, SR-267, SR-28, SR-20) with live control points, closures,
  and CHP incidents.
- **Push alerts.** Watch a route and get a notification the minute a control
  tier changes, a closure goes up, or a winter storm warning lands on your
  pass. Nothing promotional, ever.
- **Storm timing.** NWS pass forecasts plus hourly snow accumulation, split
  into "before you leave" and "while you're driving."
- **Resort snow.** 24h totals, base depth, and lifts open across 11 Tahoe
  resorts.
- **Trip brief.** Pick a route, origin, and your car; get a short plain-text
  brief built from the live data. An AI writes the words, but it can only
  narrate verified facts: every brief is validated so no active control is
  dropped and no road state is invented, and the chain rules for your vehicle
  come from encoded Caltrans definitions the AI cannot alter.

Mountain cell coverage is bad, so the app keeps the last known state and
shows an honest "as of" timestamp instead of a blank screen.

## The chain rules

R1, R2, and R3 vehicle requirements are encoded as structured logic from the
published Caltrans definitions and covered by exhaustive unit tests. The app
tells you what the rules require for your drivetrain, tires, weight, and
trailer. It never tells you conditions are safe. That call is yours.

## How it's built

- `backend/`: Python 3.12, FastAPI on Cloud Run. Road data comes from the
  [ca_roads](https://github.com/nicglazkov/ca-roads-mcp) feed layer (Caltrans
  district feeds, CHP dispatch XML). Forecasts from api.weather.gov and
  Open-Meteo. Resort conditions from public JSON feeds where resorts have
  them and light, per-resort adapters where they don't; each adapter fails
  alone and can be disabled by config. Adaptive polling: every 2 minutes
  during active weather, 15 otherwise. Firestore subscriptions, FCM push.
- `composeApp/`: Kotlin + Compose Multiplatform. Android and iOS from one
  codebase.
- Tests: pytest for the backend (fixture-replay on real feed formats, the
  full rules table, a 25-scenario trip-brief eval set), Gradle unit tests for
  the app. CI runs both on every PR.

## Run it locally

Backend:

```
cd backend
uv venv && uv pip install -e ".[dev]"
uv run uvicorn chaincheck.api.app:app --reload
```

Android: open the repo in Android Studio, or

```
./gradlew :composeApp:installDebug -PchaincheckBaseUrl=http://10.0.2.2:8000
```

## Data sources and thanks

- Chain controls, lane closures, cameras: [Caltrans](https://dot.ca.gov)
  public district feeds
- Incidents: [CHP](https://www.chp.ca.gov) dispatch feed
- Forecasts and winter alerts: [National Weather Service](https://www.weather.gov)
- Hourly snow: [Open-Meteo](https://open-meteo.com)
- Resort conditions: each resort's public snow report (attributed in-app)

ChainCheck is not affiliated with Caltrans, the CHP, the NWS, or any resort.
Conditions change faster than any app. Verify before you drive: dial 511 or
check [quickmap.dot.ca.gov](https://quickmap.dot.ca.gov). Whether it is safe
to drive is always your decision.

MIT license.
