package dev.wha.app.ui.settings

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import dev.wha.app.corpus.CorpusFetch
import dev.wha.app.corpus.CorpusState
import dev.wha.app.embed.OnnxEmbedder
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.double
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

@Composable
fun DiagnosticsList(vm: SettingsViewModel) {
    val state by vm.state.collectAsState()
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var selfTest by remember { mutableStateOf<String?>(null) }
    val corpus by CorpusFetch.state.collectAsState()

    Column {
        state.doctor.forEach { row ->
            Text("${row.name}: ${row.status}. ${row.detail}", style = MaterialTheme.typography.bodySmall)
        }
        Row(Modifier.padding(top = 4.dp)) {
            Button(onClick = { vm.runJob("ingest") }) { Text("Run ingest now") }
            TextButton(onClick = { vm.runJob("nightly") }) { Text("Score nights now") }
            TextButton(onClick = { vm.runJob("episode_tick") }) { Text("Step episodes now") }
        }
        state.jobResult?.let { Text(it) }
        state.lastIngest?.let { Text("Last pull $it", style = MaterialTheme.typography.bodySmall) }
        Row(Modifier.padding(top = 4.dp)) {
            Button(onClick = {
                selfTest = "Running."
                scope.launch {
                    selfTest = withContext(Dispatchers.IO) { embedderSelfTest(context) }
                }
            }) { Text("Run the embedder self test") }
        }
        selfTest?.let { Text(it) }
        when (val c = corpus) {
            is CorpusState.Ready -> Text("General health information is on the phone.")
            is CorpusState.Fetching -> Text("General health information is downloading.")
            is CorpusState.Failed -> {
                Text("General health information could not be downloaded.")
                TextButton(onClick = { CorpusFetch.start(context) }) { Text("Try again") }
            }
            is CorpusState.Missing -> {
                Text("General health information is not on the phone yet.")
                TextButton(onClick = { CorpusFetch.start(context) }) { Text("Download now") }
            }
        }
    }
}

/**
 * The phone half of the agreement proof, on demand: embeds the agreement
 * sentences on the device and compares to the PC vectors in the fixture.
 */
private fun embedderSelfTest(context: android.content.Context): String {
    return try {
        val fixture = Json.parseToJsonElement(
            context.assets.open("embedder/embedder_fixture.json").bufferedReader().readText(),
        ).jsonObject
        val sentences = fixture["sentences"]!!.jsonArray.map { it.jsonPrimitive.content }
        val expected = fixture["vectors"]!!.jsonArray.map { row ->
            row.jsonArray.map { it.jsonPrimitive.double }
        }
        val flat = OnnxEmbedder(context).embed(sentences)
        val worst = sentences.indices.minOf { i ->
            val got = flat.slice(i * 384 until (i + 1) * 384).map { it.toDouble() }
            cosine(got, expected[i])
        }
        if (worst >= OnnxEmbedder.MIN_COSINE) {
            "The phone embeds as the computer does."
        } else {
            "The phone disagrees with the computer, so retrieval results cannot be trusted yet."
        }
    } catch (e: Exception) {
        "The self test could not run: ${e.message}"
    }
}

private fun cosine(a: List<Double>, b: List<Double>): Double {
    var dot = 0.0
    var na = 0.0
    var nb = 0.0
    a.indices.forEach { i ->
        dot += a[i] * b[i]
        na += a[i] * a[i]
        nb += b[i] * b[i]
    }
    if (na == 0.0 || nb == 0.0) return 0.0
    return dot / (Math.sqrt(na) * Math.sqrt(nb))
}
