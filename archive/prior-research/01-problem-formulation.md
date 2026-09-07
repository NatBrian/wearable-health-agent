# 01. Problem Formulation in Precise Technical Terms

**Status:** Phase 1 output. Formulation only. No architecture is proposed or implied here.
**Date:** 2026-08-30

---

## 1.1 The informal idea, restated in one sentence

Given a continuous stream of consumer-wearable physiological telemetry from one individual, decide on an ongoing basis whether that individual's physiology has departed from their own norm in a way that warrants attention, decide what (if anything) to ask them in order to find out why it departed, and communicate a calibrated, evidence-grounded account of what is happening.

That sentence hides four genuinely different technical problems that the earlier work collapsed into one. Separating them is the single most important thing this document does, because each has a different literature, a different evaluation protocol, a different data requirement, and a different answer to the question "does AI/ML actually help here."

---

## 1.2 Decomposition into four sub-problems

### P1. Detection: personalized change detection on non-stationary multivariate telemetry

Let *u* denote a single user and let *t* index a **decision epoch**. The natural unit is very likely one night rather than one minute (see decision gate G2 in doc 06).

Observed per epoch: a feature vector **x**_t in R^d derived from raw sensor streams. Candidate components, with availability being device-dependent and itself an open unknown (doc 02, U1):

| Family | Example features |
|---|---|
| Autonomic (cardiac) | nocturnal resting HR, minimum nocturnal HR, HRV (rMSSD / SDNN) |
| Thermal | distal skin temperature deviation from personal nocturnal baseline |
| Pulmonary | nocturnal respiratory rate |
| Sleep and behaviour | total sleep time, sleep efficiency, onset/offset clock time, step count, active minutes |
| Data quality | wear time, fraction of epoch with valid samples, motion index |

The series {**x**_t} is:

- **non-stationary** (seasonal drift, fitness change, device firmware change),
- **strongly periodic** (circadian, plus weekday/weekend structure),
- **irregularly sampled and gappy** (charging, non-wear, sync failure),
- **individually scaled** (a resting HR of 72 is alarming for one person and unremarkable for another, so population thresholds are invalid by construction).

The detection task is therefore **change-point and novelty detection against a personalized, seasonally adjusted baseline**, producing a deviation score a_t = g(**x**_{1:t} ; B_u), where B_u is a personal baseline estimated over a trailing window.

This is a largely solved problem. It is infrastructure, not contribution.

### P2. Attribution: assigning a cause to a detected deviation

This is the part the earlier work under-specified, and it is where the difficulty actually lives.

Given that a deviation has occurred, the latent cause is a categorical variable C_t taking values such as:

```
infection-like immune activation alcohol (dose and timing)
acute exertion / DOMS acute sleep restriction or fragmentation
acute psychological stress luteal phase of menstrual cycle
travel / altitude / heat exposure recent vaccination
recovery tail of prior illness medication change
sensor artifact / poor wear unexplained
```

Two properties make this hard, and both must be stated plainly up front.

**(a) The causes are physiologically confusable.** Alcohol and acute infection both produce elevated nocturnal HR, suppressed HRV, and disturbed sleep architecture. A purely passive sensor stream is, for a large fraction of deviations, genuinely *insufficient* to identify the cause. This is not an algorithmic shortcoming to be engineered away; it is an identifiability limit of the sensing modality.

**(b) There is very likely no ground truth for C_t in any public dataset.** Public wearable cohorts label *illness episodes* (PCR date, or self-reported symptom onset). They do not label "this Tuesday's HR spike was three glasses of wine." This is open unknown U2 in doc 02, and it directly constrains what can honestly be claimed and measured.

Because (a) holds, information must be acquired from outside the sensor stream. That leads directly to P3.

### P3. Active sensing: deciding when to ask, and what to ask

At each epoch the system chooses an action a_t:

```
OBSERVE stay silent, keep accumulating evidence
ASK(q) pose a low-friction question q to the user
ESCALATE(level, why) surface a warning with an explanation
SAFETY_OVERRIDE deterministic red-flag path, bypasses all model reasoning
```

Asking is not free. Every question spends a finite budget of user attention, and the empirical record on daily symptom surveys (high attrition) is exactly why purely-active systems fail. So the ask/don't-ask decision is a **value-of-information** problem:

> ask q if and only if
> E_{r ~ P(r | q, h_t)} [ U*(h_t + {q, r}) ] - U*(h_t) > c_q

where U*(h) is the expected utility of acting optimally given history h, and c_q is the interaction cost of asking.

Framing it this way is what makes "agentic" a technical claim rather than a marketing word. Whether the controller implementing this policy should be an LLM, an explicit Bayesian decision layer, or a hybrid is an **open architecture question** (doc 06, G4), not a foregone conclusion. Stating the objective in this form is also what later lets us measure the policy against a static-pipeline baseline instead of merely asserting that agency helped.

