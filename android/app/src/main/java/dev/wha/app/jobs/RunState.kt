package dev.wha.app.jobs

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.time.Instant

/** Whether a job is running right now. The Record tab reads this to animate progress. */
object RunState {
    sealed interface Status {
        data object Idle : Status
        data class Running(val job: String, val since: Instant) : Status
    }

    private val _status = MutableStateFlow<Status>(Status.Idle)
    val status: StateFlow<Status> = _status

    fun set(status: Status) {
        _status.value = status
    }
}
