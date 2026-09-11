"""Writes the fixtures the Kotlin tokenizer and embedder tests compare against.

- android/app/src/test/resources/tokenizer_fixture.json: sentences and the ids
  the PC tokenizer produces for them, so the Kotlin tokenizer can be tested
  for equality.
- android/app/src/androidTest/resources/embedder_fixture.json: the same
  agreement sentences plus the PC's normalised CLS vectors, so the phone can
  measure cosine agreement on-device rather than assume it.

Run whenever the export in android/app/src/main/assets/embedder changes.
"""

import json
from pathlib import Path

from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "android/app/src/main/assets/embedder"

TOKENIZER_SENTENCES = [
    "A fever is a body temperature above normal.",
    "Resting heart rate rises during infection.",
    "Alcohol in the evening can raise overnight heart rate.",
    "Dizziness, nausea and vomiting since yesterday",
]

EMBEDDER_SENTENCES = [
    "A fever is a body temperature above normal.",
    "Resting heart rate rises during infection.",
    "Alcohol in the evening can raise overnight heart rate.",
]


def main() -> None:
    tok = Tokenizer.from_file(str(ASSETS / "tokenizer.json"))
    test_dir = ROOT / "android/app/src/test/resources"
    test_dir.mkdir(parents=True, exist_ok=True)
    fixture = {s: tok.encode(s).ids for s in TOKENIZER_SENTENCES}
    (test_dir / "tokenizer_fixture.json").write_text(
        json.dumps(fixture, indent=1), encoding="utf-8"
    )

    import numpy as np
    import onnxruntime

    tok.enable_padding()
    tok.enable_truncation(max_length=512)
    enc = tok.encode_batch(EMBEDDER_SENTENCES)
    ids = np.array([e.ids for e in enc], dtype=np.int64)
    mask = np.array([e.attention_mask for e in enc], dtype=np.int64)
    sess = onnxruntime.InferenceSession(str(ASSETS / "model.onnx"))
    names = {i.name for i in sess.get_inputs()}
    feed = {"input_ids": ids, "attention_mask": mask}
    if "token_type_ids" in names:
        feed["token_type_ids"] = np.zeros_like(ids)
    out = sess.run(None, feed)[0]
    cls = out[:, 0, :]
    cls = cls / np.linalg.norm(cls, axis=1, keepdims=True)
    android_test_dir = ROOT / "android/app/src/androidTest/resources"
    android_test_dir.mkdir(parents=True, exist_ok=True)
    (android_test_dir / "embedder_fixture.json").write_text(
        json.dumps(
            {"sentences": EMBEDDER_SENTENCES, "vectors": cls.tolist()},
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"wrote tokenizer fixture ({len(fixture)} sentences) and embedder fixture")


if __name__ == "__main__":
    main()