> **Update 2026-08-30: the interruption cost c_q cannot be empirically anchored, and must be swept instead.**
>
> Doc 03 area K and doc 04 item F.2 assumed we could find an evidence-based value for c_q. Phase 2 searched for it and reports that **no dose-response curve exists** in the literature: there is no published finding of the form "after N alerts per week, response rate falls to X%". The agent looked and explicitly warns against inventing one (`findings/F7-agentic-governance-rag.md`).
>
> What does exist is bounding evidence rather than a calibration:
> - **Alarm fatigue in clinical monitoring is severe and quantified.** Drew et al. 2014 logged 2,558,760 alarms over 31 days across 77 beds, roughly **187 audible alarms per bed per day**, with **88.8% of annotated arrhythmia alarms false**. Joint Commission Sentinel Event Alert 50 records 98 events and 80 deaths, and states that between 85 and 99 percent of alarm signals do not require clinical intervention.
> - **Ecological momentary assessment compliance is around 75%** (pooled 75.06%, 95% CI 72.37 to 77.65, k = 126, n = 19,431), and, importantly, **prompt frequency was not a significant moderator** in that meta-analysis and reversed sign by clinical status in another. So "ask less often" is not an evidence-backed principle.
> - **Event-contingent prompting outperforms time-contingent prompting.** That is precisely the regime this design already occupies: ask only when something has happened, never on a schedule. This is direct support for the architecture, and it is the one place the EMA literature speaks to our design decision.
>
> **Consequence for the objective.** c_q becomes a swept parameter reported as a sensitivity analysis, not a cited constant. The deliverable is the accuracy-versus-friction trade-off curve across a range of c_q, with the honest statement that the literature does not fix a point on it. That is a stronger result than a single number resting on an invented constant, and it removes a soft spot a reviewer would otherwise find.

### P4. Communication: calibrated, grounded, safe output

The output is not a diagnosis. Consumer wearables measure host response, not pathogens; a system claiming "you have influenza" is both clinically wrong and regulatorily reckless. The honest output object is closer to:

```
deviation: which metrics moved, by how much, relative to whose baseline
persistence: how many consecutive epochs
hypotheses: ranked causes, with probabilities or explicit uncertainty
ruled_out: what the user's answers eliminated, and what remains ambiguous
guidance: non-pharmacological, sourced, with citations
confidence: calibrated, and honest about the identifiability limit
safety: escalation language when red-flag thresholds are crossed
```

The research question attached to P4 is whether retrieval-grounding measurably improves factual accuracy and citation precision over a well-prompted model with the same facts inlined in context. That is testable, and it is currently untested (doc 02, U9).

---

## 1.3 The quantitative reason this problem is interesting: it is a precision problem

This reframing did not appear in the prior work, and it should drive everything downstream.

**Updated 2026-08-30 with measured evidence. My original estimate was too generous.**

I originally estimated positive predictive value by assuming a commonly cited operating point (sensitivity around 0.78, false alerts around 0.3 per user-week) against a base rate of 2.5 acute respiratory infections per adult per year, giving roughly 2.0 true alerts and 15.6 false alerts annually, so **PPV of about 11%**.

Phase 2 research found a real measurement rather than an estimate. An independent prospective evaluation (Northwell / Fitbit, JMIR 2024; see `findings/F2-commercial-products.md`) reported:

- **Positive predictive value: 4%**
- 665 alerts issued across 470 people
- Attributed causes of the false alerts: **stress 16.0%, poor sleep 13.7%, exercise 9.7%, alcohol 6.0%**

So the real operating point is roughly **twenty-four false alerts for every true one**, worse than my estimate by a factor of nearly three. Even a threefold reduction in false alerts would leave PPV near 11%, which is where I had wrongly assumed the field already sat.

The second line of that finding matters as much as the first. **About 45% of the false alerts were attributed to causes a single question could have resolved** (stress, sleep, exercise, alcohol). That is the addressable fraction, measured rather than assumed, and the study's own authors recommend pairing detection with symptom tracking.

Three consequences follow immediately.

1. **Sensitivity and lead time are the wrong headline metrics.** They are already adequate in the published literature. The binding constraint is precision at a realistic base rate. A project that optimizes sensitivity is optimizing the half that is already solved.

2. **Confounder disambiguation is not a nice-to-have feature; it is the direct intervention on the binding constraint.** Every alert correctly re-attributed to alcohol or a hard workout is a false positive removed.

3. **The product framing may be wrong.** Most of those "false" alerts are not false physiology. They are true physiological strain from a non-infectious cause. A system framed as *"explain and triage unexplained physiological deviations"* is both more honest and more useful than one framed as *"predict sickness."* Whether to adopt that reframing is decision gate G10 in doc 06. It must not be settled before the research is done.

