package com.glazkov.chaincheck.push

// APNs/FCM wiring lands with the iOS build on the Mac; until then the Alerts
// screen saves locally and explains that push is not available.
actual suspend fun currentPushToken(): String? = null

actual fun requestNotificationPermission() {}
