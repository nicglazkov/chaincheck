package com.glazkov.chaincheck.data

// App Check is wired on iOS with the App Attest provider when the iOS app is
// built (Task #7). Until then there is no attestation token to send.
actual suspend fun appCheckToken(): String? = null
