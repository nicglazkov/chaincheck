package com.glazkov.chaincheck.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import com.glazkov.chaincheck.data.MapData
import com.glazkov.chaincheck.data.MapWebcam
import platform.Foundation.NSURL
import platform.UIKit.UIApplication

// MapKit-backed map lands with the iOS build on the Mac.
@Composable
actual fun PlatformMap(
    data: MapData,
    onWebcamTap: (MapWebcam) -> Unit,
    onNavigateTo: (lat: Double, lon: Double, label: String) -> Unit,
    modifier: Modifier,
) {
    Box(modifier.fillMaxSize()) {
        Text(
            "Map arrives with the iOS build.",
            modifier = Modifier.align(Alignment.Center),
        )
    }
}

actual fun launchNavigation(lat: Double, lon: Double, label: String) {
    val url = NSURL.URLWithString("http://maps.apple.com/?daddr=$lat,$lon") ?: return
    UIApplication.sharedApplication.openURL(url)
}
