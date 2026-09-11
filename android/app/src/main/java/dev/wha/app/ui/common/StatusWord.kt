package dev.wha.app.ui.common

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

/** Colour plus icon plus word: status is never colour alone. */
@Composable
fun StatusWord(level: String, modifier: Modifier = Modifier) {
    val (word, color, icon) = when (level) {
        "GREEN" -> Triple("Usual", Color(0xFF0CA30C), Icons.Filled.Check)
        "YELLOW" -> Triple("Raised", Color(0xFFFAB219), Icons.Filled.Warning)
        "RED" -> Triple("High", Color(0xFFD03B3B), Icons.Filled.Warning)
        else -> Triple("Not measured", Color.Gray, Icons.Filled.Close)
    }
    Row(modifier = modifier, verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, contentDescription = null, tint = color)
        Text(word, color = color, style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(start = 4.dp))
    }
}
