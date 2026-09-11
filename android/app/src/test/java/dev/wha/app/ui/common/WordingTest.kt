package dev.wha.app.ui.common

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class WordingTest {
    private val wording = mapOf(
        "level.RED" to "Your sleeping heart rate was clearly above your usual range.",
        "level.immature_note" to "Your own range is still being learned.",
    )

    @Test fun aMatureRungKeepsYourUsualRange() {
        assertEquals(
            "Your sleeping heart rate was clearly above your usual range.",
            Wording.level("RED", "SHRINKING", wording),
        )
    }

    @Test fun anImmatureRungQualifiesTheRange() {
        val out = Wording.level("RED", "COLD", wording)
        assertTrue("the usual range for an adult" in out)
        assertTrue("still being learned" in out)
    }
}
