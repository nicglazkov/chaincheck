package com.glazkov.chaincheck.ui

import android.annotation.SuppressLint
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.glazkov.chaincheck.data.MapData
import com.glazkov.chaincheck.data.MapWebcam
import com.google.android.gms.maps.CameraUpdateFactory
import com.google.android.gms.maps.model.BitmapDescriptor
import com.google.android.gms.maps.model.BitmapDescriptorFactory
import com.google.android.gms.maps.model.CameraPosition
import com.google.android.gms.maps.model.LatLng
import com.google.android.gms.maps.model.MapStyleOptions
import com.google.maps.android.compose.GoogleMap
import com.google.maps.android.compose.MapProperties
import com.google.maps.android.compose.MapUiSettings
import com.google.maps.android.compose.Marker
import com.google.maps.android.compose.MarkerComposable
import com.google.maps.android.compose.MarkerState
import com.google.maps.android.compose.rememberCameraPositionState

private val TAHOE_CENTER = LatLng(39.09, -120.25)

/** Small anti-aliased dot with a contrast ring - the quiet marker language. */
private fun dotDescriptor(fill: Int, ring: Int, sizePx: Int): BitmapDescriptor {
    val bitmap = Bitmap.createBitmap(sizePx, sizePx, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)
    val center = sizePx / 2f
    val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    paint.color = ring
    canvas.drawCircle(center, center, center, paint)
    paint.color = fill
    canvas.drawCircle(center, center, center - sizePx * 0.16f, paint)
    return BitmapDescriptorFactory.fromBitmap(bitmap)
}

@SuppressLint("MissingPermission")
@Composable
actual fun PlatformMap(
    data: MapData,
    focus: MapFocus?,
    layers: MapLayers,
    onWebcamTap: (MapWebcam) -> Unit,
    onNavigateTo: (lat: Double, lon: Double, label: String) -> Unit,
    modifier: Modifier,
) {
    val palette = LocalPalette.current
    val cameraPositionState = rememberCameraPositionState {
        position = CameraPosition.fromLatLngZoom(
            focus?.let { LatLng(it.lat, it.lon) } ?: TAHOE_CENTER,
            focus?.zoom ?: 9f,
        )
    }
    LaunchedEffect(focus) {
        focus?.let {
            cameraPositionState.animate(
                CameraUpdateFactory.newLatLngZoom(LatLng(it.lat, it.lon), it.zoom),
                700,
            )
        }
    }

    var locationGranted by remember { mutableStateOf(hasLocationPermission()) }
    requestLocationPermissionOnce { locationGranted = it }

    GoogleMap(
        modifier = modifier,
        cameraPositionState = cameraPositionState,
        properties = MapProperties(
            isMyLocationEnabled = locationGranted,
            mapStyleOptions = MapStyleOptions(
                if (palette.isDark) DARK_MAP_STYLE else LIGHT_MAP_STYLE
            ),
        ),
        uiSettings = MapUiSettings(
            myLocationButtonEnabled = locationGranted,
            mapToolbarEnabled = false,
        ),
    ) {
        // Created inside map content: BitmapDescriptorFactory needs the Maps
        // SDK initialized, which GoogleMap guarantees for its children.
        val ringColor = if (palette.isDark) 0xFF0E1726.toInt() else 0xFFFFFFFF.toInt()
        val webcamDot = remember(palette.isDark) {
            dotDescriptor(0xFF4DA8C7.toInt(), ringColor, 34)
        }
        val closureDot = remember(palette.isDark) {
            dotDescriptor(0xFFE8930A.toInt(), ringColor, 38)
        }
        val incidentDot = remember(palette.isDark) {
            dotDescriptor(0xFFE03131.toInt(), ringColor, 38)
        }

        if (layers.webcams) {
            data.webcams.forEach { cam ->
                Marker(
                    state = MarkerState(LatLng(cam.lat, cam.lon)),
                    icon = webcamDot,
                    anchor = androidx.compose.ui.geometry.Offset(0.5f, 0.5f),
                    onClick = {
                        onWebcamTap(cam)
                        true
                    },
                )
            }
        }

        if (layers.roads) {
            data.closures.forEach { closure ->
                Marker(
                    state = MarkerState(LatLng(closure.begin.lat, closure.begin.lon)),
                    icon = closureDot,
                    title = "Closure: ${closure.location}",
                    snippet = listOfNotNull(
                        "${closure.route} ${closure.direction}",
                        closure.work.ifBlank { closure.type },
                        closure.delayMinutes?.let { "$it min delay" },
                    ).joinToString(" · "),
                )
            }
            data.incidents.forEach { incident ->
                Marker(
                    state = MarkerState(LatLng(incident.lat, incident.lon)),
                    icon = incidentDot,
                    title = incident.type.ifBlank { "CHP incident" },
                    snippet = incident.location,
                )
            }
            data.controls.filter { it.tier > 0 }.forEach { control ->
                val color = TierColors.forTier(control.tier, palette)
                MarkerComposable(
                    keys = arrayOf(control.tierLabel, palette.isDark),
                    state = MarkerState(LatLng(control.lat, control.lon)),
                    title = "${control.tierLabel} · ${control.location}",
                    snippet = "${control.route} ${control.direction} · tap for navigation",
                    onInfoWindowClick = {
                        onNavigateTo(control.lat, control.lon, control.location)
                    },
                ) {
                    TierPill(control.tierLabel, color)
                }
            }
        }

        if (layers.resorts) {
            data.resorts.forEach { resort ->
                MarkerComposable(
                    keys = arrayOf(resort.id, resort.snow24hIn ?: -1.0, palette.isDark),
                    state = MarkerState(LatLng(resort.lat, resort.lon)),
                    title = resort.name,
                    snippet = buildString {
                        resort.snow24hIn?.let { append("24h ${it}\" · ") }
                        val open = resort.liftsOpen
                        val total = resort.liftsTotal
                        if (open != null || total != null) {
                            append("lifts ${open ?: "?"}/${total ?: "?"}")
                        } else if (!resort.ok) append("report unavailable")
                    },
                    onInfoWindowClick = {
                        onNavigateTo(resort.lat, resort.lon, resort.name)
                    },
                ) {
                    ResortChip(resort.name, resort.snow24hIn, palette)
                }
            }
        }

        data.passes.forEach { pass ->
            MarkerComposable(
                keys = arrayOf(pass.id, palette.isDark),
                state = MarkerState(LatLng(pass.lat, pass.lon)),
                title = "${pass.name} · ${pass.elevationFt} ft",
                snippet = pass.route,
            ) {
                PassChip(pass.elevationFt, palette)
            }
        }
    }
}

