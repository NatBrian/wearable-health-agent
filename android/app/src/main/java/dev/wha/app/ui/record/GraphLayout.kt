package dev.wha.app.ui.record

import dev.wha.app.core.CanonicalSteps
import dev.wha.app.core.PipelineStepView

data class Node(
    val id: String,
    val ordinal: Int,
    val layer: String,
    val group: String,
    val dimmed: Boolean,
)

/**
 * The same twenty-one steps in the same five groups for every night. A step that
 * did not run stays in place dimmed with its reason; the frame never reshapes
 * around what happened.
 */
object GraphLayout {
    fun build(steps: List<PipelineStepView>): List<Node> {
        val byId = steps.associateBy { it.step_id }
        return CanonicalSteps.all.map { canonical ->
            val step = byId[canonical.id]
            Node(
                id = canonical.id,
                ordinal = canonical.ordinal,
                layer = canonical.layer,
                group = canonical.group,
                dimmed = step == null || (step.status != "ran" && step.status != "running"),
            )
        }
    }

    /** The four machine words the Provenance chips show. */
    fun machineWord(layer: String): String = when (layer) {
        "deterministic" -> "arithmetic"
        "safety" -> "rule"
        "agentic" -> "model"
        "user" -> "you"
        else -> layer
    }
}
