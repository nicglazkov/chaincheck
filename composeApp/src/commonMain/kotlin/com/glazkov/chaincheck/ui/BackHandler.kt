package com.glazkov.chaincheck.ui

import androidx.compose.runtime.Composable

/**
 * System back support: Android users navigate with the back gesture at least
 * as often as with on-screen arrows, and back must never silently exit the
 * app from an inner screen. iOS has no system back; its actual is a no-op.
 */
@Composable
expect fun PlatformBackHandler(enabled: Boolean, onBack: () -> Unit)
