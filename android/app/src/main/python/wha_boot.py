"""What Kotlin calls once, after Python starts and before anything else.

Registers the phone's notification sink and embedder, then returns the facade module.
Everything else on the phone goes through wha_android.facade.

Either argument may be None: the sink arrives with Task 15 (notifications) and the
embedder with Task 16 (ONNX). Until then the core runs without them, exactly as the PC
does with no sink registered and the default embedder.
"""

from __future__ import annotations

from typing import Any


def boot(notify_sink: Any, embedder: Any) -> Any:
    if notify_sink is not None:
        from wha.notify import android as android_notify

        android_notify.set_sink(lambda payload: bool(notify_sink.deliver(payload)))
    if embedder is not None:
        from wha.retrieve import embedder_registry

        embedder_registry.set_default_embedder(_KotlinEmbedder(embedder))

    from wha_android import facade

    return facade


class _KotlinEmbedder:
    """Adapts the Kotlin ONNX embedder to the Embedder protocol."""

    def __init__(self, kotlin_embedder: Any) -> None:
        self._k = kotlin_embedder

    def embed_texts(self, texts: list[str]) -> Any:
        import numpy as np

        if not texts:
            return np.empty((0, 384), dtype=np.float32)
        flat = self._k.embed(list(texts))          # FloatArray, row-major N x 384
        arr = np.asarray(list(flat), dtype=np.float32).reshape(len(texts), 384)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        return arr / np.where(norms == 0, 1.0, norms)
