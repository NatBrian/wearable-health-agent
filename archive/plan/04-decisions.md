# 04. Decisions

**Part A** records what was decided and why, so it is not re-litigated by an agent that does not
know it was already settled. **Part B** records every place where this plan contradicts
`history/PROPOSAL.md`, and how each is resolved.

Reopening a decision requires new evidence, not a new opinion.

---

# Part A. Decisions

## Inherited from the design and unchanged

| # | Decision | Why it stands |
|---|---|---|
| D-001 | The detector is not the agent. Deterministic statistics flag; the agent investigates | The LLM is never invoked on a quiet night, and most nights are quiet. That is what makes the cost model work |
| D-002 | **Nothing is trained** | Too few labelled episodes to generalise, and fitted weights cannot be cited. Every number is an elicited prior with a source |
| D-003 | Single agent, not multi-agent | Free-tier rate limits, one auditable action log, and published ablations showing extra validate and replan stages contribute nothing |
| D-004 | The red-flag intercept is deterministic code upstream of the agent | It cannot be reasoned past because it is not reasoning. OWASP LLM06 mitigation 7: authorisation belongs in the downstream system, not in a prompt |
| D-005 | LangGraph with a SQLite checkpointer and `interrupt()` | Thread-scoped checkpoints give state across multi-day waits; `get_state_history()` supplies most of the audit trail |
| D-006 | Local-first. One SQLite file. No server, no health-data cloud | Wearable data never leaves the machine except as question text on the configured notification channel |

---

## D-101. Where agency lives: T0 to T4 plus X

Actions are classified by control tier, assigned **per action, per data scope, per blast radius**.
The table is in `01-overview.md` 3.1 and is the authoritative version.

The distinctions that matter, beyond naming:

- **Drafting is T2, sending is T4.** Drafting a question or an outcome is reversible and happens
  inside a fixed schema, so the LLM does it freely. Only the send is gated. Blurring these two is
  what makes a design either over-constrained or unsafe.
- **There is no T3 surface.** The system commits nothing administratively. That is a real narrowing
  of blast radius and is worth stating.
- **X is denied outright.** No shell, no code execution, no open web, no self-expansion. Attempts
  are logged and counted.
- **T1 is free but not risk-free.** In an agentic loop the output of one cycle is the input to the
  next, so a wrong read-only summary propagates. Every T1 return carries source, timestamp and a
  freshness verdict.

**The asymmetry underneath the whole design:** the model can always make the system quieter or
safer, never louder or riskier. It may add a red-flag escalation and never remove one. It may veto
an interruption the policy authorised and never authorise one the policy declined.

## D-102. The decision to interrupt stays in arithmetic. Everything else is the model's

This is the one thing the LLM does not do, and it is not caution.

**It is the contribution.** *Project Hermes* (arXiv:2602.18643) already publishes LLM-generated
contextual questions plus Bayesian updating. What is unpublished is weighing the question against
the cost of asking. Delegate that to the model and the project becomes a reimplementation of a
preprint with no benchmark against never-ask, always-ask or a fixed threshold.

**It is also the measured-worse option.** MediQ (Li et al., arXiv:2406.00922) found that directly
prompting state-of-the-art models to ask questions **degrades** performance, and that an abstention
gate recovered **+22.3%** diagnostic accuracy. Models are good at asking well and bad at knowing
when to stop.

**Supporting evidence for keeping the gate in code rather than in a prompt.** The PocketOS incident
of April 2026, in which an agent deleted a company's production database and backups in nine
seconds, is attributed to over-reliance on *soft* guardrails, where the team relied on
system-prompt instructions, plus over-scoped credentials. The conclusion drawn is that goal-driven
reasoning loops inside language models readily override prompt-based rules when the agent feels
blocked.

Everything else in the investigation is the model's: which tools to call, in what order, when it has
enough, how to word the question, what to ask next inside an open conversation, and how to
synthesise the explanation.

## D-103. Probes and questions are separate objects

The likelihood table `p(answer | cause)` is defined over **what is being asked about**, not over a
question string. Physiology and recall reliability do not change because a sentence is phrased
differently.

So the policy selects a `Probe` by value of information, and the LLM writes the `Question` for that
probe, freely and in context. Only the **answer space** is fixed, because that is what the cited
likelihood table lives over.

