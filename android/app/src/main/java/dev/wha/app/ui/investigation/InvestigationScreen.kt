package dev.wha.app.ui.investigation

import android.content.Intent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.Button
import androidx.compose.material3.Card
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import dev.wha.app.ui.common.ErrorCard
import dev.wha.app.ui.common.Provenance

@Composable
fun InvestigationScreen(vm: InvestigationViewModel, onOpenSettings: () -> Unit) {
    val state by vm.state.collectAsState()
    val context = LocalContext.current
    val error = state.error
    if (error != null) {
        ErrorCard(error, onRetry = vm::load, onOpenSettings = onOpenSettings)
        return
    }
    val detail = state.detail ?: return
    val outcome = detail.outcome
    LazyColumn(Modifier.fillMaxSize().padding(8.dp)) {
        item {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text("What it concluded", style = MaterialTheme.typography.titleMedium)
                    if (outcome != null) {
                        Text(outcome.observation)
                        Text(
                            state.wording["disposition.${outcome.disposition}"]
                                ?: outcome.disposition.replace("_", " ").lowercase(),
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        if (outcome.escalation_criteria.isNotEmpty()) {
                            outcome.escalation_criteria.forEach { Text(it) }
                        }
                        Text("Settled on ${detail.summary.closed_on ?: detail.summary.opened_on}.")
                    } else if (detail.summary.state == "AWAITING_HUMAN_REVIEW") {
                        Text("Waiting for you to check it.")
                        ReviewButtons(vm)
                    } else {
                        Text("Still being looked into.")
                    }
                }
            }
        }
        item {
            Card(Modifier.fillMaxWidth().padding(top = 8.dp)) {
                Column(Modifier.padding(16.dp)) {
                    Text("Why", style = MaterialTheme.typography.titleMedium)
                    state.narrative.forEach { Text(it, modifier = Modifier.padding(top = 4.dp)) }
                    BeliefBars(state.causes)
                }
            }
        }
        item {
            var expanded by remember { mutableStateOf(false) }
            TextButton(onClick = { expanded = !expanded }) {
                Text(if (expanded) "Hide the full trace" else "The full trace")
            }
            if (expanded) {
                detail.stages.forEach { stage ->
                    Text("${stage.name}: ${stage.reason}", style = MaterialTheme.typography.bodySmall)
                }
                detail.interactions.forEach { interaction ->
                    Text(
                        "Asked ${interaction.probe_id}: value ${interaction.evsi}, cost ${interaction.interruption_cost}.",
                        style = MaterialTheme.typography.bodySmall,
                    )
                    if (interaction.rejected.isNotEmpty()) {
                        Text(
                            "Not asked: ${interaction.rejected.joinToString()}",
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                }
                Text(
                    state.wording["policy.evsi_explained"] ?: "",
                    style = MaterialTheme.typography.bodySmall,
                )
                detail.measurements.forEach { measurement ->
                    Text(
                        "${measurement.kind}: ${measurement.value ?: "not measured"}",
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                detail.citations.forEach { citation ->
                    Text(
                        citation.title.ifBlank { citation.source_id },
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                if (detail.stripped_claims.isNotEmpty()) {
                    Text(
                        "Sentences removed because no source supported them",
                        style = MaterialTheme.typography.titleSmall,
                        modifier = Modifier.padding(top = 8.dp),
                    )
                    detail.stripped_claims.forEach {
                        Text(it, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
        item {
            Row(Modifier.padding(top = 8.dp)) {
                Button(onClick = {
                    vm.loadHandover()
                }) { Text("Summary for your doctor") }
            }
            state.handover?.let { handover ->
                Text(handover.text, modifier = Modifier.padding(top = 4.dp))
                Button(onClick = {
                    context.startActivity(
                        Intent(Intent.ACTION_SEND).apply {
                            type = "text/plain"
                            putExtra(Intent.EXTRA_TEXT, handover.text)
                        }.let { Intent.createChooser(it, null) },
                    )
                }) { Text("Share") }
            }
        }
    }
}

@Composable
private fun ReviewButtons(vm: InvestigationViewModel) {
    var prose by remember { mutableStateOf("") }
    var rationale by remember { mutableStateOf("") }
    OutlinedTextField(value = prose, onValueChange = { prose = it }, label = { Text("Wording") }, modifier = Modifier.fillMaxWidth())
    OutlinedTextField(value = rationale, onValueChange = { rationale = it }, label = { Text("Why") }, modifier = Modifier.fillMaxWidth())
    Row {
        Button(onClick = { vm.review("approve", prose.ifBlank { null }, rationale.ifBlank { null }) }) { Text("Looks right") }
        TextButton(onClick = { vm.review("reject", null, rationale.ifBlank { "Rejected on review" }) }) { Text("Not right") }
        TextButton(onClick = { vm.review("escalate", null, rationale.ifBlank { "Escalated on review" }) }) { Text("Needs a doctor") }
    }
    Provenance("you")
}
