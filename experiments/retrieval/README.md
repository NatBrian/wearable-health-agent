# Retrieval: sixteen configurations of a reranker

**An engineering comparison of our own search against itself. Not evidence of anything
clinical.**

A cross-encoder reranker was tried across sixteen configurations of model, candidate depth
and scoring. None improved on plain hybrid retrieval on our own corpus and our own queries,
so it was not adopted.

That is a fact about this codebase and this corpus on one afternoon. It is not a finding
about rerankers, and it is not a finding about anybody's health.

## The numbers, and how to get them again

`sweep-results.txt` holds all sixteen rows with the baseline above them. It lived in
`tools/` until 7 September 2026, which was a miss in the claims cleanup: a table this
project scored itself against belongs behind the disclaimer, not beside the code.

```bash
uv run python tools/rerank_sweep.py     # writes sweep-results.txt, downloads 1.1 GB of weights
```

The script stays in `tools/` because it imports the judged query set from
`tools/retrieval_check.py`, which is the live retrieval check and is not an experiment. It
writes here rather than beside itself, on purpose.
