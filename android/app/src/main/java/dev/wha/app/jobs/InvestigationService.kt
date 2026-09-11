package dev.wha.app.jobs

import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import dev.wha.app.R
import dev.wha.app.core.PythonWhaCore
import dev.wha.app.notify.NotificationChannels
import java.time.Instant
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/**
 * Runs one episode tick in the foreground while an investigation is active, so the
 * person can see the system working. Started by [EpisodeTickWorker], never by a tap.
 */
class InvestigationService : Service() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val subject = intent?.getStringExtra(EXTRA_SUBJECT) ?: "me"
        val notification = NotificationCompat.Builder(this, NotificationChannels.ONGOING)
            .setContentTitle(getString(R.string.investigating_title))
            .setContentText(getString(R.string.investigating_text))
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setOngoing(true)
            .build()
        if (Build.VERSION.SDK_INT >= 29) {
            ServiceCompat.startForeground(
                this, 1, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC,
            )
        } else {
            @Suppress("DEPRECATION")
            startForeground(1, notification)
        }
        RunState.set(RunState.Status.Running("episode_tick", Instant.now()))
        scope.launch {
            try {
                PythonWhaCore(this@InvestigationService).runEpisodeTick()
            } finally {
                RunState.set(RunState.Status.Idle)
                stopSelf(startId)
            }
        }
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    companion object {
        private const val EXTRA_SUBJECT = "subject"

        fun start(context: Context, subject: String) {
            val intent = Intent(context, InvestigationService::class.java)
                .putExtra(EXTRA_SUBJECT, subject)
            androidx.core.content.ContextCompat.startForegroundService(context, intent)
        }
    }
}
