package com.glazkov.chaincheck.push

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.ComponentActivity
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.tasks.await
import java.lang.ref.WeakReference

object NotificationPermission {
    private var launcher: ActivityResultLauncher<String>? = null
    private var activityRef: WeakReference<ComponentActivity>? = null

    fun register(activity: ComponentActivity) {
        activityRef = WeakReference(activity)
        launcher = activity.registerForActivityResult(
            ActivityResultContracts.RequestPermission()
        ) { /* result read lazily via checkSelfPermission */ }
    }

    fun requestIfNeeded() {
        if (Build.VERSION.SDK_INT < 33) return
        val activity = activityRef?.get() ?: return
        val granted = ContextCompat.checkSelfPermission(
            activity, Manifest.permission.POST_NOTIFICATIONS
        ) == PackageManager.PERMISSION_GRANTED
        if (!granted) launcher?.launch(Manifest.permission.POST_NOTIFICATIONS)
    }
}

actual fun requestNotificationPermission() {
    NotificationPermission.requestIfNeeded()
}

actual suspend fun currentPushToken(): String? = runCatching {
    FirebaseMessaging.getInstance().token.await()
}.onSuccess {
    if (com.glazkov.chaincheck.BuildConfig.DEBUG) {
        android.util.Log.d("ChainCheck", "FCM token: $it")
    }
}.getOrNull()
