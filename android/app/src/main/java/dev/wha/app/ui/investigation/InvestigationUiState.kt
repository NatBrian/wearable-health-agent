package dev.wha.app.ui.investigation

import dev.wha.app.core.EpisodeDetail
import dev.wha.app.core.Handover
import dev.wha.app.core.WhaResult

data class CauseBar(val id: String, val label: String, val probability: Double)

data class InvestigationUiState(
    val detail: EpisodeDetail? = null,
    val narrative: List<String> = emptyList(),
    val causes: List<CauseBar> = emptyList(),
    val handover: Handover? = null,
    val wording: Map<String, String> = emptyMap(),
    val error: WhaResult.Err? = null,
)
