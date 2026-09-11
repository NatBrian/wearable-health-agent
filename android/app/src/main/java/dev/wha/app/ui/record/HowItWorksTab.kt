package dev.wha.app.ui.record

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonPrimitive

/** One topic and the pipeline ordinals it explains. Titles come from wording at render time. */
data class Topic(val number: Int, val ordinals: List<Int>)

/**
 * The same machinery as the graph, grouped by topic. Mirrors TOPIC_STEPS in
 * src/wha/ui/components/how_it_works.py; tests/unit/android/test_topic_steps_match.py
 * fails if the two lists differ, and TopicCoverageTest fails if a canonical step
 * has no topic.
 */
object Topics {
    val all = listOf(
        Topic(1, listOf(1, 2, 3, 4)),
        Topic(2, listOf(5)),
        Topic(3, listOf(6, 7)),
        Topic(4, listOf(8)),
        Topic(5, listOf(9, 10, 11)),
        Topic(6, listOf(12)),
        Topic(7, listOf(13, 14, 15)),
        Topic(8, listOf(16, 17, 18, 19)),
        Topic(9, listOf(20, 21)),
        Topic(10, listOf()),
    )

    fun stepsLabel(ordinals: List<Int>): String {
        if (ordinals.isEmpty()) return "not a step: this is true of all of them"
        if (ordinals.size == 1) return "step ${ordinals[0]}"
        val runs = mutableListOf<String>()
        var start = ordinals[0]
        var previous = ordinals[0]
        for (value in ordinals.drop(1)) {
            if (value == previous + 1) {
                previous = value
                continue
            }
            runs.add(if (start == previous) "$start" else "$start to $previous")
            start = value
            previous = value
        }
        runs.add(if (start == previous) "$start" else "$start to $previous")
        return "steps ${runs.joinToString(", ")}"
    }
}

/**
 * Fills the shared topic body with figures from the running config. Same keys,
 * same values as topic_body in how_it_works.py (device "this phone", surface
 * "this app"); every figure comes from data, never from prose.
 */
fun topicBody(
    n: Int,
    wording: Map<String, String>,
    config: Map<String, JsonElement>,
    toolNames: List<String>,
    assumed: Int,
    rows: Int,
): String {
    fun num(key: String): Int = (config[key] as? JsonPrimitive)?.content?.toDoubleOrNull()?.toInt() ?: 0
    fun raw(key: String): String = (config[key] as? JsonPrimitive)?.content ?: ""
    val nCauses = num("N_CAUSES")
    return (wording["topic.$n.body"] ?: "")
        .replace("{MIN_NOCTURNAL_MINUTES}", raw("MIN_NOCTURNAL_MINUTES"))
        .replace("{HR_PLAUSIBLE_MIN_BPM}", raw("HR_PLAUSIBLE_MIN_BPM"))
        .replace("{HR_PLAUSIBLE_MAX_BPM}", raw("HR_PLAUSIBLE_MAX_BPM"))
        .replace("{RUNG_COLD_MAX_NIGHTS}", raw("RUNG_COLD_MAX_NIGHTS"))
        .replace("{COLD_MAX_PLUS_ONE}", "${num("RUNG_COLD_MAX_NIGHTS") + 1}")
        .replace("{RUNG_PRIOR_MAX_NIGHTS}", raw("RUNG_PRIOR_MAX_NIGHTS"))
        .replace("{PRIOR_MAX_PLUS_ONE}", "${num("RUNG_PRIOR_MAX_NIGHTS") + 1}")
        .replace("{RUNG_SHRINKING_MAX_NIGHTS}", raw("RUNG_SHRINKING_MAX_NIGHTS"))
        .replace("{SHRINKING_MAX_PLUS_ONE}", "${num("RUNG_SHRINKING_MAX_NIGHTS") + 1}")
        .replace("{RUNG_PERSONAL_MAX_NIGHTS}", raw("RUNG_PERSONAL_MAX_NIGHTS"))
        .replace("{PERSONAL_MAX_PLUS_ONE}", "${num("RUNG_PERSONAL_MAX_NIGHTS") + 1}")
        .replace("{BASELINE_SCALE_FLOOR_BPM}", raw("BASELINE_SCALE_FLOOR_BPM"))
        .replace("{DETECT_YELLOW_BPM}", raw("DETECT_YELLOW_BPM"))
        .replace("{DETECT_RED_BPM}", raw("DETECT_RED_BPM"))
        .replace("{DETECT_PERSISTENCE_NIGHTS}", raw("DETECT_PERSISTENCE_NIGHTS"))
        .replace("{SYMPTOM_RUN_GAP_DAYS}", raw("SYMPTOM_RUN_GAP_DAYS"))
        .replace("{SYMPTOM_COOCCURRENCE_WINDOW_NIGHTS}", raw("SYMPTOM_COOCCURRENCE_WINDOW_NIGHTS"))
        .replace("{BASELINE_MIN_NIGHTS_PERSONAL}", raw("BASELINE_MIN_NIGHTS_PERSONAL"))
        .replace("{TOOL_COUNT}", "${toolNames.size}")
        .replace("{TOOLS}", toolNames.joinToString("\n") { "- $it" })
        .replace("{N_CAUSES}", "$nCauses")
        .replace("{N_CAUSES_POWER}", "%,d".format(java.util.Locale.US, 1 shl nCauses))
        .replace("{INTERRUPTION_BUDGET_PER_WEEK}", raw("INTERRUPTION_BUDGET_PER_WEEK"))
        .replace("{ASSUMED_COUNT}", "$assumed")
        .replace("{ROW_COUNT}", "$rows")
        .replace("{DEVICE}", "this phone")
        .replace("{SURFACE}", "this app")
}

@Composable
fun HowItWorksTab(
    wording: Map<String, String>,
    config: Map<String, JsonElement>,
    toolNames: List<String>,
    safetyRows: List<Map<String, String>>,
) {
    val assumed = safetyRows.count { it["provenance"] == "ASSUMED" }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
        Topics.all.forEach { topic ->
            var expanded by remember { mutableStateOf(false) }
            val title = wording["topic.${topic.number}.title"] ?: ""
            TextButton(onClick = { expanded = !expanded }) {
                Text("$title (${Topics.stepsLabel(topic.ordinals)})")
            }
            if (expanded) {
                Text(
                    topicBody(topic.number, wording, config, toolNames, assumed, safetyRows.size),
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.padding(horizontal = 8.dp),
                )
                if (topic.number == 9) {
                    safetyRows.forEach { row ->
                        Text(
                            "${row["rule"]}: ${row["number"]} (${provenanceWords(row["provenance"])})",
                            style = MaterialTheme.typography.bodySmall,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                        )
                    }
                }
            }
        }
    }
}

private fun provenanceWords(provenance: String?): String = when (provenance) {
    "ASSUMED" -> "no published source found"
    "DERIVED" -> "worked out from other figures here"
    else -> "a published study"
}
