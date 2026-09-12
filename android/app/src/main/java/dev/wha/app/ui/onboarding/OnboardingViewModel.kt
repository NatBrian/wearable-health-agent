package dev.wha.app.ui.onboarding

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dev.wha.app.core.ErrorKind
import dev.wha.app.core.WhaCore
import dev.wha.app.core.WhaResult
import dev.wha.app.settings.AppSettings
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonPrimitive

data class OnboardingUiState(
    val disclaimerTicked: Boolean = false,
    val webhookHost: String = "127.0.0.1",
    val webhookPort: String = "8787",
    val webhookToken: String = "",
    val providerBaseUrl: String = "",
    val providerModel: String = "",
    val providerKey: String = "",
    val bridgeResult: String? = null,
    val providerResult: String? = null,
    val finished: Boolean = false,
) {
    val canFinish: Boolean get() = disclaimerTicked
}

class OnboardingViewModel(
    private val core: WhaCore,
    private val settings: AppSettings,
) : ViewModel() {
    private val _state = MutableStateFlow(
        OnboardingUiState(
            webhookHost = settings.webhookHost,
            webhookPort = settings.webhookPort.toString(),
            providerBaseUrl = settings.providerBaseUrl,
            providerModel = settings.providerModel,
        )
    )
    val state: StateFlow<OnboardingUiState> = _state

    fun tickDisclaimer(ticked: Boolean) {
        _state.value = _state.value.copy(disclaimerTicked = ticked)
    }

    fun setWebhook(host: String, port: String, token: String) {
        _state.value = _state.value.copy(webhookHost = host, webhookPort = port, webhookToken = token)
    }

    fun setProvider(baseUrl: String, model: String, key: String) {
        _state.value = _state.value.copy(providerBaseUrl = baseUrl, providerModel = model, providerKey = key)
    }

    fun testBridge() {
        val s = _state.value
        viewModelScope.launch {
            val overrides = """{"bridge_host": ${jsonStr(s.webhookHost)}, "bridge_token": ${jsonStr(s.webhookToken)}}"""
            // A Test button must show words, never close the app: this is the first
            // touch of Python, so any throw during first start lands here.
            val result = try {
                core.diagnose("bridge", overrides)
            } catch (e: Exception) {
                WhaResult.Err(ErrorKind.INTERNAL, "${e::class.simpleName}: ${e.message}")
            }
            _state.value = s.copy(bridgeResult = describe(result))
        }
    }

    fun testProvider() {
        val s = _state.value
        viewModelScope.launch {
            val overrides = """{"provider": "openai_compatible", "model": ${jsonStr(s.providerModel)}}"""
            val result = try {
                core.diagnose("llm", overrides)
            } catch (e: Exception) {
                WhaResult.Err(ErrorKind.INTERNAL, "${e::class.simpleName}: ${e.message}")
            }
            _state.value = s.copy(providerResult = describe(result))
        }
    }

    private fun describe(result: WhaResult<JsonElement>): String = when (result) {
        is WhaResult.Ok -> (result.value as? JsonObject)?.get("detail")?.jsonPrimitive?.content
            ?: "The check answered, but not in words I can show."
        is WhaResult.Err -> when (result.kind) {
            ErrorKind.UNAVAILABLE -> "Could not reach it: ${result.message}"
            else -> result.message
        }
    }

    fun finish() {
        if (!_state.value.canFinish) return
        val s = _state.value
        settings.webhookHost = s.webhookHost
        settings.webhookPort = s.webhookPort.toIntOrNull() ?: 8787
        settings.webhookToken = s.webhookToken
        settings.providerBaseUrl = s.providerBaseUrl
        settings.providerModel = s.providerModel
        settings.providerKey = s.providerKey
        // Jobs (Task 14) and the corpus fetch (Task 16) do not exist yet; Finish only
        // records consent and settings. Later tasks enqueue work here.
        settings.onboarded = true
        _state.value = s.copy(finished = true)
    }

    private fun jsonStr(raw: String): String =
        '"' + raw.replace("\\", "\\\\").replace("\"", "\\\"") + '"'
}
