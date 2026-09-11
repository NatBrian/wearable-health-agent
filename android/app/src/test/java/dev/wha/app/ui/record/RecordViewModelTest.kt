package dev.wha.app.ui.record

import dev.wha.app.core.FakeWhaCore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@OptIn(ExperimentalCoroutinesApi::class)
@RunWith(RobolectricTestRunner::class)
class RecordViewModelTest {
    @Test fun selectingANightLoadsItsPipeline() = runTest {
        Dispatchers.setMain(Dispatchers.Unconfined)
        val core = FakeWhaCore()
        core.canned["pipeline_nights"] = """[{"night_date":"2026-09-09","level":"RED","has_episode":true,"usable":true}]"""
        core.canned["lineage"] = "[]"
        core.canned["wording"] = "{}"
        core.canned["night_pipeline"] = """{"subject_id":"me","night_date":"2026-09-09",
            "headline":{"level":"RED","flagged":true,"coverage_minutes":340,"questions_asked":1,"sources_read":2},
            "steps":[{"step_id":"detect","ordinal":7,"layer":"deterministic","status":"ran","reason":"Clearly above."}]}"""
        val vm = RecordViewModel(core, "me")
        advanceUntilIdle()
        assertEquals("2026-09-09", vm.state.value.selected)
        assertEquals(1, vm.state.value.pipeline?.steps?.size)
        vm.open("detect")
        advanceUntilIdle()
        assertEquals("detect", vm.state.value.sheet?.step_id)
        Dispatchers.resetMain()
    }
}
