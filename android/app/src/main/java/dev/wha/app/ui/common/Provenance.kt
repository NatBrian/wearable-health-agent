package dev.wha.app.ui.common

import androidx.compose.material3.AssistChip
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable

/** Which machine produced something: arithmetic, rule, model, or you. */
@Composable
fun Provenance(layer: String) {
    val word = when (layer) {
        "deterministic", "arithmetic" -> "arithmetic"
        "safety", "rule" -> "rule"
        "agentic", "model" -> "model"
        "user", "you" -> "you"
        else -> layer
    }
    AssistChip(onClick = {}, label = { Text(word) })
}
