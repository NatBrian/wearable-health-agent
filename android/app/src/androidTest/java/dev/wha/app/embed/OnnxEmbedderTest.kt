package dev.wha.app.embed

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.double
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/**
 * The phone half of the agreement proof: embeds the agreement sentences on the
 * device and compares to PC vectors. Runs on the phone with
 * ./gradlew connectedDebugAndroidTest, or the same check from the Settings
 * self-test row; both compare against the same MIN_COSINE as the PC test.
 */
@RunWith(AndroidJUnit4::class)
class OnnxEmbedderTest {
    @Test fun onDeviceVectorsAgreeWithThePc() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val stream = requireNotNull(
            javaClass.getResourceAsStream("/embedder_fixture.json"),
        ) { "embedder_fixture.json missing from androidTest resources" }
        val fixture = Json.parseToJsonElement(stream.bufferedReader().readText()).jsonObject
        val sentences = fixture["sentences"]!!.jsonArray.map { it.jsonPrimitive.content }
        val expected = fixture["vectors"]!!.jsonArray.map { row ->
            row.jsonArray.map { it.jsonPrimitive.double }
        }
        val flat = OnnxEmbedder(context).embed(sentences)
        sentences.indices.forEach { i ->
            val got = flat.slice(i * 384 until (i + 1) * 384).map { it.toDouble() }
            val cosine = cosine(got, expected[i])
            assertTrue("sentence $i cosine $cosine below floor", cosine >= OnnxEmbedder.MIN_COSINE)
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
        return dot / (Math.sqrt(na) * Math.sqrt(nb))
    }
}