This is what lets the model write its own questions without destroying the benchmark. Inside an open
conversation the model may also generate follow-ups that no authored bank contains, because the
interruption has already been spent and the human has opted in by answering.

## D-104. NightSignal-style overnight resting heart rate, not the Mishra activity-masked method

The data forces this. The published Mishra method defines resting heart rate as samples where the
rolling 12-minute step sum is zero; the bridge delivers **steps as daily buckets**, so per-minute
masking is impossible. NightSignal takes overnight resting heart rate from a fixed local 00:00 to
07:00 window and needs no step granularity. It also has an independent publication record: 78% of
symptomatic cases alerted at or before onset, median 3 days early, 86.9% specificity per person-day.

Steps become a **daily activity covariate** for explained-variance subtraction instead of a masking
input.

## D-105. The baseline maturity ladder replaces historical backfill

The Samsung Health export is ruled out and Health Connect holds roughly one day at the outset, so
`history/PROPOSAL.md` F2 has no mechanism.

This is treated as the general case rather than a defect. Every competitor needs 7 to 28 nights and
none says what it can tell you before that. The system starts from a population prior over nocturnal
resting heart rate and shrinks toward the personal estimate as nights accrue, by closed-form
conjugate updating. `history/PROPOSAL.md` Appendix A already blesses the mechanism as "closed-form Bayesian
updating rather than model training", where it was a stretch goal. It is now core.

What the agent may claim is gated by the rung, and `EpisodeOutcome` carries `baseline_nights` and
`baseline_rung` so the limitation is machine-readable.

**It also produces an unpublished result:** detection recall and false-alert rate as a function of
baseline age, obtained by truncating each cohort participant's history.

## D-106. `MEASURE` is a spot resting heart rate reading, not an orthostatic test

An orthostatic heart-rate response peaks 15 to 30 seconds after standing. The bridge delivers heart
rate in **1-minute avg/min/max buckets**, giving roughly one bucket per posture. The result would
not be reliably attributable, would be hard to test, and could fail in a demonstration.

`MEASURE` therefore instructs a spot resting heart rate reading. The episode parks in
`AWAITING_MEASUREMENT` and waits for a heart-rate record timestamped after the request. A second
kind, `wear_tonight`, exists as a fallback and is useful in its own right, since non-wear is the
most common data failure.

> **Unverified:** whether a manually triggered reading reaches Health Connect at all. This is a
> **human check with a phone**, not a numbered task, and it blocks nothing. Implement **both** kinds.
> If the spot reading turns out to be unavailable, `MEASURE` degrades to `wear_tonight` alone. Do
> not assume either way and do not wait for the answer.

## D-107. Twelve independent binary causes with additive effects, not one categorical variable

**This replaces an earlier decision, and the earlier justification was wrong.**

The first draft modelled the cause as a single categorical variable over twelve values, the
"dominant explanation", and justified it by claiming that twelve binaries would "explode the state
space to 4096". **That is not a real objection.** Exact enumeration over 4096 states is microseconds
in numpy. The computational argument does not hold, and once it is removed, three separate things
turn out to favour the binary model.

**1. It matches the evidence we actually have.** `research/findings/F8`'s entire confounder table is
a list of **additive bpm effects**: alcohol +2.4 to +2.8, evening exertion +4.14, luteal +3.91,
infection +1.1 to +2.1, vaccination +1.52. A categorical "which single cause" model cannot use that
structure at all. A binary model with additive contributions uses it directly, as the likelihood.

**2. It needs roughly a quarter of the elicited numbers, and removes exactly the unsourceable ones.**

| | Categorical | Binary additive |
|---|---|---|
| Probe likelihood tables | 12 causes x 4 answers x 9 probes = **432** | 2 rows x 4 answers x 9 probes = **72** |
| Cause parameters | 12 priors | 12 priors + 12 effect sizes + 12 temporal profiles |
| **Total elicited** | **~450** | **~108** |

The categorical model forced a value for `p("two drinks" | stress was the cause)`. Eleven rows out
of twelve per probe were nuisance entries meaning "the person answers truthfully about drinking
regardless of what actually raised their heart rate". Those are the rows a model would have
fabricated most confidently. **In the binary model a probe depends only on its target cause, so they
do not exist.**

