package dev.wha.app.jobs

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** WorkManager survives reboot for periodic work, but re-enqueueing keeps it explicit. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            Jobs.enqueueAll(context)
        }
    }
}
