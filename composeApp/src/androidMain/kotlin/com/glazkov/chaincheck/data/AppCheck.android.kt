package com.glazkov.chaincheck.data

import com.google.firebase.appcheck.FirebaseAppCheck
import kotlinx.coroutines.tasks.await

actual suspend fun appCheckToken(): String? =
    // No Firebase / no provider installed (e.g. a build without
    // google-services.json) throws here; the backend then records the request
    // as unattested and moves on. Never let attestation failure break a call.
    runCatching {
        FirebaseAppCheck.getInstance().getAppCheckToken(false).await().token
    }.getOrNull()?.ifBlank { null }
