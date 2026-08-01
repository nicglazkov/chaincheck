# ChainCheck for iOS

This directory holds the Xcode app that wraps the shared `ComposeApp` framework.
The Xcode project is created on a Mac (iOS builds only run on macOS with Xcode).
Everything in the shared Kotlin module is already iOS ready, so most of the work
here is Xcode setup plus three native integrations.

## Current state

The shared Kotlin code compiles for iOS and runs the full app. All `expect`
declarations have iOS `actual` implementations in `composeApp/src/iosMain/`.

| Area | iOS status | File |
|---|---|---|
| App entry point | Done | `iosMain/.../MainViewController.kt` |
| HTTP client (Darwin) | Done | `iosMain/.../data/Api.ios.kt` |
| Open URL | Done | `iosMain/.../data/OpenUrl.ios.kt` |
| Launch navigation (Apple Maps) | Done | `iosMain/.../ui/MapScreen.ios.kt` |
| System back handling | Done (no-op, correct on iOS) | `iosMain/.../ui/BackHandler.ios.kt` |
| Map view | Placeholder text | `iosMain/.../ui/MapScreen.ios.kt` |
| Push token (FCM) | Stub returns `null` | `iosMain/.../push/PushToken.ios.kt` |
| App Check token | Stub returns `null` | `iosMain/.../data/AppCheck.ios.kt` |
| Xcode project | Done, generated with xcodegen | `project.yml` |

What this means: once the Xcode project embeds the framework, the app launches
and Home, Routes, Resorts, Trip brief, and Alerts all work against the live
public backend with no further code. Only the Map tab (placeholder) and push
(no token) are incomplete. App Check returning `null` is fine because backend
enforcement is off (monitoring only); wire it when enforcement flips in October.

## Toolchain and identity

- Kotlin 2.1.21, Compose Multiplatform 1.8.2, Gradle 8.14.5, AGP 8.7.3.
- Framework: `baseName = "ComposeApp"`, static, targets `iosArm64` and
  `iosSimulatorArm64` (Apple Silicon). On an Intel Mac, add `iosX64()` to the
  target list in `composeApp/build.gradle.kts`.
- Bundle identifier: reuse `com.glazkov.chaincheck` (matches Android).
- Backend base URL is baked in as the default in
  `composeApp/src/commonMain/.../data/Api.kt` and is public. No per-platform
  backend work is needed; the JSON API is client agnostic.

## Build and release

The Xcode project is generated, not committed. To build locally:

```bash
brew install xcodegen   # once
cd iosApp && xcodegen generate
xcodebuild -project ChainCheck.xcodeproj -scheme ChainCheck \
  -destination "generic/platform=iOS Simulator" build
```

Release signing is manual: an Apple Distribution certificate plus the
"ChainCheck AppStore" provisioning profile, both created through the App Store
Connect API. The scheduled workflow `.github/workflows/testflight.yml`
re-archives and re-uploads a TestFlight build when the newest one has less
than 35 days of life left, using `scripts/testflight.py` for the API steps.
Secrets live in the GitHub repo settings (ASC key, dist cert and key, profile,
all base64).

## Step 1: create the Xcode project

On the Mac, create a SwiftUI app in this `iosApp/` directory (Xcode: New
Project, iOS App, SwiftUI, bundle id `com.glazkov.chaincheck`, name ChainCheck).
Then replace the two generated Swift files with these.

`iosApp/iosApp/iOSApp.swift`:

```swift
import SwiftUI

@main
struct iOSApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView().ignoresSafeArea(.all)
        }
    }
}
```

`iosApp/iosApp/ContentView.swift`:

```swift
import SwiftUI
import ComposeApp

struct ComposeView: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> UIViewController {
        // MainViewController() is a top-level Kotlin function; K/N exposes it
        // on the file-name class MainViewControllerKt.
        MainViewControllerKt.MainViewController()
    }
    func updateUIViewController(_ vc: UIViewController, context: Context) {}
}

struct ContentView: View {
    var body: some View { ComposeView().ignoresSafeArea() }
}
```

## Step 2: embed the shared framework

Add a Run Script build phase to the app target, above "Compile Sources":

```bash
cd "$SRCROOT/.."
./gradlew :composeApp:embedAndSignAppleFrameworkForXcode
```

