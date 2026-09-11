package dev.wha.app.ui.history

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class NightChartGeometryTest {
    private val nights = listOf(
        NightSummary(night_date = "2026-09-01", rhr_bpm = 60.0, band_lo = 57.0, band_hi = 63.0, level = "GREEN", usable = true, coverage_minutes = 400),
        NightSummary(night_date = "2026-09-02", rhr_bpm = 70.0, band_lo = 57.0, band_hi = 63.0, level = "RED", usable = true, coverage_minutes = 380),
        NightSummary(night_date = "2026-09-03", rhr_bpm = null, band_lo = null, band_hi = null, level = "NA", usable = false, coverage_minutes = 0),
    )

    @Test fun yScaleMapsBandAndPointsIntoThePlotArea() {
        val g = NightChartGeometry(nights, plotHeightPx = 200f, plotWidthPx = 300f)
        assertTrue(g.y(70.0) < g.y(60.0))
        assertEquals(3, g.xs.size)
        assertTrue(g.yMin <= 57.0 - g.padding && g.yMax >= 70.0 + g.padding)
        assertNull(g.points[2].y)
    }
}