**3. It is true.** A person can drink *and* be stressed on the same night, and both contribute. The
categorical model forced a choice and therefore mis-stated `EXPLAINED_BY_EVENT` whenever two causes
were jointly responsible.

### The model, precisely

Each cause `i` is present with prior `base_rate_i`. A present cause contributes
`effect_mean_bpm_i` scaled by `profile_i[t]`, where `t` is nights since the episode opened. The
observed residual on night `t` is Normal about the sum of contributions. Inference is exact
enumeration over all 4096 states.

**The temporal profile is what discriminates.** Alcohol contributes on night one and then stops;
infection rises across nights; the luteal plateau lasts about twelve. That single fact is the
strongest sensor-only discriminator available and it comes straight from F8's published onset and
duration columns.

### Two contortions this removes

- **Priors are plain published base rates.** The categorical model required
  `P(cause | a flag fired) ∝ base_rate x P(flag | cause)`, which was an easy thing to get backwards
  and would have inflated infection roughly twentyfold. The generative residual likelihood now does
  that work, so the prior is just the base rate.
- **The marginals do not sum to 1, and that is correct.** They are per-cause probabilities of
  contributing. A clinician's differential does not sum to 1 either.

### No probabilistic-graphical-model library

`pgmpy` is **dropped**. The model is a conditional-linear-Gaussian structure that
`DiscreteBayesianNetwork` cannot express anyway, and exact enumeration is about 80 lines of numpy
that can be read end to end. This removes a dependency, a numpy version constraint, and an API that
renamed its central class between releases. The graph figure for the write-up is rendered with
graphviz directly.

It is still a hand-specified Bayesian model with literature-elicited parameters and exact inference.
The library was never the model. See B-12.

## D-108. Four models, none trained, none optional. Chronos is advisory

The inventory is in `01-overview.md` 3.3. Two points are frequently confused and are settled here.

**Chronos is always built and always runs.** What is uncertain is whether it *wins*.
`research/findings/F4` found the evidence thin: the most on-point paper puts zero-shot Chronos at
MASE 0.82 against EWMA at 0.84 at context length 32, a 2.4% relative gain over a five-line baseline,
and several independent evaluations find time-series foundation models losing to linear and
seasonal-naive baselines. Reporting a negative result is a finding, not a failure.

**Its role is sharpened rather than left as a bare comparison.** Chronos supplies a second deviation
score `(actual - predicted) / half-interval` which enters the belief model as evidence. The
deterministic detector alone sets `level` and `flagged`, so the claim that there is no model
inference in the safety-critical numeric path survives, and a Chronos failure degrades nothing.

**The experiment worth running is not the one the literature already answered.** A rolling median
and MAD baseline needs history, and at five nights MAD frequently collapses to zero on quantised
data. A zero-shot foundation model carries a prior over short series and yields a calibrated
interval from very few points. The hypothesis is that **Chronos beats statistics precisely where
statistics is weakest, which is the cold-start regime**, tested on the baseline-age curve from
D-105 at the cost of one extra line on an existing plot.

The other two non-LLM models were never in question: the Bayesian network is the reasoning core and
the embedding model is required by hybrid retrieval.

## D-109. The cause set is twelve, and the provenance of that number is stated

**Each individual cause is evidence-based. The closed set of exactly twelve is a modelling
decision.** The write-up keeps those apart.

Evidence for the causes: published effect sizes on nocturnal resting heart rate, mostly grade A or B
in `research/findings/F8`, each cited in `data/knowledge/causes.yaml`.

Independent corroboration of the *list*: Alavi et al. 2022, *Nature Medicine* 28:175-184, ran a
deployed alerting system on 3,318 participants and enumerated the observed non-illness triggers as
stress and work stress, alcohol, intense exercise, travel, poor sleep, vaccination (both doses),
altitude change, and other respiratory infections. The list was not invented and then justified.

Excluded from F8's fuller table, each with a reason:

| Excluded | Reason |
|---|---|
| Late meals | +0.73 bpm, grade C preprint, below the measurement noise floor. Cannot fire an alert alone |
| Caffeine | Footprint is almost entirely in the sleep channel, with weak and inconsistent heart-rate effects |
| Ambient room temperature | Weakest-evidenced item in the review, and it acts on skin temperature, which this system does not have |
| Nicotine | Magnitudes unverified, and habitual use folds into the personal baseline rather than presenting as an event |

