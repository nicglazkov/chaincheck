package com.glazkov.chaincheck.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Map
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.glazkov.chaincheck.data.ChainCheckApi
import com.glazkov.chaincheck.data.CorridorDetail
import com.glazkov.chaincheck.data.Repository

@Composable
fun RoutesScreen(
    repository: Repository,
    onOpenRoute: (String) -> Unit,
    onShowOnMap: (MapFocus) -> Unit = {},
    modifier: Modifier = Modifier,
) {
    val state by repository.home.collectAsState()
    val corridors = state.summary?.corridors ?: emptyList()
    val passByCorridor = state.summary?.passes?.associateBy { it.corridorId } ?: emptyMap()

    LazyColumn(
        modifier = modifier.fillMaxSize().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        items(corridors, key = { it.id }) { corridor ->
            CcCard(Modifier.fillMaxWidth().clickable { onOpenRoute(corridor.id) }) {
                Row(
                    Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(
                        Modifier
                            .size(52.dp)
                            .background(TierColors.forTier(corridor.tier), CircleShape),
                        verticalArrangement = Arrangement.Center,
                        horizontalAlignment = Alignment.CenterHorizontally,
                    ) {
                        Text(
                            corridor.tierLabel,
                            color = Color.White,
                            fontWeight = FontWeight.Bold,
                            style = MaterialTheme.typography.titleSmall,
                        )
                    }
                    Spacer(Modifier.width(14.dp))
                    Column(Modifier.weight(1f)) {
                        Text(corridor.name, style = MaterialTheme.typography.titleMedium)
                        Text(
                            corridor.description,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        if (corridor.closures + corridor.incidents > 0) {
                            Text(
                                countLabel(corridor.closures, "closure") + " - " +
                                    countLabel(corridor.incidents, "incident"),
                                style = MaterialTheme.typography.bodySmall,
                            )
                        }
                    }
                    val pass = passByCorridor[corridor.id]
                    val focus = if (pass?.lat != null && pass.lon != null) {
                        MapFocus(pass.lat, pass.lon, 10f, corridor.name)
                    } else {
                        CORRIDOR_CENTERS[corridor.id]?.let { (lat, lon) ->
                            MapFocus(lat, lon, 10f, corridor.name)
                        }
                    }
                    if (focus != null) {
                        IconButton(onClick = { onShowOnMap(focus) }) {
                            Icon(
                                Icons.Filled.Map,
                                contentDescription = "Show ${corridor.name} on map",
                                tint = LocalPalette.current.accent,
                            )
                        }
                    }
                }
            }
        }
    }
}

/**
 * CHP dispatch shorthand ("1181-Trfc Collision-Minor Inj") reads like radio
 * chatter. Strip the code and expand the abbreviations drivers won't know.
 */
private val CHP_ABBREVIATIONS = mapOf(
    "Trfc" to "Traffic",
    "Veh" to "Vehicle",
    "Injs" to "Injuries",
    "Inj" to "Injury",
    "Enrt" to "En Route",
    "Rte" to "Route",
    "Hwy" to "Highway",
    "Rdwy" to "Roadway",
    "Anml" to "Animal",
    "Med" to "Medical",
    "Maint" to "Maintenance",
)

internal fun humanizeIncidentType(raw: String): String {
    var text = raw.replace(Regex("^\\d+[A-Za-z]?\\s*-\\s*"), "")
    for ((abbr, full) in CHP_ABBREVIATIONS) {
        text = text.replace(Regex("\\b$abbr\\b"), full)
    }
    return text.replace(Regex("\\s*-\\s*"), " · ")
}

/**
 * Fallback map targets for corridors whose pass has no coordinates, so every
 * route row gets the same "show me" affordance. Midpoints of the baked OSM
 * geometry; corridors are static so these are too.
 */
private val CORRIDOR_CENTERS = mapOf(
    "sr20" to (39.2707 to -120.8558),
    "sr28" to (39.2048 to -120.0748),
)

@Composable
fun RouteDetailScreen(
    corridorId: String,
    repository: Repository,
    onBack: () -> Unit,
    onShowOnMap: (MapFocus) -> Unit = {},
    modifier: Modifier = Modifier,
) {
    var detail by remember { mutableStateOf<CorridorDetail?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var attempt by remember { mutableStateOf(0) }
    val showAllPoints = remember { mutableStateOf(false) }
    val api = remember { ChainCheckApi() }
    val cachedCorridor = repository.home.collectAsState().value
        .summary?.corridors?.firstOrNull { it.id == corridorId }

    LaunchedEffect(corridorId, attempt) {
        error = null
        runCatching { api.routeDetail(corridorId) }
            .onSuccess { detail = it }
            .onFailure { error = it.message ?: "load failed" }
    }

    Column(modifier.fillMaxSize().padding(16.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
            }
            Text(
                detail?.name ?: cachedCorridor?.name ?: "Route",
                style = MaterialTheme.typography.titleLarge,
            )
        }

        val loaded = detail
        when {
            loaded == null && error != null -> Column(
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                // Offline still answers the headline question from the last
                // saved summary; only the checkpoint list needs a connection.
                if (cachedCorridor != null) {
                    Text(
                        "${cachedCorridor.tierLabel}: ${cachedCorridor.tierMeaning}",
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.SemiBold,
                        color = TierColors.forTier(cachedCorridor.tier),
                    )
                    Text(
                        "From your last update. Checkpoint details need a connection.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Text(humanizeError(error), color = MaterialTheme.colorScheme.error)
                TextButton(onClick = { attempt++ }) { Text("Try again") }
            }
            loaded == null -> Row(
                Modifier.fillMaxWidth().padding(top = 24.dp),
                horizontalArrangement = Arrangement.Center,
            ) { CircularProgressIndicator() }
            else -> LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                item {
                    Text(
                        "${loaded.tierLabel}: ${loaded.tierMeaning}",
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.SemiBold,
                        color = TierColors.forTier(loaded.tier),
                    )
                    Text(
                        "As of ${formatLocalTime(loaded.feed.asOf)}" +
                            if (loaded.feed.stale) " (cached)" else "",
                        style = MaterialTheme.typography.bodySmall,
                    )
                    HorizontalDivider(Modifier.padding(vertical = 8.dp))
                }
                if (loaded.controlPoints.isNotEmpty()) {
                    item { Text("Chain control points", style = MaterialTheme.typography.titleSmall) }
                    // A quiet corridor collapses its checkpoint list: one calm
                    // sentence beats three screens of identical "no controls".
                    val allClear = loaded.controlPoints.all { it.tier == 0 }
                    if (allClear && !showAllPoints.value) {
                        item {
                            Row(
                                Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Text(
                                    "All ${loaded.controlPoints.size} checkpoints " +
                                        "on this route are clear right now.",
                                    modifier = Modifier.weight(1f),
                                )
                                TextButton(onClick = { showAllPoints.value = true }) {
                                    Text("Show them")
                                }
                            }
                        }
                    } else {
                        items(loaded.controlPoints) { point ->
                            Row(
                                Modifier.fillMaxWidth().clickable {
                                    onShowOnMap(MapFocus(point.lat, point.lon, 13f, point.location))
                                }.padding(vertical = 2.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Text(
                                    point.tierLabel,
                                    color = TierColors.forTier(point.tier),
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.width(64.dp),
                                )
                                Column {
                                    Text("${point.location} (${point.direction})")
                                    // R0's "nothing happening" text is implied
                                    // by the label; repeating it row after row
                                    // buries the real information.
                                    if (point.description.isNotBlank() && point.tier != 0) {
                                        Text(
                                            point.description,
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
                if (loaded.closureList.isNotEmpty()) {
                    item {
                        HorizontalDivider(Modifier.padding(vertical = 8.dp))
                        Text("Closures", style = MaterialTheme.typography.titleSmall)
                    }
                    items(loaded.closureList) { closure ->
                        Column(
                            Modifier.fillMaxWidth().clickable {
                                onShowOnMap(
                                    MapFocus(closure.begin.lat, closure.begin.lon, 13f, closure.location)
                                )
                            }.padding(vertical = 2.dp),
                        ) {
                            Text("${closure.location} (${closure.direction})")
                            Text(
                                listOfNotNull(
                                    closure.type.takeIf { it.isNotBlank() },
                                    closure.work.takeIf { it.isNotBlank() },
                                    closure.delayMinutes?.let { "$it min delay" },
                                ).joinToString(" - "),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
                if (loaded.incidentList.isNotEmpty()) {
                    item {
                        HorizontalDivider(Modifier.padding(vertical = 8.dp))
                        Text("CHP incidents", style = MaterialTheme.typography.titleSmall)
                    }
                    items(loaded.incidentList) { incident ->
                        Column(
                            Modifier.fillMaxWidth().clickable {
                                onShowOnMap(MapFocus(incident.lat, incident.lon, 13f, incident.location))
                            }.padding(vertical = 2.dp),
                        ) {
                            Text(humanizeIncidentType(incident.type))
                            Text(
                                "${incident.location} - ${incident.area}",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
            }
        }
    }
}
