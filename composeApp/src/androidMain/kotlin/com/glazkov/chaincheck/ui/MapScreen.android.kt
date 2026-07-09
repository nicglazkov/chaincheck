package com.glazkov.chaincheck.ui

import android.annotation.SuppressLint
import android.content.Intent
import android.net.Uri
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import com.glazkov.chaincheck.data.MapData
import com.glazkov.chaincheck.data.MapWebcam
import com.google.android.gms.maps.model.BitmapDescriptorFactory
import com.google.android.gms.maps.model.CameraPosition
import com.google.android.gms.maps.model.LatLng
import com.google.maps.android.compose.GoogleMap
import com.google.maps.android.compose.MapProperties
import com.google.maps.android.compose.MapUiSettings
import com.google.maps.android.compose.Marker
import com.google.maps.android.compose.MarkerInfoWindow
import com.google.maps.android.compose.MarkerState
import com.google.maps.android.compose.rememberCameraPositionState

private val TAHOE_CENTER = LatLng(39.09, -120.25)

private fun tierHue(tier: Int): Float = when (tier) {
    0 -> BitmapDescriptorFactory.HUE_GREEN
    1 -> BitmapDescriptorFactory.HUE_YELLOW
    2 -> BitmapDescriptorFactory.HUE_ORANGE
    3 -> BitmapDescriptorFactory.HUE_RED
    4 -> BitmapDescriptorFactory.HUE_VIOLET
    else -> BitmapDescriptorFactory.HUE_AZURE
}

@SuppressLint("MissingPermission")
@Composable
actual fun PlatformMap(
    data: MapData,
    onWebcamTap: (MapWebcam) -> Unit,
    onNavigateTo: (lat: Double, lon: Double, label: String) -> Unit,
    modifier: Modifier,
) {
    val cameraPositionState = rememberCameraPositionState {
        position = CameraPosition.fromLatLngZoom(TAHOE_CENTER, 9f)
    }
    var locationGranted by remember { mutableStateOf(hasLocationPermission()) }
    requestLocationPermissionOnce { locationGranted = it }

    GoogleMap(
        modifier = modifier,
        cameraPositionState = cameraPositionState,
        properties = MapProperties(isMyLocationEnabled = locationGranted),
        uiSettings = MapUiSettings(myLocationButtonEnabled = locationGranted),
    ) {
        // Chain control points: only non-R0 get their own loud marker; R0
        // checkpoints would bury the map in green pins.
        data.controls.filter { it.tier > 0 }.forEach { control ->
            Marker(
                state = MarkerState(LatLng(control.lat, control.lon)),
                title = "${control.tierLabel} - ${control.location}",
                snippet = "${control.route} ${control.direction} - tap to navigate",
                icon = BitmapDescriptorFactory.defaultMarker(tierHue(control.tier)),
                onInfoWindowClick = {
                    onNavigateTo(control.lat, control.lon, control.location)
                },
            )
        }

        data.closures.forEach { closure ->
            Marker(
                state = MarkerState(LatLng(closure.begin.lat, closure.begin.lon)),
                title = "Closure: ${closure.location}",
                snippet = listOfNotNull(
                    "${closure.route} ${closure.direction}",
                    closure.work.ifBlank { closure.type },
                    closure.delayMinutes?.let { "$it min delay" },
                ).joinToString(" - "),
                icon = BitmapDescriptorFactory.defaultMarker(
                    BitmapDescriptorFactory.HUE_ORANGE
                ),
                alpha = 0.85f,
            )
        }

        data.incidents.forEach { incident ->
            Marker(
                state = MarkerState(LatLng(incident.lat, incident.lon)),
                title = incident.type.ifBlank { "CHP incident" },
                snippet = incident.location,
                icon = BitmapDescriptorFactory.defaultMarker(BitmapDescriptorFactory.HUE_RED),
            )
        }

        data.webcams.forEach { cam ->
            Marker(
                state = MarkerState(LatLng(cam.lat, cam.lon)),
                title = cam.name,
                snippet = "Tap marker again for the live view",
                icon = BitmapDescriptorFactory.defaultMarker(BitmapDescriptorFactory.HUE_CYAN),
                alpha = 0.75f,
                onClick = {
                    onWebcamTap(cam)
                    true
                },
            )
        }

        data.passes.forEach { pass ->
            MarkerInfoWindow(
                state = MarkerState(LatLng(pass.lat, pass.lon)),
                title = "${pass.name} - ${pass.elevationFt} ft",
                snippet = pass.route,
                icon = BitmapDescriptorFactory.defaultMarker(BitmapDescriptorFactory.HUE_BLUE),
            )
        }

        data.resorts.forEach { resort ->
            Marker(
                state = MarkerState(LatLng(resort.lat, resort.lon)),
                title = resort.name,
                snippet = buildString {
                    resort.snow24hIn?.let { append("24h ${it}\" - ") }
                    val open = resort.liftsOpen
                    val total = resort.liftsTotal
                    if (open != null || total != null) {
                        append("lifts ${open ?: "?"}/${total ?: "?"}")
                    } else if (!resort.ok) append("report unavailable")
                },
                icon = BitmapDescriptorFactory.defaultMarker(
                    BitmapDescriptorFactory.HUE_MAGENTA
                ),
                alpha = 0.9f,
                onInfoWindowClick = {
                    onNavigateTo(resort.lat, resort.lon, resort.name)
                },
            )
        }
    }
}

actual fun launchNavigation(lat: Double, lon: Double, label: String) {
    val context = navContext ?: return
    val encoded = Uri.encode(label)
    val intent = Intent(
        Intent.ACTION_VIEW,
        Uri.parse("google.navigation:q=$lat,$lon($encoded)"),
    ).apply {
        `package` = "com.google.android.apps.maps"
        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    }
    if (intent.resolveActivity(context.packageManager) != null) {
        context.startActivity(intent)
    } else {
        // No Google Maps app: any geo handler will do.
        context.startActivity(
            Intent(
                Intent.ACTION_VIEW,
                Uri.parse("geo:$lat,$lon?q=$lat,$lon($encoded)"),
            ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        )
    }
}

/** Set by MainActivity so navigation intents have a context. */
internal var navContext: android.content.Context? = null

private fun hasLocationPermission(): Boolean {
    val context = navContext ?: return false
    return androidx.core.content.ContextCompat.checkSelfPermission(
        context, android.Manifest.permission.ACCESS_COARSE_LOCATION
    ) == android.content.pm.PackageManager.PERMISSION_GRANTED
}

@Composable
private fun requestLocationPermissionOnce(onResult: (Boolean) -> Unit) {
    val launcher = androidx.activity.compose.rememberLauncherForActivityResult(
        androidx.activity.result.contract.ActivityResultContracts.RequestMultiplePermissions()
    ) { grants -> onResult(grants.values.any { it }) }
    androidx.compose.runtime.LaunchedEffect(Unit) {
        if (!hasLocationPermission()) {
            launcher.launch(
                arrayOf(
                    android.Manifest.permission.ACCESS_COARSE_LOCATION,
                    android.Manifest.permission.ACCESS_FINE_LOCATION,
                )
            )
        } else {
            onResult(true)
        }
    }
}
