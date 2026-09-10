"""Where a host process hands the index an embedder it cannot construct itself.

The phone has no sentence-transformers and no torch. It has the same bge-small model as
ONNX, run from Kotlin, and this is how that reaches ``build_index`` without the index
knowing anything about Android. Empty on the PC, where the default embedder is built as
before.
"""

from wha.retrieve.index import Embedder

_DEFAULT: Embedder | None = None


def set_default_embedder(embedder: Embedder | None) -> None:
    """Register the embedder every subsequently built index will use, or clear it."""
    global _DEFAULT
    _DEFAULT = embedder


def get_default_embedder() -> Embedder | None:
    return _DEFAULT
