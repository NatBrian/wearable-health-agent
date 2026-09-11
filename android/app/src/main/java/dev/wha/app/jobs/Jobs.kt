package dev.wha.app.jobs

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import dev.wha.app.core.PythonWhaCore
import dev.wha.app.core.WhaCore
import dev.wha.app.core.WhaResult
import java.time.Instant
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

object Jobs {
    // Mirror the PC scheduler (service/scheduler.py create_scheduler): ingest every 30
    // minutes, episode tick every 15. tests/unit/android/test_job_intervals.py fails if
    // either side changes alone.
    const val INGEST_MINUTES = 30L
    const val TICK_MINUTES = 15L
    // Mirrors NIGHTLY_RESCORE_INTERVAL_HOURS in src/wha/constants.py, checked by the
    // same test. A literal rather than a core call so enqueueing needs no Python.
    const val NIGHTLY_HOURS = 3L

    fun enqueueAll(context: Context) {
        val wm = WorkManager.getInstance(context)
        wm.enqueueUniquePeriodicWork(
            "ingest", ExistingPeriodicWorkPolicy.UPDATE,
            PeriodicWorkRequestBuilder<IngestWorker>(INGEST_MINUTES, TimeUnit.MINUTES).build(),
        )
        wm.enqueueUniquePeriodicWork(
            "nightly", ExistingPeriodicWorkPolicy.UPDATE,
            PeriodicWorkRequestBuilder<NightlyWorker>(NIGHTLY_HOURS, TimeUnit.HOURS).build(),
        )
        wm.enqueueUniquePeriodicWork(
            "episode_tick", ExistingPeriodicWorkPolicy.UPDATE,
            PeriodicWorkRequestBuilder<EpisodeTickWorker>(TICK_MINUTES, TimeUnit.MINUTES).build(),
        )
    }

    fun runCatchupNow(context: Context) {
        WorkManager.getInstance(context).enqueueUniqueWork(
            "startup_catchup", ExistingWorkPolicy.KEEP,
            OneTimeWorkRequestBuilder<CatchupWorker>().build(),
        )
    }
}

private suspend fun runJob(name: String, call: suspend () -> WhaResult<*>) {
    RunState.set(RunState.Status.Running(name, Instant.now()))
    try {
        when (val r = withContext(Dispatchers.IO) { call() }) {
            is WhaResult.Ok -> Unit
            is WhaResult.Err -> android.util.Log.w("WhaJobs", "$name not delivered: ${r.kind} ${r.message}")
        }
    } finally {
        RunState.set(RunState.Status.Idle)
    }
}

class IngestWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        // A failed ingest is a fact for the status screen, not a reason to back off:
        // success either way so WorkManager keeps the schedule instead of retrying
        // into the same wall.
        runJob("ingest") { PythonWhaCore(applicationContext).runIngest() }
        return Result.success()
    }
}

class NightlyWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        runJob("nightly") { PythonWhaCore(applicationContext).runNightly() }
        return Result.success()
    }
}

class CatchupWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        runJob("startup_catchup") { PythonWhaCore(applicationContext).runStartupCatchup() }
        return Result.success()
    }
}

class EpisodeTickWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val core: WhaCore = PythonWhaCore(applicationContext)
        val subject = core.configSubject()
        if (subject != null && investigationActive(core, subject)) {
            InvestigationService.start(applicationContext, subject)
        } else {
            runJob("episode_tick") { core.runEpisodeTick() }
        }
        return Result.success()
    }

    private suspend fun investigationActive(core: WhaCore, subject: String): Boolean {
        // The status strip carries no episode id, so an open episode is read from the
        // episode list: anything not closed means an investigation exists. A pending
        // question needs no service; the person answers from the notification.
        when (val pending = core.pending(subject)) {
            is WhaResult.Ok -> if (pending.value != null) return false
            is WhaResult.Err -> return false
        }
        val episodes = core.episodes(subject)
        if (episodes !is WhaResult.Ok) return false
        return episodes.value.any { it.state != "CLOSED" }
    }
}

/** The configured subject, or null when config is unreachable. */
private suspend fun WhaCore.configSubject(): String? {
    val config = config()
    if (config !is WhaResult.Ok) return null
    return (config.value["configured_subject"] as? kotlinx.serialization.json.JsonPrimitive)?.content
}
