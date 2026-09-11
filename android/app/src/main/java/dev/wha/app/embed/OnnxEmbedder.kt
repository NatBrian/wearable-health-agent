package dev.wha.app.embed

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import android.content.Context
import java.nio.LongBuffer

/** The same embedding model the PC retrieves with, run on the phone. CLS pooled; Python normalises. */
class OnnxEmbedder(context: Context) {
    private val appContext = context.applicationContext
    private val env: OrtEnvironment by lazy { OrtEnvironment.getEnvironment() }
    private val session by lazy {
        val bytes = appContext.assets.open("embedder/model.onnx").readBytes()
        env.createSession(bytes)
    }
    private val tokenizer by lazy {
        WordPieceTokenizer.fromTokenizerJson(
            appContext.assets.open("embedder/tokenizer.json").bufferedReader().readText(),
        )
    }

    /** Row-major N x 384, CLS pooled, L2 normalised in Python (wha_boot). */
    fun embed(texts: List<String>): FloatArray {
        val encoded = texts.map { tokenizer.encode(it) }
        val length = encoded.maxOf { it.size }
        val n = texts.size
        val ids = LongArray(n * length)
        val mask = LongArray(n * length)
        encoded.forEachIndexed { i, row ->
            row.forEachIndexed { j, id ->
                ids[i * length + j] = id.toLong()
                mask[i * length + j] = 1L
            }
        }
        val shape = longArrayOf(n.toLong(), length.toLong())
        val inputs = mutableMapOf(
            "input_ids" to OnnxTensor.createTensor(env, LongBuffer.wrap(ids), shape),
            "attention_mask" to OnnxTensor.createTensor(env, LongBuffer.wrap(mask), shape),
        )
        if ("token_type_ids" in session.inputNames) {
            inputs["token_type_ids"] = OnnxTensor.createTensor(env, LongBuffer.wrap(LongArray(n * length)), shape)
        }
        session.run(inputs).use { out ->
            @Suppress("UNCHECKED_CAST")
            val hidden = out[0].value as Array<Array<FloatArray>> // N x T x 384
            val result = FloatArray(n * 384)
            for (i in 0 until n) System.arraycopy(hidden[i][0], 0, result, i * 384, 384)
            return result
        }
    }

    companion object {
        /** Cosine agreement floor, the same MIN_COSINE the PC test pins (test_onnx_agreement.py). */
        const val MIN_COSINE = 0.98f
    }
}
