package dev.wha.app.ui.today

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import dev.wha.app.corpus.CorpusState
import dev.wha.app.ui.common.ErrorCard
import dev.wha.app.ui.common.Provenance
import dev.wha.app.ui.common.SignalQualityLine
import dev.wha.app.ui.common.StatusWord

@Composable
fun TodayScreen(
    vm: TodayViewModel,
    onOpenSettings: () -> Unit,
    onOpenRecord: (String) -> Unit,
    onOpenInvestigation: (String) -> Unit,
) {
    val state by vm.state.collectAsState()
    var input by remember { mutableStateOf("") }
    LazyColumn(Modifier.fillMaxSize().padding(8.dp)) {
        item {
            LastNightCard(state, onOpenRecord)
            Spacer(Modifier.height(8.dp))
        }
        if (!state.providerConfigured) {
            item {
                Card(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                    Column(Modifier.padding(16.dp)) {
                        Text("No model provider is configured, so investigations cannot run and the assistant cannot reply. Readings are still watched.")
                        Button(onClick = onOpenSettings, modifier = Modifier.padding(top = 8.dp)) { Text("Open settings") }
                    }
                }
            }
        }
        when (val corpus = state.corpus) {
            is CorpusState.Fetching -> item {
                Card(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                    Text(
                        "General health information is not yet available to the assistant; downloading.",
                        modifier = Modifier.padding(16.dp),
                    )
                }
            }
            is CorpusState.Failed -> item {
                Card(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                    Column(Modifier.padding(16.dp)) {
                        Text("General health information could not be downloaded.")
                        TextButton(onClick = { vm.refresh() }) { Text("Try again") }
                    }
                }
            }
            else -> Unit
        }
        val urgency = state.urgency
        if (urgency != null && urgency.urgency != null && urgency.urgency != "none") {
            item {
                Card(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                    Column(Modifier.padding(16.dp)) {
                        Text(urgency.reason)
                        var ticked by remember { mutableStateOf(false) }
                        Row {
                            androidx.compose.material3.Checkbox(checked = ticked, onCheckedChange = { ticked = it })
                            Text("I have read this")
                        }
                        Button(onClick = vm::acknowledgeUrgency, enabled = ticked) { Text("Acknowledge") }
                    }
                }
            }
        }
        val pending = state.pending
        if (pending != null) {
            item {
                PendingCard(vm, state)
                Spacer(Modifier.height(8.dp))
            }
        } else if (state.quietReason != null) {
            item {
                Card(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                    Column(Modifier.padding(16.dp)) {
                        Text(state.quietReason!!)
                        if (state.quietFromDecide) Provenance("arithmetic")
                        state.lastNight?.let { night ->
                            TextButton(onClick = { onOpenRecord(night.date) }) { Text("See the steps") }
                        }
                    }
                }
            }
        }
        state.openEpisodeId?.let { episodeId ->
            item {
                Card(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                    Column(Modifier.padding(16.dp)) {
                        Text("Being looked into.")
                        TextButton(onClick = { onOpenInvestigation(episodeId) }) { Text("Open the investigation") }
                    }
                }
            }
        }
        items(state.thread) { turn ->
            Card(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                Column(Modifier.padding(12.dp)) {
                    Text(turn.text)
                    turn.citations.forEach { citation ->
                        Text(
                            citation.title.ifBlank { citation.source_id },
                            style = MaterialTheme.typography.bodySmall,
                            modifier = Modifier.padding(top = 4.dp),
                        )
                    }
                    if (turn.uncited.isNotEmpty()) {
                        Card(Modifier.padding(top = 4.dp)) {
                            Column(Modifier.padding(8.dp)) {
                                Text("Not from a cited source")
                                turn.uncited.forEach { Text(it, style = MaterialTheme.typography.bodySmall) }
                            }
                        }
                    }
                }
            }
        }
        item {
            Row(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                OutlinedTextField(
                    value = input,
                    onValueChange = { input = it },
                    label = { Text("Say something") },
                    modifier = Modifier.weight(1f),
                )
                Button(
                    onClick = { vm.say(input); input = "" },
                    enabled = input.isNotBlank(),
                    modifier = Modifier.padding(start = 8.dp),
                ) { Text("Send") }
            }
        }
        state.error?.let { err ->
            item { ErrorCard(err, onRetry = vm::refresh, onOpenSettings = onOpenSettings) }
        }
    }
}

@Composable
private fun LastNightCard(state: TodayUiState, onOpenRecord: (String) -> Unit) {
    val night = state.lastNight ?: return
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp)) {
            Text("Last night", style = MaterialTheme.typography.titleMedium)
            StatusWord(night.level)
            if (state.levelSentence.isNotBlank()) Text(state.levelSentence)
            SignalQualityLine(night.coverageMinutes, night.sleepSource, night.rung, night.usableNights, state.wording)
            state.lastPull?.let { Text("Last pull $it", style = MaterialTheme.typography.bodySmall) }
            TextButton(onClick = { onOpenRecord(night.date) }) { Text("See the steps") }
        }
    }
}

@Composable
private fun PendingCard(vm: TodayViewModel, state: TodayUiState) {
    val pending = state.pending ?: return
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp)) {
            when (pending.kind) {
                "question" -> {
                    val question = pending.question
                    Text(question?.text ?: "")
                    var freeText by remember { mutableStateOf("") }
                    OutlinedTextField(
                        value = freeText,
                        onValueChange = { freeText = it },
                        label = { Text("Anything to add") },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    (question?.options ?: emptyList()).forEach { option ->
                        FilledTonalButton(onClick = { vm.answer(option.option_id, freeText.ifBlank { null }, false) }) {
                            Text(option.label)
                        }
                    }
                    TextButton(onClick = { vm.answer(question?.options?.firstOrNull()?.option_id, null, true) }) {
                        Text("Not now")
                    }
                }
                "review" -> {
                    val draft = pending.draft_outcome
                    Text(draft?.observation ?: "")
                    var prose by remember { mutableStateOf(draft?.observation ?: "") }
                    var rationale by remember { mutableStateOf("") }
                    OutlinedTextField(value = prose, onValueChange = { prose = it }, label = { Text("Wording") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = rationale, onValueChange = { rationale = it }, label = { Text("Why") }, modifier = Modifier.fillMaxWidth())
                    Row {
                        Button(onClick = { vm.review("approve", prose.takeIf { it != draft?.observation }, rationale.ifBlank { null }) }) { Text("Looks right") }
                        TextButton(onClick = { vm.review("reject", null, rationale.ifBlank { "Rejected on review" }) }) { Text("Not right") }
                        TextButton(onClick = { vm.review("escalate", null, rationale.ifBlank { "Escalated on review" }) }) { Text("Needs a doctor") }
                    }
                }
                "measurement" -> {
                    // The spot-reading limb was removed, so nothing creates these any
                    // more; very old records may still hold one, shown as words only.
                    Text(pending.measurement?.instruction ?: "")
                }
            }
        }
    }
}
