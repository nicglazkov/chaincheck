package com.glazkov.chaincheck.data

import android.content.Intent
import android.net.Uri

actual fun openUrl(url: String) {
    // Reuses the app context MainActivity stored for navigation intents.
    val context = com.glazkov.chaincheck.ui.navContext ?: return
    context.startActivity(
        Intent(Intent.ACTION_VIEW, Uri.parse(url))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    )
}
