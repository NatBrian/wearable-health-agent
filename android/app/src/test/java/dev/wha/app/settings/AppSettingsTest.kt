package dev.wha.app.settings

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

private fun settings() =
    AppSettings(ApplicationProvider.getApplicationContext(), SecretStore(ApplicationProvider.getApplicationContext(), PlainBacking()))

@RunWith(RobolectricTestRunner::class)
class AppSettingsTest {

    @Test fun environmentUsesLocalhostWebhookByDefault() {
        val env = settings().pythonEnvironment(File("/tmp/wha"))
        assertEquals("http://127.0.0.1:8787", env["WHA_BRIDGE_URL"])
        assertEquals("127.0.0.1", env["WHA_BRIDGE_HOST"])
        assertEquals("8787", env["WHA_BRIDGE_PORT"])
        assertEquals("android", env["WHA_NOTIFY_CHANNEL"])
        assertEquals("/tmp/wha/data/wha.sqlite", env["WHA_DB_PATH"])
        assertEquals("cassette", env["WHA_LLM_PROVIDER"]) // until a key is entered
    }

    @Test fun aProviderKeySwitchesTheProviderOn() {
        val s = settings()
        s.providerKey = "sk-test"; s.providerBaseUrl = "https://api.example/v1"; s.providerModel = "m"
        val env = s.pythonEnvironment(File("/tmp/wha"))
        assertEquals("openai_compatible", env["WHA_LLM_PROVIDER"])
        assertEquals("sk-test", env["WHA_LLM_API_KEY"])
    }

    @Test fun portChangesTheUrl() {
        val s = settings(); s.webhookPort = 9000
        assertEquals("http://127.0.0.1:9000", s.pythonEnvironment(File("/tmp/wha"))["WHA_BRIDGE_URL"])
    }

    @Test fun secretsAreNotInPlainPreferences() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val s = settings(); s.providerKey = "sk-secret"
        val plain = context.getSharedPreferences("wha", Context.MODE_PRIVATE).all.values.joinToString()
        assertFalse(plain.contains("sk-secret"))
    }
}
