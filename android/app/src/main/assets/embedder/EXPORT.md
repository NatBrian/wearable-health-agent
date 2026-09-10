# Embedder export

Model: BAAI/bge-small-en-v1.5
Exported: 2026-09-10
Opset: 17
model.onnx sha256: abf3da0c5bdf719df7b7b9ef80ca0d5f0ad9a446ac33aaad16b1ec68c2af920d

Pooling: CLS token, then L2 normalise, which is what sentence-transformers does for this model.

Quantised to int8 with onnxruntime dynamic quantisation: the fp32 export was 133 MB
and the phone ships the 34 MB int8 file as model.onnx. The agreement test
(tests/unit/retrieve/test_onnx_agreement.py, floor 0.98) passes on the quantised
model, so phone and PC retrieve the same passages.