Then, in the app target build settings:

- Framework Search Paths:
  `$(SRCROOT)/../composeApp/build/xcode-frameworks/$(CONFIGURATION)/$(SDK_NAME)`
- Other Linker Flags: `-framework ComposeApp`
- User Script Sandboxing: No (the script writes into the build directory).

Build for an Apple Silicon simulator. The app should launch to Home with live
data. If the framework is not found, run
`./gradlew :composeApp:linkDebugFrameworkIosSimulatorArm64` once, then rebuild.

## Step 3: Info.plist

Add:

- `NSLocationWhenInUseUsageDescription`: "ChainCheck uses your location to show
  nearby chain controls and cameras on the map." (needed once the map requests
  location).
- Display name: ChainCheck.

App Transport Security needs no exception (the backend is HTTPS). Opening Apple
Maps via `launchNavigation` needs no URL scheme registration.

## The three native integrations

### 1. Map (`MapScreen.ios.kt` `PlatformMap`)

The Android map uses Google's `maps-compose`, which is Android only. Implement
the iOS map with MapKit via Compose `UIKitView` interop hosting an `MKMapView`.

- Feed annotations from the `MapData` argument: control points, closures,
  incidents, webcams, resorts, and passes (each already carries lat/lon and a
  kind). Color by tier where relevant to match the Android look.
- Draw corridor lines as `MKPolyline` from the route geometry in `MapData`.
- Tap a webcam annotation, call `onWebcamTap(webcam)`; the shared UI opens the
  webcam sheet. Tap a place, call `onNavigateTo(lat, lon, label)`, which is
  already wired to `launchNavigation` (Apple Maps).
- Set the visible region from the route bounds.

MapKit needs no API key and is free. If you want exact visual parity with the
Android Google map instead, the Google Maps iOS SDK works via `UIKitView` too,
but it needs an iOS-restricted Maps key (register it in the `chaincheck-app`
Google Cloud project, restricted to this bundle id). Start with MapKit.

### 2. Push (`PushToken.ios.kt`)

- Add the Firebase iOS SDK with Swift Package Manager (FirebaseMessaging).
- Xcode capabilities: Push Notifications, and Background Modes with Remote
  notifications checked.
- In the Firebase console for project `chaincheck-app`: register an iOS app with
  bundle id `com.glazkov.chaincheck`, download `GoogleService-Info.plist`, and
  add it to the app target (it is gitignored, same policy as the Android
  `google-services.json`). Upload an APNs auth key (.p8 from the Apple Developer
  account) under Cloud Messaging.
- In `iOSApp`: `FirebaseApp.configure()`, set the messaging delegate, request
  `UNUserNotificationCenter` authorization, and register for remote
  notifications.
- Bridge the token to Kotlin: add a small holder the Swift delegate writes to
  on `didReceiveRegistrationToken`, and return it from `currentPushToken()`.
  Leave `requestNotificationPermission()` a no-op if you request authorization
  from Swift at launch.

No backend change is needed. The subscription flow (`POST /v1/subscriptions`
with the token in the body) is identical across platforms; the backend sends
through FCM, which delivers to iOS via APNs once the APNs key is uploaded. Test
push on a real device (the simulator cannot receive real APNs pushes).

### 3. App Check (`AppCheck.ios.kt`)

Deferred. Enforcement is off, so `null` is correct today. When enforcement flips
(October, at Play/App Store launch), add Firebase App Check with the App Attest
provider and return its token here. See `docs/app-check.md` for the enforcement
plan.

## Secrets and accounts (never commit)

Provided on the Mac, not in the repo:

- `GoogleService-Info.plist` (Firebase iOS config). Gitignored.
- APNs auth key (.p8), uploaded to the Firebase console.
- Apple Developer account for signing, the bundle id, provisioning, and the
  Push Notifications entitlement.
- Only if you choose the Google Maps iOS SDK over MapKit: an iOS-restricted
  Maps key.

## Verify

- Launch on an Apple Silicon simulator: Home shows live tiers and closures,
  Routes and Resorts load, the Trip brief returns an AI summary, Alerts screen
  renders. The Map tab shows the placeholder until step 1 of the integrations is
  done.
- Push and App Attest need a real device and the Apple Developer account.
