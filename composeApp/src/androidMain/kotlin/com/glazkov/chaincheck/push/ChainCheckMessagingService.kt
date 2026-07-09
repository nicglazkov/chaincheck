package com.glazkov.chaincheck.push

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import androidx.core.app.NotificationCompat
import com.glazkov.chaincheck.MainActivity
import com.glazkov.chaincheck.R
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

class ChainCheckMessagingService : FirebaseMessagingService() {

    override fun onNewToken(token: String) {
        // The Alerts screen re-reads the current token on open and re-saves the
        // subscription; a stale server-side token just stops matching.
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val notification = message.notification ?: return
        val manager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(
            NotificationChannel(
                CHANNEL_ID,
                "Road alerts",
                NotificationManager.IMPORTANCE_HIGH,
            ).apply { description = "Chain control changes, closures, storm warnings" }
        )
        val intent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE,
        )
        val built = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(notification.title ?: "ChainCheck")
            .setContentText(notification.body ?: "")
            .setStyle(NotificationCompat.BigTextStyle().bigText(notification.body ?: ""))
            .setAutoCancel(true)
            .setContentIntent(intent)
            .build()
        manager.notify(message.messageId.hashCode(), built)
    }

    private companion object {
        const val CHANNEL_ID = "road_alerts"
    }
}
