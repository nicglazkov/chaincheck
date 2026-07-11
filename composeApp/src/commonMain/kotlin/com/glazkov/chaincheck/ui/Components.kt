package com.glazkov.chaincheck.ui

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.datetime.Clock
import kotlinx.datetime.Instant
import kotlinx.datetime.TimeZone
import kotlinx.datetime.toLocalDateTime

/** The one card. Glass on Summit, bordered white with soft lift on Sierra. */
@Composable
fun CcCard(
    modifier: Modifier = Modifier,
    content: @Composable ColumnScope.() -> Unit,
) {
    val palette = LocalPalette.current
    Surface(
        modifier = modifier,
        shape = MaterialTheme.shapes.medium,
        color = palette.cardSurface,
        contentColor = MaterialTheme.colorScheme.onSurface,
        shadowElevation = if (palette.isDark) 0.dp else 1.dp,
        border = androidx.compose.foundation.BorderStroke(1.dp, palette.cardBorder),
    ) {
        Column(Modifier.padding(16.dp), content = content)
    }
}

/** The tier answer: ring badge with tinted core and (on Summit) a soft halo. */
@Composable
fun TierRing(tier: Int, label: String, modifier: Modifier = Modifier) {
    val palette = LocalPalette.current
    val color = TierColors.forTier(tier, palette)
    Box(modifier = modifier.size(148.dp), contentAlignment = Alignment.Center) {
        if (palette.isDark) {
            Box(
                Modifier
                    .size(148.dp)
                    .background(
                        Brush.radialGradient(
                            listOf(color.copy(alpha = 0.30f), Color.Transparent)
                        ),
                        CircleShape,
                    )
            )
        }
        Box(
            Modifier
                .size(124.dp)
                .background(
                    Brush.radialGradient(
                        listOf(
                            color.copy(alpha = if (palette.isDark) 0.16f else 0.10f),
                            color.copy(alpha = if (palette.isDark) 0.05f else 0.04f),
                        )
                    ),
                    CircleShape,
                )
                .border(5.dp, color, CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    label,
                    color = color,
                    fontSize = 40.sp,
                    fontWeight = FontWeight.ExtraBold,
                    letterSpacing = (-1).sp,
                )
                Text(
                    tierCaption(tier),
                    color = color.copy(alpha = 0.85f),
                    fontSize = 9.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.2.sp,
                )
            }
        }
    }
}

private fun tierCaption(tier: Int): String = when (tier) {
    0 -> "NO CONTROLS"
    1 -> "CHAINS OR SNOW TIRES"
    2 -> "CHAINS REQUIRED"
    3 -> "CHAINS - ALL VEHICLES"
    4 -> "ROAD CLOSED"
    else -> "STATUS UNKNOWN"
}

/**
 * Freshness line with a live pulse: "Updated 2 min ago" beats a timestamp,
 * and data age is this product's credibility.
 */
@Composable
fun FreshnessLine(
    asOfIso: String?,
    stale: Boolean,
    error: String?,
    onRefresh: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val palette = LocalPalette.current
    Row(
        modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
            if (!stale && error == null) {
                val pulse = rememberInfiniteTransition(label = "pulse")
                val alpha by pulse.animateFloat(
                    initialValue = 1f,
                    targetValue = 0.25f,
                    animationSpec = infiniteRepeatable(
                        tween(1100, easing = LinearEasing), RepeatMode.Reverse
                    ),
                    label = "pulseAlpha",
                )
                Box(
                    Modifier
                        .size(8.dp)
                        .background(palette.livePulse.copy(alpha = alpha), CircleShape)
                )
            } else {
                Box(Modifier.size(8.dp).background(palette.r2, CircleShape))
            }
            Column(Modifier.padding(start = 8.dp)) {
                Text(
                    freshnessText(asOfIso, stale),
                    style = MaterialTheme.typography.bodySmall,
                    color = if (stale) palette.r2 else palette.subtleText,
                )
                if (error != null) {
                    Text(
                        humanizeError(error),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                }
            }
        }
        TextButton(onClick = onRefresh) { Text("Refresh") }
    }
}

internal fun freshnessText(asOfIso: String?, stale: Boolean): String {
    val suffix = if (stale) " · cached" else " · live"
    val instant = asOfIso?.let { runCatching { Instant.parse(it) }.getOrNull() }
        ?: return "Updated: unknown"
    val minutes = (Clock.System.now() - instant).inWholeMinutes
    val age = when {
        minutes < 1 -> "just now"
        minutes < 60 -> "$minutes min ago"
        minutes < 48 * 60 -> "${minutes / 60} h ago"
        else -> "${minutes / (24 * 60)} d ago"
    }
    return "Updated $age$suffix"
}

/** "1 closure", "7 closures" - counts read as words, not database fields. */
internal fun countLabel(count: Int, singular: String): String =
    if (count == 1) "1 $singular" else "$count ${singular}s"

/**
 * Raw transport exceptions ("Unable to resolve host chaincheck-api...") are
 * for logs, not people. Everything the UI shows about a failed refresh goes
 * through here.
 */
internal fun humanizeError(raw: String?): String {
    val lowered = raw?.lowercase() ?: return "Couldn't refresh right now."
    return when {
        "unable to resolve host" in lowered ||
            "no address" in lowered ||
            "network is unreachable" in lowered ||
            "failed to connect" in lowered ||
            "connection refused" in lowered ->
            "You're offline - showing the last saved update."
        "timeout" in lowered || "timed out" in lowered ->
            "The connection timed out - will keep trying."
        else -> "Couldn't refresh right now - will keep trying."
    }
}

private val MONTHS =
    listOf("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

/** ISO instant -> "Jul 10, 5:11 PM" in the device's own time zone. */
internal fun formatLocalTime(iso: String?): String {
    val instant = iso?.let { runCatching { Instant.parse(it) }.getOrNull() }
        ?: return "unknown"
    val local = instant.toLocalDateTime(TimeZone.currentSystemDefault())
    val hour12 = when (val h = local.hour % 12) {
        0 -> 12
        else -> h
    }
    val ampm = if (local.hour < 12) "AM" else "PM"
    val minute = local.minute.toString().padStart(2, '0')
    return "${MONTHS[local.monthNumber - 1]} ${local.dayOfMonth}, $hour12:$minute $ampm"
}
