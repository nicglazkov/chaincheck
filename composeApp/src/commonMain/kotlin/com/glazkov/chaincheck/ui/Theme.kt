package com.glazkov.chaincheck.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Tier colors follow ski-report conventions: green fine, amber caution,
// red chains, deep red closed.
object TierColors {
    val r0 = Color(0xFF2E7D32)
    val r1 = Color(0xFFF9A825)
    val r2 = Color(0xFFEF6C00)
    val r3 = Color(0xFFC62828)
    val closed = Color(0xFF8E0000)
    val unknown = Color(0xFF757575)

    fun forTier(tier: Int): Color = when (tier) {
        0 -> r0
        1 -> r1
        2 -> r2
        3 -> r3
        4 -> closed
        else -> unknown
    }
}

private val lightScheme = lightColorScheme(
    primary = Color(0xFF1565C0),
    secondary = Color(0xFF455A64),
    tertiary = Color(0xFF00838F),
)

private val darkScheme = darkColorScheme(
    primary = Color(0xFF90CAF9),
    secondary = Color(0xFFB0BEC5),
    tertiary = Color(0xFF80DEEA),
)

@Composable
fun ChainCheckTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) darkScheme else lightScheme,
        content = content,
    )
}
