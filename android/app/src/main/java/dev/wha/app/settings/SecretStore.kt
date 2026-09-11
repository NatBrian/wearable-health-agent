package dev.wha.app.settings

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/** Where a secret is kept. The production backing encrypts; tests use plain memory. */
interface SecretBacking {
    fun get(key: String): String
    fun put(key: String, value: String)
}

private class EncryptedBacking(context: Context) : SecretBacking {
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()
    private val prefs: SharedPreferences = EncryptedSharedPreferences.create(
        context,
        "wha_secrets",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    override fun get(key: String): String = prefs.getString(key, "") ?: ""
    override fun put(key: String, value: String) {
        prefs.edit().putString(key, value).apply()
    }
}

/** Plain in-memory backing, for Robolectric tests only: the keystore is not there. */
class PlainBacking : SecretBacking {
    private val map = mutableMapOf<String, String>()
    override fun get(key: String): String = map[key] ?: ""
    override fun put(key: String, value: String) {
        map[key] = value
    }
}

/** Secrets never touch a readable file. Everything else lives in plain preferences. */
class SecretStore(context: Context, private val backing: SecretBacking = EncryptedBacking(context)) {
    fun get(key: String): String = backing.get(key)
    fun put(key: String, value: String) = backing.put(key, value)
}
