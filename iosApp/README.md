# iosApp

The Xcode project for the iOS build lives here. It is generated on the Mac
(iOS builds happen there) and embeds the shared `ComposeApp` framework built
by `:composeApp`. Until that lands, the shared Kotlin code already declares
the iOS targets and `MainViewController`, so the Mac setup is:

1. Open this repo on the Mac and run the Kotlin Multiplatform wizard's iOS
   template into `iosApp/` (or `kdoctor` + Xcode new-project embedding the
   framework).
2. Add APNs capability + `google-services` iOS app config from the
   `chaincheck-app` Firebase project.
3. Implement `currentPushToken()` in `iosMain` against FirebaseMessaging.
