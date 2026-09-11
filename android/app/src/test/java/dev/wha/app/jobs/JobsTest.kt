package dev.wha.app.jobs

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.work.WorkManager
import androidx.work.testing.WorkManagerTestInitHelper
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class JobsTest {
    @Test fun enqueueAllRegistersThreeUniquePeriodicJobs() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        WorkManagerTestInitHelper.initializeTestWorkManager(context)
        Jobs.enqueueAll(context)
        val wm = WorkManager.getInstance(context)
        val names = listOf("ingest", "nightly", "episode_tick").map { wm.getWorkInfosForUniqueWork(it).get().size }
        assertEquals(listOf(1, 1, 1), names)
    }

    @Test fun ingestIntervalMatchesThePcScheduler() {
        assertEquals(30L, Jobs.INGEST_MINUTES)
        assertEquals(15L, Jobs.TICK_MINUTES)
    }
}
