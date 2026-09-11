package dev.wha.app.ui.record

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dev.wha.app.core.ErrorKind
import dev.wha.app.core.NightPipeline
import dev.wha.app.core.WhaCore
import dev.wha.app.core.WhaResult
import dev.wha.app.jobs.RunState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class RecordViewModel(
    private val core: WhaCore,
    private val subject: String,
    initialDate: String? = null,
) : ViewModel() {
    private val _state = MutableStateFlow(RecordUiState())
    val state: StateFlow<RecordUiState> = _state

    init {
        viewModelScope.launch {
            val nights = load { core.pipelineNights(subject, 60) }
            when (nights) {
                is WhaResult.Err -> {
                    _state.value = RecordUiState(error = nights)
                    return@launch
                }
                is WhaResult.Ok -> {
                    val lineage = load { core.lineage() }
                    val wording = load { core.wording() }
                    val config = load { core.config() }
                    val audit = load { core.audit(subject, 1, 0) }
                    val safety = load { core.safetyProvenance() }
                    _state.value = RecordUiState(
                        nights = nights.value.sortedByDescending { it.night_date },
                        lineage = (lineage as? WhaResult.Ok)?.value ?: emptyList(),
                        wording = (wording as? WhaResult.Ok)?.value ?: emptyMap(),
                        config = (config as? WhaResult.Ok)?.value ?: emptyMap(),
                        toolNames = (audit as? WhaResult.Ok)?.value?.permitted_tools ?: emptyList(),
                        safetyRows = (safety as? WhaResult.Ok)?.value ?: emptyList(),
                    )
                    val first = initialDate ?: nights.value.maxByOrNull { it.night_date }?.night_date
                    if (first != null) select(first)
                    watchLive()
                }
            }
        }
    }

    fun select(date: String) {
        viewModelScope.launch {
            val pipeline = load { core.nightPipeline(subject, date) }
            when (pipeline) {
                is WhaResult.Err -> {
                    _state.value = _state.value.copy(error = pipeline)
                    return@launch
                }
                is WhaResult.Ok -> {
                    _state.value = _state.value.copy(
                        selected = date,
                        pipeline = pipeline.value,
                        highlighted = emptySet(),
                        running = null,
                    )
                }
            }
        }
    }

    fun open(stepId: String) {
        _state.value = _state.value.copy(
            sheet = _state.value.pipeline?.steps?.singleOrNull { it.step_id == stepId },
        )
    }

    fun closeSheet() {
        _state.value = _state.value.copy(sheet = null)
    }

    /** Tapping a result highlights where it came from and what read it. */
    fun highlight(stepId: String, output: String) {
        val lineage = Lineage(_state.value.lineage)
        _state.value = _state.value.copy(
            sheet = null,
            highlighted = lineage.upstream(stepId, output) + lineage.downstream(stepId, output) + stepId,
        )
    }

    fun clearHighlight() {
        _state.value = _state.value.copy(highlighted = emptySet())
    }

    /**
     * While a job runs, the graph follows what lands. When the run ends, one
     * reload settles the picture and the pulse clears.
     */
    private fun watchLive() {
        viewModelScope.launch {
            RunState.status.collect { status ->
                if (status is RunState.Status.Running) {
                    val date = _state.value.selected ?: return@collect
                    LivePoller(core, subject, date).observe().collect { pipeline ->
                        _state.value = _state.value.copy(
                            pipeline = pipeline,
                            running = nextStepId(pipeline),
                        )
                    }
                    _state.value = _state.value.copy(running = null)
                    select(date)
                } else {
                    _state.value = _state.value.copy(running = null)
                }
            }
        }
    }

    private fun nextStepId(pipeline: NightPipeline): String? {
        val steps = pipeline.steps.sortedBy { it.ordinal }
        val lastRan = steps.filter { it.status == "ran" }.maxOfOrNull { it.ordinal } ?: 0
        return steps.firstOrNull { it.ordinal == lastRan + 1 }?.step_id
    }

    fun localise(utcIso: String, onDone: (String) -> Unit) {
        viewModelScope.launch {
            val localised = load { core.localise(utcIso) }
            onDone((localised as? WhaResult.Ok)?.value ?: utcIso)
        }
    }

    private suspend fun <T> load(call: suspend () -> WhaResult<T>): WhaResult<T> = try {
        call()
    } catch (e: Exception) {
        WhaResult.Err(ErrorKind.INTERNAL, "${e::class.simpleName}: ${e.message}")
    }
}
