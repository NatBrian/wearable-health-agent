package dev.wha.app.notify

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationManagerCompat
import dev.wha.app.core.PythonWhaCore
import dev.wha.app.core.WhaResult
import dev.wha.app.settings.AppSettings
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

/**
 * Records one tap on a question notification. The tap carries the probe and the
 * chosen option; the episode comes from the current pending question, because the
 * interaction id alone does not identify it.
 */
class AnswerReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != NotificationSink.ACTION_ANSWER) return
        val probeId = intent.getStringExtra("probe_id") ?: return
        val optionId = if (intent.hasExtra("option_id")) intent.getStringExtra("option_id") else null
        val declined = intent.getBooleanExtra("declined", false)
        val notificationId = intent.getIntExtra("notification_id", 0)
        val pending = goAsync()
        CoroutineScope(SupervisorJob() + Dispatchers.IO).launch {
            try {
                val settings = AppSettings(context)
                val core = PythonWhaCore(context)
                when (val p = core.pending(settings.subject)) {
                    is WhaResult.Ok -> {
                        val pendingInteraction = p.value
                        if (pendingInteraction != null) {
                            core.answer(
                                episodeId = pendingInteraction.episode_id,
                                probeId = probeId,
                                optionId = optionId,
                                freeText = null,
                                declined = declined,
                            )
                        }
                    }
                    is WhaResult.Err -> Unit
                }
                NotificationManagerCompat.from(context).cancel(notificationId)
            } finally {
                pending.finish()
            }
        }
    }
}
