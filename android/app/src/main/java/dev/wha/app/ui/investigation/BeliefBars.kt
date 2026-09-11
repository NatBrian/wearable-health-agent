package dev.wha.app.ui.investigation

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

/**
 * The twelve causes from the latest belief, sorted, in words. The top bar in
 * the accent, the rest muted; direct label on the top bar only, table toggle
 * for the rest. Probabilities come from the data.
 */
@Composable
fun BeliefBars(causes: List<CauseBar>) {
    var table by remember { mutableStateOf(false) }
    val accent = MaterialTheme.colorScheme.primary
    val muted = Color.Gray
    Column(Modifier.fillMaxWidth()) {
        if (!table) {
            causes.forEachIndexed { i, cause ->
                Column(Modifier.padding(vertical = 1.dp)) {
                    Text(
                        if (i == 0) "${cause.label} ${cause.probability}" else cause.label,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    Box(
                        Modifier
                            .fillMaxWidth(fraction = cause.probability.toFloat().coerceIn(0f, 1f))
                            .height(12.dp)
                            .background(if (i == 0) accent else muted),
                    )
                }
            }
        } else {
            causes.forEach { cause ->
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(cause.label, modifier = Modifier.weight(1f))
                    Text("${cause.probability}")
                }
            }
        }
        TextButton(onClick = { table = !table }) {
            Text(if (table) "Show as bars" else "Show as table")
        }
    }
}
