package dev.wha.app.notify

import android.app.Application
import android.app.Notification
import android.app.NotificationManager
import android.content.Context
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows
import org.robolectric.annotation.Config

// Channels need API 26 (the app's minSdk); pin the test SDK there or above so
// the test runs where the production code runs.
@Config(sdk = [33])
@RunWith(RobolectricTestRunner::class)
class NotificationSinkTest {
    private fun context(): Context = ApplicationProvider.getApplicationContext()

    @Test fun aQuestionPostsOneActionPerOptionPlusNotNow() {
        val context = context()
        Shadows.shadowOf(context as Application)
            .grantPermissions(android.Manifest.permission.POST_NOTIFICATIONS)
        NotificationChannels.ensure(context)
        val sink = NotificationSink(context)
        val ok = sink.deliver(
            mapOf(
                "kind" to "QUESTION",
                "text" to "Did you drink alcohol last night?",
                "interaction_id" to "int-1",
                "probe_id" to "alcohol",
                "recipient_id" to "me",
                "options" to listOf(
                    mapOf("option_id" to "yes", "label" to "Yes"),
                    mapOf("option_id" to "no", "label" to "No"),
                ),
                "url" to null,
            ),
        )
        assertTrue(ok)
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val shown = Shadows.shadowOf(manager).allNotifications
        assertEquals(1, shown.size)
        assertEquals(listOf("Yes", "No", "Not now"), shown[0].actions.map { it.title.toString() })
        assertEquals("questions", shown[0].channelId)
    }

    @Test fun anEscalationUsesTheUrgentChannelAndIsOngoing() {        val context = context()
        Shadows.shadowOf(context as Application)
            .grantPermissions(android.Manifest.permission.POST_NOTIFICATIONS)
        NotificationChannels.ensure(context)
        NotificationSink(context).deliver(
            mapOf(
                "kind" to "ESCALATION",
                "text" to "See a clinician today.",
                "interaction_id" to null,
                "probe_id" to null,
                "recipient_id" to "me",
                "options" to emptyList<Any>(),
                "url" to null,
            ),
        )
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val n = Shadows.shadowOf(manager).allNotifications.single()
        assertEquals("urgent", n.channelId)
        assertTrue(n.flags and Notification.FLAG_ONGOING_EVENT != 0)
    }

    @Test fun theJsonStringWhaBootSendsDeliversTheSame() {
        val context = context()
        Shadows.shadowOf(context as Application)
            .grantPermissions(android.Manifest.permission.POST_NOTIFICATIONS)
        NotificationChannels.ensure(context)
        val ok = NotificationSink(context).deliver(
            """{"kind":"QUESTION","text":"Did you drink alcohol last night?","interaction_id":"int-1","probe_id":"alcohol","recipient_id":"me","options":[{"option_id":"yes","label":"Yes"}],"url":null}""",
        )
        assertTrue(ok)
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val shown = Shadows.shadowOf(manager).allNotifications
        assertEquals(1, shown.size)
        assertEquals(listOf("Yes", "Not now"), shown[0].actions.map { it.title.toString() })
    }
}
