package com.glazkov.chaincheck.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import com.glazkov.chaincheck.data.ChainCheckApi
import com.glazkov.chaincheck.data.MapData
import com.glazkov.chaincheck.data.MapWebcam
import com.glazkov.chaincheck.data.Repository

/**
 * The platform map (Google Maps on Android, MapKit on iOS later). Draws the
 * markers and calls back on webcam taps and navigate requests.
 */
@Composable
expect fun PlatformMap(
    data: MapData,
    focus: MapFocus?,
    layers: MapLayers,
    onWebcamTap: (MapWebcam) -> Unit,
    onNavigateTo: (lat: Double, lon: Double, label: String) -> Unit,
    modifier: Modifier = Modifier,
)

/** Hand off to the platform's navigation app for turn-by-turn. */
expect fun launchNavigation(lat: Double, lon: Double, label: String)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MapScreen(
    repository: Repository,
    focus: MapFocus? = null,
    modifier: Modifier = Modifier,
) {
    val api = remember { ChainCheckApi() }
    var data by remember { mutableStateOf<MapData?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var webcam by remember { mutableStateOf<MapWebcam?>(null) }
    var layers by remember { mutableStateOf(MapLayers()) }

    LaunchedEffect(Unit) {
        runCatching { api.mapData() }
            .onSuccess { data = it }
            .onFailure { error = it.message ?: "couldn't load map data" }
    }

    Box(modifier.fillMaxSize()) {
        when {
            error != null -> Column(
                Modifier.align(Alignment.Center),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text("Map data unavailable: ${error!!.substringBefore(" [").take(80)}")
            }

            data == null -> CircularProgressIndicator(Modifier.align(Alignment.Center))

            else -> {
                PlatformMap(
                    data = data!!,
                    focus = focus,
                    layers = layers,
                    onWebcamTap = { webcam = it },
                    onNavigateTo = { lat, lon, label -> launchNavigation(lat, lon, label) },
                    modifier = Modifier.fillMaxSize(),
                )
                RouteSuggestionCard(
                    repository = repository,
                    modifier = Modifier
                        .align(Alignment.TopCenter)
                        .padding(horizontal = 12.dp, vertical = 8.dp),
                )
                LayerToggles(
                    layers = layers,
                    onChange = { layers = it },
                    modifier = Modifier
                        .align(Alignment.BottomStart)
                        .padding(start = 12.dp, bottom = 18.dp),
                )
            }
        }

        webcam?.let { cam ->
            ModalBottomSheet(onDismissRequest = { webcam = null }) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(cam.name, style = MaterialTheme.typography.titleMedium)
                    Text(
                        listOf(cam.route, cam.direction, cam.nearby)
                            .filter { it.isNotBlank() }
                            .joinToString(" - "),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    AsyncImage(
                        model = cam.imageUrl,
                        contentDescription = "Live view: ${cam.name}",
                        contentScale = ContentScale.FillWidth,
                        modifier = Modifier.fillMaxWidth().height(220.dp),
                    )
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            "Camera image: Caltrans",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        TextButton(onClick = {
                            launchNavigation(cam.lat, cam.lon, cam.name)
                            webcam = null
                        }) { Text("Navigate here") }
                    }
                }
            }
        }
    }
}

@Composable
private fun LayerToggles(
    layers: MapLayers,
    onChange: (MapLayers) -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(modifier, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        MapToggleChip("Roads", layers.roads) { onChange(layers.copy(roads = it)) }
        MapToggleChip("Cams", layers.webcams) { onChange(layers.copy(webcams = it)) }
        MapToggleChip("Resorts", layers.resorts) { onChange(layers.copy(resorts = it)) }
    }
}

@Composable
private fun MapToggleChip(label: String, on: Boolean, onToggle: (Boolean) -> Unit) {
    val palette = LocalPalette.current
    androidx.compose.material3.FilterChip(
        selected = on,
        onClick = { onToggle(!on) },
        label = { Text(label) },
        shape = MaterialTheme.shapes.extraLarge,
        colors = androidx.compose.material3.FilterChipDefaults.filterChipColors(
            containerColor = if (palette.isDark) androidx.compose.ui.graphics.Color(0xCC101B2E)
            else androidx.compose.ui.graphics.Color(0xF2FFFFFF),
            selectedContainerColor = palette.accent,
            selectedLabelColor = MaterialTheme.colorScheme.onPrimary,
        ),
    )
}

/** Compact "which way right now" strip built from data the app already has. */
@Composable
private fun RouteSuggestionCard(repository: Repository, modifier: Modifier = Modifier) {
    val state by repository.home.collectAsState()
    val summary = state.summary ?: return
    val candidates = summary.corridors.filter { it.id in setOf("i80", "us50", "sr88") }
    if (candidates.isEmpty()) return
    // Lower tier wins; fewer closures breaks ties. Presented as status, not advice.
    val best = candidates.minByOrNull { it.tier * 100 + it.closures } ?: return
    // The destination picked on Home decides which route this reader cares
    // about; the card answers for that route first, then names the clearest.
    val chosen = candidates.firstOrNull { it.id == repository.selectedCorridor }

    CcCard(modifier) {
        Column(Modifier.padding(horizontal = 14.dp, vertical = 10.dp)) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                candidates.forEach { corridor ->
                    Text(
                        "${corridor.route} ${corridor.tierLabel}",
                        color = TierColors.forTier(corridor.tier),
                        fontWeight = if (corridor.id == best.id) FontWeight.Bold
                        else FontWeight.Normal,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            }
            val bestStatus = "${best.route} (${best.tierLabel}, " +
                countLabel(best.closures, "closure") + ")"
            Text(
                when {
                    chosen == null || chosen.id == best.id ->
                        "Clearest right now: $bestStatus"
                    else ->
                        "Your route ${chosen.route}: ${chosen.tierLabel}, " +
                            countLabel(chosen.closures, "closure") +
                            ". Clearest: $bestStatus"
                },
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
