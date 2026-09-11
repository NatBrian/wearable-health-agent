package dev.wha.app.ui.history

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import kotlin.math.abs

/** One night as the chart needs it. Null reading or band means not measured. */
data class NightSummary(
    val night_date: String,
    val rhr_bpm: Double?,
    val band_lo: Double?,
    val band_hi: Double?,
    val level: String,
    val usable: Boolean,
    val coverage_minutes: Int,
    val episode_id: String? = null,
    val deviation_bpm: Double? = null,
)

/** Positions for the night chart, in pixels, computed without any drawing. */
class NightChartGeometry(
    nights: List<NightSummary>,
    val plotWidthPx: Float,
    val plotHeightPx: Float,
) {
    val padding: Double = 2.0

    val yMin: Double
    val yMax: Double
    val xs: List<Float>
    val points: List<ChartPoint>

    init {
        val values = nights.flatMap { listOfNotNull(it.rhr_bpm, it.band_lo, it.band_hi) }
        if (values.isEmpty()) {
            yMin = 55.0 - padding
            yMax = 75.0 + padding
        } else {
            yMin = values.min() - padding
            yMax = values.max() + padding
        }
        xs = nights.indices.map { i ->
            if (nights.size == 1) {
                plotWidthPx / 2f
            } else {
                val margin = plotWidthPx * 0.06f
                margin + i * (plotWidthPx - 2 * margin) / (nights.size - 1)
            }
        }
        points = nights.mapIndexed { i, night ->
            ChartPoint(x = xs[i], y = night.rhr_bpm?.let { y(it) }, night = night)
        }
    }

    fun y(value: Double): Float {
        val span = yMax - yMin
        if (span <= 0) return plotHeightPx / 2f
        return (plotHeightPx - ((value - yMin) / span * plotHeightPx)).toFloat()
    }
}

data class ChartPoint(val x: Float, val y: Float?, val night: NightSummary)

/**
 * Status colours, shared with StatusWord. Amber and green differ under some colour
 * vision; every point also carries its word in the tooltip and the table, which is
 * the mitigation.
 */
object ChartColours {
    val green = Color(0xFF0CA30C)
    val amber = Color(0xFFFAB219)
    val red = Color(0xFFD03B3B)
    val band = Color(0xFF2F6F73)
    val muted = Color.Gray

    fun forLevel(level: String): Color = when (level) {
        "GREEN" -> green
        "YELLOW" -> amber
        "RED" -> red
        else -> muted
    }
}

fun levelWord(level: String): String = when (level) {
    "GREEN" -> "Usual"
    "YELLOW" -> "Raised"
    "RED" -> "High"
    else -> "Not measured"
}

/**
 * Resting heart rate over time against the person's own band. One axis; unmeasured
 * nights keep their slot and draw as open circles, because a dropped night reads
 * as a quiet one. Tap a point for its values; the tooltip offers the Record tab.
 */
@Composable
fun NightChart(
    nights: List<NightSummary>,
    onOpenRecord: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    var selected by remember { mutableStateOf<Int?>(null) }
    val surface = MaterialTheme.colorScheme.surface
    val onSurface = MaterialTheme.colorScheme.onSurface
    Column(modifier) {
        ChartLegend()
        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(240.dp)
                .pointerInput(nights) {
                    detectTapGestures { offset ->
                        selected = nearestPoint(nights, size.width.toFloat(), size.height.toFloat(), offset.x)
                    }
                },
        ) {
            val g = NightChartGeometry(nights, size.width, size.height)
            nights.forEachIndexed { i, night ->
                val lo = night.band_lo
                val hi = night.band_hi
                if (lo != null && hi != null) {
                    val left = if (i == 0) 0f else (g.xs[i] + g.xs[i - 1]) / 2f
                    val right = if (i == nights.lastIndex) size.width else (g.xs[i] + g.xs[i + 1]) / 2f
                    drawRect(
                        color = ChartColours.band.copy(alpha = 0.12f),
                        topLeft = Offset(left, g.y(hi)),
                        size = Size(right - left, g.y(lo) - g.y(hi)),
                    )
                }
            }
            val measured = g.points.filter { it.y != null }
            for (k in 0 until measured.size - 1) {
                drawLine(
                    color = onSurface,
                    start = Offset(measured[k].x, measured[k].y!!),
                    end = Offset(measured[k + 1].x, measured[k + 1].y!!),
                    strokeWidth = 2.dp.toPx(),
                )
            }
            g.points.forEachIndexed { i, point ->
                val color = ChartColours.forLevel(point.night.level)
                if (point.y == null) {
                    drawCircle(
                        color = ChartColours.muted,
                        radius = 8.dp.toPx(),
                        center = Offset(point.x, size.height / 2f),
                        style = Stroke(width = 2.dp.toPx()),
                    )
                } else {
                    val center = Offset(point.x, point.y)
                    drawCircle(color = surface, radius = 8.dp.toPx() + 2.dp.toPx(), center = center)
                    drawCircle(color = color, radius = 8.dp.toPx(), center = center)
                    if (selected == i) {
                        drawCircle(
                            color = color,
                            radius = 8.dp.toPx() + 5.dp.toPx(),
                            center = center,
                            style = Stroke(width = 2.dp.toPx()),
                        )
                    }
                }
            }
        }
        selected?.let { i ->
            val night = nights[i]
            Card(modifier = Modifier.fillMaxWidth().padding(top = 4.dp)) {
                Column(Modifier.padding(12.dp)) {
                    Text(night.night_date)
                    Text(
                        if (night.rhr_bpm != null) {
                            "Reading ${night.rhr_bpm}, usual ${night.band_lo} to ${night.band_hi}, ${levelWord(night.level)}."
                        } else {
                            "Not measured."
                        },
                    )
                    TextButton(onClick = { onOpenRecord(night.night_date) }) {
                        Text("Open in the record")
                    }
                }
            }
        }
    }
}

private fun nearestPoint(nights: List<NightSummary>, width: Float, height: Float, tapX: Float): Int? {
    if (nights.isEmpty()) return null
    val g = NightChartGeometry(nights, width, height)
    return g.xs.indices.minByOrNull { abs(g.xs[it] - tapX) }
}

@Composable
private fun ChartLegend() {
    Row(modifier = Modifier.padding(vertical = 4.dp)) {
        listOf("Usual", "Raised", "High", "Usual range", "Not measured").forEach { label ->
            Text(
                label,
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(end = 12.dp),
            )
        }
    }
}