Merged rather than dropped: altitude into `travel`; beta blockers, stimulants, antihistamines and
SSRIs into `medication`.

Three safeguards make a closed set defensible: `unexplained` is a first-class cause and not a
dustbin; every probability-table row carries an A-to-D evidence grade so weak rows are visibly weak;
and the priors get a sensitivity sweep, because a conclusion that survives a wide sweep is a far
stronger claim than one resting on a point estimate.

## D-110. Knowledge artefacts are authored by a human and are read-only to the coding agent

`data/knowledge/` holds the cause set, the probe bank with its likelihood tables, the red-flag rules
and the corpus manifest. These are the project's intellectual core and what the novelty claim rests
on. A model asked to produce hundreds of cited conditional probabilities will produce hundreds of
plausible fabrications.

The coding agent loads these files and never edits, extends or regenerates them.

## D-111. The system runs end to end with the LLM switched off

The self-hosted endpoint has short sessions, a weekly quota, and a URL and key that regenerate.
An unattended build will outlive it.

Every test therefore runs with `WHA_LLM_PROVIDER=cassette` against recorded responses. The live
endpoint is exercised only by `wha doctor` and a smoke check run by hand. `LLMUnavailable` parks the
episode and retries on the next tick; it never fabricates a response and never closes an episode.

This also answers "how does the agent survive the endpoint being down" almost for free.

## D-112. The LLM client is provider-agnostic

Development and any human-run command use an **OpenAI-compatible endpoint configured in `.env`**,
currently `deepseek-v3.2`, which has a stable URL and key. **Every test uses `cassette`**, forced by
an autouse fixture that overrides `.env`, because an unattended run executes the suite hundreds of
times and a live provider would be slow, costly and nondeterministic.

The deployed product is not welded to one endpoint. `llm/` is an interface with three
implementations: `cassette` (the default, and what every test uses), `ollama_native` (the only path
where `"think": false` works), and `openai_compatible` (covers OpenRouter, OpenAI, Together, Groq,
vLLM, and a local Ollama).

Consequences the implementation must handle:

- **Structured output is not uniform.** Always request JSON, always validate with Pydantic, perform
  exactly one repair round, then raise `ValidationFailed`. Never trust a provider to enforce a
  schema.
- **The `max_tokens` floor applies to any thinking model**, not just one family, so it is global.
- **Model capability is a variable.** Running the frozen scenario suite under two or three models is
  a real experiment, and published work in this domain found contextual framing matters more than
  parameter count, so a negative result is plausible and worth reporting.

"Bring your own model" is a product feature and a privacy answer, not a fallback.

## D-113. A prompt is a versioned specification with mandatory refusal conditions

Six components: instruction, context, output schema, constraints, examples, and **refusal
conditions**. The last is the one usually omitted and the one that makes `INSUFFICIENT_DATA`
reachable in practice rather than only in the type system.

Prompts carry `prompt_id` and `prompt_version`, written to every audit row. Changing a prompt is a
behaviour change and re-runs the full regression suite. Temperature is matched to risk per call:
extraction, red-flag classification, self-critique and tool selection at zero, because a check that
varies is not a check; question phrasing and outcome prose at 0.3.

A related point that strengthens the retrieval case: **Singapore MOH clinical guidance is sparsely
represented in general pretraining corpora and local documentation conventions barely at all.** The
model does not know MOH guidance. That makes the Singapore retrieval layer load-bearing rather than
localisation for its own sake, and it is a better justification than the one in `history/PROPOSAL.md` 4.6.4.

## D-114. Two-way Telegram notifications

With a desktop dashboard as the only surface, `history/PROPOSAL.md` 3.5's claim that the system "wakes
itself" and that "the user never opens an app to start it" would be false. With an interruption
budget of two per week, a dashboard that must be checked daily to learn there is nothing is
precisely the burden the project exists to remove.

Telegram delivers the answer options as inline buttons and receives the reply, closing the loop
without a screen. Free, no app to build, reaches the phone.

