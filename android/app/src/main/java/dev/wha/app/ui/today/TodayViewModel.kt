package dev.wha.app.ui.today

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dev.wha.app.core.Citation
import dev.wha.app.core.WhaCore
import dev.wha.app.core.WhaResult
import dev.wha.app.corpus.CorpusFetch
import dev.wha.app.corpus.CorpusState
import dev.wha.app.ui.common.Wording
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

class TodayViewModel(
    private val core: WhaCore,
    private val subject: String,
    corpus: CorpusState = CorpusFetch.state.value,
) : ViewModel() {
    private val _state = MutableStateFlow(TodayUiState(corpus = corpus))
    val state: StateFlow<TodayUiState> = _state

    private val json = Json { ignoreUnknownKeys = true }

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            var error: WhaResult.Err? = null
            fun note(err: WhaResult.Err) {
                if (error == null) error = err
            }

            val status = load { core.status(subject) }.also { if (it is WhaResult.Err) note(it) }
            val pending = load { core.pending(subject) }.also { if (it is WhaResult.Err) note(it) }
            val urgency = load { core.urgency(subject) }.also { if (it is WhaResult.Err) note(it) }
            val nights = load { core.nights(subject, 60) }.also { if (it is WhaResult.Err) note(it) }
            val conversation = load { core.conversation(subject, 40) }.also { if (it is WhaResult.Err) note(it) }
            // Static maps degrade silently: a missing sentence leaves a blank line,
            // never an error card over the whole screen.
            val wording = (load { core.wording() } as? WhaResult.Ok)?.value ?: emptyMap()
            val settings = (load { core.settings() } as? WhaResult.Ok)?.value
            val episodes = (load { core.episodes(subject) } as? WhaResult.Ok)?.value ?: emptyList()

            val newest = (nights as? WhaResult.Ok)?.value?.maxByOrNull { it.night_date }
            var pipeline: WhaResult<dev.wha.app.core.NightPipeline>? = null
            if (newest != null) {
                pipeline = load { core.nightPipeline(subject, newest.night_date) }
                if (pipeline is WhaResult.Err) note(pipeline)
            }
            val statusValue = (status as? WhaResult.Ok)?.value
            // The pull time is when the data was last fresh; a stale reading must read
            // as stale. Localised for reading, raw when localisation itself fails.
            val lastPull = statusValue?.last_ingest_utc?.let { utc ->
                (load { core.localise(utc) } as? WhaResult.Ok)?.value ?: utc
            }
            val pipe = (pipeline as? WhaResult.Ok)?.value
            val usableNights = (status as? WhaResult.Ok)?.value?.usable_nights ?: 0
            val rung = (status as? WhaResult.Ok)?.value?.rung ?: ""
            val lastNight = newest?.let {
                LastNight(
                    date = it.night_date,
                    level = it.level,
                    coverageMinutes = it.coverage_minutes,
                    sleepSource = it.rhr_window_source,
                    rung = rung,
                    usableNights = usableNights,
                    episodeId = it.episode_id,
                )
            }
            val pendingValue = (pending as? WhaResult.Ok)?.value
            val quiet = if (pendingValue == null && lastNight != null) {
                val flagged = pipe?.headline?.flagged == true
                val decideReason = pipe?.steps?.singleOrNull { it.step_id == "decide" }?.reason
                if ((flagged || pipe?.episode_id != null) && !decideReason.isNullOrBlank()) {
                    decideReason to true
                } else {
                    (wording["today.quiet.${lastNight.level}"] ?: "") to false
                }
            } else {
                null
            }
            _state.value = TodayUiState(
                lastNight = lastNight,
                levelSentence = if (lastNight != null) Wording.level(lastNight.level, rung.ifBlank { null }, wording) else "",
                quietReason = quiet?.first,
                quietFromDecide = quiet?.second == true,
                pending = pendingValue,
                urgency = (urgency as? WhaResult.Ok)?.value?.takeUnless { it.urgency == "none" || it.cleared },
                providerConfigured = settings?.llm_provider?.let { it != "cassette" } ?: true,
                corpus = _state.value.corpus,
                thread = (conversation as? WhaResult.Ok)?.value?.map { turn ->
                    ThreadTurn(
                        role = turn.role,
                        text = turn.text,
                        citations = parseCitations(turn.citations_json),
                        uncited = parseStrings(turn.uncited_json),
                    )
                } ?: _state.value.thread,
                error = error,
                wording = wording,
                openEpisodeId = episodes.firstOrNull { it.state != "CLOSED" }?.episode_id,
                lastPull = lastPull,
            )
        }
    }

    fun say(text: String) {
        viewModelScope.launch {
            val sent = load { core.say(subject, text, null) }
            if (sent is WhaResult.Err) {
                _state.value = _state.value.copy(error = sent)
                return@launch
            }
            val conversation = load { core.conversation(subject, 40) }
            if (conversation is WhaResult.Ok) {
                _state.value = _state.value.copy(
                    thread = conversation.value.map {
                        ThreadTurn(it.role, it.text, parseCitations(it.citations_json), parseStrings(it.uncited_json))
                    },
                )
            }
        }
    }

    fun answer(optionId: String?, freeText: String?, declined: Boolean) {
        val pending = _state.value.pending?.takeIf { it.kind == "question" } ?: return
        val probeId = pending.question?.probe?.probe_id ?: return
        viewModelScope.launch {
            load { core.answer(pending.episode_id, probeId, optionId, freeText, declined) }
            refresh()
        }
    }

    fun review(decision: String, editedProse: String?, rationale: String?) {
        val pending = _state.value.pending?.takeIf { it.kind == "review" } ?: return
        viewModelScope.launch {
            load { core.review(pending.episode_id, decision, editedProse, rationale) }
            refresh()
        }
    }

    fun acknowledgeUrgency() {
        viewModelScope.launch {
            load { core.acknowledgeUrgency(subject) }
            refresh()
        }
    }

    /** A throw from the core (a fake without the canned call, a broken bridge) is a failed card, not a crash. */
    private suspend fun <T> load(call: suspend () -> WhaResult<T>): WhaResult<T> = try {
        call()
    } catch (e: Exception) {
        WhaResult.Err(dev.wha.app.core.ErrorKind.INTERNAL, "${e::class.simpleName}: ${e.message}")
    }

    private fun parseCitations(raw: String): List<Citation> = try {
        if (raw.isBlank()) emptyList()
        else json.parseToJsonElement(raw).jsonArray.map { json.decodeFromJsonElement(Citation.serializer(), it) }
    } catch (e: Exception) {
        emptyList()
    }

    private fun parseStrings(raw: String): List<String> = try {
        if (raw.isBlank()) emptyList()
        else json.parseToJsonElement(raw).jsonArray.map { it.jsonPrimitive.content }
    } catch (e: Exception) {
        emptyList()
    }
}
