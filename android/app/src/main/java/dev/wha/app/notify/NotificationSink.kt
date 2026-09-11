package dev.wha.app.notify

import android.Manifest
import android.app.Notification
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat

/** Delivers what the agent decides to say as a phone notification. Python calls [deliver]. */
class NotificationSink(private val context: Context) {

    /**
     * Payload keys from wha.notify.android (Task 6): kind, text, interaction_id,
     * probe_id, options. Accepts the JSON string wha_boot sends or a Map, so the
     * boundary never depends on Chaquopy's nested conversions.
     */
    fun deliver(payload: Any?): Boolean {
        val map = when (payload) {
            is String -> parseJson(payload)
            is Map<*, *> -> {
                @Suppress("UNCHECKED_CAST")
                payload as Map<String, Any?>
            }
            else -> null
        } ?: return false
        if (Build.VERSION.SDK_INT >= 33 && ActivityCompat.checkSelfPermission(
                context, Manifest.permission.POST_NOTIFICATIONS,
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            return false
        }
        NotificationChannels.ensure(context)
        val kind = map["kind"]?.toString() ?: "SYSTEM"
        val text = map["text"]?.toString() ?: ""
        val interactionId = map["interaction_id"]?.toString()
        val probeId = map["probe_id"]?.toString() ?: ""
        @Suppress("UNCHECKED_CAST")
        val options = (map["options"] as? List<Map<String, Any?>>) ?: emptyList()
        val channel = if (kind == "ESCALATION") NotificationChannels.URGENT else NotificationChannels.QUESTIONS
        val id = notificationId(kind, text, interactionId)
        val builder = NotificationCompat.Builder(context, channel)
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setAutoCancel(kind != "ESCALATION")
        if (kind == "ESCALATION") {
            builder.setOngoing(true)
            builder.setCategory(Notification.CATEGORY_ALARM)
        }
        if (kind == "QUESTION") {
            options.forEach { option ->
                val optionId = option["option_id"]?.toString() ?: ""
                val label = option["label"]?.toString() ?: optionId
                builder.addAction(
                    0, label,
                    answerIntent(context, id, interactionId, probeId, optionId, declined = false),
                )
            }
            builder.addAction(
                0, "Not now",
                answerIntent(context, id, interactionId, probeId, optionId = null, declined = true),
            )
        }
        if (kind == "QUESTION") {
            // Tag each action with the row id so the receiver clears exactly this row,
            // even when the interaction id is missing and the id came from the text.
            // (The intents already carry it as notification_id, set when built above.)
        }
        NotificationManagerCompat.from(context).notify(id, builder.build())
        return true
    }

    private fun parseJson(raw: String): Map<String, Any?>? = try {
        val json = org.json.JSONObject(raw)
        val options = json.optJSONArray("options")?.let { array ->
            List(array.length()) { i ->
                val option = array.getJSONObject(i)
                mapOf(
                    "option_id" to option.optString("option_id"),
                    "label" to option.optString("label"),
                )
            }
        }
        mapOf(
            "kind" to json.optString("kind", "SYSTEM"),
            "text" to json.optString("text", ""),
            "interaction_id" to json.opt("interaction_id")
                .takeUnless { it == null || it == org.json.JSONObject.NULL }?.toString(),
            "probe_id" to json.optString("probe_id", ""),
            "options" to options,
        )
    } catch (e: Exception) {
        null
    }

    companion object {
        const val ACTION_ANSWER = "dev.wha.ANSWER"

        fun notificationId(kind: String, text: String, interactionId: String?): Int {
            val key = interactionId ?: "$kind:$text"
            return key.hashCode()
        }

        private fun answerIntent(
            context: Context, notificationId: Int, interactionId: String?, probeId: String,
            optionId: String?, declined: Boolean,
        ): PendingIntent {
            val intent = Intent(context, AnswerReceiver::class.java)
                .setAction(ACTION_ANSWER)
                .putExtra("notification_id", notificationId)
                .putExtra("interaction_id", interactionId)
                .putExtra("probe_id", probeId)
                .putExtra("declined", declined)
            if (optionId != null) intent.putExtra("option_id", optionId)
            val request = (interactionId to optionId to declined).hashCode()
            return PendingIntent.getBroadcast(
                context, request, intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )
        }
    }
}
