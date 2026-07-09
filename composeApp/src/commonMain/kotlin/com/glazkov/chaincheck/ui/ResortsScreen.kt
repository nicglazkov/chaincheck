package com.glazkov.chaincheck.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
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
import com.glazkov.chaincheck.data.Repository
import com.glazkov.chaincheck.data.ResortReport

private enum class ResortSort(val label: String) {
    Snow24h("24h snow"),
    Base("Base"),
    Lifts("Lifts open"),
}

@Composable
fun ResortsScreen(repository: Repository, modifier: Modifier = Modifier) {
    val state by repository.resorts.collectAsState()
    var sort by remember { mutableStateOf(ResortSort.Snow24h) }

    val sorted = when (sort) {
        ResortSort.Snow24h -> state.resorts.sortedByDescending { it.snow24hIn ?: -1.0 }
        ResortSort.Base -> state.resorts.sortedByDescending { it.baseDepthIn ?: -1.0 }
        ResortSort.Lifts -> state.resorts.sortedByDescending { it.liftsOpen ?: -1 }
    }

    Column(modifier.fillMaxSize().padding(horizontal = 16.dp)) {
        Text("Resorts", style = MaterialTheme.typography.headlineSmall)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            ResortSort.entries.forEach { option ->
                FilterChip(
                    selected = sort == option,
                    onClick = { sort = option },
                    label = { Text(option.label) },
                )
            }
        }
        if (state.error != null && state.resorts.isEmpty()) {
            Text("Couldn't load resorts: ${state.error}")
        }
        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.padding(top = 8.dp),
        ) {
            items(sorted, key = { it.id }) { resort -> ResortRow(resort) }
        }
    }
}

@Composable
private fun ResortRow(resort: ResortReport) {
    CcCard(Modifier.fillMaxWidth()) {
        Row(
            Modifier.fillMaxWidth().padding(14.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(resort.name, style = MaterialTheme.typography.titleMedium)
                val subtitle = when {
                    !resort.ok -> "report unavailable"
                    resort.stale -> "stale report"
                    else -> listOfNotNull(
                        resort.baseDepthIn?.let {
                            val max = resort.baseDepthMaxIn
                            if (max != null && max != it) {
                                "base ${it.toInt()}-${max.toInt()}\""
                            } else "base ${it.toInt()}\""
                        },
                        resort.seasonTotalIn?.let { "season ${it.toInt()}\"" },
                    ).joinToString(" - ").ifBlank { "no snow data" }
                }
                Text(
                    subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    resort.snow24hIn?.let { fmtIn(it) } ?: "--",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                )
                Text("24h", style = MaterialTheme.typography.bodySmall)
                val open = resort.liftsOpen
                val total = resort.liftsTotal
                if (open != null || total != null) {
                    Text(
                        "lifts ${open ?: "?"}/${total ?: "?"}",
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
        }
    }
}
