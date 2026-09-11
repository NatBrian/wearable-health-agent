package dev.wha.app.ui.history

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import dev.wha.app.ui.common.ErrorCard

@Composable
fun HistoryScreen(vm: HistoryViewModel, onOpenRecord: (String) -> Unit, onOpenSettings: () -> Unit) {
    val state by vm.state.collectAsState()
    Column(Modifier.fillMaxSize().padding(8.dp)) {
        Row {
            Button(onClick = { vm.toggleTable(false) }, enabled = state.showTable) { Text("Chart") }
            TextButton(onClick = { vm.toggleTable(true) }, modifier = Modifier.padding(start = 8.dp)) { Text("Table") }
        }
        val error = state.error
        if (error != null) {
            ErrorCard(error, onRetry = vm::refresh, onOpenSettings = onOpenSettings)
            return@Column
        }
        if (!state.showTable) {
            NightChart(nights = state.nights.reversed(), onOpenRecord = onOpenRecord)
        } else {
            val scroll = rememberScrollState()
            LazyColumn(Modifier.horizontalScroll(scroll)) {
                items(state.nights) { night ->
                    val episode = state.episodes[night.episode_id]
                    Column(Modifier.padding(vertical = 6.dp)) {
                        Text(night.night_date, style = MaterialTheme.typography.titleSmall)
                        Text(
                            listOf(
                                "Conclusion: ${levelWord(night.level)}",
                                "Reading: ${night.rhr_bpm?.toString() ?: "not measured"}",
                                "Against your normal: ${night.deviation_bpm?.toString() ?: "not measured"}",
                                "Sleep measured: ${night.coverage_minutes} minutes",
                                "Looked into: ${episode?.let { "${it.state} ${it.disposition ?: ""}".trim() } ?: "no"}",
                            ).joinToString(" · "),
                            style = MaterialTheme.typography.bodySmall,
                        )
                        TextButton(onClick = { onOpenRecord(night.night_date) }) { Text("Open in the record") }
                    }
                }
            }
        }
    }
}
