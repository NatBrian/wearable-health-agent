package dev.wha.app.corpus

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import dev.wha.app.core.PythonWhaCore
import dev.wha.app.core.WhaResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/** Whether the general health information is on the phone yet. */
sealed interface CorpusState {
    data object Missing : CorpusState
    data object Fetching : CorpusState
    data object Ready : CorpusState
    data class Failed(val message: String) : CorpusState
}

/**
 * Fetches the corpus the assistant retrieves from. The download streams into
 * data/corpus under the working directory the boot set; nothing new in Python.
 */
object CorpusFetch {
    private val _state = MutableStateFlow<CorpusState>(CorpusState.Missing)
    val state: StateFlow<CorpusState> = _state

    fun start(context: Context) {
        _state.value = CorpusState.Fetching
        WorkManager.getInstance(context).enqueueUniqueWork(
            "corpus_fetch", ExistingWorkPolicy.KEEP,
            OneTimeWorkRequestBuilder<CorpusWorker>().build(),
        )
    }

    internal fun set(state: CorpusState) {
        _state.value = state
    }
}

class CorpusWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val core = PythonWhaCore(applicationContext)
        return when (val fetched = core.fetchCorpus()) {
            is WhaResult.Err -> {
                CorpusFetch.set(CorpusState.Failed(fetched.message))
                Result.failure()
            }
            is WhaResult.Ok -> when (val ready = core.retrievalReady()) {
                is WhaResult.Ok -> {
                    CorpusFetch.set(if (ready.value.ready) CorpusState.Ready else CorpusState.Failed("The download finished but the library is still not available."))
                    if (ready.value.ready) Result.success() else Result.failure()
                }
                is WhaResult.Err -> {
                    CorpusFetch.set(CorpusState.Failed(ready.message))
                    Result.failure()
                }
            }
        }
    }
}
