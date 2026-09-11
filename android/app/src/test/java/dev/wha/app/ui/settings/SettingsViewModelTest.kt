package dev.wha.app.ui.settings

import androidx.test.core.app.ApplicationProvider
import dev.wha.app.core.FakeWhaCore
import dev.wha.app.settings.AppSettings
import dev.wha.app.settings.PlainBacking
import dev.wha.app.settings.SecretStore
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
class SettingsViewModelTest {
    private fun settings(): AppSettings = AppSettings(
        ApplicationProvider.getApplicationContext(),
        // The keystore is not there under Robolectric; the cipher is not what is tested.
        SecretStore(ApplicationProvider.getApplicationContext(), PlainBacking()),
    )

    @Test fun savingThePortRestartsNothingButChangesTheEnvironmentForNextBoot() = runTest {
        Dispatchers.setMain(Dispatchers.Unconfined)
        val settings = settings()
        val vm = SettingsViewModel(FakeWhaCore(), settings)
        vm.setWebhookPort("9000"); vm.save(); advanceUntilIdle()
        assertEquals(9000, settings.webhookPort)
        assertTrue(vm.state.value.restartNeeded)
        Dispatchers.resetMain()
    }

    @Test fun constantsComeFromConfigWithTheirProvenance() = runTest {
        Dispatchers.setMain(Dispatchers.Unconfined)
        val core = FakeWhaCore()
        core.canned["config"] = """{"DETECT_YELLOW_BPM":3.0,"DETECT_RED_BPM":4.0,"today":"2026-09-10","configured_subject":"me"}"""
        core.canned["knowledge_provenance"] = """{"DETECT_RED_BPM":{"source":"NightSignal, Alavi et al. 2022","kind":"published"}}"""
        val vm = SettingsViewModel(core, settings()); vm.load(); advanceUntilIdle()
        val red = vm.state.value.constants.single { it.name == "DETECT_RED_BPM" }
        assertEquals("4.0", red.value); assertEquals("NightSignal, Alavi et al. 2022", red.source)
        Dispatchers.resetMain()
    }
}
