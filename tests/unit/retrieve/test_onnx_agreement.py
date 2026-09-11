"""The phone embeds with ONNX; the PC with sentence-transformers. If they disagree, phone
retrieval silently ranks different passages. This pins them together.

Skipped when onnxruntime is not installed, which is the normal PC state; run it with
    uv run --with onnxruntime --with tokenizers pytest tests/unit/retrieve/test_onnx_agreement.py
whenever the export changes.
"""

from pathlib import Path

import numpy as np
import pytest

onnxruntime = pytest.importorskip("onnxruntime")
tokenizers = pytest.importorskip("tokenizers")

ASSETS = Path("android/app/src/main/assets/embedder")
SENTENCES = [
    "A fever is a body temperature above normal.",
    "Resting heart rate rises during infection.",
    "Alcohol in the evening can raise overnight heart rate.",
]
# Cosine agreement floor. int8 quantisation of a small BERT costs a little; below this
# the phone would rank passages differently from the PC. Recorded with the export.
MIN_COSINE = 0.98


def _onnx_embed(texts: list[str]) -> np.ndarray:
    tok = tokenizers.Tokenizer.from_file(str(ASSETS / "tokenizer.json"))
    tok.enable_padding()
    tok.enable_truncation(max_length=512)
    enc = tok.encode_batch(texts)
    ids = np.array([e.ids for e in enc], dtype=np.int64)
    mask = np.array([e.attention_mask for e in enc], dtype=np.int64)
    types = np.zeros_like(ids)
    sess = onnxruntime.InferenceSession(str(ASSETS / "model.onnx"))
    names = {i.name for i in sess.get_inputs()}
    feed = {"input_ids": ids, "attention_mask": mask}
    if "token_type_ids" in names:
        feed["token_type_ids"] = types
    out = sess.run(None, feed)[0]  # (N, T, 384) last hidden state
    cls = out[:, 0, :]
    return cls / np.linalg.norm(cls, axis=1, keepdims=True)


def test_onnx_matches_sentence_transformers() -> None:
    from wha.retrieve.index import DefaultSentenceTransformerEmbedder

    reference = DefaultSentenceTransformerEmbedder().embed_texts(SENTENCES)
    candidate = _onnx_embed(SENTENCES)
    cosines = np.sum(reference * candidate, axis=1)
    assert cosines.min() >= MIN_COSINE, f"cosine agreement per sentence: {cosines}"
