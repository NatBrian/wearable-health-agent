package dev.wha.app.ui.record

import dev.wha.app.core.LineageEdge
import dev.wha.app.core.NightPipeline
import dev.wha.app.core.PipelineNightRef
import dev.wha.app.core.PipelineStepView
import dev.wha.app.core.WhaResult
import kotlinx.serialization.json.JsonElement

data class RecordUiState(
    val nights: List<PipelineNightRef> = emptyList(),
    val selected: String? = null,
    val pipeline: NightPipeline? = null,
    val lineage: List<LineageEdge> = emptyList(),
    val highlighted: Set<String> = emptySet(),
    val running: String? = null,
    val sheet: PipelineStepView? = null,
    val wording: Map<String, String> = emptyMap(),
    val config: Map<String, JsonElement> = emptyMap(),
    val toolNames: List<String> = emptyList(),
    val safetyRows: List<Map<String, String>> = emptyList(),
    val error: WhaResult.Err? = null,
)
