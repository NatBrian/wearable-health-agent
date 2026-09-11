package dev.wha.app.ui.common

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable

/**
 * How much of the night the watch measured, and over what. Contact minutes come
 * from the data; the source tells whether sleep was recorded or a clock window stood in.
 */
@Composable
fun SignalQualityLine(coverageMinutes: Int, sleepSource: String, rung: String, usableNights: Int, wording: Map<String, String>) {
    val over = if (sleepSource == "sleep") {
        wording["metric.window_source.sleep"] ?: ""
    } else {
        wording["metric.window_source.clock"] ?: ""
    }
    val rungLine = Wording.rung(rung, wording)
    Text(
        "$coverageMinutes minutes measured. $over $rungLine From $usableNights nights.",
        style = MaterialTheme.typography.bodySmall,
    )
}