### 1.3.1 The gap statement, corrected

My working premise had been "commercial systems are passive and cannot ask the user anything." **Phase 2 research refutes that as stated.** As of 2026, several products do ask questions: WHOOP Journal prompts a fixed questionnaire every morning, WHOOP has shipped proactive check-ins, Oura Advisor supports configurable check-ins, and an Oura medical-AI partnership explicitly conducts follow-up questioning.

The gap survives, but it must be stated precisely:

> **Nothing closes the loop between a detected physiological deviation and a targeted question capable of resolving it.** Questioning, where it exists, is unconditional and scheduled. Detection, where it exists, does not drive questioning.

The sharpest illustration found: Apple's Vitals notification text itself lists the candidate causes, naming "medications, elevation, alcohol intake, or even illness", and then asks the user nothing.

**A genuine challenge to the premise, which must be answered rather than ignored.** Apple reduced false alarms without asking anything, using a concordance rule requiring at least two of five metrics to be outliers simultaneously. That is cheap, silent, and imposes zero user burden. Any claim that asking is worthwhile has to beat a multi-signal concordance baseline, not merely a single-metric threshold. This becomes a required arm in any evaluation (doc 06, gate G7).

Two shipped precedents are worth studying rather than dismissing. Google's Loss of Pulse Detection (FDA cleared, 2025) is the only shipped wearable feature that responds to an anomaly by asking the user something and escalating autonomously if unanswered. Ultrahuman's "Jade" responds to anomalies by triggering a *confirmatory measurement* rather than by giving advice, which is a notably safe choice of action space.

### 1.3.2 Closest prior art in the research literature, and how much of the gap survives

From `findings/F3-health-llm-agents.md`:

- **Nobody models the cost of interrupting the user.** The agent read the actual triggering policies of three proactive health agents in source. One uses a hardcoded plus-or-minus 30% against a 7-day moving average; one uses agent-authored thresholds with a cooldown timer; one uses three fixed clinical threshold rules plus a cached LLM judge. None weighs information gain against interruption cost. The value-of-information gap is real and confirmed by code inspection rather than by absence of evidence.
- **The nearest formal work is not in health.** ContextAgent (NeurIPS 2025) and ProAgentBench both learn *when to act proactively*, with real metrics. Neither addresses health or physiological signals. Transplanting that framing into physiological monitoring is a defensible statement of contribution.
- **One preprint overlaps our core idea directly and must be read before anything is designed.** *Project Hermes* (arXiv:2602.18643) reports an LLM asking the user a question plus a Bayesian update, cutting false positives from 61.7% to 12.5% at 89% sensitivity. That is approximately the result this project would aim for. It is a single-author preprint with no released code, so it is weak evidence, but it is either a strong validation of the premise or a novelty problem, and which one it is depends on details we have not yet read. **Treat as a blocking read.**
- **Novelty is eroding.** Three genuinely proactive health agents shipped during 2026. The "almost everything is reactive question-answering" framing was true through 2025 and is becoming false.

---

## 1.4 What "success" would have to mean

For the project to be defensible, at least one of the following must be demonstrated with evidence rather than asserted.

| Claim type | Concrete demonstrable form | What it requires |
|---|---|---|
| **Engineering** | An end-to-end system that ingests real longitudinal telemetry, gates LLM invocation on a cheap statistical trigger, and produces grounded output within bounded latency and cost | Real data plus a working pipeline |
| **Empirical** | Measured reduction in false alerts per user-week at matched sensitivity, versus a passive baseline detector, attributable to the active-query policy | A benchmark carrying confounder ground truth (believed not to exist; see U2) |
| **Methodological** | An ablation isolating the contribution of each component (baseline model, time-series foundation model, LLM attribution, query policy, RAG), rather than shipping a stack and asserting it works | Careful experiment design. Cheap to do, high marginal credibility |
| **Interaction** | A quantified accuracy-versus-friction curve: alerts avoided per question asked | A simulated or scripted user; see doc 02, U11 |

The methodological claim is the cheapest to earn and the hardest to attack. It should be treated as a first-class deliverable, not an afterthought.

---

## 1.5 Explicit scope boundaries for the formulation

**In scope as stated:** one individual at a time; consumer-grade non-invasive sensors; retrospective or replayed data as an acceptable stand-in for live streaming; a system that advises rather than diagnoses or treats.

**Out of scope unless a specific research finding pulls it back in:** pathogen identification; clinical-grade sensors (ECG leads, core temperature probes); population-level epidemic surveillance; any claim of regulated medical-device function; training a model from scratch.

**Deliberately left undecided at this stage:** the target condition (respiratory infection versus any deviation), the decision cadence, the detector family, where the decision policy lives, whether RAG is included, and the interface. Every one of these is a decision gate in doc 06, and every one is downstream of research that has not yet been done.
