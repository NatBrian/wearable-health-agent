package dev.wha.app.ui.record

import dev.wha.app.core.CanonicalSteps
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class TopicCoverageTest {
    @Test fun everyCanonicalStepHasATopic() {
        val covered = Topics.all.flatMap { it.ordinals }.toSet()
        val real = CanonicalSteps.all.map { it.ordinal }.toSet()
        assertEquals(real, covered)
    }

    @Test fun stepLabelsReadLikeTheDashboard() {
        assertEquals("step 5", Topics.stepsLabel(listOf(5)))
        assertEquals("steps 1 to 4", Topics.stepsLabel(listOf(1, 2, 3, 4)))
        assertTrue("not a step" in Topics.stepsLabel(emptyList()))
    }
}
