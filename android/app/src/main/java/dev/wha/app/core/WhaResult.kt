package dev.wha.app.core

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject

enum class ErrorKind { UNAVAILABLE, INVALID, INTERNAL }

@Serializable data class Envelope(val error: EnvelopeError)
@Serializable data class EnvelopeError(val kind: String, val message: String)

sealed class WhaResult<out T> {
    data class Ok<T>(val value: T) : WhaResult<T>()
    data class Err(val kind: ErrorKind, val message: String) : WhaResult<Nothing>()

    companion object {
        val json = Json { ignoreUnknownKeys = true; coerceInputValues = true; explicitNulls = false }

        inline fun <reified T> parse(raw: String): WhaResult<T> = try {
            val element = json.parseToJsonElement(raw)
            if (element is kotlinx.serialization.json.JsonObject && "error" in element.jsonObject) {
                val env = json.decodeFromJsonElement(Envelope.serializer(), element)
                Err(runCatching { ErrorKind.valueOf(env.error.kind.uppercase()) }.getOrDefault(ErrorKind.INTERNAL), env.error.message)
            } else Ok(json.decodeFromJsonElement(kotlinx.serialization.serializer<T>(), element))
        } catch (e: Exception) {
            Err(ErrorKind.INTERNAL, "${e::class.simpleName}: ${e.message}")
        }
    }
}
