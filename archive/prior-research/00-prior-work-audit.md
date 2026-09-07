# 00. Audit of the Archived Prior Work

**Status:** Phase 1 output. Read this before reusing anything from `archive/2026-08-30-prior-generation/`.
**Date:** 2026-08-30

The archived material is eight documents totalling roughly 180 KB, produced in an earlier session by a lower-capability model. It is a genuinely useful list of leads. It is not a source of facts. This document separates the two and records the specific defects, so that the same errors are not inherited.

---

## 1. What is worth keeping (as leads to verify, not as facts)

The archived work correctly surfaced several things that a Phase 2 search would otherwise have to rediscover. Each of these is a **pointer to check**, not a finding:

- The names of the major academic wearable-illness cohorts and the commercial products in the space.
- The observation that nocturnal, sleep-window measurement has better signal-to-noise than daytime measurement.
- The observation that personalized rolling baselines are mandatory and population thresholds are invalid.
- The observation that deterministic statistical detectors are competitive with, and sometimes better than, complex learned models on this data.
- The observation that language models should not do arithmetic on sensor data.
- The observation that language model invocation should be gated by a cheap statistical trigger rather than polled.
- The identification of confounder disambiguation as an open failure mode of commercial products.
- The list of pip-installable time-series and biosignal packages, as candidates to test.

Several of these are sound engineering instincts. All of them still need a primary source before they appear in any deliverable.

---

## 2. Demonstrable errors found

These are not "unverified"; they are internally inconsistent or arithmetically wrong on the face of the documents.

### 2.1 Citation inconsistency (doc 05)

Mishra et al. 2020 is cited as *Nature Biomedical Engineering*, volume 4, pages 1208 to 1220, with DOI `10.1038/s41598-020-00640-6`. The `s41598` prefix belongs to *Scientific Reports*, not *Nature Biomedical Engineering* (which uses `s41551`).

**Verified in Phase 2:** the title, journal, volume and pages were all correct; only the DOI prefix was wrong. The correct DOI is `10.1038/s41551-020-00640-6`.

> **Correction to my original inference (added 2026-08-30).** I originally wrote that this error "demonstrates that identifiers in these documents were generated rather than retrieved, which means none of them can be trusted." **That inference was too strong and is refuted.** Phase 2 checked every suspicious arXiv identifier in the archive, including the 2026-dated ones I flagged as likely fabrications, against both the arXiv abstract pages and the arXiv Atom export API. **All of them resolve to real papers with the claimed titles.** See `findings/F3-health-llm-agents.md`.
>
> The accurate characterisation is narrower and more useful: **the archive's identifiers are mostly reliable; its numbers are not.** Phase 2 found the DOI prefix error above, one wrong venue attribution (AI on the Pulse is not CIKM 2025), and a long list of fabricated or badly distorted performance figures documented in section 3. Blanket distrust of the citations was the wrong call. Distrust of the quantities was correct and productive.

### 2.2 Ranking table contradicts its own scores (doc 07)

The strategic ranking matrix in doc 07 Part 3 sorts candidates by "Composite Score" but the sort is wrong. Candidate 6 is assigned a composite of 7.2 and placed at rank 8, below three candidates assigned 5.5 (ranks 5, 6 and 7). Either the composite or the rank is wrong; as written the table is self-contradictory.

### 2.3 Internal inconsistency on cadence (docs 06 and 01)

Doc 06 states as a firm empirical conclusion that intraday streaming produces roughly ten times the false-alarm rate of nocturnal rollup, and that nocturnal rollup is the correct design. The same document then specifies a real-time streaming replay server with 1x / 60x / 300x speed controls as deliverable number one, and doc 01's pivot questions present the choice as still open. The recommended architecture contradicts the recommendation that produced it.

This is resolved as decision gate G2 in doc 06 of the current work.

---

## 3. Unverified claims (treat every one as a hypothesis)

Every quantitative figure in the archive is unverified. This includes, non-exhaustively:

| Claim type | Examples appearing in the archive |
|---|---|
| Detector performance | 78 to 81 percent sensitivity, 3-day median lead time, 0.26 to 0.34 alerts per user-week, 82 to 90 percent sensitivity, 2.75-day lead time, AUC 0.80 |
| Model comparisons | "+22 percent F1 over 12 baselines", "25 to 30 percent relative gain over ReAct", "84 percent numerical accuracy versus under 40 percent zero-shot", "90 percent reduction in LLM cost" |
| Biomarker effect sizes | temperature rise of +0.5 to +1.5 C, RHR surge of +5 to +15 bpm, alcohol effect of +5 to +15 bpm, luteal phase +0.3 to +0.5 C, "adding temperature boosts AUC by 5 to 8 percent" |
| Behavioural claims | "greater than 70 percent survey attrition within 30 days", "greater than 60 percent abandonment from false alarms", "over 30 percent of wearable streams suffer artifacts" |
| Platform facts | API deprecation dates, rate limits, webhook latencies, access tiers |
| Model specifications | parameter counts, inference latencies, VRAM requirements, context lengths |
| Repository and package names | every GitHub path and pip package named in the archive |
| Paper identifiers | every arXiv ID and DOI, including several dated 2025 and 2026 |

