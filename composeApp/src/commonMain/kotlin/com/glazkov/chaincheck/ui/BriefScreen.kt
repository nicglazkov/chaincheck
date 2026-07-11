package com.glazkov.chaincheck.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.glazkov.chaincheck.data.ChainCheckApi
import com.glazkov.chaincheck.data.Repository
import com.glazkov.chaincheck.data.TripBriefAnswer
import com.glazkov.chaincheck.data.TripBriefQuery
import kotlinx.coroutines.launch

private val BRIEF_CORRIDORS = listOf("i80", "us50", "sr88", "sr89", "sr267")

private enum class DrivetrainOption(val wire: String, val label: String) {
    TwoWheel("2wd", "2WD"),
    FourWheel("4wd_awd", "4WD/AWD"),
}

private enum class TiresOption(val wire: String, val label: String) {
    None("no_snow", "Regular tires"),
    DriveAxle("snow_drive_axle", "Snow tires (drive axle)"),
    AllFour("snow_all_four", "Snow tires (all four)"),
}

@Composable
fun BriefScreen(repository: Repository, modifier: Modifier = Modifier) {
    val home by repository.home.collectAsState()
    val api = remember { ChainCheckApi() }
    val scope = rememberCoroutineScope()

    var corridor by remember { mutableStateOf(repository.selectedCorridor) }
    var origin by remember { mutableStateOf("Sacramento") }
    var drivetrain by remember { mutableStateOf(DrivetrainOption.FourWheel) }
    var tires by remember { mutableStateOf(TiresOption.AllFour) }
    var towing by remember { mutableStateOf(false) }
    var heavy by remember { mutableStateOf(false) }
    var loading by remember { mutableStateOf(false) }
    var answer by remember { mutableStateOf<TripBriefAnswer?>(null) }
    var error by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        if (corridor !in BRIEF_CORRIDORS) corridor = "i80"
    }

    val scrollState = rememberScrollState()
    // The generated brief lands below the fold; bring it into view so the
    // user never wonders whether anything happened.
    LaunchedEffect(answer) {
        if (answer != null) scrollState.animateScrollTo(scrollState.maxValue)
    }

    Column(
        modifier.fillMaxSize().verticalScroll(scrollState).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Trip brief", style = MaterialTheme.typography.headlineSmall)
        Text(
            "Pick your route and car; get the drive summed up from live controls, " +
                "closures, and the pass forecast.",
            style = MaterialTheme.typography.bodyMedium,
        )

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            val byId = home.summary?.corridors?.associateBy { it.id } ?: emptyMap()
            BRIEF_CORRIDORS.mapNotNull { byId[it] }.take(3).forEach { c ->
                FilterChip(
                    selected = corridor == c.id,
                    onClick = { corridor = c.id },
                    label = { Text(c.route) },
                )
            }
        }

        OutlinedTextField(
            value = origin,
            onValueChange = { origin = it },
            label = { Text("Leaving from") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )

        Text("Your vehicle", style = MaterialTheme.typography.titleSmall)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            DrivetrainOption.entries.forEach { option ->
                FilterChip(
                    selected = drivetrain == option,
                    onClick = { drivetrain = option },
                    label = { Text(option.label) },
                )
            }
        }
        // Whole rows toggle, not just the checkbox squares: gloves, again.
        Column {
            TiresOption.entries.forEach { option ->
                Row(
                    Modifier.fillMaxWidth().clickable { tires = option },
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Checkbox(
                        checked = tires == option,
                        onCheckedChange = { tires = option },
                    )
                    Text(option.label)
                }
            }
        }
        Row(
            Modifier.fillMaxWidth().clickable { towing = !towing },
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Checkbox(checked = towing, onCheckedChange = { towing = it })
            Text("Towing a trailer")
        }
        Row(
            Modifier.fillMaxWidth().clickable { heavy = !heavy },
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Checkbox(checked = heavy, onCheckedChange = { heavy = it })
            Text("Over 6,000 lbs gross weight")
        }

        Button(
            onClick = {
                loading = true
                error = null
                scope.launch {
                    runCatching {
                        api.tripBrief(
                            TripBriefQuery(
                                corridorId = corridor,
                                origin = origin.ifBlank { "Sacramento" },
                                drivetrain = drivetrain.wire,
                                tires = tires.wire,
                                over6000Lbs = heavy,
                                towing = towing,
                            )
                        )
                    }
                        .onSuccess { answer = it }
                        .onFailure { error = it.message ?: "request failed" }
                    loading = false
                }
            },
            enabled = !loading,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(if (loading) "Working..." else "Get my brief") }

        if (loading) CircularProgressIndicator(Modifier.align(Alignment.CenterHorizontally))
        error?.let { Text(humanizeError(it), color = MaterialTheme.colorScheme.error) }

        answer?.let { brief ->
            CcCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(
                            brief.tierLabel,
                            style = MaterialTheme.typography.titleMedium,
                            color = TierColors.forTier(brief.tier),
                        )
                        Text(
                            if (brief.ai) "AI summary of live data" else "Live data",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    Text(brief.brief, style = MaterialTheme.typography.bodyMedium)
                    Text(
                        buildString {
                            append("As of ")
                            append(formatLocalTime(brief.asOf))
                            if (brief.stale) append(" (cached)")
                        },
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        brief.disclaimer,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}
