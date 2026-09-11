package dev.wha.app.ui.today

import dev.wha.app.core.Citation
import dev.wha.app.core.PendingInteraction
import dev.wha.app.core.Urgency
import dev.wha.app.core.WhaResult
import dev.wha.app.corpus.CorpusState

data class LastNight(
    val date: String,
    val level: String,
    val coverageMinutes: Int,
    val sleepSource: String,
    val rung: String,
    val usableNights: Int,
    val episodeId: String?,
)

data class ThreadTurn(
    val role: String,
    val text: String,
    val citations: List<Citation> = emptyList(),
    val uncited: List<String> = emptyList(),
)

data class TodayUiState(
    val lastNight: LastNight? = null,
    val levelSentence: String = "",
    val quietReason: String? = null,
    val quietFromDecide: Boolean = false,
    val pending: PendingInteraction? = null,
    val urgency: Urgency? = null,
    val providerConfigured: Boolean = true,
    val corpus: CorpusState = CorpusState.Missing,
    val thread: List<ThreadTurn> = emptyList(),
    val error: WhaResult.Err? = null,
    val wording: Map<String, String> = emptyMap(),
    val openEpisodeId: String? = null,
    val lastPull: String? = null,
)
