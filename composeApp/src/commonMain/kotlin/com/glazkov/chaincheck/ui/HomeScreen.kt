package com.glazkov.chaincheck.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.glazkov.chaincheck.data.PassSummary
import com.glazkov.chaincheck.data.Repository

private fun cmToInches(cm: Double): Double = cm / 2.54

@Composable
fun HomeScreen(
    repository: Repository,
    onOpenRoute: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val state by repository.home.collectAsState()
    var selected by remember { mutableStateOf(repository.selectedCorridor) }

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

        // Route picker
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            summary.corridors.filter { it.id in setOf("i80", "us50", "sr88") }
                .forEach { corridor ->
                    FilterChip(
                        selected = selected == corridor.id,
                        onClick = {
                            selected = corridor.id
                            repository.selectedCorridor = corridor.id
                        },
                        label = { Text(corridor.route) },
                    )
                }
        }

        val corridor = summary.corridors.firstOrNull { it.id == selected }
            ?: summary.corridors.firstOrNull()
        if (corridor != null) {
            val color = TierColors.forTier(corridor.tier)
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(20.dp),
            ) {
                Column(
                    Modifier.fillMaxWidth().padding(20.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(corridor.name, style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(12.dp))
                    Column(
                        modifier = Modifier
                            .size(140.dp)
                            .background(color, RoundedCornerShape(70.dp)),
                        verticalArrangement = Arrangement.Center,
                        horizontalAlignment = Alignment.CenterHorizontally,
                    ) {
                        Text(
                            corridor.tierLabel,
                            color = Color.White,
                            fontSize = 44.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                    Spacer(Modifier.height(12.dp))
                    Text(
                        corridor.tierMeaning,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    if (corridor.closures > 0 || corridor.incidents > 0) {
                        Spacer(Modifier.height(8.dp))
                        Text(
                            "${corridor.closures} closures - ${corridor.incidents} incidents",
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                    TextButton(onClick = { onOpenRoute(corridor.id) }) {
                        Text("Route detail")
                    }
                }
            }

            summary.passes.firstOrNull { it.corridorId == corridor.id }?.let { pass ->
                StormCard(pass)
            }
        }

        FeedHealthLine(
            asOf = summary.feed.asOf,
            stale = summary.feed.stale || state.fromCache,
            error = state.error,
            onRefresh = { repository.refreshHome() },
        )
    }
}

@Composable
fun StormCard(pass: PassSummary) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(
                "${pass.name} - ${pass.elevationFt} ft",
                style = MaterialTheme.typography.titleSmall,
            )
            pass.alerts.firstOrNull()?.let { alert ->
                Text(
                    alert.headline.ifBlank { alert.event },
                    color = TierColors.r2,
                    fontWeight = FontWeight.SemiBold,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            val snow24 = pass.snowNext24hCm?.let(::cmToInches)
            val snow72 = pass.snowNext72hCm?.let(::cmToInches)
            if (snow24 != null && snow72 != null) {
                val text = if (snow72 < 0.2) {
                    "No snow expected in the next 3 days"
                } else {
                    "Forecast snow: ${fmtIn(snow24)} next 24h, ${fmtIn(snow72)} next 72h"
                }
                Text(text, style = MaterialTheme.typography.bodyMedium)
            }
            pass.nextPeriod?.let { period ->
                Text(
                    "${period.name}: ${period.short}, ${period.temperatureF ?: "--"} F, " +
                        "wind ${period.wind}",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }
}

fun fmtIn(value: Double): String {
    val rounded = (value * 10).toInt() / 10.0
    return if (rounded == rounded.toInt().toDouble()) "${rounded.toInt()}\"" else "$rounded\""
}

@Composable
fun FeedHealthLine(
    asOf: String?,
    stale: Boolean,
    error: String?,
    onRefresh: () -> Unit,
) {
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(
                buildString {
                    append("As of ")
                    append(asOf?.take(16)?.replace("T", " ") ?: "unknown")
                    if (stale) append(" (cached)")
                },
                style = MaterialTheme.typography.bodySmall,
                color = if (stale) TierColors.r2 else MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (error != null) {
                Text(
                    "Refresh failed: $error",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                )
            }
        }
        TextButton(onClick = onRefresh) { Text("Refresh") }
    }
}
