package dev.wha.app.ui.investigation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dev.wha.app.core.ErrorKind
import dev.wha.app.core.WhaCore
import dev.wha.app.core.WhaResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.double
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

class InvestigationViewModel(
    private val core: WhaCore,
    private val episodeId: String,
    private val subject: String = "me",
) : ViewModel() {
    private val _state = MutableStateFlow(InvestigationUiState())
    val state: StateFlow<InvestigationUiState> = _state

    private val json = Json { ignoreUnknownKeys = true }

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            val detail = load { core.episode(episodeId) }
            when (detail) {
                is WhaResult.Err -> {
                    _state.value = InvestigationUiState(error = detail)
                    return@launch
                }
                is WhaResult.Ok -> {
                    val wording = (load { core.wording() } as? WhaResult.Ok)?.value ?: emptyMap()
                    val episode = detail.value
                    _state.value = InvestigationUiState(
                        detail = episode,
                        narrative = narrative(episode, wording),
                        causes = causes(episode, wording),
                        wording = wording,
                    )
                }
            }
        }
    }

    fun loadHandover() {
        viewModelScope.launch {
            val handover = load { core.handover(subject, episodeId) }
            if (handover is WhaResult.Ok) {
                _state.value = _state.value.copy(handover = handover.value)
            }
        }
    }

    fun review(decision: String, editedProse: String?, rationale: String?) {
        viewModelScope.launch {
            load { core.review(episodeId, decision, editedProse, rationale) }
            load()
        }
    }

    /** Latest belief first: id, label in words, probability, sorted. */
    private fun causes(
        episode: dev.wha.app.core.EpisodeDetail,
        wording: Map<String, String>,
    ): List<CauseBar> {
        val last = episode.belief_history.lastOrNull() ?: return emptyList()
        val belief = last.jsonArray.getOrNull(2)?.jsonObject ?: return emptyList()
        val marginals = belief["marginals"]?.jsonObject ?: return emptyList()
        return marginals.map { (id, value) ->
            CauseBar(id, wording["cause.$id"] ?: id, value.jsonPrimitive.double)
        }.sortedByDescending { it.probability }
    }

    /**
     * One sentence per question and answer, one per belief movement. Question
     * text is the model's or the fallback per text_source; belief is arithmetic
     * and the answer is the person's — the screen labels each.
     */
    private fun narrative(
        episode: dev.wha.app.core.EpisodeDetail,
        wording: Map<String, String>,
    ): List<String> {
        val lines = mutableListOf<String>()
        episode.interactions.forEach { interaction ->
            val answer = interaction.free_text ?: interaction.answer_option_id
            if (interaction.status == "answered" && answer != null) {
                lines.add("You were asked \u201c${interaction.question_text}\u201d and answered $answer.")
            } else if (interaction.status == "pending" || interaction.status == "PENDING") {
                lines.add("You were asked \u201c${interaction.question_text}\u201d and have not answered yet.")
            }
        }
        episode.belief_history.drop(1).forEach { entry ->
            val array = entry.jsonArray
            val label = array.getOrNull(1)?.jsonPrimitive?.content ?: return@forEach
            val marginals = array.getOrNull(2)?.jsonObject?.get("marginals")?.jsonObject ?: return@forEach
            val top = marginals.maxByOrNull { it.value.jsonPrimitive.double } ?: return@forEach
            val name = wording["cause.${top.key}"] ?: top.key
            lines.add("After $label, the most likely cause became $name.")
        }
        return lines
    }

    private suspend fun <T> load(call: suspend () -> WhaResult<T>): WhaResult<T> = try {
        call()
    } catch (e: Exception) {
        WhaResult.Err(ErrorKind.INTERNAL, "${e::class.simpleName}: ${e.message}")
    }
}
