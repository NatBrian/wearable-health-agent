package dev.wha.app.ui.record

import dev.wha.app.core.FakeWhaCore
import dev.wha.app.jobs.RunState
import java.time.Instant
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.flow.toList
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class ReplayTest {
    @OptIn(ExperimentalCoroutinesApi::class)
    @Test fun playAdvancesOneStepPerTickAndStopsAtTheEnd() = runTest {
        val replay = Replay(stepCount = 3, cadenceMs = 100, scope = this)
        replay.play(); advanceTimeBy(350)
        assertEquals(2, replay.state.value.index)
        assertFalse(replay.state.value.playing)
    }

    @OptIn(ExperimentalCoroutinesApi::class)
    @Test fun previousDoesNotGoBelowZero() = runTest {
        val replay = Replay(3, 100, this); replay.previous()
        assertEquals(0, replay.state.value.index)
    }
}

class LivePollerTest {
    @OptIn(ExperimentalCoroutinesApi::class)
    @Test fun pollsOnlyWhileRunningAndEmitsOnChange() = runTest {
        val core = FakeWhaCore()
        core.canned["night_pipeline"] = """{"subject_id":"me","night_date":"2026-09-09","headline":{"level":"NA","flagged":false,"coverage_minutes":0,"questions_asked":0,"sources_read":0},"steps":[]}"""
        RunState.set(RunState.Status.Running("nightly", Instant.EPOCH))
        try {
            val emitted = mutableListOf<dev.wha.app.core.NightPipeline>()
            val job = launch { LivePoller(core, "me", "2026-09-09", intervalMs = 100).observe().toList(emitted) }
            advanceTimeBy(250)
            core.canned["night_pipeline"] = core.canned["night_pipeline"]!!.replace("\"steps\":[]", "\"steps\":[{\"step_id\":\"collect\",\"ordinal\":1,\"layer\":\"deterministic\",\"status\":\"ran\",\"reason\":\"\"}]")
            advanceTimeBy(150)
            RunState.set(RunState.Status.Idle)
            advanceTimeBy(150); job.cancel()
            assertEquals(2, emitted.size)
            assertTrue(core.calls.count { it == "night_pipeline" } in 3..5)
        } finally {
            RunState.set(RunState.Status.Idle)
        }
    }

    private fun assertTrue(value: Boolean) = org.junit.Assert.assertTrue(value)
}
