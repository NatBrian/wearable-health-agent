package dev.wha.app.ui.settings

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
import kotlinx.serialization.json.JsonPrimitive

class SettingsViewModel(
    private val core: WhaCore,
    private val settings: AppSettings,
) : ViewModel() {
    private val _state = MutableStateFlow(
        SettingsUiState(
            webhookHost = settings.webhookHost,
            webhookPort = settings.webhookPort.toString(),
            providerBaseUrl = settings.providerBaseUrl,
            providerModel = settings.providerModel,
        ),
    )
    val state: StateFlow<SettingsUiState> = _state

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            val config = (load { core.config() } as? WhaResult.Ok)?.value ?: emptyMap()
            val knowledge = (load { core.knowledgeProvenance() } as? WhaResult.Ok)?.value ?: emptyMap()
            val safety = (load { core.safetyProvenance() } as? WhaResult.Ok)?.value ?: emptyList()
            val service = (load { core.settings() } as? WhaResult.Ok)?.value
            val doctor = (load { core.doctor() } as? WhaResult.Ok)?.value ?: emptyList()
            val status = (load { core.status(settings.subject) } as? WhaResult.Ok)?.value
            _state.value = _state.value.copy(
                constants = config.filterKeys { it.first().isUpperCase() }
                    .toSortedMap().map { (name, value) ->
                        ConstantRow(name, plain(value), provenance(name, knowledge, safety))
                    },
                notifyChannel = service?.notify_channel ?: "",
                doctor = doctor,
                lastIngest = status?.last_ingest_utc,
            )
        }
    }

    /**
     * Where a constant's value came from. The knowledge file names its published
     * source where one exists; anything else is an operating parameter of the code
     * rather than a claim about health.
     */
    private fun provenance(
        name: String,
        knowledge: Map<String, Map<String, String>>,
        safety: List<Map<String, String>>,
    ): String {
        knowledge[name]?.let { entry ->
            return entry["source"] ?: entry["citation"] ?: entry["note"] ?: entry["provenance"] ?: ""
        }
        safety.firstOrNull { it["rule"] == name }?.let { row ->
            return when (row["provenance"]) {
                "ASSUMED" -> "no published source found"
                "DERIVED" -> "worked out from other figures here"
                else -> "a published study"
            }
        }
        return "operating parameter of the code"
    }

    fun setWebhook(host: String, port: String, token: String) {
        _state.value = _state.value.copy(webhookHost = host, webhookPort = port, webhookToken = token)
    }

    fun setWebhookPort(port: String) {
        _state.value = _state.value.copy(webhookPort = port)
    }

    fun setProvider(baseUrl: String, model: String, key: String) {
        _state.value = _state.value.copy(providerBaseUrl = baseUrl, providerModel = model, providerKey = key)
    }

    /** Saving changes the environment for the next start; Python reads it at boot. */
    fun save() {
        val s = _state.value
        settings.webhookHost = s.webhookHost
        settings.webhookPort = s.webhookPort.toIntOrNull() ?: settings.webhookPort
        if (s.webhookToken.isNotBlank()) settings.webhookToken = s.webhookToken
        settings.providerBaseUrl = s.providerBaseUrl
        settings.providerModel = s.providerModel
        if (s.providerKey.isNotBlank()) settings.providerKey = s.providerKey
        _state.value = s.copy(restartNeeded = true)
    }

    fun testBridge() {
        val s = _state.value
        viewModelScope.launch {
            val overrides = """{"bridge_host": "${s.webhookHost}", "bridge_token": "${s.webhookToken}"}"""
            _state.value = s.copy(bridgeResult = describe(load { core.diagnose("bridge", overrides) }))
        }
    }

    fun testProvider() {
        val s = _state.value
        viewModelScope.launch {
            val overrides = """{"provider": "openai_compatible", "model": "${s.providerModel}"}"""
            _state.value = s.copy(providerResult = describe(load { core.diagnose("llm", overrides) }))
        }
    }

    fun runJob(job: String) {
        viewModelScope.launch {
            val result = when (job) {
                "nightly" -> load { core.runNightly() }
                "episode_tick" -> load { core.runEpisodeTick() }
                else -> load { core.runIngest() }
            }
            _state.value = _state.value.copy(
                jobResult = when (result) {
                    is WhaResult.Ok -> "Ran."
                    is WhaResult.Err -> result.message
                },
            )
            load()
        }
    }

    fun export() {
        viewModelScope.launch {
            val exported = load { core.auditExport(settings.subject) }
            if (exported is WhaResult.Ok) {
                _state.value = _state.value.copy(exportText = exported.value.content)
            }
        }
    }

    private fun describe(result: WhaResult<JsonElement>): String = when (result) {
        is WhaResult.Ok -> (result.value as? kotlinx.serialization.json.JsonObject)
            ?.get("detail")?.let { (it as? kotlinx.serialization.json.JsonPrimitive)?.content }
            ?: "Answered."
        is WhaResult.Err -> when (result.kind) {
            ErrorKind.UNAVAILABLE -> "Could not reach it: ${result.message}"
            else -> result.message
        }
    }

    private suspend fun <T> load(call: suspend () -> WhaResult<T>): WhaResult<T> = try {
        call()
    } catch (e: Exception) {
        WhaResult.Err(ErrorKind.INTERNAL, "${e::class.simpleName}: ${e.message}")
    }

    private fun plain(value: JsonElement): String {
        val prim = value as? JsonPrimitive ?: return value.toString()
        return if (prim.isString) prim.content else prim.toString()
    }
}
