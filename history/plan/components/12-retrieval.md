# Component 12. Retrieval

**Phase:** B. **Module:** `src/wha/retrieve/`. **Depends on:** `data/knowledge/corpus.yaml`.

A small curated corpus, hybrid search, and **claim-to-source enforcement that is a deterministic
string test, not a judgement**.

---

## 1. Why the corpus is small on purpose

Tens to low hundreds of documents. A small curated corpus with verifiable citations beats a large
uncurated one on every metric this project is measured on, and it is far easier to demonstrate
working.

**The corpus is not where the value is. The `sources` field in the audit log is.** Being able to
point at the passage behind a claim is the deliverable; having a million documents is not.

---

## 2. Layers

Declared in `data/knowledge/corpus.yaml`, read-only, with licence stated per source.

| Layer | Source | Licence | Role |
|---|---|---|---|
| 1 | **MedlinePlus health topics**, bulk XML, roughly 29 MB, refreshed daily | Free, **attribution only** | The bulk layer. Consumer register, which matches a wellness tool's voice |
| 2 | **StatPearls** via NCBI Bookshelf, a selected subset | **CC BY-NC-ND 4.0** | Clinical depth. **Non-commercial and no-derivatives, stated in the report.** Fine for a research prototype, not for a product |
| 3 | **Singapore care pathways and dengue guidance**, hand-curated excerpts with source URLs | Attribution, quoted | Changes the differential and the recommendation |
| 4 | **The confounder evidence table**, generated from `causes.yaml` | Ours | Every effect size, retrievable and citable |

**Layer 3 is hand-curated rather than scraped.** Licensing for the relevant national sources could
not be verified programmatically, and bulk-ingesting content whose terms are unread is not
defensible in a public repository. A small set of quoted excerpts with source URLs and dates is.

**Layer 1 is not decoration.** General pretraining corpora represent Singapore MOH clinical guidance
sparsely and local documentation conventions barely at all. **The model does not know MOH
guidance.** That is the hard argument for the Singapore layer, and it is stronger than the relevance
argument in `history/PROPOSAL.md` 4.6.4.

---

## 3. Pipeline

```
fetch -> parse -> chunk -> index (BM25 + dense) -> query -> fuse -> filter -> return
```

**Chunking.** Section-aware, splitting on document structure, target `CHUNK_TARGET_TOKENS`, with
**parent-document retrieval**: match on the small chunk, return the enclosing section. Clinical
documents are already structured by heading, and retrieving a fragment that has lost its context is
the classic failure.

**Indexing.** Hybrid, both built at ingest and stored under `data/corpus_index/`:

- **BM25** via `rank_bm25`. Clinical text is full of exact terms (drug names, condition names,
  "Centor") where lexical match wins.
- **Dense** via `bge-small-en-v1.5`, CPU, embeddings in a numpy array with a chunk-id map. **No
  vector database.** At this corpus size a brute-force cosine over a few thousand vectors is
  microseconds, and a database would be a dependency bought for nothing.

**Fusion.** Reciprocal rank fusion, `score = sum over lists of 1 / (RRF_K + rank)`. Parameter-light,
and it needs no score normalisation between two incompatible scoring schemes.

**Filtering.** Metadata filters on layer, source authority, condition and geography, so the agent can
restrict to Singapore care pathways when forming a recommendation and to clinical reference when
forming a differential.

**Reranking is deliberately absent.** A cross-encoder would improve precision, but at tens of
documents hybrid plus fusion is already close to ceiling. Added complexity for a marginal gain, and
that judgement is stated rather than silently made.

---

## 4. Agentic retrieval

This is a tool the agent calls, with a query it constructs, at a moment it chooses. It is not a fixed
retrieve-then-generate stage.

The agent decides **whether** to retrieve at all (a deviation fully explained by a recorded workout
needs no clinical evidence), **what** to query, derived from the belief state rather than from the
subject's raw words, **when to re-query** after an answer changes the belief, and **which layer** to
query.

**"RETRIEVE not called: deviation fully explained by a recorded workout" is one of the most
convincing lines in the whole trace**, because it shows the system deciding rather than executing.

Every returned passage carries `source_id`, title, URI and retrieval score, which flow into
`sources_json` on the audit row and into `EpisodeOutcome.citations`.

---

## 5. Claim-to-source enforcement

```python
def enforce_grounding(claims: list[GeneratedClaim],
                      passages: list[Citation]) -> tuple[list[GeneratedClaim], int]
```

