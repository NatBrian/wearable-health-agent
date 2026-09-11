package dev.wha.app.embed

import org.json.JSONObject
import java.text.Normalizer

/**
 * WordPiece from the vocab in the exported tokenizer.json, matching the BERT
 * normalizer plus pre-tokenizer the PC uses (lowercase, strip accents, split on
 * whitespace and punctuation, greedy longest-match with ## continuation).
 */
class WordPieceTokenizer private constructor(
    private val vocab: Map<String, Int>,
    private val lowercase: Boolean,
    private val unkToken: String = "[UNK]",
) {
    fun encode(sentence: String): List<Int> {
        val normalized = normalize(sentence)
        val tokens = mutableListOf<Int>()
        tokens.add(vocab.getValue("[CLS]"))
        for (word in split(normalized)) {
            if (word.isEmpty()) continue
            var start = 0
            val pieces = mutableListOf<Int>()
            var failed = false
            while (start < word.length) {
                var end = word.length
                var found: Int? = null
                while (end > start) {
                    val piece = (if (start == 0) "" else "##") + word.substring(start, end)
                    val id = vocab[piece]
                    if (id != null) {
                        found = id
                        break
                    }
                    end--
                }
                if (found == null) {
                    failed = true
                    break
                }
                pieces.add(found)
                start = end
            }
            if (failed) {
                tokens.add(vocab.getValue(unkToken))
            } else {
                tokens.addAll(pieces)
            }
            if (tokens.size >= MAX_LEN - 1) break
        }
        if (tokens.size > MAX_LEN - 1) return tokens.take(MAX_LEN - 1) + vocab.getValue("[SEP]")
        tokens.add(vocab.getValue("[SEP]"))
        return tokens
    }

    private fun normalize(sentence: String): String {
        var s = sentence
        // clean_text: drop controls, whitespace folds to a space.
        val cleaned = StringBuilder(s.length)
        for (ch in s) {
            when {
                ch == '\u0000' || ch == '\ufffd' || ch.category == CharCategory.CONTROL -> Unit
                ch.isWhitespace() -> cleaned.append(' ')
                else -> cleaned.append(ch)
            }
        }
        s = cleaned.toString()
        // handle_chinese_chars: space around every CJK codepoint.
        val spaced = StringBuilder(s.length + 8)
        for (ch in s) {
            if (isChinese(ch)) {
                spaced.append(' ').append(ch).append(' ')
            } else {
                spaced.append(ch)
            }
        }
        s = spaced.toString()
        if (lowercase) s = s.lowercase()
        // strip_accents (the export leaves it unset, which with lowercase means strip).
        s = Normalizer.normalize(s, Normalizer.Form.NFD)
        return s.filter { it.category != CharCategory.NON_SPACING_MARK }
    }

    private fun split(s: String): List<String> {
        // BertPreTokenizer: split on whitespace and punctuation, keeping punctuation.
        val out = mutableListOf<String>()
        val current = StringBuilder()
        fun flush() {
            if (current.isNotEmpty()) {
                out.add(current.toString())
                current.clear()
            }
        }
        for (ch in s) {
            when {
                ch.isWhitespace() -> flush()
                isPunctuation(ch) -> {
                    flush()
                    out.add(ch.toString())
                }
                else -> current.append(ch)
            }
        }
        flush()
        return out
    }

    private fun isPunctuation(ch: Char): Boolean {
        val type = Character.getType(ch).toByte()
        return type == Character.CONNECTOR_PUNCTUATION || type == Character.DASH_PUNCTUATION ||
            type == Character.START_PUNCTUATION || type == Character.END_PUNCTUATION ||
            type == Character.INITIAL_QUOTE_PUNCTUATION || type == Character.FINAL_QUOTE_PUNCTUATION ||
            type == Character.OTHER_PUNCTUATION || type == Character.MATH_SYMBOL ||
            type == Character.CURRENCY_SYMBOL || type == Character.MODIFIER_SYMBOL ||
            type == Character.OTHER_SYMBOL
    }

    private fun isChinese(ch: Char): Boolean {
        val code = ch.code
        return code in 0x4E00..0x9FFF || code in 0x3400..0x4DBF ||
            code in 0x20000..0x2A6DF || code in 0x2A700..0x2B73F ||
            code in 0x2B740..0x2B81F || code in 0x2B820..0x2CEAF ||
            code in 0xF900..0xFAFF || code in 0x2F800..0x2FA1F
    }

    companion object {
        const val MAX_LEN = 512

        fun fromTokenizerJson(json: String): WordPieceTokenizer {
            val root = JSONObject(json)
            val vocabJson = root.getJSONObject("model").getJSONObject("vocab")
            val vocab = mutableMapOf<String, Int>()
            val keys = vocabJson.keys()
            while (keys.hasNext()) {
                val k = keys.next()
                vocab[k] = vocabJson.getInt(k)
            }
            val normalizer = root.optJSONObject("normalizer")
            val lowercase = normalizer?.optBoolean("lowercase", true) ?: true
            return WordPieceTokenizer(vocab, lowercase)
        }
    }
}
