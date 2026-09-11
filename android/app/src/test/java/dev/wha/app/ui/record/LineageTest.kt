package dev.wha.app.ui.record

import dev.wha.app.core.LineageEdge
import org.junit.Assert.assertEquals
import org.junit.Test

class LineageTest {
    private val edges = listOf(
        LineageEdge("features", "resting_hr_bpm", "baseline"),
        LineageEdge("features", "resting_hr_bpm", "subtract_explained"),
        LineageEdge("baseline", "centre_bpm", "subtract_explained"),
        LineageEdge("subtract_explained", "residual_bpm", "detect"),
        LineageEdge("detect", "level", "safety_floor"),
    )

    @Test fun downstreamFollowsEveryConsumerTransitively() {
        assertEquals(
            setOf("baseline", "subtract_explained", "detect", "safety_floor"),
            Lineage(edges).downstream("features", "resting_hr_bpm"),
        )
    }

    @Test fun upstreamFollowsProducersOfWhatTheStepRead() {
        assertEquals(
            setOf("subtract_explained", "features", "baseline"),
            Lineage(edges).upstream("detect", "residual_bpm"),
        )
    }
}
