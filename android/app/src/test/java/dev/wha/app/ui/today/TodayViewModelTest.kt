package dev.wha.app.ui.today

import dev.wha.app.core.ErrorKind
import dev.wha.app.core.FakeWhaCore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@OptIn(ExperimentalCoroutinesApi::class)
@RunWith(RobolectricTestRunner::class)
class TodayViewModelTest {
    private fun viewModel(core: FakeWhaCore): TodayViewModel {
        Dispatchers.setMain(Dispatchers.Unconfined)
        return TodayViewModel(core, subject = "me")
    }

    @Test fun aRedNightWithNoQuestionShowsTheReasonTheSystemIsQuiet() = runTest {
        val core = FakeWhaCore()
        core.canned["status"] = """{"components":[],"usable_nights":12,"rung":"SHRINKING","errors_24h":0,"quiet_nights_streak":0,"unmeasured_recent_nights":0}"""
        core.canned["pending"] = "null"
        core.canned["urgency"] = """{"urgency":"none","reason":"","set_on":null,"days_ago":null,"stale":false,"cleared":true}"""
        core.canned["night_pipeline"] = """{"subject_id":"me","night_date":"2026-09-09","episode_id":"e1","headline":{"level":"RED","flagged":true,"rung":"SHRINKING","coverage_minutes":340,"questions_asked":0,"sources_read":2},
            "steps":[{"step_id":"decide","ordinal":13,"layer":"agentic","status":"ran","reason":"Asking would not change what the system concludes, so it is watching another night.","outputs":{"action":"OBSERVE"}}]}"""
        core.canned["nights"] = """[{"night_date":"2026-09-09","level":"RED","usable":true,"coverage_minutes":340,"sleep_source":"recorded","episode_id":"e1"}]"""
        core.canned["conversation"] = "[]"
        val vm = viewModel(core)
        vm.refresh(); advanceUntilIdle()
        val s = vm.state.value
        assertEquals("RED", s.lastNight?.level)
        assertEquals("Asking would not change what the system concludes, so it is watching another night.", s.quietReason)
        assertNull(s.pending)
        Dispatchers.resetMain()
    }

    @Test fun anUnavailableCoreBecomesAnErrorCardNotACrash() = runTest {
        val core = FakeWhaCore()
        core.canned["status"] = """{"error":{"kind":"unavailable","message":"no database yet"}}"""
        val vm = viewModel(core); vm.refresh(); advanceUntilIdle()
        assertEquals(ErrorKind.UNAVAILABLE, vm.state.value.error?.kind)
        Dispatchers.resetMain()
    }

    @Test fun sayingSomethingAppendsToTheThreadThroughTheCore() = runTest {
        val core = FakeWhaCore()
        core.canned["say"] = """{"text":"Noted. Has the dizziness changed since yesterday?","citations":[],"refused":false}"""
        core.canned["conversation"] = """[{"role":"user","text":"I feel dizzy"},{"role":"assistant","text":"Noted. Has the dizziness changed since yesterday?"}]"""
        val vm = viewModel(core); vm.say("I feel dizzy"); advanceUntilIdle()
        assertEquals(listOf("say", "conversation"), core.calls.takeLast(2))
        assertEquals(2, vm.state.value.thread.size)
        Dispatchers.resetMain()
    }
}
