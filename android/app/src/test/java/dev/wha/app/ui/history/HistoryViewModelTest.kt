package dev.wha.app.ui.history

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
class HistoryViewModelTest {
    @Test fun newestNightComesFirstAndUnmeasuredNightsStay() = runTest {
        Dispatchers.setMain(Dispatchers.Unconfined)
        val core = FakeWhaCore()
        core.canned["nights"] = """[
            {"night_date":"2026-09-01","level":"GREEN","usable":true,"coverage_minutes":400,"rhr_bpm":60.0,"band_lo":57.0,"band_hi":63.0},
            {"night_date":"2026-09-02","level":"NA","usable":false,"coverage_minutes":0}
        ]"""
        core.canned["episodes"] = "[]"
        val vm = HistoryViewModel(core, "me")
        vm.refresh(); advanceUntilIdle()
        assertEquals(listOf("2026-09-02", "2026-09-01"), vm.state.value.nights.map { it.night_date })
        Dispatchers.resetMain()
    }
}
