# 05. Assumptions That Must NOT Be Made Yet

**Status:** Phase 1 output.
**Date:** 2026-08-30

Each entry states the tempting assumption, why it is unsafe right now, and what would license it. Items marked **[NEW]** are ones the archived prior work did not raise, and several of those are the ones most likely to sink the project.

---

## About the problem

### 1. Do not assume "predict sickness" is the right target. **[NEW in emphasis]**
The identifiability argument in doc 01 (P2) and the base-rate arithmetic in doc 01 section 1.3 both point toward a different framing: *triage and explain unexplained physiological deviations*, of which suspected infection is one output class. That framing is more honest about what the sensors can support and more useful to a user. Committing to the infection framing now forecloses it.
**Licensed by:** Track C.5 gap statement plus Track D.2 separability analysis.

### 2. Do not assume the interesting metric is sensitivity or lead time. **[NEW]**
Those are the parts the published literature already handles adequately. The binding constraint is precision at a realistic base rate, expressed as alerts per user-week and PPV. Optimizing sensitivity is optimizing a solved problem.
**Licensed by:** Track B.2 and B.4.

### 3. Do not assume detecting illness earlier is automatically valuable.
Lead time is only worth something if an action follows it. What a user actually does differently with 48 hours of warning, and whether that action has evidence behind it, is an unexamined premise of this whole product category.
**Licensed by:** Track C.2 and Track D.

### 4. Do not assume the system must identify a specific pathogen.
Non-invasive wearables measure host response. Influenza, COVID, RSV, a common cold, and a bacterial infection produce broadly similar systemic signatures. Any claim of pathogen identification is unsupportable.

---

## About the data

### 5. Do not assume a suitable public dataset exists. **[NEW, and this is the big one]**
The archived work assumed it and designed an entire architecture on top. The realistic failure mode is subtler than absence: the obtainable datasets may carry only heart rate and step count, in which case the multi-signal "triad" reasoning that the prior design treats as its core is **not implementable on the data we have**.
**Licensed by:** Track A.2, with the schema actually printed.

### 6. Do not assume confounder ground truth exists. **[NEW]**
Public cohorts label illness, not "the user drank on Tuesday." Without those labels the central claim cannot be evaluated on real data, and the evaluation must be restructured (see item 7).
**Licensed by:** Track A.5.

### 7. Do not assume a self-built simulator can validate the central claim. **[NEW, and this is the sharpest objection]**
If we inject confounders into a simulator that we wrote, and then show the agent recovers them, we have demonstrated that our detector can find our own planted signal. That is circular. A simulator is still useful, but only if its generative assumptions are stated, varied, and reported as a sensitivity analysis, and only if a real-data anchor exists alongside it.
**Licensed by:** Track B.5.

### 8. Do not assume symptom-onset date equals infection onset.
Self-reported onset is coarse, recalled, and biased. Lead time measured against it means "time before the person noticed," which is a different and weaker quantity than "time before infection took hold." Say which one is being measured.
**Licensed by:** Track A.4.

### 9. Do not assume published operating points transfer.
A sensitivity figure obtained on one device, one population, one pathogen, and one season does not carry over to a different dataset. Treat every archived number as a hypothesis until re-derived or re-verified.
**Licensed by:** Track B.3.

### 10. Do not assume a single fixed baseline window.
Window length (7 / 14 / 21 / 28 days) trades responsiveness against stability and interacts with missingness. It is a hyperparameter with real consequences, not a convention to inherit.
**Licensed by:** Track E.2.

### 11. Do not assume clean data.
Non-wear, overnight charging, sync failures, and firmware changes are the normal case. Missingness is not preprocessing noise here; it is a first-class part of the problem and it may be informative (a user who stops wearing the device may be ill).
**Licensed by:** Track A.3.

---

## About the modelling

### 12. Do not assume a time-series foundation model beats a simple statistical baseline.
Short, low-dimensional, heavily gapped, strongly seasonal series are precisely the regime where classical methods are hard to beat. Include one only if it wins a measured head-to-head.
**Licensed by:** Track E.3.

### 13. Do not assume the LLM improves attribution.
The LLM may add nothing over a small rule set or a logistic model given identical features. If so, its defensible role narrows to question selection and explanation, which is still real but must be claimed accurately.
**Licensed by:** Track E.4.

