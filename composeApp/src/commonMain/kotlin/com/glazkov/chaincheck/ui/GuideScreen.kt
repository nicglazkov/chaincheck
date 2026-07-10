package com.glazkov.chaincheck.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.glazkov.chaincheck.data.ChainCheckApi
import com.glazkov.chaincheck.data.RulesQuery

private data class TierInfo(val tier: Int, val label: String, val name: String, val meaning: String)

private val TIERS = listOf(
    TierInfo(0, "R0", "No controls", "The road is open with no chain requirement. Normal winter caution still applies."),
    TierInfo(1, "R1", "Requirement 1", "Chains, traction devices, or snow tires are required. Passenger vehicles under 6,000 lbs with snow tires on the drive wheels are exempt from installing - but must carry chains."),
    TierInfo(2, "R2", "Requirement 2", "Chains or traction devices required on all vehicles except 4WD/AWD with snow-tread tires on all four wheels (who must still carry chains)."),
    TierInfo(3, "R3", "Requirement 3", "Chains on every vehicle. No exceptions. Highways usually close before R3 is posted."),
    TierInfo(4, "Closed", "Road closed", "The highway is shut. Nobody drives it until Caltrans reopens it."),
)

@Composable
fun GuideScreen(onBack: () -> Unit, modifier: Modifier = Modifier) {
    val palette = LocalPalette.current
    val api = remember { ChainCheckApi() }

    var selectedTier by remember { mutableStateOf(TIERS[2]) }
    var awd by remember { mutableStateOf(true) }
    var snowTires by remember { mutableStateOf(true) }
    var towing by remember { mutableStateOf(false) }
    var heavy by remember { mutableStateOf(false) }
    var ruling by remember { mutableStateOf<String?>(null) }
    var loadingRuling by remember { mutableStateOf(false) }

    LaunchedEffect(selectedTier, awd, snowTires, towing, heavy) {
        loadingRuling = true
        ruling = runCatching {
            api.evaluateRules(
                RulesQuery(
                    tier = selectedTier.tier,
                    drivetrain = if (awd) "4wd_awd" else "2wd",
                    tires = if (snowTires) {
                        if (awd) "snow_all_four" else "snow_drive_axle"
                    } else "no_snow",
                    over6000Lbs = heavy,
                    towing = towing,
                )
            ).reason
        }.getOrNull()
        loadingRuling = false
    }

    Column(
        modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
            }
            Text("How chain controls work", style = MaterialTheme.typography.headlineSmall)
        }

        Text(
            "When Sierra storms hit, Caltrans and CHP post \"chain controls\" on the " +
                "highways to Tahoe: checkpoints where your car must have chains or " +
                "qualifying tires to continue. ChainCheck watches those controls, the " +
                "weather, and the resorts - and pushes you an alert the moment your " +
                "route changes.",
            style = MaterialTheme.typography.bodyMedium,
        )

        // ---- Interactive tier explorer ----
        CcCard(Modifier.fillMaxWidth()) {
            Text("Try it: pick a control level", style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                TIERS.forEach { info ->
                    val color = TierColors.forTier(info.tier)
                    FilterChip(
                        selected = selectedTier.tier == info.tier,
                        onClick = { selectedTier = info },
                        label = {
                            Text(info.label, fontWeight = FontWeight.Bold)
                        },
                        shape = MaterialTheme.shapes.extraLarge,
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = color,
                            selectedLabelColor = Color.White,
                            labelColor = color,
                        ),
                    )
                }
            }
            Spacer(Modifier.height(12.dp))
            Column(
                Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                TierRing(tier = selectedTier.tier, label = selectedTier.label)
                Spacer(Modifier.height(8.dp))
                Text(
                    selectedTier.name,
                    style = MaterialTheme.typography.titleMedium,
                    color = TierColors.forTier(selectedTier.tier),
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    selectedTier.meaning,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }

        // ---- Your car, live against the real rules engine ----
        CcCard(Modifier.fillMaxWidth()) {
            Text("...and describe your car", style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.height(6.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(
                    selected = !awd, onClick = { awd = false },
                    label = { Text("2WD") }, shape = MaterialTheme.shapes.extraLarge,
                )
                FilterChip(
                    selected = awd, onClick = { awd = true },
                    label = { Text("4WD / AWD") }, shape = MaterialTheme.shapes.extraLarge,
                )
            }
            GuideCheck("Snow-rated (M+S) tires", snowTires) { snowTires = it }
            GuideCheck("Towing a trailer", towing) { towing = it }
            GuideCheck("Over 6,000 lbs", heavy) { heavy = it }
            Spacer(Modifier.height(8.dp))
            Box(
                Modifier
                    .fillMaxWidth()
                    .background(
                        TierColors.forTier(selectedTier.tier).copy(alpha = 0.10f),
                        RoundedCornerShape(12.dp),
                    )
                    .padding(12.dp)
            ) {
                when {
                    loadingRuling && ruling == null -> CircularProgressIndicator(
                        Modifier.size(18.dp).align(Alignment.Center)
                    )
                    ruling != null -> Text(
                        ruling!!,
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.SemiBold,
                    )
                    else -> Text(
                        "Couldn't reach the rules service - check your connection.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                }
            }
            Spacer(Modifier.height(4.dp))
            Text(
                "These rules come from Caltrans' published requirements and are " +
                    "checked by tests, not written by AI.",
                style = MaterialTheme.typography.bodySmall,
                color = palette.subtleText,
            )
        }

        // ---- Map legend ----
        CcCard(Modifier.fillMaxWidth()) {
            Text("Reading the map", style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.height(8.dp))
            LegendRow(palette.r0, "Route line - colored by its current control level")
            LegendRow(Color(0xFF4DA8C7), "Live Caltrans camera - tap for the actual view right now")
            LegendRow(Color(0xFFE8930A), "Closure - lane or full road work/blockage")
            LegendRow(Color(0xFFE03131), "CHP incident - crash, spinout, hazard")
            LegendRowText("R2", TierColors.forTier(2), "Active chain checkpoint (only shown when controls are up)")
            LegendRowText("❄", MaterialTheme.colorScheme.onSurface, "Ski resort - snow totals and lifts")
            LegendRowText("▲", palette.subtleText, "Mountain pass and its elevation")
        }

        // ---- Freshness + trust ----
        CcCard(Modifier.fillMaxWidth()) {
            Text("Why you can trust it", style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.height(6.dp))
            Text(
                "Every number comes from official public sources: Caltrans district " +
                    "feeds, CHP dispatch, the National Weather Service, and the resorts " +
                    "themselves. The green pulse means data is live; if we're showing " +
                    "anything cached, it says so with a timestamp. ChainCheck never " +
                    "guesses a road state, and it will never tell you conditions are " +
                    "safe - that call is always yours. Verify before you drive: dial 511 " +
                    "or check quickmap.dot.ca.gov.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Spacer(Modifier.height(8.dp))
    }
}

@Composable
private fun GuideCheck(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Checkbox(checked = checked, onCheckedChange = onChange)
        Text(label, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun LegendRow(color: Color, text: String) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.padding(vertical = 4.dp),
    ) {
        Box(Modifier.size(14.dp).background(color, CircleShape))
        Spacer(Modifier.width(10.dp))
        Text(text, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun LegendRowText(symbol: String, color: Color, text: String) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.padding(vertical = 4.dp),
    ) {
        Box(Modifier.width(14.dp), contentAlignment = Alignment.Center) {
            Text(symbol, color = color, fontWeight = FontWeight.Bold)
        }
        Spacer(Modifier.width(10.dp))
        Text(text, style = MaterialTheme.typography.bodySmall)
    }
}