**Implementation:** raw HTTP long-polling against the Bot API via `httpx` in a background thread,
not `python-telegram-bot`, whose async-first design from version 21 fights Streamlit's threading
model.

**Security consequence:** see B-7. This creates an outbound channel where the design previously
claimed none, and the claim is narrowed rather than defended.

## D-115. Subjects, not a demo mode

Every table carries `subject_id`. Demo scenarios and cohort replays write to their own subjects and
the dashboard renders them identically to live data, because it does not know the difference. A
subject selector appears only when more than one subject exists.

One code path, one interface, no mode branching, and a demo that is real because it runs the real
pipeline. Required regardless, because cohort evaluation iterates over many participants.

## D-116. A UI-agnostic service layer

All business logic lives in `src/wha/service/`. Pages and CLI commands call service functions and
render. No page queries the database and no page imports from `detect/`, `belief/`, `policy/`,
`agent/` or `db/`. Enforced by a lint rule, not by good intentions.

This makes D-117's Phase D a wrapper rather than a rewrite.

## D-117. Streamlit now, optional Next frontend as Phase D

Streamlit is chosen for risk, not cost. A React frontend adds a second language, a build step, an
API client and schema duplication, each a place an unattended model produces something that compiles
and is wrong. Streamlit shares the Pydantic models directly and has a first-party test framework
(`streamlit.testing.v1.AppTest`), so the interface is test-gated like everything else.

The honest cost is that it looks like an internal tool. D-116 makes the decision reversible rather
than permanent.

## D-118. Evaluation is built in Phase A, not last

The policy benchmark is the contribution and it needs no LLM, no LangGraph, no retrieval and no
interface. It needs the belief model, the probe bank, the value-of-information arithmetic and a data
loader. So it finishes before any integration risk exists, rather than being sacrificed at the end,
which is what happens to evaluation in practice.

## D-119. Course and team framing removed from all public documents

The repository will be public. `history/PROPOSAL.md`, `README.md` and `history/HANDOFF.md` currently refer to a
course, a marker, a module and a team, and the system is solo. This is a narrative rewrite performed
by a human, not by the coding agent.

## D-120. Expected value of sample information, not expected information gain

`research/findings/F8` 6.2 states the distinction and flags it as a real modelling compromise:

> **Value of information is exactly zero if the information cannot change the decision.** No matter
> how much entropy an answer would remove, if you would alert either way, the answer is worth
> nothing. Entropy-based information gain does **not** have this property; it will happily pay to
> reduce uncertainty with no action consequence.

The first draft used entropy gain and then bolted on a hand-set threshold band to compensate. D-107
makes the better formulation available, because there is now a single decision-relevant variable,
`p_illness`, rather than a spread over twelve categories.

**Utility over (decision, truth), in the same units throughout:**

```
                       infection present   infection absent
conclude illness              0.0                -1.0
conclude benign              -9.0                 0.0
```

`EVSI(probe) = E_answer[ max_d E_{truth|answer} U ] - max_d E_truth U`. Ask iff
`EVSI - POLICY_COST_PER_INTERRUPT > 0` **and** the interruption budget allows.

Three things fall out that previously had to be asserted:

1. **The testing threshold is derived, not hand-set.** Indifference sits at
   `|U_FA| / (|U_FA| + |U_MISS|) = 1/10 = 0.10`, which coincides with the Pauker and Kassirer
   threshold. It is now a consequence of the stated utilities rather than a number chosen to match
   a paper.
2. **The upper "act regardless" threshold disappears entirely.** Once no answer could change the
   decision, EVSI goes to zero on its own. `POLICY_TREAT_THRESHOLD` is deleted and must not be
   reintroduced.
3. **One fewer free parameter.** `POLICY_COST_WEIGHT`, which converted bits into cost units, is gone
   because everything is already in utility units.

The sensitivity sweep runs over the miss-to-false-alarm ratio and
`POLICY_COST_PER_INTERRUPT`, and reports the accuracy-versus-interruption frontier rather than a
single operating point, because the literature does not fix a point on it.

## D-121. Cheap context is pre-loaded; tools stay freely callable

Six of the seven T1 tools are cheap deterministic reads that the model will want on essentially
every episode. Making it spend turns fetching them, at roughly nine tokens per second, buys nothing
and adds ordering nondeterminism to the cassette tests.

