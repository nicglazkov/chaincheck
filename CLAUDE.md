# ChainCheck

Live Caltrans chain controls, closures, pass weather, and resort snow for the
Sierra passes to Lake Tahoe, with push alerts and an AI trip brief.

## Architecture

- **Backend**: Python 3.12 / FastAPI on Google Cloud Run (project
  `chaincheck-app`, region us-west1, service `chaincheck-api`). Public, keyless
  JSON API. Reuses the `ca_roads` feed layer. Firestore for subscriptions, FCM
  for push, Cloud Scheduler drives a 2-minute poll. Lives in `backend/`.
- **App**: Kotlin Compose Multiplatform. Android ships from GitHub Releases as a
  sideload APK; iOS ships through the public TestFlight beta
  (https://testflight.apple.com/join/fAuhRHU8). One shared module in
  `composeApp/`:
  - `src/commonMain` shared UI, data, and logic.
  - `src/androidMain` and `src/iosMain` platform actuals (`expect`/`actual`).
  - `iosApp/` holds the Xcode app (created on a Mac). See `iosApp/README.md`.

The backend API is client agnostic; there is no per-platform backend work.

## Build and test

```bash
# Backend (uv)
cd backend && uv run pytest && uv run ruff check .
uv run uvicorn chaincheck.api.app:app --reload

# Android (JDK 17+, Android SDK)
./gradlew :composeApp:testDebugUnitTest
./gradlew :composeApp:assembleDebug          # add -PchaincheckBaseUrl=... to point at a local backend

# iOS: see iosApp/README.md (Xcode on macOS)
```

CI runs the backend suite, lint, and an Android build on every pull request.

## Conventions

- **Pull requests only.** `main` is protected and requires green CI. Branch from
  `main`, open a PR, let the backend and android checks pass, then squash merge.
- **Commits**: this GitHub account blocks pushes that expose the owner's real
  email. On any machine that pushes here, set
  `git config user.email` to the account's `@users.noreply.github.com` address,
  or pushes are rejected.
- **Docs voice**: no em dashes and no marketing copy in the README or `docs/`.
  Keep it plain and factual.
- **Never commit secrets**: `google-services.json`, `GoogleService-Info.plist`,
  `*.keystore`/`*.jks`, `local.properties`, `.env*`, and anything in
  `docs-private/` are gitignored. Keep it that way.
- **gcloud**: all infrastructure is in project `chaincheck-app`. Always pass
  `--project=chaincheck-app` explicitly; the machine's active gcloud config may
  point elsewhere.

## Status

Android v0.1.2 is published. iOS is live on public TestFlight; the scheduled
workflow `.github/workflows/testflight.yml` keeps the build fresh
automatically. The backend is production hardened (deny-all Firestore,
token-gated internal endpoints, rate/size/SSRF guards) and runs unattended.
Next up: the iOS map (MapKit) and push wiring (`iosApp/README.md`), then App
Store and Google Play at the store-prep stage.
