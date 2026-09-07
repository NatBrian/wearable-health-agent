# 06. Decision Gates: Questions Whose Answers Change the Architecture

**Status:** Phase 1 output. All gates OPEN. No positions taken.
**Date:** 2026-08-30

> **Update, same day.** Answers received from the developer (team project, an assessed course project plus personal tool plus portfolio, Samsung Galaxy Watch and WHOOP owned by team members, 90 to 110 hours per person, live real-time expected) constrain G1, G2, G7, G8 and G9. See [`08-confirmed-constraints.md`](08-confirmed-constraints.md). The gate board at the bottom of this file reflects those constraints. No gate is closed yet.

These are the forks where a different answer produces a materially different system, not a different setting. Each gate states the question, the live options, what each option implies, the evidence that closes it, and what it blocks while open.

Gates are ordered by dependency. G1 and G2 constrain almost everything below them.

---

## G1. Data foundation

**Question.** What does the system actually run on?

| Option | Implication if chosen |
|---|---|
| **A. Public cohort with illness labels** | Real detection metrics and lead times are reportable. Channels limited to whatever the cohort recorded. Confounder claims remain unevaluable on real data (see G7). |
| **B. The user's own exported history, retrospectively annotated** | Uniquely provides confounder labels, which no public dataset offers. N of 1, so no population claims. Depends entirely on whether the history exists and how deep it goes. |
| **C. Semi-synthetic: real baselines with injected episodes and confounders** | Full control over the evaluation, unlimited episodes, but exposed to the circularity objection (doc 05, item 7) unless carefully framed. |
| **D. Hybrid: A or B as the real-data anchor, C as the controlled policy benchmark** | Most likely to satisfy a skeptical reviewer, at the cost of building two evaluation paths. |

**Closed by:** Track A (all items), Track 0.2.
**Blocks while open:** the target condition, the feature set, every evaluation design, and G2 through G4.
**Note:** this is the highest-stakes gate in the project. Everything the prior work concluded rests on an unexamined answer to it.

---

## G2. Decision cadence

**Question.** What is one decision epoch?

| Option | Implication |
|---|---|
| **A. Nightly rollup** | Cleanest signal, matches how published systems operate, dramatically simpler infrastructure. "Real-time" becomes a replay presentation choice. |
| **B. Intraday, hourly or finer** | Genuinely real-time, but far more confounded by activity, meals, posture, and stress. Higher false-alarm load, and it may not be supported by the data's cadence at all. |
| **C. Nightly primary with an intraday safety-only channel** | Nightly for the illness signal, plus a deterministic red-flag watcher for acute emergencies. |

**Closed by:** A.2 and A.3 (what cadence the data even has), Track C.1, Track 0.6.
**Blocks while open:** G3, G9, and the entire streaming/storage budget in area M.
**Note:** the prior work asserted A and then designed for B. That inconsistency must be resolved deliberately.

---

## G3. Detection engine

**Question.** What produces the deviation score?

| Option | Implication |
|---|---|
| **A. Classical only** (personalized rolling median/MAD, CUSUM or EWMA, persistence rules) | Fast, interpretable, zero dependencies, published-competitive. Low novelty on its own. |
| **B. Time-series foundation model** (zero-shot forecast band, or reconstruction error) | Modern and demonstrable, but unproven on short gappy daily-cadence series, and adds real dependency and compute cost. |
| **C. Both, with A as the operating detector and B measured against it as a reported ablation** | Turns an unresolved question into a result. Costs one extra experiment. |

**Closed by:** E.1, E.2, E.3 under the Track B protocol.
**Blocks while open:** compute requirements, latency budget, and the shape of the results section.
**Note:** option C is the only one that converts this gate's uncertainty into a deliverable rather than a bet.

---

## G4. Where the agency lives

**Question.** What actually decides between OBSERVE, ASK, and ESCALATE?

| Option | Implication |
|---|---|
| **A. LLM tool-calling loop decides freely** | Flexible and quick to build. Policy behaviour is demonstrable but not measurable; no stated objective, so no way to show it is good. Most exposed to the "gimmick agent" criticism. |
| **B. Explicit decision layer** (value of information / expected information gain over a small hypothesis set) with the LLM handling language, hypothesis framing, and explanation | Principled, evaluable, comparable against never-ask and always-ask baselines. Likely cheap if the hypothesis set stays small. The LLM's role becomes narrower and more honest. |
| **C. Hybrid: LLM proposes candidate questions, the decision layer scores and selects** | Combines LLM flexibility in generating context-aware questions with a defensible selection rule. More moving parts. |

