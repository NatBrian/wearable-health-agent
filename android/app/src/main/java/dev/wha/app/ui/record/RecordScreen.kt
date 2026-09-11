package dev.wha.app.ui.record

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp
import dev.wha.app.core.PipelineStepView
import dev.wha.app.ui.common.ErrorCard
import dev.wha.app.ui.common.Provenance

@Composable
fun RecordScreen(vm: RecordViewModel, onOpenSettings: () -> Unit) {
    val state by vm.state.collectAsState()
    var tab by remember { mutableStateOf(0) }
    Column(
        Modifier
            .fillMaxSize()
            .padding(8.dp)
            .clickable(
                enabled = state.highlighted.isNotEmpty(),
                onClick = vm::clearHighlight,
            ),
    ) {
        TabRow(selectedTabIndex = tab) {
            Tab(selected = tab == 0, onClick = { tab = 0 }, text = { Text("This night") })
            Tab(selected = tab == 1, onClick = { tab = 1 }, text = { Text("How it works") })
        }
        if (tab == 1) {
            HowItWorksTab(
                wording = state.wording,
                config = state.config,
                toolNames = state.toolNames,
                safetyRows = state.safetyRows,
            )
            return@Column
        }
        if (state.highlighted.isNotEmpty()) {
            Text(
                "Highlighting where this came from and what read it; tap anywhere to clear.",
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(vertical = 4.dp),
            )
        }
        Row(Modifier.horizontalScroll(rememberScrollState())) {
            state.nights.forEach { night ->
                FilterChip(
                    selected = night.night_date == state.selected,
                    onClick = { vm.select(night.night_date) },
                    label = { Text("${night.night_date} ${levelWord(night.level)}") },
                    modifier = Modifier.padding(end = 4.dp),
                )
            }
        }
        val error = state.error
        if (error != null) {
            ErrorCard(error, onRetry = { state.selected?.let(vm::select) }, onOpenSettings = onOpenSettings)
            return@Column
        }
        val pipeline = state.pipeline
        if (pipeline != null) {
            val scope = rememberCoroutineScope()
            val replay = remember(pipeline.night_date, pipeline.steps.size) {
                Replay(pipeline.steps.size.coerceAtLeast(1), 1500L, scope)
            }
            val replayState by replay.state.collectAsState()
            ReplayControls(replay, pipeline.steps, state.wording["replay.pacing_note"] ?: "")
            // During replay the graph dims everything past the playhead; otherwise
            // the highlight set (Task 21 lineage taps) and the live pulse rule.
            val ordered = pipeline.steps.sortedBy { it.ordinal }
            val current = ordered.getOrNull(replayState.index)?.step_id
            val replayActive = replayState.playing || replayState.index > 0
            PipelineGraph(
                steps = pipeline.steps,
                wording = state.wording,
                highlighted = if (replayActive) {
                    ordered.filter { it.ordinal <= (ordered.getOrNull(replayState.index)?.ordinal ?: 0) }
                        .map { it.step_id }.toSet()
                } else {
                    state.highlighted
                },
                running = if (replayState.playing) current else state.running,
                onTap = vm::open,
                modifier = Modifier
                    .weight(1f)
                    .verticalScroll(rememberScrollState()),
            )
        }
    }
    state.sheet?.let { step ->
        StepSheet(
            step = step,
            wording = state.wording,
            localise = vm::localise,
            onTapOutput = { output -> vm.highlight(step.step_id, output) },
            onDismiss = vm::closeSheet,
        )
    }
}

private fun levelWord(level: String): String = when (level) {
    "GREEN" -> "usual"
    "YELLOW" -> "raised"
    "RED" -> "high"
    else -> "not measured"
}

/**
 * Every night as the same steps in the same groups. Cards rather than a drawn
 * canvas, so each node stays selectable and readable by accessibility services;
 * the frame (order, groups, branches) is what the spec pins, not the renderer.
 */
