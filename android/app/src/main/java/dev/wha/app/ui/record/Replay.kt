package dev.wha.app.ui.record

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class ReplayState(val index: Int = 0, val playing: Boolean = false)

/**
 * Steps through a finished night one step at a time. Pacing is fixed for
 * reading and says so next to the controls; it is not how long steps took.
 */
class Replay(
    private val stepCount: Int,
    private val cadenceMs: Long,
    private val scope: CoroutineScope,
) {
    private val _state = MutableStateFlow(ReplayState())
    val state: StateFlow<ReplayState> = _state

    private var job: Job? = null

    fun play() {
        if (job?.isActive == true || _state.value.index >= stepCount - 1) {
            if (_state.value.index >= stepCount - 1) {
                _state.value = ReplayState(index = 0, playing = true)
                start()
            }
            return
        }
        _state.value = _state.value.copy(playing = true)
        start()
    }

    private fun start() {
        job?.cancel()
        job = scope.launch {
            while (_state.value.index < stepCount - 1) {
                delay(cadenceMs)
                _state.value = _state.value.copy(index = _state.value.index + 1)
            }
            _state.value = _state.value.copy(playing = false)
        }
    }

    fun pause() {
        job?.cancel()
        job = null
        _state.value = _state.value.copy(playing = false)
    }

    fun next() {
        pause()
        _state.value = _state.value.copy(index = (_state.value.index + 1).coerceAtMost(stepCount - 1))
    }

    fun previous() {
        pause()
        _state.value = _state.value.copy(index = (_state.value.index - 1).coerceAtLeast(0))
    }

    fun seek(i: Int) {
        pause()
        _state.value = _state.value.copy(index = i.coerceIn(0, stepCount - 1))
    }
}
