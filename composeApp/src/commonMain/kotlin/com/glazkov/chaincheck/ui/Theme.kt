package com.glazkov.chaincheck.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * ChainCheck design system: "Sierra Light" by day, "Summit" by night.
 * One shape language (18dp cards, pill chips, ring badge); dark adds the
 * night gradient and glow, light trades them for crisp borders and soft
 * elevation.
 */

data class ChainCheckPalette(
    val isDark: Boolean,
    val r0: Color,
    val r1: Color,
    val r2: Color,
    val r3: Color,
    val closed: Color,
    val unknown: Color,
    val accent: Color,
    val cardBorder: Color,
    val cardSurface: Color,
    val subtleText: Color,
    val livePulse: Color,
    val backgroundBrush: Brush,
)

private val Summit = ChainCheckPalette(
    isDark = true,
    r0 = Color(0xFF4ADE80),
    r1 = Color(0xFFFFD43B),
    r2 = Color(0xFFFF922B),
    r3 = Color(0xFFFF6B6B),
    closed = Color(0xFFE64980),
    unknown = Color(0xFF8FA2BD),
    accent = Color(0xFF7FD4FF),
    cardBorder = Color(0x17FFFFFF),
    cardSurface = Color(0x0EFFFFFF),
    subtleText = Color(0xFF8FA2BD),
    livePulse = Color(0xFF38D39F),
    backgroundBrush = Brush.verticalGradient(
        listOf(Color(0xFF0E1726), Color(0xFF101D33), Color(0xFF0D1422))
    ),
)

private val SierraLight = ChainCheckPalette(
    isDark = false,
    r0 = Color(0xFF1B7F37),
    r1 = Color(0xFFB08900),
    r2 = Color(0xFFE8710A),
    r3 = Color(0xFFD6336C),
    closed = Color(0xFF9C1F5F),
    unknown = Color(0xFF6B7A90),
    accent = Color(0xFF0B63CE),
    cardBorder = Color(0xFFE6EAF0),
    cardSurface = Color(0xFFFFFFFF),
    subtleText = Color(0xFF8494A9),
    livePulse = Color(0xFF15A46B),
    backgroundBrush = Brush.verticalGradient(
        listOf(Color(0xFFFAFBFC), Color(0xFFFAFBFC))
    ),
)

val LocalPalette = staticCompositionLocalOf { SierraLight }

/** Stable accessor the screens use; resolves against the active palette. */
object TierColors {
    val palette: ChainCheckPalette
        @Composable get() = LocalPalette.current

    @Composable
    fun forTier(tier: Int): Color = forTier(tier, LocalPalette.current)

    fun forTier(tier: Int, palette: ChainCheckPalette): Color = with(palette) {
        when (tier) {
            0 -> r0
            1 -> r1
            2 -> r2
            3 -> r3
            4 -> closed
            else -> unknown
        }
    }

    val r2: Color @Composable get() = LocalPalette.current.r2
}

private fun sierraLightScheme() = lightColorScheme(
    primary = Color(0xFF0B63CE),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFDCEAFB),
    onPrimaryContainer = Color(0xFF083A78),
    secondary = Color(0xFF45536B),
    background = Color(0xFFFAFBFC),
    onBackground = Color(0xFF16202B),
    surface = Color(0xFFFFFFFF),
    onSurface = Color(0xFF16202B),
    surfaceVariant = Color(0xFFF0F3F7),
    onSurfaceVariant = Color(0xFF45536B),
    surfaceContainer = Color(0xFFFFFFFF),
    surfaceContainerHigh = Color(0xFFF4F6F9),
    outline = Color(0xFFDDE3EA),
    outlineVariant = Color(0xFFE6EAF0),
    error = Color(0xFFC92A2A),
)

private fun summitScheme() = darkColorScheme(
    primary = Color(0xFF7FD4FF),
    onPrimary = Color(0xFF06263C),
    primaryContainer = Color(0xFF12395C),
    onPrimaryContainer = Color(0xFFCBE9FF),
    secondary = Color(0xFFC9D6EA),
    background = Color(0xFF0E1726),
    onBackground = Color(0xFFEEF3FB),
    surface = Color(0xFF142034),
    onSurface = Color(0xFFEEF3FB),
    surfaceVariant = Color(0xFF1B2A42),
    onSurfaceVariant = Color(0xFFCFDAEB),
    surfaceContainer = Color(0xFF15223A),
    surfaceContainerHigh = Color(0xFF1B2A45),
    outline = Color(0xFF2C3D58),
    outlineVariant = Color(0xFF22314B),
    error = Color(0xFFFF8787),
)

private val chainCheckShapes = Shapes(
    extraSmall = RoundedCornerShape(8.dp),
    small = RoundedCornerShape(12.dp),
    medium = RoundedCornerShape(18.dp),
    large = RoundedCornerShape(24.dp),
    extraLarge = RoundedCornerShape(32.dp),
)

@Composable
private fun chainCheckTypography(): Typography {
    val base = Typography()
    return base.copy(
        headlineMedium = base.headlineMedium.copy(
            fontWeight = FontWeight.ExtraBold,
            letterSpacing = (-0.5).sp,
        ),
        headlineSmall = base.headlineSmall.copy(
            fontWeight = FontWeight.Bold,
            letterSpacing = (-0.25).sp,
        ),
        titleMedium = base.titleMedium.copy(fontWeight = FontWeight.Bold),
        titleSmall = base.titleSmall.copy(fontWeight = FontWeight.Bold),
    )
}

@Composable
fun ChainCheckTheme(content: @Composable () -> Unit) {
    val dark = isSystemInDarkTheme()
    val palette = if (dark) Summit else SierraLight
    CompositionLocalProvider(LocalPalette provides palette) {
        MaterialTheme(
            colorScheme = if (dark) summitScheme() else sierraLightScheme(),
            shapes = chainCheckShapes,
            typography = chainCheckTypography(),
            content = content,
        )
    }
}
