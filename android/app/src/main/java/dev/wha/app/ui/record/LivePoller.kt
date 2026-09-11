package dev.wha.app.ui.record

import dev.wha.app.core.NightPipeline
import dev.wha.app.core.WhaCore
import dev.wha.app.core.WhaResult
import dev.wha.app.jobs.RunState
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow

/**
 * Watches a night while a job runs. Polls only while RunState is Running and
 * emits only when the pipeline changed, so the graph moves as steps land and
 * sits still otherwise. Progress is read from what each step wrote, so the
 * picture cannot claim work that did not happen.
 */
class LivePoller(
    private val core: WhaCore,
    private val subject: String,
    private val date: String,
    private val intervalMs: Long = 1000L,
) {
    fun observe(): Flow<NightPipeline> = flow {
        var last: NightPipeline? = null
        while (RunState.status.value is RunState.Status.Running) {
            val current = try {
                core.nightPipeline(subject, date)
            } catch (e: Exception) {
                null
            }
            if (current is WhaResult.Ok && current.value != last) {
                last = current.value
                emit(current.value)
            }
            delay(intervalMs)
        }
    }
}
