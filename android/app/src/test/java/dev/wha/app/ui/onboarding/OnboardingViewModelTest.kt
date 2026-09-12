package dev.wha.app.ui.onboarding

import androidx.test.core.app.ApplicationProvider
import dev.wha.app.core.FakeWhaCore
import dev.wha.app.settings.AppSettings
import dev.wha.app.settings.PlainBacking
import dev.wha.app.settings.SecretStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@OptIn(ExperimentalCoroutinesApi::class)
@RunWith(RobolectricTestRunner::class)
class OnboardingViewModelTest {
    private val dispatcher = StandardTestDispatcher()

    private fun viewModel(core: FakeWhaCore = FakeWhaCore()): Pair<OnboardingViewModel, AppSettings> {
        Dispatchers.setMain(dispatcher)
        val settings = AppSettings(
            ApplicationProvider.getApplicationContext(),
            SecretStore(ApplicationProvider.getApplicationContext(), PlainBacking()),
        )
        return OnboardingViewModel(core, settings) to settings
    }

    @Test fun finishIsDisabledUntilTheDisclaimerIsTicked() = runTest(dispatcher) {
        val (vm, _) = viewModel()
        vm.finish(); advanceUntilIdle()
        assertFalse(vm.state.value.finished)
        vm.tickDisclaimer(true)
        vm.finish(); advanceUntilIdle()
        assertTrue(vm.state.value.finished)
        Dispatchers.resetMain()
    }

    @Test fun aSuccessfulBridgeTestShowsItsDetail() = runTest(dispatcher) {
        val core = FakeWhaCore()
        core.canned["diagnose"] = """{"ok": true, "detail": "Connected to bridge", "latency_ms": 12}"""
        val (vm, _) = viewModel(core)
        vm.testBridge(); advanceUntilIdle()
        assertEquals("Connected to bridge", vm.state.value.bridgeResult)
        Dispatchers.resetMain()
    }

    @Test fun anUnreachableBridgeShowsWordsNotACrash() = runTest(dispatcher) {
        val core = FakeWhaCore()
        core.canned["diagnose"] = """{"error": {"kind": "unavailable", "message": "no route"}}"""
        val (vm, _) = viewModel(core)
        vm.testBridge(); advanceUntilIdle()
        assertEquals("Could not reach it: no route", vm.state.value.bridgeResult)
        Dispatchers.resetMain()
    }

    @Test fun finishSavesTheConnections() = runTest(dispatcher) {
        val (vm, settings) = viewModel()
        vm.setWebhook("192.168.1.2", "9000", "tok")
        vm.tickDisclaimer(true)
        vm.finish(); advanceUntilIdle()
        assertEquals("192.168.1.2", settings.webhookHost)
        assertEquals(9000, settings.webhookPort)
        assertTrue(settings.onboarded)
        Dispatchers.resetMain()
    }

    @Test fun aThrowingCoreShowsWordsNotACrash() = runTest(dispatcher) {
        // Run 1 finding 1: the Test buttons are the first touch of Python, and a
        // throw there closed the app. The fake throws when nothing is canned, like
        // a failed first start does on the phone.
        val (vm, _) = viewModel(FakeWhaCore())
        vm.testBridge(); advanceUntilIdle()
        assertTrue(vm.state.value.bridgeResult?.contains("no canned JSON") == true)
        vm.testProvider(); advanceUntilIdle()
        assertTrue(vm.state.value.providerResult?.contains("no canned JSON") == true)
        Dispatchers.resetMain()
    }
}
