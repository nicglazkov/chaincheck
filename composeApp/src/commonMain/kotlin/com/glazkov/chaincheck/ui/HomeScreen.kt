package com.glazkov.chaincheck.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.clickable
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.glazkov.chaincheck.data.PassSummary
import com.glazkov.chaincheck.data.Repository

private fun cmToInches(cm: Double): Double = cm / 2.54

@Composable
fun HomeScreen(
    repository: Repository,
    onOpenRoute: (String) -> Unit,
    onShowOnMap: (MapFocus) -> Unit = {},
    onQuickNav: (Tab) -> Unit = {},
    modifier: Modifier = Modifier,
) {
    val state by repository.home.collectAsState()
    var selected by remember { mutableStateOf(repository.selectedCorridor) }
    val palette = LocalPalette.current

    Column(
        modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("ChainCheck", style = MaterialTheme.typography.headlineMedium)

        val summary = state.summary
        if (summary == null) {
            if (state.loading) {
                CircularProgressIndicator(Modifier.align(Alignment.CenterHorizontally))
            } else {
                Text(state.error ?: "No data yet.")
                TextButton(onClick = { repository.refreshHome() }) { Text("Retry") }
            }
            return@Column
        }

        Text(
            "Where are you headed?",
            style = MaterialTheme.typography.titleSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            summary.corridors.filter { it.id in DESTINATIONS.keys }
                .sortedBy { DESTINATIONS.keys.indexOf(it.id) }
                .forEach { corridor ->
                    val isSelected = selected == corridor.id
                    FilterChip(
                        selected = isSelected,
                        onClick = {
                            selected = corridor.id
                            repository.selectedCorridor = corridor.id
                        },
                        label = {
                            Column(
                                horizontalAlignment = Alignment.CenterHorizontally,
                                modifier = Modifier.padding(vertical = 6.dp),
                            ) {
                                Text(
                                    DESTINATIONS.getValue(corridor.id),
                                    fontWeight = FontWeight.Bold,
                                )
                                Text(
                                    corridor.route,
                                    style = MaterialTheme.typography.labelSmall,
                                    color = if (isSelected)
                                        MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.85f)
                                    else palette.subtleText,
                                )
                            }
                        },
                        shape = MaterialTheme.shapes.medium,
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = palette.accent,
                            selectedLabelColor = MaterialTheme.colorScheme.onPrimary,
                        ),
                    )
                }
        }

        val corridor = summary.corridors.firstOrNull { it.id == selected }
            ?: summary.corridors.firstOrNull()
        if (corridor != null) {
            CcCard(Modifier.fillMaxWidth()) {
                Column(
                    Modifier.fillMaxWidth().padding(vertical = 4.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(corridor.name, style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(10.dp))
                    TierRing(tier = corridor.tier, label = corridor.tierLabel)
                    Spacer(Modifier.height(10.dp))
                    Text(
                        corridor.tierMeaning,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    if (corridor.closures > 0 || corridor.incidents > 0) {
                        Spacer(Modifier.height(6.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                            Text(
                                "${corridor.closures} closures",
                                style = MaterialTheme.typography.bodySmall,
                                color = palette.subtleText,
                            )
                            Text(
                                "${corridor.incidents} incidents",
                                style = MaterialTheme.typography.bodySmall,
                                color = palette.subtleText,
                            )
                        }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        TextButton(onClick = { onOpenRoute(corridor.id) }) {
                            Text("Route detail", color = palette.accent)
                        }
                        val pass = summary.passes.firstOrNull { it.corridorId == corridor.id }
                        if (pass?.lat != null && pass.lon != null) {
                            TextButton(onClick = {
                                onShowOnMap(MapFocus(pass.lat, pass.lon, 10f, corridor.name))
                            }) { Text("View on map", color = palette.accent) }
                        }
                    }
                }
            }

            summary.passes.firstOrNull { it.corridorId == corridor.id }?.let { pass ->
                StormCard(pass, onShowOnMap)
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            QuickAction("Map", Modifier.weight(1f)) { onQuickNav(Tab.Map) }
            QuickAction("Trip brief", Modifier.weight(1f)) { onQuickNav(Tab.Brief) }
            QuickAction("Alerts", Modifier.weight(1f)) { onQuickNav(Tab.Alerts) }
        }

        FreshnessLine(
            asOfIso = summary.feed.asOf,
            stale = summary.feed.stale || state.fromCache,
            error = state.error,
            onRefresh = { repository.refreshHome() },
        )
    }
}

@Composable
fun StormCard(pass: PassSummary, onShowOnMap: (MapFocus) -> Unit = {}) {
    val palette = LocalPalette.current
    val cardModifier = if (pass.lat != null && pass.lon != null) {
        Modifier.fillMaxWidth().clickable {
            onShowOnMap(MapFocus(pass.lat, pass.lon, 12f, pass.name))
        }
    } else Modifier.fillMaxWidth()
    CcCard(cardModifier) {
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(
                "${pass.name} · ${pass.elevationFt} ft",
                style = MaterialTheme.typography.titleSmall,
            )
            pass.alerts.firstOrNull()?.let { alert ->
                Text(
                    "⚠ " + alert.headline.ifBlank { alert.event },
                    color = palette.r2,
                    fontWeight = FontWeight.SemiBold,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            val snow24 = pass.snowNext24hCm?.let(::cmToInches)
            val snow72 = pass.snowNext72hCm?.let(::cmToInches)
            if (snow24 != null && snow72 != null) {
                if (snow72 < 0.2) {
                    StatRow("Snow next 3 days", "None expected", palette.accent)
                } else {
                    StatRow("Snow next 24h", fmtIn(snow24), palette.accent)
                    StatRow("Snow next 72h", fmtIn(snow72), palette.accent)
                }
            }
            pass.nextPeriod?.let { period ->
                StatRow(
                    period.name,
                    "${period.short} · ${period.temperatureF ?: "--"}°F · ${period.wind}",
                    MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun StatRow(label: String, value: String, valueColor: androidx.compose.ui.graphics.Color) {
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            label,
            style = MaterialTheme.typography.bodySmall,
            color = LocalPalette.current.subtleText,
        )
        Text(
            value,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold,
            color = valueColor,
        )
    }
}

fun fmtIn(value: Double): String {
    val rounded = (value * 10).toInt() / 10.0
    return if (rounded == rounded.toInt().toDouble()) "${rounded.toInt()}\"" else "$rounded\""
}


/** Destination-first labels: newcomers know places, veterans know routes. */
private val DESTINATIONS = linkedMapOf(
    "i80" to "North Lake",
    "us50" to "South Lake",
    "sr88" to "Kirkwood",
)

@Composable
private fun QuickAction(label: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    val palette = LocalPalette.current
    CcCard(modifier.clickable(onClick = onClick)) {
        Text(
            label,
            style = MaterialTheme.typography.titleSmall,
            color = palette.accent,
            modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
            textAlign = androidx.compose.ui.text.style.TextAlign.Center,
        )
    }
}
