package dev.wha.app.ui.record

import dev.wha.app.core.CanonicalSteps
import dev.wha.app.core.PipelineStepView
import kotlinx.serialization.json.JsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class GraphLayoutTest {
    private fun step(id: String, ordinal: Int, layer: String, status: String = "ran") =
        PipelineStepView(step_id = id, ordinal = ordinal, layer = layer, status = status, reason = "")

    @Test fun twentyOneStepsFallIntoFiveGroupsInOrder() {
        val steps = CanonicalSteps.all.map { step(it.id, it.ordinal, it.layer) }
        val nodes = GraphLayout.build(steps)
        assertEquals(21, nodes.size)
        assertEquals(
            listOf("Reading the watch", "Comparing with your normal", "What you have told us", "The investigation", "The safety rules on your words"),
            nodes.map { it.group }.distinct(),
        )
        assertTrue(nodes.zipWithNext().all { (a, b) -> a.ordinal < b.ordinal })
    }

    @Test fun aSkippedStepStaysInPlaceDimmed() {
        val steps = CanonicalSteps.all.map { step(it.id, it.ordinal, it.layer, if (it.id == "ask") "skipped" else "ran") }
        val ask = GraphLayout.build(steps).single { it.id == "ask" }
        assertTrue(ask.dimmed)
        assertEquals(14, ask.ordinal)
    }

    @Test fun layerMapsToTheFourMachineWords() {
        assertEquals("arithmetic", GraphLayout.machineWord("deterministic"))
        assertEquals("rule", GraphLayout.machineWord("safety"))
        assertEquals("model", GraphLayout.machineWord("agentic"))
        assertEquals("you", GraphLayout.machineWord("user"))
    }

    @Test fun aMissingStepStaysInPlaceDimmed() {
        val steps = CanonicalSteps.all
            .filter { it.id != "investigate" }
            .map { step(it.id, it.ordinal, it.layer) }
        val node = GraphLayout.build(steps).single { it.id == "investigate" }
        assertTrue(node.dimmed)
    }
}