So the graph **pre-loads** nightly features, personal baseline, known events, data quality, and the
episode's own history into the first investigation prompt.

**This is an optimisation, not a restriction.** Every T1 tool remains callable at any time,
including re-fetching a pre-loaded one with different arguments. The model's real judgement is
concentrated where it matters: **constructing the retrieval query from the case, re-querying after
learning something, choosing the pattern for `find_similar_past_episodes`, and deciding when it has
enough.** That is where the path genuinely depends on what it discovers.

## D-122. Claim-to-source enforcement is deterministic; the LLM critique is additive

A model checking its own citations is unreliable, and the literature on self-preference bias says
so plainly. But the check that matters is not a judgement:

> Does every clinical claim carry a `evidence_span` that appears **verbatim** in a retrieved
> passage?

That is a string containment test. It runs in code, it cannot be talked out of, and it produces
`EpisodeOutcome.unsupported_claims` as a hard count rather than an opinion.

The LLM self-critique pass stays, but it is **additive and advisory**: it looks for contradictions
with the evidence and for tone, and it can only cause more claims to be removed, never fewer. Same
asymmetry as the red-flag rule.

## D-123. Red flags are tiered, and the posture is balanced rather than over-sensitive

`history/PROPOSAL.md` 5.1 specifies a "deliberately over-sensitive" red-flag layer. The operator has chosen
**balanced** instead: fewer escalations, on the grounds that a stream of unnecessary "see someone"
messages is itself a failure mode for a tool meant to reduce alarm fatigue.

Implemented literally, "escalate only when two or more symptom red flags co-occur" leaves a hole: a
single serious symptom in free text would not reach the deterministic path and would depend on the
LLM second-opinion detector. That contradicts D-004 and OWASP LLM06 mitigation 7, which put
authorisation in code rather than in a model.

**Three tiers. Balanced overall, no hole.**

| Tier | Rule | Contents |
|---|---|---|
| **A** | **One is enough.** Deterministic, immediate `ESCALATE(urgent)` | Chest pain or pressure, breathlessness at rest, confusion or altered consciousness, fainting or near-fainting, stiff neck with fever, uncontrolled bleeding. Roughly six items. Nobody wants a second opinion on these |
| **B** | **Two or more, or persistence beyond a stated duration.** Deterministic, `ESCALATE(same_day)` | Fever, body aches, marked fatigue, poor appetite, exertional breathlessness, persistent vomiting. **This is where "balanced" lives**, and where a blanket rule would generate the noise being avoided |
| **C** | **Additive only.** LLM second opinion over the free text | Catches unusual phrasing that a rule misses. May add an escalation, **never remove one** |

Vitals thresholds sit alongside tier A and are unchanged: a resting heart rate far outside the
subject's own established range escalates regardless of reported symptoms.

Every tier-A and tier-B rule lives in `data/knowledge/red_flags.yaml`, is read-only to the coding
agent, and is exercised by a named scenario fixture. See B-14.

## D-124. Every knowledge-table number is labelled CITED, DERIVED or ASSUMED

The rows are not all the same kind of claim, and treating them as though they were is how
fabrication enters. Each carries a `provenance` field:

| Label | Meaning | Requirement |
|---|---|---|
| `CITED` | A published number | Full citation, and the study's n |
| `DERIVED` | Computed from published numbers | The derivation is written out in the row, plus the source it derives from |
| `ASSUMED` | **No published value exists** | States the assumption, states which direction it is deliberately conservative in, and **must** appear in the sensitivity sweep |

**The `ASSUMED` category is unavoidable and must not be disguised.** `research/findings/F8` 6.1 says
the answer-reliability tables, meaning how accurately a person reports drinking or stress when an
app asks, are "essentially unmeasured", and 6.5(v) states that the medical test-selection literature
"transfers the mathematics cleanly and the measurement discipline not at all". A model asked to cite
these will search, find nothing, and produce a confident number regardless. Better data does not fix
this, because the measurement does not exist.

Two consequences:

- **Assumed values are set conservatively**, meaning they under-estimate how informative a question
  is. Over-estimating question value makes the system interrupt more than it should, which is the
  failure this project exists to fix.
