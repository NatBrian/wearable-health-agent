"""Give the reranker its fairest shot before writing item 30 off.

Naive top-20 pure-cross-encoder reordering lost to the baseline for both models. Three
things could be doing that, and each is cheap to test:

  1. The passage text alone may not say what topic it is from. MedlinePlus chunks often
     read "It usually gets better on its own" with the topic name only in the title.
  2. Replacing the RRF order throws away BM25's exact term match, which on a small topical
     corpus is a strong signal. Fusing the two ranks keeps it.
  3. A deeper pool feeds the reranker more junk it can promote. 20 may be too deep.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from retrieval_check import JUDGED, relevant

from wha.constants import RETRIEVE_TOP_K, RRF_K
from wha.retrieve.knowledge_docs import get_default_index


def precision(rows):
    hits = total = 0
    for query, results in rows:
        for r in results:
            total += 1
            hits += bool(relevant(r.chunk_id, r.title, JUDGED[query]))
    return hits, total


# A single run takes over an hour on CPU, so every line is written and flushed as it is
# produced rather than at the end. An earlier run was killed by a timeout with the whole
# result set still sitting in a pipe buffer, and an hour of measurement was lost.
# UNDER experiments/, never beside the code. This is a number this project measured
# about itself, so it belongs behind the disclaimer in experiments/README.md. Moving
# the file without moving this line would put it back on the next run.
RESULTS = REPO / "experiments" / "retrieval" / "sweep-results.txt"
_LINES: list[str] = []


def say(line: str = "") -> None:
    print(line, flush=True)
    _LINES.append(line)
    RESULTS.write_text(chr(10).join(_LINES) + chr(10), encoding="utf-8")


def main() -> int:
    index = get_default_index()
    base_rows = [(q, index.query(q, top_k=RETRIEVE_TOP_K)) for q in JUDGED]
    bh, bt = precision(base_rows)
    say(f"baseline                                        {bh}/{bt} = {bh / bt:.1%}\n")

    pools = {depth: {q: index.query(q, top_k=depth) for q in JUDGED} for depth in (12, 20)}

    from sentence_transformers import CrossEncoder

    for name in ("cross-encoder/ms-marco-MiniLM-L-6-v2", "BAAI/bge-reranker-base"):
        model = CrossEncoder(name, max_length=512)
        say(name)
        for depth in (12, 20):
            for with_title in (False, True):
                for fuse in (False, True):
                    rows = []
                    t0 = time.perf_counter()
                    for q, pool in pools[depth].items():
                        pairs = [
                            (q, f"{r.title}. {r.heading}. {r.text}" if with_title else r.text)
                            for r in pool
                        ]
                        scores = model.predict(pairs, show_progress_bar=False)
                        ce_order = sorted(
                            range(len(pool)), key=lambda i: float(scores[i]), reverse=True
                        )
                        if fuse:
                            # RRF over the two rankings. The pool is already in RRF order,
                            # so its index IS its rank from the hybrid search.
                            ce_rank = {idx: rank for rank, idx in enumerate(ce_order, start=1)}
                            final = sorted(
                                range(len(pool)),
                                key=lambda i: 1.0 / (RRF_K + i + 1) + 1.0 / (RRF_K + ce_rank[i]),
                                reverse=True,
                            )
                        else:
                            final = ce_order
                        rows.append((q, [pool[i] for i in final[:RETRIEVE_TOP_K]]))
                    per_q = (time.perf_counter() - t0) / len(pools[depth]) * 1000
                    h, t = precision(rows)
                    tag = f"pool={depth} title={'y' if with_title else 'n'} fuse={'y' if fuse else 'n'}"
                    flag = "  WINS" if h > bh else ""
                    say(f"    {tag:<32} {h}/{t} = {h / t:5.1%}  {per_q:5.0f} ms/q{flag}")
        say()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