**Closed by:** F.1 (is exact information gain cheap here?), E.4 (does the LLM add attribution accuracy?), F.2 (is there an empirical cost term?).
**Blocks while open:** the central contribution claim, and the evaluation in G7.
**Note:** this gate determines whether "agentic" is a measured property or an adjective. Doc 05 item 16 applies.

---

## G5. Agent-computer interface

**Question.** How does the model touch the data?

| Option | Implication |
|---|---|
| **A. Typed deterministic tools** with validated arguments returning structured values | Reproducible, low latency, no execution sandbox, easy to test. Cannot answer questions outside the predefined set. |
| **B. Generated code in a sandbox** over dataframes | Handles arbitrary ad-hoc queries. Adds sandboxing, retry loops on syntax errors, latency, and an injection surface. |
| **C. Typed tools for the monitoring loop, code generation only for a free-form exploration mode** | Keeps the safety-critical path deterministic while allowing open exploration if the deliverable wants it. |

**Closed by:** F.3, and by whether the deliverable requires open-ended conversational querying (Track 0.1).
**Blocks while open:** build complexity and latency budget.
**Note:** doc 05 item 17. Our computation set is fixed and small, which is not the regime the code-generation pattern was designed for.

---

## G6. Retrieval and grounding

**Question.** Is RAG in the system, and over what?

| Option | Implication |
|---|---|
| **A. No retrieval, curated facts inlined in prompt** | Simplest, fastest, fully reproducible. Requires justifying the omission with a measurement. |
| **B. Small curated corpus with vector or hybrid retrieval and citation enforcement** | Verifiable citations, updatable knowledge, satisfies an explicit RAG requirement if one exists. |
| **C. Build A and B, measure the difference, report it** | Turns the question into a finding. The negative result is publishable-quality reasoning and directly answers "why is RAG here?" |

**Closed by:** F.4 (how many facts?), F.5 (licence-clean corpora?), F.6 (how measured?), Track 0.1 (is RAG a required requirement?).
**Blocks while open:** the knowledge-base build and the safety/citation contract.

---

## G7. Evaluation strategy

**Question.** What evidence will the finished project present, and how does it escape circularity?

| Option | Implication |
|---|---|
| **A. Real-data detection metrics only** | Credible but does not evaluate the actual contribution, which is the query policy. |
| **B. Semi-synthetic policy benchmark only** | Evaluates the contribution but is circular unless carefully framed. |
| **C. Both, plus a sensitivity analysis over the simulator's generative assumptions** | The defensible answer. Real data anchors detection; the simulated benchmark evaluates the policy, with assumptions stated and varied rather than fixed. |
| **D. C, plus an N-of-1 real-confounder case series from the user's own annotated data** | Strongest available, if G1 option B is viable. Small N, but it is real. |

**Closed by:** B.1, B.5, B.6, B.7, and G1.
**Blocks while open:** the entire results section and the shape of the final claim.
**Note:** this gate and G1 together determine whether the project produces evidence or a demonstration.

---

## G8. Output contract and safety envelope

**Question.** What exactly does the system emit, and what can it never emit?

Open sub-questions: risk expressed as a calibrated probability, an ordinal tier, or an explicit uncertainty statement; whether ranked hypotheses with probabilities are shown or only the top explanation; what the red-flag thresholds are and where the deterministic bypass sits; the disclaimer and escalation language; and whether the system is permitted to say "I do not know, and here is why I cannot know."

**Closed by:** F.7, Track L reading, Track 0.1.
**Blocks while open:** all user-facing text and the schema enforcement layer.
**Note:** the "I cannot determine this from these sensors" output is a genuine design option and is consistent with the identifiability limit in doc 01. Most commercial systems cannot say it. That may itself be a differentiator.

---

## G9. Demonstration harness

**Question.** How is the behaviour made legible to the audience?

| Option | Implication |
|---|---|
| **A. Notebook plus static figures** | Cheapest. Adequate if the deliverable is a report. Weak for a live audience. |
| **B. Lightweight interactive app** (time scrubber, injectable events, live agent trace, question widget) | Strong demonstration value for modest cost. Makes the decision policy visible, which is the point. |
| **C. Full web stack** | High cost, no AI/ML content, classic two-week time sink. |

**Closed by:** Track 0.1, 0.6, G.3.
**Blocks while open:** the time budget. This is the area most likely to silently consume the build, so the cap should be set explicitly and in advance.

