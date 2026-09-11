package dev.wha.app.ui.settings

import dev.wha.app.core.DoctorRow

data class ConstantRow(val name: String, val value: String, val source: String)

data class SettingsUiState(
    val webhookHost: String = "",
    val webhookPort: String = "",
    val webhookToken: String = "",
    val providerBaseUrl: String = "",
    val providerModel: String = "",
    val providerKey: String = "",
    val bridgeResult: String? = null,
    val providerResult: String? = null,
    val restartNeeded: Boolean = false,
    val constants: List<ConstantRow> = emptyList(),
    val notifyChannel: String = "",
    val doctor: List<DoctorRow> = emptyList(),
    val jobResult: String? = null,
    val exportText: String? = null,
    val lastIngest: String? = null,
)
