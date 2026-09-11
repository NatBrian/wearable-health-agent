package dev.wha.app.ui.record

import dev.wha.app.core.LineageEdge

/**
 * Walks the lineage the core declares. Upstream answers "where did what this
 * step read come from"; downstream answers "what read what this step wrote".
 * Recursion is gated on first visit, so the answer-to-investigate loop cannot
 * send the walk around forever.
 */
class Lineage(private val edges: List<LineageEdge>) {

    fun downstream(step: String, output: String): Set<String> {
        val found = mutableSetOf<String>()
        fun consume(from: String, out: String?) {
            edges.filter { it.from_step == from && (out == null || it.output == out) }
                .forEach { edge ->
                    if (found.add(edge.to_step)) consume(edge.to_step, null)
                }
        }
        consume(step, output)
        return found
    }

    fun upstream(step: String, output: String): Set<String> {
        val found = mutableSetOf<String>()
        fun produce(to: String, out: String?) {
            edges.filter { it.to_step == to && (out == null || it.output == out) }
                .forEach { edge ->
                    if (found.add(edge.from_step)) produce(edge.from_step, null)
                }
        }
        produce(step, output)
        return found
    }
}
