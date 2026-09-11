package dev.wha.app.settings

import android.content.Context
import java.io.File

class AppSettings(context: Context, private val secrets: SecretStore = SecretStore(context)) {
    private val prefs = context.getSharedPreferences("wha", Context.MODE_PRIVATE)

    var onboarded: Boolean
        get() = prefs.getBoolean("onboarded", false); set(v) = prefs.edit().putBoolean("onboarded", v).apply()
    var webhookHost: String
        get() = prefs.getString("webhook_host", "127.0.0.1")!!; set(v) = prefs.edit().putString("webhook_host", v).apply()
    var webhookPort: Int
        get() = prefs.getInt("webhook_port", 8787); set(v) = prefs.edit().putInt("webhook_port", v).apply()
    var providerBaseUrl: String
        get() = prefs.getString("provider_base_url", "")!!; set(v) = prefs.edit().putString("provider_base_url", v).apply()
    var providerModel: String
        get() = prefs.getString("provider_model", "")!!; set(v) = prefs.edit().putString("provider_model", v).apply()
    var subject: String
        get() = prefs.getString("subject", "me")!!; set(v) = prefs.edit().putString("subject", v).apply()
    var timezone: String
        get() = prefs.getString("timezone", java.util.TimeZone.getDefault().id)!!; set(v) = prefs.edit().putString("timezone", v).apply()
    var webhookToken: String
        get() = secrets.get("webhook_token"); set(v) = secrets.put("webhook_token", v)
    var providerKey: String
        get() = secrets.get("provider_key"); set(v) = secrets.put("provider_key", v)

    /** Exactly the variables the core reads (docs/CONTRACTS.md section 2). */
    fun pythonEnvironment(root: File): Map<String, String> {
        val url = "http://$webhookHost:$webhookPort"
        val hasProvider = providerKey.isNotBlank() && providerBaseUrl.isNotBlank()
        return mapOf(
            "WHA_DB_PATH" to File(root, "data/wha.sqlite").path,
            "WHA_DATA_DIR" to File(root, "data/datasets").path,
            "WHA_SUBJECT" to subject,
            "WHA_TIMEZONE" to timezone,
            "WHA_BRIDGE_URL" to url,
            "WHA_BRIDGE_HOST" to webhookHost,
            "WHA_BRIDGE_PORT" to webhookPort.toString(),
            "WHA_BRIDGE_TOKEN" to webhookToken,
            "WHA_LLM_PROVIDER" to if (hasProvider) "openai_compatible" else "cassette",
            "WHA_LLM_BASE_URL" to providerBaseUrl,
            "WHA_LLM_API_KEY" to providerKey,
            "WHA_LLM_MODEL" to providerModel,
            "WHA_CASSETTE_DIR" to File(root, "cassettes").path,
            "WHA_NOTIFY_CHANNEL" to "android",
        )
    }
}