@Composable
private fun TierPill(label: String, color: Color) {
    Text(
        label,
        color = Color.White,
        fontSize = 13.sp,
        fontWeight = FontWeight.ExtraBold,
        modifier = Modifier
            .background(color, RoundedCornerShape(50))
            .border(2.dp, Color.White.copy(alpha = 0.9f), RoundedCornerShape(50))
            .padding(horizontal = 10.dp, vertical = 4.dp),
    )
}

@Composable
private fun ResortChip(name: String, snow24h: Double?, palette: ChainCheckPalette) {
    val bg = if (palette.isDark) Color(0xF0142034) else Color(0xF7FFFFFF)
    val fg = if (palette.isDark) Color(0xFFEEF3FB) else Color(0xFF16202B)
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .background(bg, RoundedCornerShape(10.dp))
            .border(1.dp, palette.cardBorder, RoundedCornerShape(10.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp),
    ) {
        Text(
            "❄ " + name.substringBefore(" ("),
            color = fg,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
        )
        if (snow24h != null && snow24h > 0) {
            Text(
                "${snow24h}\" 24h",
                color = palette.accent,
                fontSize = 10.sp,
                fontWeight = FontWeight.SemiBold,
            )
        }
    }
}

@Composable
private fun PassChip(elevationFt: Int, palette: ChainCheckPalette) {
    val bg = if (palette.isDark) Color(0xB3101B2E) else Color(0xE6F0F3F7)
    val fg = if (palette.isDark) Color(0xFFC9D6EA) else Color(0xFF45536B)
    Text(
        "▲ ${elevationFt} ft",
        color = fg,
        fontSize = 10.sp,
        fontWeight = FontWeight.SemiBold,
        modifier = Modifier
            .background(bg, RoundedCornerShape(6.dp))
            .padding(horizontal = 6.dp, vertical = 2.dp),
    )
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
    LaunchedEffect(Unit) {
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

// Both styles mute POI/transit clutter so ChainCheck's own layers carry the
// map; dark matches the Summit night gradient.
private const val LIGHT_MAP_STYLE = """
[
  {"featureType":"poi","stylers":[{"visibility":"off"}]},
  {"featureType":"transit","stylers":[{"visibility":"off"}]},
  {"featureType":"road","elementType":"labels.icon","stylers":[{"visibility":"off"}]},
  {"featureType":"administrative.land_parcel","stylers":[{"visibility":"off"}]},
  {"featureType":"landscape.natural","elementType":"geometry","stylers":[{"saturation":-25},{"lightness":6}]},
  {"featureType":"water","elementType":"geometry","stylers":[{"color":"#a6c8e8"}]},
  {"featureType":"road.highway","elementType":"geometry","stylers":[{"color":"#f2c94c"},{"saturation":-35}]},
  {"featureType":"road.highway","elementType":"geometry.stroke","stylers":[{"color":"#d9d4c8"}]}
]
"""

private const val DARK_MAP_STYLE = """
[
  {"elementType":"geometry","stylers":[{"color":"#101b2c"}]},
  {"elementType":"labels.text.fill","stylers":[{"color":"#8fa2bd"}]},
  {"elementType":"labels.text.stroke","stylers":[{"color":"#0b1220"}]},
  {"featureType":"poi","stylers":[{"visibility":"off"}]},
  {"featureType":"transit","stylers":[{"visibility":"off"}]},
  {"featureType":"road","elementType":"labels.icon","stylers":[{"visibility":"off"}]},
  {"featureType":"road","elementType":"geometry","stylers":[{"color":"#22314b"}]},
  {"featureType":"road.highway","elementType":"geometry","stylers":[{"color":"#3c5077"}]},
  {"featureType":"road.highway","elementType":"geometry.stroke","stylers":[{"color":"#16203a"}]},
  {"featureType":"water","elementType":"geometry","stylers":[{"color":"#0c2438"}]},
  {"featureType":"landscape.natural","elementType":"geometry","stylers":[{"color":"#12203a"}]},
  {"featureType":"administrative","elementType":"geometry.stroke","stylers":[{"color":"#2c3d58"}]}
]
"""
