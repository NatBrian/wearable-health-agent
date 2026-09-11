package dev.wha.app.ui.investigation

import dev.wha.app.core.FakeWhaCore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@OptIn(ExperimentalCoroutinesApi::class)
@RunWith(RobolectricTestRunner::class)
class InvestigationViewModelTest {
    @Test fun causesAreRankedFromTheLatestBeliefAndNamedInWords() = runTest {
        Dispatchers.setMain(Dispatchers.Unconfined)
        val core = FakeWhaCore()
        core.canned["episode"] = """{"summary":{"episode_id":"e1","opened_on":"2026-09-08","state":"CLOSED","disposition":"LIKELY_BENIGN","night_span":["2026-09-07","2026-09-08"],"top_cause":"alcohol","top_probability":0.61},
          "outcome":{"disposition":"LIKELY_BENIGN","prose":"Your raised rate is most consistent with alcohol the evening before.","when_to_seek_care":"If you develop fever, see a clinician.","reviewed_by_person":true},
          "stages":[],"belief_history":[[1,"prior",{"marginals":{"alcohol":0.2,"infection":0.2}}],[2,"after answers",{"marginals":{"alcohol":0.61,"infection":0.12}}]],
          "interactions":[{"id":"i1","probe_id":"alcohol","question_text":"Did you drink last night?","text_source":"llm","options":[],"evsi":0.3,"interruption_cost":0.2,"rejected":[],"answer_option_id":"yes","status":"answered","asked_at_utc":"2026-09-08T09:00:00Z"}],
          "measurements":[],"citations":[],"stripped_claims":["It is probably a virus."]}"""
        core.canned["wording"] = """{"cause.alcohol":"alcohol the evening before","cause.infection":"an infection starting"}"""
        val vm = InvestigationViewModel(core, "e1"); vm.load(); advanceUntilIdle()
        val s = vm.state.value
        assertEquals(listOf("alcohol the evening before", "an infection starting"), s.causes.map { it.label })
        assertEquals(0.61, s.causes.first().probability, 1e-9)
        assertTrue(s.narrative.any { it.contains("Did you drink last night?") && it.contains("yes") })
        assertEquals(listOf("It is probably a virus."), s.detail?.stripped_claims)
        Dispatchers.resetMain()
    }
}
