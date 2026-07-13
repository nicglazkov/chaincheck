package com.glazkov.chaincheck.data

/**
 * The current Firebase App Check token, or null when attestation is
 * unavailable (Firebase not configured, provider not installed, or the
 * platform has no App Check yet). The backend records attestation and, once
 * the app ships through Play, will require it on write endpoints.
 */
expect suspend fun appCheckToken(): String?
