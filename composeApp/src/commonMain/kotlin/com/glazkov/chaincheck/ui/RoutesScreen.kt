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
import androidx.compose.material3.Card
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
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
    modifier: Modifier = Modifier,
) {
    val state by repository.home.collectAsState()
    val corridors = state.summary?.corridors ?: emptyList()

    LazyColumn(
        modifier = modifier.fillMaxSize().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        items(corridors, key = { it.id }) { corridor ->
            Card(Modifier.fillMaxWidth().clickable { onOpenRoute(corridor.id) }) {
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
                    Column {
                        Text(corridor.name, style = MaterialTheme.typography.titleMedium)
                        Text(
                            corridor.description,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        if (corridor.closures + corridor.incidents > 0) {
                            Text(
                                "${corridor.closures} closures - " +
                                    "${corridor.incidents} incidents",
                                style = MaterialTheme.typography.bodySmall,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun RouteDetailScreen(
    corridorId: String,
    repository: Repository,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    var detail by remember { mutableStateOf<CorridorDetail?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    val api = remember { ChainCheckApi() }

    LaunchedEffect(corridorId) {
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
                detail?.name ?: corridorId,
                style = MaterialTheme.typography.titleLarge,
            )
        }

        val loaded = detail
        when {
            error != null -> Text("Couldn't load: $error")
            loaded == null -> Text("Loading...")
            else -> LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                item {
                    Text(
                        "${loaded.tierLabel}: ${loaded.tierMeaning}",
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.SemiBold,
                        color = TierColors.forTier(loaded.tier),
                    )
                    Text(
                        "As of ${loaded.feed.asOf?.take(16)?.replace("T", " ") ?: "unknown"}" +
                            if (loaded.feed.stale) " (cached)" else "",
                        style = MaterialTheme.typography.bodySmall,
                    )
                    HorizontalDivider(Modifier.padding(vertical = 8.dp))
                }
                if (loaded.controlPoints.isNotEmpty()) {
                    item { Text("Chain control points", style = MaterialTheme.typography.titleSmall) }
                    items(loaded.controlPoints) { point ->
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                point.tierLabel,
                                color = TierColors.forTier(point.tier),
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.width(64.dp),
                            )
                            Column {
                                Text("${point.location} (${point.direction})")
                                if (point.description.isNotBlank()) {
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
                if (loaded.closureList.isNotEmpty()) {
                    item {
                        HorizontalDivider(Modifier.padding(vertical = 8.dp))
                        Text("Closures", style = MaterialTheme.typography.titleSmall)
                    }
                    items(loaded.closureList) { closure ->
                        Column(Modifier.fillMaxWidth()) {
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
                        Column(Modifier.fillMaxWidth()) {
                            Text(incident.type)
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
