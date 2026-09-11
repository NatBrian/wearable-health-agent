package dev.wha.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val Scheme = lightColorScheme(
    primary = Accent,
    surface = Surface,
    onSurface = OnSurface,
    outline = Outline,
)

@Composable
fun WhaTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = Scheme,
        typography = WhaTypography,
        content = content,
    )
}