- **The operator reviews the `ASSUMED` rows only.** Roughly ten to fifteen numbers. The `CITED` rows
  quote studies with tens of thousands of participants and do not need review.

**Before writing:** every number that `research/findings/F8` marks `[secondary]`, meaning it was read
from a search summary rather than the paper, is re-verified against the primary source. Those are
the most likely to be wrong and F8 says so itself.

---

# Part B. Contradictions with `history/PROPOSAL.md`, and their resolution

A coding agent cannot resolve a contradiction; it silently picks a branch. Each is resolved here.

### B-1. `MEASURE` as specified cannot run

`history/PROPOSAL.md` 4.3 describes the distinguishing feature as *"a one-minute stress and HRV reading on
the watch. The result arrives and the belief updates."* Samsung Health writes only heart rate,
steps, sleep stages and exercise to Health Connect, so **a stress or HRV reading never reaches our
code.** The feature as written has no data path.

**Resolved by D-106.**

### B-2. F2, a MUST feature, has no mechanism

F2 depends on the Samsung Health export, which is ruled out and which Appendix B day 0 already
strikes through. The system had no way to obtain the baseline it requires before saying anything.

**Resolved by D-105.**

### B-3. The document disagrees with itself about available channels

Section 4.7.1 says *"the deployed system is expected to use HRV, respiratory rate and blood oxygen
as well"*. Section 4.5.1 and `history/HANDOFF.md` section 6 say those channels are not obtainable at all.

**Resolved:** 4.5.1 is correct. The working channel set is **heart rate, steps, and sleep stages if
they arrive**. 4.7.1 is stale and is corrected in the documentation pass (D-119).

### B-4. Section 3.6 reads as if the rich channels are available

*"It exposes 31 data types including HRV, respiratory rate, skin temperature, resting heart rate,
blood oxygen and sleep stages."* True of the **bridge app's capability**, false of what Samsung
populates.

**Resolved:** corrected in the documentation pass. Nothing in the implementation may assume those
channels exist.

### B-5. A structurally broken table

`history/PROPOSAL.md` lines 563 to 565 contain two orphaned table rows left from an earlier edit, sitting
after the fallback paragraph with no header. This is the class of damage `history/HANDOFF.md` section 7
warns about.

**Resolved:** repaired in the documentation pass. The OpenRouter row is superseded by D-112.

### B-6. Multi-signal concordance assumes signals we do not have

F5 draws its credibility from a "two of five metrics are outliers together" rule. With heart rate,
steps and possibly sleep there is realistically **one** physiological channel plus behavioural
context.

**Resolved:** concordance is redefined as **multi-night persistence plus cross-channel corroboration
where available**. Weight shifts onto persistence, which is well evidenced (red-alert clusters
average 4.3 days in COVID-positives versus 1.9 in negatives). This *strengthens* the argument for
asking, because fewer causes are separable from sensors alone, and it is stated as a limitation
rather than glossed.

### B-7. Telegram falsifies the strongest security claim

`history/PROPOSAL.md` 5.4 states *"The system has no exfiltration vector."* Adding a notifier creates one.

**Resolved by narrowing the claim rather than defending it.** The mitigations are architectural:

1. The notifier is **not an agent tool**. It is absent from the tool table and the LLM cannot call
   it. It is invoked by deterministic code in the episode state machine.
2. Message kinds are a closed enum with fixed templates.
3. The LLM writes the question text, but only for a `Probe` the arithmetic already selected. It
   cannot choose to send, and it cannot invent a probe.
4. Outbound text is validated before sending: length cap, no URLs except the single dashboard link,
   no markup, and the probe must exist in `data/knowledge/probes.yaml`.
5. The bot accepts input only from the configured `WHA_TELEGRAM_CHAT_ID`. Everything else is dropped
   and logged as a `safety_event`.
6. Sending is rate-limited by the interruption budget, enforced upstream of the notifier.
7. Notifications are **opt-in and off by default**.

Revised claim: *the system has one outbound channel, which is one-way for content, fixed-format,
unreachable from the agent's tool space, and rate-limited.* Weaker than "no exfiltration vector",
and the write-up says so. `history/PROPOSAL.md` 5.3 also gains a second egress caveat, because question text
and answers contain health information.

### B-8. Team and course framing versus a solo public artefact

