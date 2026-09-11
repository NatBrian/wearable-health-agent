package dev.wha.app.embed

import java.io.File
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class WordPieceTokenizerTest {
    @Test fun matchesThePcTokenizerOnTheFixture() {
        val vocabJson = File("src/main/assets/embedder/tokenizer.json").readText()
        val tok = WordPieceTokenizer.fromTokenizerJson(vocabJson)
        val fixture = Json.parseToJsonElement(
            File("src/test/resources/tokenizer_fixture.json").readText(),
        ).jsonObject
        for ((sentence, ids) in fixture) {
            assertEquals(
                sentence,
                ids.jsonArray.map { it.jsonPrimitive.int },
                tok.encode(sentence),
            )
        }
    }
}