**Deterministic.** For each claim, `evidence_span` must appear **verbatim** in one of the retrieved
passages, after whitespace normalisation and case folding. That is a string containment test. It runs
in code and it cannot be talked out of.

A claim failing it gets `citation=None`, is **stripped before display**, and is counted in
`EpisodeOutcome.unsupported_claims`. That number appears on screen, because a zero there is a claim
about the system's honesty.

The LLM self-critique runs **after**, and may only strip more.

> Hallucination in *numbers* is prevented architecturally: every physiological figure comes from a
> deterministic tool return, never from generated text. Hallucination in *claims* is mitigated by
> this check plus the visible `sources` field. **They are different failure modes with different
> mechanisms**, and the write-up distinguishes them rather than conflating both into "we use RAG".

---

## 6. Corpus build

```bash
uv run wha data fetch corpus
```

Idempotent and resumable. Downloads, parses, chunks, embeds, writes both indexes and a manifest with
per-source licence, fetch date, document count and checksum.

**Unit tests never build the real corpus.** They use a tiny fixture corpus of about twenty chunks
committed under `tests/fixtures/corpus/`, which includes the poisoned `INJ-001` document used by
component 11.

Rebuild is required after any change to `corpus.yaml` or the chunking parameters, and the manifest
records which parameters produced the index so a stale one is detectable.

---

## 7. Evaluation

Reported in component 16:

- **Retrieval precision and recall** on a small hand-built question set with known relevant
  passages.
- **Unsupported-claim rate**, straight from the deterministic check. Target near zero for clinical
  facts.
- **Source and citation accuracy**: does the cited passage actually support the claim it is attached
  to? Sampled and human-audited, because this one cannot be automated honestly.

> If an LLM judge is used anywhere here, it must be a **different model family** from the one under
> evaluation, presentation order randomised, pointwise against a fixed rubric rather than pairwise,
> calibrated against a human-labelled subset, and **the human agreement rate reported alongside the
> score**. A judge score without an agreement number is not reported.

---

## 8. Edge cases

| Case | Behaviour |
|---|---|
| Empty query | `ok=True`, empty result, note. **Do not fabricate a query** |
| No passage above the score floor | Empty result. The agent must handle "found nothing", and the outcome says so rather than inventing support |
| Index missing | `ok=False`, note naming the build command. Not a crash |
| Index stale versus `corpus.yaml` | Warn in `wha doctor`, still usable |
| A chunk longer than the model's input | Truncate at embed time with a recorded marker |
| Duplicate passages across layers | Dedupe by content hash after fusion, keep the higher-authority source |
| A retrieved passage contains injection text | Returned as data, flagged by component 11, **not removed**, because removing it hides the attack from the trace |

---

## 9. Tests

`tests/unit/retrieve/`, against the fixture corpus. **No network, no model download**; the embedder
is stubbed with deterministic vectors.

| Test | Asserts |
|---|---|
| `test_chunking_is_section_aware` | A heading boundary is respected, not a fixed character split |
| `test_parent_document_returned` | Match on a chunk, receive the enclosing section |
| `test_bm25_finds_exact_term` | "Centor" retrieves the pharyngitis passage |
| `test_dense_finds_paraphrase` | A reworded query retrieves the right passage |
| `test_rrf_fusion_combines_both` | A passage ranked highly by one list only still surfaces |
| `test_layer_filter_restricts` | A Singapore-only query returns no MedlinePlus passages |
| `test_empty_query_returns_empty_not_fabricated` | |
| `test_no_match_returns_empty` | And the caller can express "found nothing" |
| `test_grounding_accepts_verbatim_span` | |
| `test_grounding_rejects_paraphrased_span` | A near-miss is stripped. **The check is verbatim on purpose** |
| `test_grounding_normalises_whitespace_and_case` | |
| `test_stripped_claims_are_counted` | `unsupported_claims` matches the strip count |
| `test_injected_passage_returned_as_data` | Present in results, flagged, not removed |
| `test_missing_index_returns_ok_false` | With the build command in the note |
| `test_duplicate_passages_deduped` | Higher-authority source kept |

---

## 10. Exit condition

```bash
uv run pytest tests/unit/retrieve -q
uv run wha data fetch corpus && uv run wha retrieve query "dengue warning signs" --layer sg
```

The second returns real passages with source ids and scores from the built index.
