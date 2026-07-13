# App Check (attestation) rollout

App Check proves a backend request came from the genuine ChainCheck app on a
real device. It is wired end to end but runs **monitoring-first**: the app
sends an attestation token, the backend records whether each request is
attested, and nothing is rejected until enforcement is switched on.

## Status

- **App**: installs the Play Integrity provider at startup and attaches the
  token as `X-Firebase-AppCheck` on every backend call. Absent Firebase (a
  build without `google-services.json`) simply sends no token.
- **Backend**: verifies the token with the Firebase Admin SDK, records the
  outcome, and exposes the rate at `GET /internal/appcheck-stats` (behind the
  poll token). Enforcement is gated by the `APP_CHECK_ENFORCE` env var, off by
  default. When on, only write endpoints (`/v1/tripbrief`, `/v1/subscriptions*`)
  require a valid token; reads stay open for the future web page and evals.

## One-time console setup (owner only)

These cannot be scripted headlessly:

1. Firebase console -> **App Check** -> register the Android app with the
   **Play Integrity** provider.
2. Add the app's release signing **SHA-256** (and the debug SHA-256 for
   emulator testing) under Project settings -> the Android app.
3. For the emulator / a debug build, register a **debug token** (logged by the
   app on first run) so testing is not blocked once enforcement is on.

## Turning enforcement on (planned: Play Store release)

Do this only after the app is distributed through Google Play, because Play
Integrity's "this is really your app" guarantee depends on Play distribution.

1. Watch `GET /internal/appcheck-stats` until `attested_pct` for real app
   traffic is high and stable.
2. Set `APP_CHECK_ENFORCE=1` on the Cloud Run service and redeploy.
3. Flip App Check enforcement on in the Firebase console for the APIs.

Enforcement also closes the distributed rate-limit gap, because limits can
then key on the attested app instance instead of a spoofable IP.
