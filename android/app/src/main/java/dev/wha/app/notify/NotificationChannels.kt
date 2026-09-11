package dev.wha.app.notify

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context

/** The two channels the system notifies on. Questions here, escalations urgent. */
object NotificationChannels {
    const val QUESTIONS = "questions"
    const val URGENT = "urgent"

    fun ensure(context: Context) {
        val manager = context.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(QUESTIONS, "Questions", NotificationManager.IMPORTANCE_DEFAULT)
        )
        manager.createNotificationChannel(
            NotificationChannel(URGENT, "Urgent", NotificationManager.IMPORTANCE_HIGH)
        )
    }
}