**Resolved by D-119.**

### B-9. Stale conclusions in `research/`

| File | Stale claim |
|---|---|
| `research/08-confirmed-constraints.md` | Team of four, a WHOOP teammate, live real-time required |
| `research/13-galaxy-watch5-data-reality.md` | *"We should build on the export"* |
| `research/14-automatic-data-access-and-samsung-vitals.md` | Recommends an Android reader plus a Dockerised Open Wearables stack |

**Resolved:** `research/` is **evidence, not design**. `AGENTS.md` states that the coding agent may
read `research/` for cited numbers and must never take a design conclusion from it. Design comes
from `history/plan/` only.

### B-10. "Real-time" was never settled

`research/08` recorded live real-time behaviour as a requirement; `history/PROPOSAL.md` 4.2.5 specifies a
scripted replay. Both were true at different moments.

**Resolved:** the decision cadence is **nightly**. There is no intraday monitoring and no real-time
claim. Ingestion runs continuously, the batch runs once each morning, and demonstration is scenario
replay through the real pipeline (D-115). Wording implying sub-daily detection is removed in the
documentation pass.

### B-11. The system is not Plan-Then-Execute, and must not claim to be

`history/PROPOSAL.md` 5.4 claims the **Plan-Then-Execute** pattern, in which the investigation plan is fixed
before any external content is retrieved, so retrieved content can influence data but never control
flow.

**That is false of this design.** The LLM chooses its next tool call after reading retrieved
documents, so untrusted content does influence control flow. Claiming the stronger pattern would be
a security claim the implementation does not support.

**Resolved:** the system implements the **Action-Selector** pattern, and the containment argument is
stated accordingly in `01-overview.md` 3.1: a closed enumerated action space, no outbound tool so
influencing control flow yields nothing exfiltrable, untrusted text processed only into typed
objects, every T4 action gated by arithmetic the model cannot reach, and hard caps on tool calls and
graph steps. `history/PROPOSAL.md` 5.4 is corrected in the documentation pass.

### B-12. pgmpy is named as a component and is no longer used

`history/PROPOSAL.md` 4.4 and 4.5.2 name **pgmpy** as the belief-state implementation and as model number
two of four.

**Resolved by D-107.** The model is now a conditional-linear-Gaussian structure over binary causes,
which `DiscreteBayesianNetwork` cannot express, and exact enumeration over 4096 states is about 80
lines of readable numpy. The inventory still lists four models, none trained: the second is a
**hand-specified Bayesian cause model with literature-elicited priors and effect sizes, and exact
inference**. The library was never the model. `history/PROPOSAL.md` is corrected in the documentation pass,
and the change is a simplification rather than a loss: one fewer dependency, one fewer API trap, and
an inference routine that can be read end to end.

### B-14. The red-flag layer is specified as "deliberately over-sensitive"

`history/PROPOSAL.md` 5.1 states the red-flag layer is "deliberately over-sensitive". The operator has chosen
a **balanced** posture instead, on the grounds that unnecessary escalations are themselves an
alarm-fatigue failure in a tool built to reduce alarm fatigue.

**Resolved by D-123.** Three tiers, with single-symptom escalation retained only for a short
ambulance list, so the change reduces noise without moving any genuine emergency out of deterministic
code. `history/PROPOSAL.md` 5.1 is corrected in the documentation pass, and the correction is stated as a
deliberate posture choice with its reasoning, not as a weakening.

### B-13. The design specifies expected information gain, which `research/findings/F8` itself warns against

`history/PROPOSAL.md` 3.4 and 4.7 describe the policy as **expected information gain** against an
interruption cost. F8 section 6.2 explicitly identifies this as a modelling compromise, because
information gain will pay to reduce uncertainty that cannot change the decision, and states that
"if our project uses EIG rather than EVSI, that is a real modelling compromise and should be stated
as one".

**Resolved by D-120.** The policy uses **expected value of sample information** on the action
decision. The threshold band is derived from the stated utilities rather than asserted, the upper
threshold disappears, and one free parameter is removed. `history/PROPOSAL.md` is corrected in the
documentation pass, and the correction strengthens the claim rather than weakening it: the policy is
now the decision-theoretic gold standard F8 names, not an approximation to it.