---

## G10. Target condition and framing

**Question.** What is the system for?

| Option | Implication |
|---|---|
| **A. Acute respiratory infection early warning** | Matches the literature, has labels, is directly comparable to prior work, and is the most crowded. |
| **B. Unexplained physiological deviation triage**, with suspected infection as one output class | More honest about the identifiability limit, more useful year-round, weaker direct comparison to published baselines, harder to label. |
| **C. A narrower specialist scope** (for example post-vaccination or post-illness recovery tracking) | Sharper and more tractable, but episodic and narrow. |

**Closed by:** C.5 (the gap statement), D.2 (separability), A.4 (what labels exist), and Track 0.1 (what the audience rewards).
**Blocks while open:** the framing of the entire deliverable.
**Note:** deliberately last. It should be answered by the research, not before it. Doc 05 item 1.

---

## Gate status board

Revised after the course requirements was received. See [`09-rubric-mapping.md`](09-rubric-mapping.md) for the reasoning behind each change.

| Gate | Topic | Status | Closed by |
|---|---|---|---|
| G1 | Data foundation | **Largely CLOSED.** Simulated and replayed sources explicitly acceptable to the brief. Real device data now optional, kept for personal-use and portfolio value | Brief section 4 |
| G2 | Decision cadence | **CONSTRAINED.** Continuous monitor is non-agentic and deterministic; the agent is the bounded episode investigation. Replay mandatory for the 10-minute presentation | Brief, doc 09 sections 2 and 5 |
| G3 | Detection engine | **OPEN but de-prioritised.** Not graded. Strong simple baseline suffices; foundation model comparison is first on the cut list | E.1, E.2 |
| G4 | Where agency lives | **OPEN. Still the contribution-bearing gate**, now also aligned to the brief's named alert-fatigue risk | F.1, F.2, E.4 |
| G5 | Agent-computer interface | **CLOSED for the monitoring path: typed, scoped tools.** OWASP LLM06 mitigation 3 names "avoid open-ended extensions such as run a shell command" directly, and the only controlled ablation found shows direct text serialization beating code generation on anomaly, outlier and structural-break tasks. A separate sandboxed exploration mode for personal use remains open and is not on the safety-critical path | F.3, I.4, OWASP LLM06, arXiv:2606.16545 |
| G6 | Retrieval and grounding | **CLOSED: retrieval is in.** Corpus options narrowed: PMC legacy bulk FTP and Cloud datasets were **removed the week of 24 Aug 2026**, so any plan citing them is stale. Current best are MedlinePlus XML (~29 MB, daily, attribution-only) and NCBI Bookshelf/LitArch, noting StatPearls is CC BY-NC-ND 4.0. NICE and CDC returned 403 and need a human check | Brief section 6, F.5 |
| G7 | Evaluation strategy | **REFRAMED.** Spine is a positive and negative test-case suite with traces and error examples. Detection metrics are supporting evidence only | Brief sections 2 and 6, Track I.6 |
| G8 | Output contract and safety | **ELEVATED to a assessed component.** Stop condition, escalation, refusal and an audit log with enumerated fields are all required | F.7, I.2 |
| G9 | Demonstration harness | **CLOSED: interactive app required.** Visible planning, state transitions, human checkpoint and audit log cannot be shown in a notebook | Brief section 6 |
| G10 | Target condition and framing | **CLOSED (2026-08-30, user decision D1).** Diagnosis-shaped output is in scope: a ranked differential with calibrated probabilities, every claim source-linked, named conditions permitted **when symptom evidence supports them**, deterministic red-flag routing to a clinician. Excluded: a confident single named diagnosis from physiology alone with no symptoms (identifiability limit), and any treatment advice. See `11-candidate-formulations.md` Part 6 | User decision |
| G6b | Is retrieval necessary? | **CLOSED by D1: NECESSARY.** Grounding a differential is the whole basis on which diagnosis-shaped output was accepted | User decision |
| G11 | Available channels | **SUPERSEDED by `13-galaxy-watch5-data-reality.md`.** My earlier entry was wrong: it applied the Samsung Health *Data SDK* limitation to all access paths. The **manual export** does contain HRV (SDNN, RMSSD), respiratory rate, skin temperature, SpO2, sleep stages and per-minute heart rate. Rich but historical; the live paths remain poor. Pending confirmation from a real device export | doc 13 |

Phase 3 begins when every row reads CLOSED or CONSTRAINED with the evidence recorded. G4 is the one that matters.