@Composable
fun PipelineGraph(
    steps: List<PipelineStepView>,
    wording: Map<String, String>,
    highlighted: Set<String>,
    running: String?,
    onTap: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val nodes = GraphLayout.build(steps)
    val byId = steps.associateBy { it.step_id }
    val pulse by rememberInfiniteTransition(label = "running").animateFloat(
        initialValue = 1f,
        targetValue = 0.55f,
        animationSpec = infiniteRepeatable(tween(800), RepeatMode.Reverse),
        label = "pulse",
    )
    Column(modifier) {
        var lastGroup: String? = null
        nodes.forEach { node ->
            if (node.group != lastGroup) {
                lastGroup = node.group
                Text(
                    "${node.group} · ${GraphLayout.machineWord(node.layer)}",
                    style = MaterialTheme.typography.titleSmall,
                    modifier = Modifier.padding(top = 12.dp, bottom = 4.dp),
                )
            }
            val step = byId[node.id]
            val dimmed = node.dimmed || (highlighted.isNotEmpty() && node.id !in highlighted)
            Box(Modifier.graphicsLayer(alpha = if (node.id == running) pulse else 1f)) {
                Card(
                    onClick = { onTap(node.id) },
                    enabled = step != null,
                    colors = if (dimmed) {
                        CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
                    } else {
                        CardDefaults.cardColors()
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(56.dp)
                        .padding(vertical = 2.dp),
                ) {
                    Row(Modifier.padding(horizontal = 12.dp, vertical = 6.dp)) {
                        Text("${node.ordinal}", style = MaterialTheme.typography.bodySmall)
                        Column(Modifier.weight(1f).padding(start = 8.dp)) {
                            Text(
                                (wording["step.${node.id}.what"] ?: node.id).substringBefore(". "),
                                style = MaterialTheme.typography.bodyMedium,
                                maxLines = 1,
                            )
                            step?.headline_figure?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
                        }
                        Provenance(GraphLayout.machineWord(node.layer))
                    }
                }
            }
            // The conditional branches the loop takes, as words under the node.
            if (node.id == "decide") {
                Text(
                    "Then: ask, conclude, or watch another night.",
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(start = 16.dp),
                )
            }
            if (node.id == "ask") {
                Text(
                    "An answer leads back to the investigation.",
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(start = 16.dp),
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StepSheet(
    step: PipelineStepView,
    wording: Map<String, String>,
    localise: (String, (String) -> Unit) -> Unit,
    onTapOutput: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    var whenText by remember(step.step_id) { mutableStateOf(step.occurred_utc ?: "") }
    val utc = step.occurred_utc
    LaunchedEffect(step.step_id) {
        if (utc != null) localise(utc) { whenText = it }
    }
    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(Modifier.padding(16.dp).verticalScroll(rememberScrollState())) {
            Text(wording["step.${step.step_id}.what"] ?: step.step_id, style = MaterialTheme.typography.titleMedium)
            if (step.reason.isNotBlank()) Text(step.reason, modifier = Modifier.padding(top = 4.dp))
            Text(
                wording["layer.${step.layer}"] ?: "",
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(top = 4.dp),
            )
            step.headline_figure?.let { Text(it, modifier = Modifier.padding(top = 4.dp)) }
            if (whenText.isNotBlank()) Text(whenText, style = MaterialTheme.typography.bodySmall)
            if (step.inputs.isNotEmpty()) {
                Text("Read", style = MaterialTheme.typography.titleSmall, modifier = Modifier.padding(top = 8.dp))
                step.inputs.forEach { (key, value) -> Text("$key: $value", style = MaterialTheme.typography.bodySmall) }
            }
            if (step.outputs.isNotEmpty()) {
                Text("Wrote", style = MaterialTheme.typography.titleSmall, modifier = Modifier.padding(top = 8.dp))
                step.outputs.forEach { (key, value) ->
                    TextButton(onClick = { onTapOutput(key) }) { Text("$key: $value") }
                }
            }
            if (step.sources.isNotEmpty()) {
                Text("Sources", style = MaterialTheme.typography.titleSmall, modifier = Modifier.padding(top = 8.dp))
                step.sources.forEach { citation ->
                    Text(citation.title.ifBlank { citation.source_id }, style = MaterialTheme.typography.bodySmall)
                }
            }
            var expanded by remember { mutableStateOf(false) }
            TextButton(onClick = { expanded = !expanded }) {
                Text(if (expanded) "Hide everything recorded" else "Everything recorded")
            }
            if (expanded) Text(step.detail_json.toString(), style = MaterialTheme.typography.bodySmall)
        }
    }
}
