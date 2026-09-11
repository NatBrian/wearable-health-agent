package dev.wha.app

import android.app.Application
import dev.wha.app.notify.NotificationChannels

class WhaApp : Application() {
    override fun onCreate() {
        super.onCreate()
        NotificationChannels.ensure(this)
    }
}
