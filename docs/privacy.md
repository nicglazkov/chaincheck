# ChainCheck privacy policy

Effective July 11, 2026.

ChainCheck is a free app that shows Sierra Nevada road and weather
conditions. It is built to collect as close to nothing as possible.

## What the app collects

**Nothing that identifies you.** ChainCheck has no accounts, no sign-in, no
names, no email addresses, and no advertising.

**An anonymous push token, only if you use alerts.** When you choose to
watch a route, the app stores your device's Firebase Cloud Messaging token
together with the route ids you picked, so the server can send you that
route's alerts. The token identifies an app installation, not a person.
It is deleted when you turn alerts off and automatically when it stops
working, for example after you uninstall the app.

**Crash reports.** If the app crashes, Firebase Crashlytics sends a report
with the technical state of the app (stack trace, device model, OS
version) so the problem can be fixed. Crash reports contain no personal
information and no location.

## Location

If you grant location access, your position is used on your device to show
the blue dot on the map and to hand off to your navigation app. Your
location is never sent to ChainCheck servers and never stored.

## What the app requests from servers

The app fetches road, weather, and resort conditions from the ChainCheck
API. These requests are ordinary web requests; the server keeps standard
short-lived operational logs (such as IP addresses in request logs and
rate-limit counters held in memory) and no user database of any kind.
Webcam images load directly from Caltrans.

## Third parties

- Google Maps renders the map (Google's privacy policy applies to map tiles).
- Firebase Cloud Messaging delivers push alerts; Firebase Crashlytics
  receives crash reports (Google privacy policy).
- Road, weather, and resort data come from public sources (Caltrans, CHP,
  the National Weather Service, Open-Meteo, resort websites) and are
  fetched by the ChainCheck server, not from your device.

Nothing is sold or shared with anyone for advertising or analytics.

## Children

ChainCheck is a driving utility and is not directed at children.

## Changes and contact

Changes to this policy will be posted at this page. Questions:
nic@glazkov.com or open an issue at
https://github.com/nicglazkov/chaincheck/issues.
