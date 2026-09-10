"""Export BAAI/bge-small-en-v1.5 to ONNX for the phone, with its tokenizer.

Runs on the PC (`uv run python tools/export_embedder_onnx.py`). Produces
android/app/src/main/assets/embedder/{model.onnx,tokenizer.json,EXPORT.md}. The agreement
test in tests/unit/retrieve/test_onnx_agreement.py proves the export matches the
sentence-transformers model on the PC; Task 16 proves the same on the phone.

Needs `optimum[exporters]` and `onnxruntime`, installed ad hoc:
    uv run --with "optimum[exporters]<2" --with onnxruntime --with "torch>=2.1,<2.5" python tools/export_embedder_onnx.py
The upper bound is load-bearing: optimum 2.x removed the `exporters` extra, so an
unbounded spec resolves to 2.x and the export entry point is missing. The torch bound
is load-bearing too: optimum 1.x imports a symbol newer torch removed from
torch.onnx.symbolic_opset14.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

MODEL = "BAAI/bge-small-en-v1.5"
OUT = Path("android/app/src/main/assets/embedder")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    work = Path("data/embedder-export")
    work.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "optimum.exporters.onnx", "--model", MODEL, "--task",
         "feature-extraction", "--opset", "17", str(work)],
        check=True,
    )
    (OUT / "model.onnx").write_bytes((work / "model.onnx").read_bytes())
    (OUT / "tokenizer.json").write_bytes((work / "tokenizer.json").read_bytes())
    digest = hashlib.sha256((OUT / "model.onnx").read_bytes()).hexdigest()
    (OUT / "EXPORT.md").write_text(
        f"# Embedder export\n\nModel: {MODEL}\nExported: {datetime.now(UTC).isoformat()}\n"
        f"Opset: 17\nmodel.onnx sha256: {digest}\n\nPooling: CLS token, then L2 normalise, "
        "which is what sentence-transformers does for this model.\n",
        encoding="utf-8",
    )
    print(OUT / "model.onnx", digest)


if __name__ == "__main__":
    main()
