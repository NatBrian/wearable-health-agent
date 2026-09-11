package dev.wha.app.notify

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context

/** The two channels the system notifies on. Questions here, escalations urgent. */
object NotificationChannels {
    const val QUESTIONS = "questions"
    const val URGENT = "urgent"
    const val ONGOING = "ongoing"

    fun ensure(context: Context) {
        // String-based lookup rather than getSystemService(Class): it exists on
        // every API level and under Robolectric's test SDK alike.
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(
            NotificationChannel(QUESTIONS, "Questions", NotificationManager.IMPORTANCE_DEFAULT)
        )
        manager.createNotificationChannel(
            NotificationChannel(URGENT, "Urgent", NotificationManager.IMPORTANCE_HIGH)
        )
        manager.createNotificationChannel(
            NotificationChannel(ONGOING, "Working", NotificationManager.IMPORTANCE_LOW)
        )
    }
}
