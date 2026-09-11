package dev.wha.app.ui.record

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.FirstPage
import androidx.compose.material.icons.filled.LastPage
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.SkipNext
import androidx.compose.material.icons.filled.SkipPrevious
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import dev.wha.app.core.PipelineStepView

@Composable
fun ReplayControls(replay: Replay, steps: List<PipelineStepView>, pacingNote: String) {
    val state by replay.state.collectAsState()
    Column(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Row {
            IconButton(onClick = { replay.seek(0) }) { Icon(Icons.Filled.FirstPage, contentDescription = "First step") }
            IconButton(onClick = replay::previous) { Icon(Icons.Filled.SkipPrevious, contentDescription = "Previous step") }
            if (state.playing) {
                IconButton(onClick = replay::pause) { Icon(Icons.Filled.Pause, contentDescription = "Pause") }
            } else {
                IconButton(onClick = replay::play) { Icon(Icons.Filled.PlayArrow, contentDescription = "Play") }
            }
            IconButton(onClick = replay::next) { Icon(Icons.Filled.SkipNext, contentDescription = "Next step") }
            IconButton(onClick = { replay.seek(steps.size - 1) }) { Icon(Icons.Filled.LastPage, contentDescription = "Last step") }
        }
        steps.getOrNull(state.index)?.let { step ->
            Text(step.reason, style = MaterialTheme.typography.bodySmall)
        }
        Text(pacingNote, style = MaterialTheme.typography.bodySmall)
    }
}
