package dev.wha.app.ui.settings

import android.content.res.Resources
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import dev.wha.app.R

data class Disclosure(val limitation: String, val shownOn: String)

/**
 * The entries in docs/DISCLOSURES.md that name a phone screen, shipped as an
 * asset by the build so the file stays the single source. A row counts when its
 * "Shown on" names one of the five tabs and says it is the phone: dashboard rows
 * that happen to share a tab name stay out.
 */
fun loadDisclosures(resources: Resources): List<Disclosure> {
    val screens = listOf("Today", "Record", "Settings", "History", "Investigation")
    val text = try {
        resources.openRawResource(R.raw.disclosures).bufferedReader().readText()
    } catch (e: Exception) {
        return emptyList()
    }
    return text.lines().mapNotNull { line ->
        val trimmed = line.trim()
        if (!trimmed.startsWith("|") || "---" in trimmed) return@mapNotNull null
        val columns = trimmed.split("|").map { it.trim() }
        if (columns.size < 4) return@mapNotNull null
        val limitation = columns[1]
        if (limitation.equals("Limitation", ignoreCase = true)) return@mapNotNull null
        val shownOn = columns[3]
        if (screens.none { shownOn.contains(it) }) return@mapNotNull null
        if (!shownOn.contains("phone") && !shownOn.contains("Android")) return@mapNotNull null
        Disclosure(limitation, shownOn)
    }
}

@Composable
fun DisclosuresList(resources: android.content.res.Resources) {
    val entries = remember { loadDisclosures(resources) }
    Column {
        entries.forEach { entry ->
            Column(Modifier.padding(vertical = 4.dp)) {
                Text(entry.limitation, style = MaterialTheme.typography.bodyMedium)
                Text(entry.shownOn, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
