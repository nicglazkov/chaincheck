package com.glazkov.chaincheck.push

/**
 * Current device push token (FCM on Android, APNs-backed FCM on iOS), or
 * null when push isn't available (no Play services, permission denied, iOS
 * wiring pending).
 */
expect suspend fun currentPushToken(): String?

/** Ask the OS for notification permission if it needs asking. */
expect fun requestNotificationPermission()