Verification of the subset that actually matters is Track B.3 and Track C in doc 04. The subset that matters is small: the baseline operating points we intend to compare against, and the confounder effect sizes we intend to build the hypothesis set from. Everything else can simply be dropped rather than verified.

---

## 4. Method-level problems, which matter more than the factual ones

These are the reasons the archive's conclusion should not be adopted, independent of whether its numbers happen to be right.

### 4.1 It concluded before establishing that the data exists

The archive proceeds: formulate, survey, synthesize, rank candidates, recommend. At no point does it establish that a dataset exists containing the channels its recommended architecture consumes. Its chosen design fuses cardiac, thermal and respiratory signals; the cohort it names as the evaluation set may well contain only heart rate and step count. If so, the recommended system cannot be evaluated on the data it proposes to use, and the flagship "biophysical triad" is unimplementable.

Establishing the data reality first is Track A in doc 04, and it is the reason Track A precedes everything else.

### 4.2 The circularity problem is never raised

The recommended contribution is that active questioning reduces false alarms. The proposed evaluation is a benchmark with injected confounders. Nowhere does the archive note that injecting confounders into a simulator and then showing the system detects them is circular, nor does it propose a way out. This is the single sharpest objection to the whole project and it is absent.

Addressed as U2 in doc 02, item 7 in doc 05, and gate G7 in doc 06.

### 4.3 The scoring exercise is fake precision, and it rewards scope maximization

Doc 07 rates eight candidates on 1-to-10 subjective scales and averages four of them to one decimal place. Averaging self-assigned subjective scores does not produce a ranking; it produces the appearance of one. Worse, the structural outcome is predictable: the winning candidate is explicitly the one that contains all the others ("subsume the best capabilities of Candidates 2, 7 and the original baseline into Candidate 8"). A ranking method that selects the union of every option is not selecting; it is failing to select. In a two-week project, that is the most dangerous possible failure mode.

### 4.4 "Agentic" is asserted as a mechanism, not defined as a policy

The archive proposes a ReAct or CodeAct loop and treats that as satisfying the agentic requirement. A tool-calling loop is a mechanism. Without a stated objective for the ask/don't-ask decision, the resulting behaviour can be demonstrated but not measured, and the criticism the archive itself anticipates ("ensure your questioning policy is backed by mathematical evaluation rather than hardcoded heuristics") is left unanswered by its own design.

Addressed as U8 in doc 02, item 16 in doc 05, and gate G4 in doc 06.

### 4.5 Evaluation metric pathology is not considered

The archive proposes sensitivity, specificity, F1 and AUC without engaging with the known problems in time-series anomaly detection evaluation, and without computing what those numbers imply at a realistic base rate. The base-rate arithmetic in doc 01 section 1.3 changes the entire framing of the project and was never done.

Addressed as U12 in doc 02 and Track B in doc 04.

### 4.6 Patterns are transplanted across the boundary where they were justified

The code-generation-over-dataframes pattern is adopted because a cited system uses it. That system answers arbitrary open-ended questions over arbitrary personal data, which is why it needs code generation. Our monitoring loop computes a fixed, small set of quantities. The justification does not transfer, and the archive does not notice.

Addressed as U14 in doc 02, item 17 in doc 05, and gate G5 in doc 06.

### 4.7 No question was ever asked of the person doing the project

Nothing in the archive establishes the deliverable, the audience, the requirements, the available hours, the compute, the API budget, or whether the developer owns a wearable. The last of these is significant: an exported personal history with retrospective self-annotation is the only realistic route to confounder ground truth, and the archive dismissed personal hardware entirely on the grounds that live mobile ingestion is expensive, which conflates two different things.

Addressed in doc 07 of the current work.

---

## 5. Instruction for reuse

Anything drawn from the archive must satisfy one of the following before it enters a deliverable:

1. It has been re-verified at a primary source, and the source is recorded.
2. It has been re-derived by us from data we hold.
3. It is stated explicitly as an unverified claim from prior work, and nothing depends on it.

No third-hand figure appears in the final report under our name.