### 14. Do not assume the LLM should do primary anomaly detection or arithmetic.
This one the prior work got right and it holds. Numerical work belongs in deterministic code.

### 15. Do not assume more components make a better project. **[NEW]**
A stack containing a foundation model, a code sandbox, a vector store, a multi-agent loop, and a web app is not more impressive than three well-chosen components with an ablation showing what each contributes. Unjustified components are liabilities: each one adds failure modes, consumes build time, and invites the question "why is this here?"

---

## About the agent

### 16. Do not assume "agentic" requires an LLM control loop. **[NEW]**
Agentic means the system decides its own next action under uncertainty. An explicit value-of-information controller over a small hypothesis set is agentic, is fully principled, is cheap to implement, and is *evaluable*. An LLM ReAct loop is a mechanism, not a policy, and without a stated objective its questioning behaviour can only be demonstrated, never measured. The right split between the two is an open question.
**Licensed by:** Track F.1.

### 17. Do not assume the code-generation pattern is right here. **[NEW]**
Generated-pandas-in-a-sandbox exists because its originating systems answer arbitrary open-ended questions over arbitrary personal data. Our computations are fixed and few. In that regime, typed deterministic tools plausibly dominate on latency, reproducibility, safety, and debuggability. Do not copy a pattern across a boundary where its justification does not hold.
**Licensed by:** Track F.3.

### 18. Do not assume the interaction cost is a free parameter. **[NEW]**
The c_q term in the ask/don't-ask objective decides the entire behaviour of the policy. Picking it by taste makes the objective decorative. It needs an empirical anchor.
**Licensed by:** Track F.2.

### 19. Do not assume users will answer.
Non-response is the dominant real-world failure of active systems. A policy that assumes an answer always arrives is modelling a user who does not exist.
**Licensed by:** Track B.6 and F.2.

### 20. Do not assume agent autonomy should be unbounded.
Deterministic red-flag interception must sit outside and above the model. This the prior work got right.

---

## About retrieval and grounding

### 21. Do not assume RAG is needed. **[NEW in force]**
If the required knowledge amounts to a few dozen facts about prodromal timelines and confounder signatures, a curated prompt beats a vector store on accuracy, latency, cost, and reproducibility. RAG attached without that check is exactly the "artificially attached" failure the brief warns against. A measured negative result here is a stronger deliverable than an unjustified vector store.
**Licensed by:** Track F.4.

### 22. Do not assume grounding equals accuracy.
Retrieval can surface irrelevant or contradictory passages and can be cited around. Faithfulness and citation precision must be measured, not presumed from architecture.
**Licensed by:** Track F.6.

### 23. Do not assume a large medical corpus is licence-clean or bulk-retrievable.
Check terms before designing around a source.
**Licensed by:** Track F.5.

---

## About delivery

### 24. Do not assume real-time streaming is required.
If the honest decision cadence is nightly, "real-time" is a presentation choice implemented as time-warped replay, and a large amount of streaming infrastructure becomes optional.
**Licensed by:** Track 0.6 and U5.

### 25. Do not assume a live device connection is required.
Building background mobile ingestion is weeks of platform work with no AI/ML content. This the prior work got right, with one caveat: if the user already owns a device with exportable history, that data is worth having (item 26), which is a different thing from live ingestion.

### 26. Do not assume the user's own data is unusable. **[NEW]**
The prior work dismissed personal hardware entirely. But an exported personal history, with the user able to retrospectively annotate their own alcohol, training, travel, sleep, and illness, is a partial solution to the confounder-label problem (item 6) that no public dataset offers. Whether this is available is unknown and worth finding out before dismissing it.
**Licensed by:** Track 0.2 and A.6.

### 27. Do not assume two weeks is two weeks. **[NEW]**
Calendar duration is not effort. The plan must be sized against actual available hours, with an ordered cut list decided in advance rather than under deadline pressure.
**Licensed by:** Track 0.5 and G.3.

### 28. Do not assume the archived research is a shortcut. **[NEW]**
It contains at least one demonstrably incorrect identifier and a quantity of unverified figures. Reusing any of it without re-verification imports errors into the deliverable under our name. Treat it as a list of leads, not a list of facts. See doc 00.
