# F9: Advanced Techniques, Rigour and Engineering Practice

Research brief: "what would make this genuinely substantive rather than merely compliant".
Scope: uncertainty quantification and calibration, Bayesian personalisation and N-of-1 method,
sequential decision making beyond myopic VoI, rigorous evaluation of interactive/agentic systems,
adversarial evaluation, engineering practice, and proactive/interruption-aware systems outside health.

Date of research: 2026-08-30. Every factual claim carries a URL. Claims I could not verify against a
primary source are marked UNVERIFIED. Build-hour figures are my engineering estimates, not sourced facts,
and are marked as such.

Note on method: the session's web-search budget was exhausted before this task started. All research was
done by direct query against primary indexes (arXiv API, OpenAlex API, Crossref, GitHub API, HN Algolia
API) and by fetching and text-extracting primary PDFs and documentation. Every URL below was resolved
during this session.

---

## 1. Executive summary

**The single highest-leverage finding.** The techniques that will make this project look serious are
almost entirely in the *evaluation and engineering* layer, not the *modelling* layer. A frozen scenario
suite with cached LLM responses, an adversarial simulated user, a real ablation matrix with paired
bootstrap intervals, and cost/latency instrumentation are collectively about 25 to 35 hours and are the
difference between "a student wired an LLM to a Fitbit" and "this person knows how to build a system
someone could trust". By contrast the glamorous statistical machinery (conformal prediction, POMDPs,
contextual bandits, hierarchical Bayes across users) mostly requires conditions you will not have:
labelled outcomes, many users, or thousands of interactions.

**Conformal prediction is the biggest trap-shaped-like-a-prize in this brief.** It is genuinely rigorous
and genuinely cheap to implement, but its guarantee is only as meaningful as the labelled calibration set
behind it, and the finite-sample behaviour with tiny calibration sets is badly under-appreciated.
Angelopoulos and Bates give the exact numbers: coverage conditional on the calibration set is
Beta-distributed, and you need n = 102 calibration points before realised coverage lands within +/-0.05 of
the target with probability 0.9, and n = 2,491 for +/-0.01
(https://ar5iv.labs.arxiv.org/html/2107.07511, Table 1). With fewer than ~50 labelled illness episodes,
which is the realistic case here, split conformal will still *technically* satisfy marginal coverage in
expectation over calibration draws, but the coverage you actually get on your one draw is a coin flip with
a very wide spread. It is defensible to use it **only** if you say this out loud. Applying it silently and
claiming "90% coverage guarantee" is the single easiest way for a knowledgeable reviewer to catch you out.
Details in section 3.

**There is a clean, cheap, genuinely impressive way to combine an LLM with explicit probabilistic
inference**, and it is the best "beyond an intro course" move available: use the LLM as a *hypothesis and
evidence extractor* and a small hand-specified discrete Bayesian network (pgmpy, ~20 lines) as the
*inference engine*, so the arithmetic of belief updating is auditable and the LLM never does the maths.
This has direct published precedent (AutoElicit, https://arxiv.org/abs/2411.17284; From Word Models to
World Models, https://arxiv.org/abs/2306.12672; LLM-BI, https://arxiv.org/abs/2508.08300) and is about
6 to 10 hours. Details in section 4.3.

**There is a definitive published answer to "is there a formal decision-theoretic criterion for when to
interrupt a user", and it is 27 years old.** Horvitz, Jacobs and Hovel's *Attention-Sensitive Alerting*
(UAI 1999, https://arxiv.org/abs/1301.6707) defines net expected value of alerting, NEVA = EVTA - ECA,
alerts only when NEVA is positive, infers the user's attentional state with a dynamic Bayesian network,
and was deployed as the PRIORITIES system at Microsoft Research. Citing this and implementing its
structure (not its full machinery) costs a few hours and instantly places the project in a real research
lineage rather than in the "I added a notification" bucket. Details in section 9.

**On calibration of LLM-expressed confidence, the evidence is clear and unflattering.** Xiong et al.
(ICLR 2024, https://arxiv.org/abs/2306.13063) find that LLMs verbalising confidence "tend to be
overconfident, potentially imitating human patterns", with ECE > 0.25 on several benchmarks, and that
black-box consistency methods close most but not all of the gap to white-box logit methods (AUROC 0.522
to 0.605). Tian et al. (https://arxiv.org/abs/2305.14975) find the opposite-signed but compatible result
that for RLHF models the *verbalised* number is better calibrated than the model's own conditional
probabilities, "often reducing the expected calibration error by a relative 50%". Practical read: never
ship a raw verbalised confidence; combine verbalisation with self-consistency sampling and then
post-hoc recalibrate. This is a 4 to 6 hour experiment with a real, citable result.

**Prompt-injection defence is mostly theatre and the literature says so with numbers.** Zhan et al.
evaluated eight published IPI defences and broke all eight with adaptive attacks, "consistently achieving
an attack success rate of over 50%" (https://arxiv.org/abs/2503.00061). Willison's framing is the one to
adopt: architectural constraint (the lethal trifecta) rather than detection, because in security "95% is
very much a failing grade" (https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/). For this project
the honest and impressive move is a *systematic* adversarial suite (a taxonomy times an injection-vector
matrix, ~40 to 80 cases) plus an explicit architectural argument about what the agent cannot do, not a
guardrail classifier.

**The most common way portfolio ML projects fail is not technical weakness, it is absence of decisions.**
The practitioner sources converge: reviewers probe *how* you solved it, not what you built
(Eugene Yan, https://eugeneyan.com/writing/how-to-interview/: "What's more important is _how_ the candidate
solves it"), they look for error analysis and trade-offs ("How did they evaluate and perform error
analysis? What constraints did they face? What trade-offs did they make?"), and undifferentiated work is
worthless in a saturated pool (Vicki Boykis: "Don't do what everyone else is doing, because it won't
differentiate you", https://vickiboykis.com/2019/02/13/data-science-is-different-now/). Details in
section 11.

---

## 2. THE RANKED TABLE

Ordered by impressiveness-per-hour. Build hours are **my estimates** for one competent developer who
already has the base agent working, including the writing-up time, not just the coding time.

### HIGH: do these

| # | Technique | What it buys | Est. build hours | Prerequisites you may not have | Verdict | Key reference |
|---|-----------|--------------|------------------|-------------------------------|---------|---------------|
| 1 | **Frozen scenario suite + cached/replayed model responses, run in CI on every prompt change** | Turns "I tweaked the prompt and it seems better" into a measurable regression signal. This is the load-bearing engineering artefact of the whole project. | 6-10 | None. Works with zero labels. | **HIGH** | https://hamel.dev/blog/posts/evals/ ; caching design: https://inspect.aisi.org.uk/caching.html |
| 2 | **Adversarial simulated user (non-response, recall error, inconsistency, contradiction, refusal)** | Lets you evaluate the *interaction policy*, not just single answers, without needing real sick people. Directly attacks the hardest part of the system. | 8-12 | None. But you must validate it (see #4). | **HIGH** | https://arxiv.org/abs/2306.08550 ; failure modes: https://arxiv.org/abs/2601.17087 |
| 3 | **LLM proposes hypotheses/evidence, small explicit Bayesian network does the inference (pgmpy)** | The "beyond an intro course" centrepiece. Auditable posterior over benign vs concerning causes; the LLM never does arithmetic. | 6-10 | Requires you to hand-specify a small CPT set. That is a feature, not a bug: it is where domain reasoning goes. | **HIGH** | https://arxiv.org/abs/2411.17284 ; https://github.com/pgmpy/pgmpy |
| 4 | **Ablation matrix with paired bootstrap CIs + a cost-controlled trivial baseline** | The single most credible thing in an evaluation section. Includes the baseline that makes your system look bad if it deserves to. | 5-8 | Needs #1 and #2 first. | **HIGH** | https://arxiv.org/abs/2407.01502 (cost-controlled baselines); https://arxiv.org/abs/1909.03004 (reporting) |
| 5 | **Systematic adversarial / prompt-injection suite generated from a taxonomy** | Replaces one demo jailbreak with a matrix of ~40-80 cases and a measured attack success rate. | 5-8 | None. | **HIGH** | https://arxiv.org/abs/2406.13352 ; https://arxiv.org/abs/2506.08837 |
| 6 | **Tracing + per-run cost and latency instrumentation (OTel GenAI semconv or Langfuse)** | Cheap, visibly professional, and enables the accuracy-vs-cost Pareto plot that most student projects never draw. | 3-5 | None. | **HIGH** | https://github.com/open-telemetry/semantic-conventions-genai ; https://github.com/langfuse/langfuse |
| 7 | **Verbalised confidence vs self-consistency vs post-hoc recalibration, measured** | A real, citable empirical finding of your own, on a live open question. Produces a reliability diagram. | 4-6 | Needs ~100-300 labelled *judgements* (not illness episodes) which you can get from synthetic scenarios. | **HIGH** | https://arxiv.org/abs/2306.13063 ; https://arxiv.org/abs/2305.14975 |
| 8 | **Explicit decision-theoretic interruption rule in the Horvitz NEVA form** | Formal criterion for "should I ask the user right now", grounded in a canonical paper, replacing an ad-hoc threshold. | 4-6 | You must assess interruption costs yourself. Acceptable if documented. | **HIGH** | https://arxiv.org/abs/1301.6707 |

### MEDIUM: worth it if hours allow

| # | Technique | What it buys | Est. build hours | Prerequisites you may not have | Verdict | Key reference |
|---|-----------|--------------|------------------|-------------------------------|---------|---------------|
| 9 | **N-of-1 / single-case experimental design framing with a randomisation test on the question policy** | Makes defensible claims from one person's data. Cheap, rarely seen, and directly answers "you only have 3 users". | 4-8 | Requires you to *randomise* something prospectively. Must be designed in before data collection. | **MEDIUM-HIGH** | https://doi.org/10.1136/bmj.h1738 (CENT) ; https://doi.org/10.1016/j.jcbs.2013.10.002 |
| 10 | **Split conformal prediction on a small holdout, reported honestly with the Beta coverage spread** | Distribution-free prediction sets *and* a demonstration that you understand its limits. The honesty is the impressive part. | 4-6 | Needs a genuinely exchangeable labelled calibration set. Physiological time series is not exchangeable. | **MEDIUM (see caveats)** | https://arxiv.org/abs/2107.07511 ; https://github.com/scikit-learn-contrib/MAPIE |
| 11 | **Post-hoc calibration (temperature scaling / isotonic / Venn-Abers) + reliability diagram + Brier decomposition** | Standard, correct, quick. Venn-Abers gives distribution-free *probability* validity rather than set coverage. | 3-5 | Needs labels. Venn-Abers is more label-efficient than conformal sets for binary problems. | **MEDIUM** | https://arxiv.org/abs/1211.0025 ; https://github.com/ip200/venn-abers |
| 12 | **Two-step (non-myopic) lookahead over an explicit belief state for question selection** | Shows you know myopic VoI is a heuristic and that non-myopic VoI is hard. Cheap if the hypothesis set is small. | 6-10 | Needs #3 (an explicit belief state) to exist first. | **MEDIUM** | https://arxiv.org/abs/1207.1394 |
| 13 | **Hierarchical Bayesian partial pooling of per-user baseline parameters across the team** | Correct answer to "very little data per user". Shrinkage toward a population mean is exactly the right story. | 8-14 | Needs >= 3-5 users and enough days each. With 2 users the hierarchy is degenerate and it is theatre. | **MEDIUM** | https://arxiv.org/abs/2011.01808 ; https://github.com/pymc-devs/pymc |
| 14 | **Online per-user Dirichlet/Beta prior over causes (learning "this user drinks on Fridays")** | Personalisation with a closed-form conjugate update. Genuinely small code, genuinely visible behaviour. | 4-6 | Needs the user to actually answer questions repeatedly. | **MEDIUM** | Standard conjugate updating; see https://arxiv.org/abs/2011.01808 for workflow |
| 15 | **Deterministic-replay reproducibility harness (record/replay all LLM calls, pinned model IDs, seeded sampling)** | Makes your numbers re-derivable. Also makes CI fast and free. | 3-5 | None. | **MEDIUM-HIGH but boring to write about** | https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/ |
| 16 | **Conformal risk control instead of conformal prediction sets** | Controls expected loss of a monotone loss (e.g. missed-illness rate) rather than set coverage. Better matched to this problem than vanilla CP. | 5-8 | Same label requirement as CP. | **MEDIUM** | https://arxiv.org/abs/2208.02814 |

### TRAP: do not attempt

| # | Technique | Why it is a trap | Est. hours to do it properly | Verdict |
|---|-----------|------------------|------------------------------|---------|
| T1 | **Adaptive Conformal Inference (ACI) / online conformal under drift** | The update rule is alpha_{t+1} = alpha_t + gamma(alpha - err_t), and err_t requires **observing the true label Y_t at every step** (https://arxiv.org/abs/2106.00170, eq. 2). You will not know daily whether the user was truly getting ill. Without labels ACI is a no-op that drifts on noise. | 15+ and still wrong | **TRAP** |
| T2 | **Solving a POMDP (point-based value iteration, SARSOP, QMDP over a real state space)** | You have no transition model, no observation model, no reward function, and no way to validate any of the three. PBVI-class methods assume all three are given (https://doi.org/10.1016/S0933-3657(99)00042-1 for the medical formulation). | 40+ | **TRAP** |
| T3 | **Active inference / expected free energy as the decision framework** | It is a reframing, not a capability. For discrete problems EFE reduces to information gain plus expected utility, which is what a two-step VoI lookahead already gives you, with far more code and an unfamiliar vocabulary that will read as obfuscation. | 20+ | **TRAP** |
| T4 | **Contextual bandits / RL for notification timing** | Bandit personalisation in mHealth needs hundreds to thousands of decision points per user. HeartSteps-class studies run micro-randomised trials over weeks with dozens of participants (https://doi.org/10.1093/abm/kay067). With 3 users over 4 weeks you have no signal; the regret curve will be noise. | 25+ | **TRAP** |
| T5 | **Off-policy evaluation of the interaction policy (IPS / doubly robust)** | Requires a logged *stochastic* behaviour policy with recorded propensities and enough episodes for the importance weights to have finite variance. You will have neither. | 20+ | **TRAP** |
| T6 | **Automated red-teaming with a trained/optimised attacker (GCG, PAIR-style)** | Optimisation-based attacks need white-box gradients or large query budgets, and HarmBench-class infrastructure (https://arxiv.org/abs/2402.04249). Template-based systematic generation gets you 90% of the credibility for 10% of the cost. | 25+ | **TRAP** |
| T7 | **Fine-tuning an LLM for calibration** | Needs a labelled correctness dataset at a scale you will not have, and destroys reproducibility of the rest of the pipeline. | 30+ | **TRAP** |
| T8 | **Bayesian network *structure* learning from your own data** | Structure learning needs thousands of samples to beat a hand-drawn graph. With one person's 60 days it will produce nonsense you then have to defend. Hand-specify the graph. | 15+ | **TRAP** |
| T9 | **Conformal prediction on the illness label itself** | You will have single-digit to low-double-digit positive episodes. Split conformal at alpha = 0.1 formally requires ceil((n+1)(1-alpha)) <= n, i.e. n >= 9, but at n = 9 the realised coverage is nearly uninformative. See section 3.2. | 5 (and misleading) | **TRAP** |
| T10 | **Building your own observability/tracing UI** | Langfuse, Phoenix and Inspect View exist and are free. Writing your own signals that you did not survey the field. | 15+ | **TRAP** |

---

## 3. Uncertainty quantification and calibration

### 3.1 Conformal prediction: the variants and which are usable

- **Split (inductive) conformal.** Fit a model on a proper training set, compute nonconformity scores on a
 held-out calibration set of size n, take the ceil((n+1)(1-alpha))/n empirical quantile, and form the
 prediction set. Guarantee: marginal coverage >= 1-alpha under exchangeability.
 Source: Angelopoulos and Bates, *A Gentle Introduction to Conformal Prediction and Distribution-Free
 Uncertainty Quantification*, https://arxiv.org/abs/2107.07511 (HTML: https://ar5iv.labs.arxiv.org/html/2107.07511).
 This is the only variant I would consider for this project.
- **Mondrian / class-conditional conformal.** Calibrate separately within each class or group, giving
 class-conditional coverage. Covered in section 4.2 of the same tutorial. Implemented in `crepes`
 ("standard, normalized and Mondrian conformal regressors and predictive systems",
 https://crepes.readthedocs.io/en/latest/). **Warning for this project:** Mondrian splits your already
 tiny calibration set by class, which makes the small-n problem strictly worse.
- **Adaptive Conformal Inference (ACI)** for distribution shift and time series. Gibbs and Candes,
 https://arxiv.org/abs/2106.00170. The update is `alpha_{t+1} := alpha_t + gamma(alpha - err_t)` where
 `err_t` is 1 if `Y_t` fell outside the set. **You must observe `Y_t` every step.** See T1.
- **Conformal PID control**, Angelopoulos, Candes, Tibshirani, https://arxiv.org/abs/2307.16895:
 a control-theoretic generalisation of ACI. Same label requirement.
- **Conformal prediction beyond exchangeability**, Barber, Candes, Ramdas, Tibshirani,
 https://arxiv.org/abs/2202.13415: weighted conformal with a coverage gap bounded by the distance between
 the shifted and original distributions. Honest, but the bound is usually vacuous in practice without an
 estimate of the shift.
- **Conformal Risk Control**, Angelopoulos et al., https://arxiv.org/abs/2208.02814: extends conformal to
 control the expected value of *any monotone loss*, tight up to O(1/n). For this project this is the
 better-matched object: you care about controlling missed-illness rate, not set size.
- **Venn-Abers predictors**, Vovk and Petej, https://arxiv.org/abs/1211.0025: distribution-free *calibrated
 probabilities* (not sets) for binary problems, via isotonic regression fitted both ways. More
 label-efficient than conformal sets when you only need a probability. Python:
 https://github.com/ip200/venn-abers. A 2026 benchmark of 21 classifiers and 8 calibration methods on
 tabular data covers conformal and Venn-based methods head to head: https://arxiv.org/abs/2601.19944.
- **Conformal prediction for LLMs.** Multiple-choice QA: https://arxiv.org/abs/2305.18404. Black-box
 correctness coverage via self-consistency (ConU): https://arxiv.org/abs/2407.00499. Enhanced validity
 methods: https://arxiv.org/abs/2406.09714. Domain-shift-aware CP for LLMs:
 https://arxiv.org/abs/2510.05566. These are relevant if you conformalise the *agent's assessment label*
 rather than the physiology.

### 3.2 ANSWER TO QUESTION 2: is conformal prediction practical here, and when does it degrade to useless?

**Short answer: usable as a demonstration of statistical literacy, not as a safety guarantee, and only if
you report its degradation honestly.**

The hard numbers, all from Angelopoulos and Bates (https://ar5iv.labs.arxiv.org/html/2107.07511):

1. **Formal minimum n.** The quantile level is `ceil((n+1)(1-alpha))/n`. For this to be <= 1 you need
 `ceil((n+1)(1-alpha)) <= n`. At alpha = 0.1 that means n >= 9. Below that, split conformal cannot
 produce a finite set at all and must output "everything".
2. **Coverage is random, and its randomness is exactly quantified.** Conditional on the calibration set,
 `P(Y_test in C(X_test) | calibration set) ~ Beta(n+1-l, l)` where `l = floor((n+1)*alpha)`. Marginal
 coverage >= 1-alpha holds *in expectation over calibration draws*. Your single realised draw does not
 inherit that.
3. **The practical table.** To get realised coverage within `1-alpha +/- 0.05` with probability 0.9 you
 need **n = 102**. For `+/-0.01` you need **n = 2,491**. Their stated rough guideline: "choosing n=1000
 calibration points leads to coverage that is typically between .88 and .92" at alpha = 0.1.

**Where it degrades to uselessness for this project specifically:**

- **Fewer than ~50 labelled examples.** At n = 20 the Beta spread is so wide that the realised coverage
 could plausibly be anywhere from roughly 0.75 to 0.99. A "90% guarantee" claim is then rhetorically true
 and practically empty.
- **Exchangeability is violated by construction.** Consecutive days of one person's HRV are strongly
 autocorrelated and non-stationary (training blocks, seasonal effects, device firmware changes). Split
 conformal's guarantee assumes exchangeability of calibration and test points. Barber et al.
 (https://arxiv.org/abs/2202.13415) show the coverage gap is bounded by the distributional distance,
 which for a drifting personal baseline is unbounded in practice.
- **Class imbalance.** With a handful of positives, any class-conditional (Mondrian) variant is dead on
 arrival, and the marginal variant will achieve its coverage almost entirely by covering the majority
 class, which is uninformative.
- **The label is not crisp.** "Was the user actually getting ill on day t" is not a clean ground truth.
 Conformal inherits every ambiguity in your labelling protocol and adds a false veneer of rigour on top.

**The defensible way to use it anyway (recommended, ~4-6 hours):** apply split conformal to a *synthetic
or semi-synthetic* labelled set where you control the ground truth, report the realised coverage alongside
the theoretical Beta interval for your n, and write a short paragraph explaining exactly why you do **not**
claim the guarantee transfers to the real deployment. That paragraph is worth more to a reviewer than the
method itself. Consider **conformal risk control** (https://arxiv.org/abs/2208.02814) or **Venn-Abers**
(https://arxiv.org/abs/1211.0025) over vanilla CP, since both are better matched to a binary decision with
an asymmetric loss.

**Libraries (all verified live 2026-08-30):**

| Library | URL | Stars | Licence | Notes |
|---|---|---|---|---|
| MAPIE | https://github.com/scikit-learn-contrib/MAPIE | 1,584 | BSD-3-Clause | scikit-learn compatible; regression, classification, time series, risk control. v1 API released 2025. Docs: https://mapie.readthedocs.io/ |
| crepes | https://github.com/henrikbostrom/crepes | 581 | BSD-3-Clause | Standard, normalized and **Mondrian** conformal regressors, classifiers and conformal predictive systems. Lightest API. |
| TorchCP | https://github.com/ml-stat-Sustech/TorchCP | 477 | see repo | PyTorch-native, research-oriented |
| puncc | https://github.com/deel-ai/puncc | 403 | see repo | DEEL AI; broad method coverage |
| venn-abers | https://github.com/ip200/venn-abers | 207 | MIT | Binary and multi-class Venn-ABERS calibration |
| nonconformist | https://github.com/donlnz/nonconformist | 479 | see repo | **Unmaintained since 2021.** Do not use. |
| awesome-conformal-prediction | https://github.com/valeman/awesome-conformal-prediction | 1,296 | - | Curated index, actively maintained |

### 3.3 Calibration methods and the known flaws of ECE

- **Post-hoc methods.** Temperature scaling, Platt scaling, isotonic regression. A 2026 head-to-head of 21
 classifiers and 8 model-agnostic post-hoc methods on real i.i.d. tabular data, including conformal and
 Venn-based approaches: https://arxiv.org/abs/2601.19944.
- **ECE is a biased estimator and you should say so.** Nixon et al., *Measuring Calibration in Deep
 Learning*, https://arxiv.org/abs/1904.01685, document binning-scheme sensitivity. Kumar, Liang and Ma,
 *Verified Uncertainty Calibration*, https://arxiv.org/abs/1909.10155, show that the standard plug-in ECE
 estimator systematically *underestimates* true calibration error and propose a debiased estimator plus
 scaling-binning. A 2024 information-theoretic analysis of ECE's estimation bias under uniform-width vs
 uniform-mass binning: https://arxiv.org/abs/2405.15709.
- **A sharper framing for an LLM system:** a 2026 paper decomposes LLM "calibration" via signal detection
 theory into *sensitivity* (can it discriminate right from wrong) and *bias* (does it lean confident),
 arguing ECE conflates the two: https://arxiv.org/abs/2603.14893. Reporting AUROC (discrimination) and
 ECE (calibration) separately is correct practice and costs you nothing.
- **Proper scoring rules.** Gneiting and Raftery, *Strictly Proper Scoring Rules, Prediction, and
 Estimation*, JASA 2007, https://doi.org/10.1198/016214506000001437. Report Brier score with its Murphy
 decomposition (reliability, resolution, uncertainty) rather than ECE alone. Cheap and correct.

### 3.4 Calibration of LLM-expressed confidence: what the evidence actually says

This is one of the most useful sections for the project because the evidence is recent, mixed, and you can
add a data point of your own.

- **Xiong et al., ICLR 2024, *Can LLMs Express Their Uncertainty?*** https://arxiv.org/abs/2306.13063.
 Benchmarks prompting strategies x sampling x aggregation across five datasets and five LLMs including
 GPT-4. Verified findings from the paper text:
 - "LLMs, when verbalizing their confidence, tend to be overconfident, potentially imitating human
 patterns of expressing confidence."
 - ECE > 0.25 on several of the harder task groups (Professional Law, Business Ethics, Date Understanding).
 - Calibration and failure prediction improve with model capability but remain "far from ideal": roughly
 22.2% AUROC improvement from GPT-3 to GPT-4.
 - Black-box vs white-box gap is narrow: "0.522 to 0.605 in AUROC".
 - "none of these techniques consistently outperform others".
 Code: https://github.com/MiaoXiong2320/llm-uncertainty
- **Tian et al., *Just Ask for Calibration*,** https://arxiv.org/abs/2305.14975. For RLHF-tuned models
 (ChatGPT, GPT-4, Claude) "verbalized confidences emitted as output tokens are typically better-calibrated
 than the model's conditional probabilities on the TriviaQA, SciQ, and TruthfulQA benchmarks, often
 reducing the expected calibration error by a relative 50%." They also find (their Figure 5) that ECE is
 **not** consistently improved by any chain-of-thought prompt variant on gpt-3.5-turbo, which is a useful
 negative result to cite.
- **Reconciling the two:** verbalised confidence is better than the RLHF model's own logits, and still
 overconfident in absolute terms. Both can be true.
- **Methods that measurably help:**
 - *Self-consistency / sampling-based agreement.* Central to Xiong et al.'s black-box framework. Caveat
 from 2026 work: self-consistency "collapses when models are overconfident and produce the same
 incorrect answer" across samples, and cross-model disagreement is a complementary signal:
 https://arxiv.org/abs/2604.17112.
 - *Asking for top-k alternatives / multi-step decomposition* to counteract overconfidence (Xiong et al.,
 Top-K and Multi-Step prompting sections).
 - *Self-generated distractors* to calibrate verbalised confidence: https://arxiv.org/abs/2509.25532.
 - *Order-aware alignment of verbalised confidence (ORCE, 2026):* https://arxiv.org/abs/2605.12446.
 - *Aligning verbalised with internal confidence:* https://arxiv.org/abs/2512.11998.
 - *Perturbation-based UQ (SPUQ):* https://arxiv.org/abs/2403.02509.
 - Survey: https://arxiv.org/abs/2311.08298.

**Concrete 4-6 hour experiment for this project:** build 150-300 synthetic scenarios with known ground
truth (benign confounder vs early illness), elicit (a) raw verbalised confidence, (b) verbalised + top-k,
(c) self-consistency over 5 samples, (d) (c) then temperature-scaled on a 60/40 split. Plot four
reliability diagrams, report ECE (with the debiased estimator), Brier, and AUROC. That is a real result.

### 3.5 Presenting calibrated uncertainty to a non-expert without alarming or boring them

There is a mature evidence base here and almost no student project uses it.

- **Communicating uncertainty does not destroy trust, and the effect size is small.** van der Bles,
 van der Linden, Freeman and Spiegelhalter, PNAS 2020, *The effects of communicating uncertainty on public
 trust in facts and numbers*, https://doi.org/10.1073/pnas.1913678117. Companion conceptual framework:
 *Communicating uncertainty about facts, numbers and science*, Royal Society Open Science 2019,
 https://doi.org/10.1098/rsos.181870. Practical read: **numeric ranges are better than vague verbal
 hedges**, and the trust penalty for stating uncertainty is modest.
- **Natural frequencies beat probabilities for lay comprehension.** Gigerenzer and Edwards, *Simple tools
 for understanding risks: from innumeracy to insight*, BMJ 2003, https://doi.org/10.1136/bmj.327.7417.741.
 Gigerenzer et al., *Helping Doctors and Patients Make Sense of Health Statistics*, Psychological Science
 in the Public Interest 2007, https://doi.org/10.1111/j.1539-6053.2008.00033.x. Say "in 100 mornings that
 looked like this one, about 15 turned out to be the start of something" rather than "P = 0.15".
- **Verbal probability words are interpreted inconsistently.** Studies of "words of estimative probability"
 show wide variance in how people map phrases to numbers, e.g. National Weather Service usage:
 https://doi.org/10.15191/nwajom.2020.0805. Implication: pair every verbal label with a number, and use a
 fixed, published lexicon.
- **Uncertainty visualisation.** Spiegelhalter, Pearson and Short, *Visualizing Uncertainty About the
 Future*, Science 2011, https://doi.org/10.1126/science.1191181. Icon arrays for medical risk:
 https://doi.org/10.1177/0272989X241263040 ; icon arrays vs bar charts:
 https://doi.org/10.1109/tvcg.2025.3634630.
- **Prediction sets can help human decisions.** *Conformal Prediction Sets Improve Human Decision Making*,
 https://arxiv.org/abs/2401.13744. Useful if you present a *set* of candidate causes rather than a single
 point verdict.

**Design implication for this project:** present (1) a natural-frequency statement, (2) the top two or
three candidate causes as a set rather than a single verdict, (3) the specific observation that drove it
("your resting HR is 8 bpm above your 30-day median"), and (4) an explicit action threshold. Do not present
a bare percentage and do not present a bare verbal hedge.

---

## 4. Bayesian personalisation and N-of-1 methodology

### 4.1 Hierarchical / partial pooling with very little data per user

- **Bayesian Workflow**, Gelman et al., https://arxiv.org/abs/2011.01808, is the correct citation for the
 process (prior predictive checks, fitting, diagnostics, posterior predictive checks, model expansion).
 *Visualization in Bayesian workflow*, https://arxiv.org/abs/1709.01449. Visual predictive check
 recommendations, 2025: https://arxiv.org/abs/2503.01509.
- **The partial-pooling argument for this project:** with 3-5 team members and ~30-60 days each, a
 multilevel model with per-user intercepts and slopes drawn from a population distribution gives each
 user's baseline the benefit of the group without forcing them to be identical. This is the textbook
 answer to "very little data per user" and it is easy to explain in a report.
- **Honest limit:** with 2 users the population level is unidentified and the hierarchy is decoration.
 With 3-5 it is defensible but the population variance will be poorly estimated. Say so.
- **Tooling** (verified 2026-08-30): PyMC https://github.com/pymc-devs/pymc (9,731 stars),
 NumPyro https://github.com/pyro-ppl/numpyro (2,750, Apache-2.0),
 Bambi https://github.com/bambinos/bambi (1,297, MIT, formula interface, lowest friction for a
 multilevel model), ArviZ https://github.com/arviz-devs/arviz (1,851, Apache-2.0, diagnostics and
 posterior plots). For a hierarchical model on ~500 rows, Bambi + ArviZ is a few hours; hand-written PyMC
 is about a day.

### 4.2 Online Bayesian updating of a per-user prior over causes

This is the cheapest genuinely-personalised thing in the whole brief and I recommend it.

Maintain a Dirichlet posterior over cause categories (alcohol, hard training, poor sleep, stress, illness,
other), optionally conditioned on day-of-week. Each confirmed user answer is a categorical observation;
the update is `alpha_c := alpha_c + 1`, closed form, no sampler. After three weeks the system genuinely
"knows" this user drinks on Fridays and trains on Tuesdays, and you can *show* the prior shifting.
Estimated 4-6 hours including the visualisation. There is no exotic paper to cite here, which is fine:
cite the Bayesian workflow paper for the methodology and let the behaviour speak.

Related published direction: AdaptFuse, training-free sequential preference learning via externalised
Bayesian inference, motivated explicitly by the fact that LLMs "fail to update their beliefs in a manner
consistent with Bayesian inference": https://arxiv.org/abs/2604.03925.

### 4.3 ANSWER TO QUESTION 3: lightweight, credible LLM + explicit probabilistic inference

**Yes, and this should be the technical centrepiece of the project.**

The pattern: the LLM does what it is good at (reading messy natural-language context, proposing candidate
explanations, mapping a user's free-text answer onto structured evidence) and a small explicit
probabilistic model does what LLMs are bad at (consistent arithmetic belief updating over a small
hypothesis set). The posterior is then auditable, reproducible, and independent of prompt wording.

**Concrete published precedents with URLs:**

| Work | What it does | URL |
|---|---|---|
| **AutoElicit** (Capstick et al.) | Uses an LLM to elicit *expert priors* for a predictive model, then does standard Bayesian inference. Motivated explicitly by healthcare settings where interpretability and privacy matter. Closest published analogue to what you should build. | https://arxiv.org/abs/2411.17284 |
| **From Word Models to World Models** (Wong, Grand, Lew, Goodman, Mansinghka, Andreas, Tenenbaum) | "Rational meaning construction": the LLM translates natural language into a probabilistic program, and a probabilistic programming engine does the inference. The canonical statement of this architecture. | https://arxiv.org/abs/2306.12672 |
| **LLM-BI** | Uses an LLM to automate prior and likelihood specification for Bayesian inference, addressing the specification bottleneck directly. | https://arxiv.org/abs/2508.08300 |
| **LLM-Prior** | Framework for knowledge-driven prior elicitation and aggregation with LLMs. | https://arxiv.org/abs/2508.03766 |
| **Eliciting the Priors of LLMs using Iterated In-Context Learning** | Prompt-based workflow for extracting Bayesian prior distributions from an LLM. | https://arxiv.org/abs/2406.01860 |
| **LLM Processes** | Numerical predictive *distributions* conditioned on natural language. | https://arxiv.org/abs/2405.12856 |
| **SMC Steering of LLMs using Probabilistic Programs** (Lew et al.) | Sequential Monte Carlo over LLM generation specified as a probabilistic program. Heavier, but the reference for constrained generation as inference. | https://arxiv.org/abs/2306.03081 |
| **Verbalized Particle Posterior** (2026) | Bayesian inference over natural-language hypotheses; maintains a particle set instead of committing to one hypothesis. Directly relevant to "the LLM proposes hypotheses, the probabilistic layer keeps a posterior over them". | https://arxiv.org/abs/2607.22961 |

**Recommended concrete design (est. 6-10 hours):**

1. Hand-specify a small discrete Bayesian network in **pgmpy** (https://github.com/pgmpy/pgmpy, 3,321
 stars, MIT, described as a "Python Toolkit for Causal and Probabilistic Reasoning"): root node = cause
 (5-7 mutually exclusive-ish states), child nodes = observable deviations (resting HR elevated, HRV
 suppressed, respiratory rate elevated, sleep disrupted), plus answer nodes for user responses.
2. The LLM's *only* probabilistic job is to emit structured evidence, e.g. `{"alcohol_last_night": true,
 "confidence": 0.8}`, from the user's free text. It never multiplies anything.
3. Run exact inference (variable elimination) to get P(cause | evidence). pgmpy does this in milliseconds
 for a graph this small.
4. The question-selection policy uses expected information gain computed **on the network**, not on an
 LLM's opinion. This makes the VoI computation real rather than vibes.
5. Log both the LLM's raw output and the resulting posterior so the audit trail is complete.

**Why this is the right answer for a reviewer:** it demonstrates you understand the failure mode (LLMs are
inconsistent probabilistic reasoners), you chose an architecture that fixes it, and the fix is
inspectable. It also gives you an ablation axis for free (LLM-only posterior vs LLM+BN posterior), which
feeds directly into section 6.

### 4.4 N-of-1 and single-case experimental design: how to make defensible claims from one person

This is under-used and directly answers the obvious criticism of a self-experiment.

- **CENT 2015: CONSORT extension for reporting N-of-1 trials.** Shamseer et al., BMJ 2015,
 https://doi.org/10.1136/bmj.h1738. Explanation and elaboration: https://doi.org/10.1136/bmj.h1793
 (also https://doi.org/10.1016/j.jclinepi.2015.05.018). Reading and following a real reporting checklist
 is a strong, cheap credibility signal.
- **SCRIBE 2016: Single-Case Reporting guideline In BEhavioural interventions.** Tate et al.,
 https://doi.org/10.1016/j.jclinepi.2016.04.006 ; explanation and elaboration:
 https://doi.org/10.1037/arc0000027.
- **Randomisation tests for single-case designs.** Heyvaert and Onghena, *Randomization tests for
 single-case experiments: State of the art, state of the science, and state of the application*,
 https://doi.org/10.1016/j.jcbs.2013.10.002. The critical insight: **if you randomise the intervention
 schedule prospectively, you get an exact permutation-based p-value from a single participant, with no
 distributional assumptions.** R package: https://doi.org/10.3758/brm.40.2.467.
- **Serial correlation matters.** N-of-1 data are autocorrelated and naive t-tests are anticonservative:
 https://arxiv.org/abs/1904.01622.
- **Digital N-of-1 trials in experimental physiology** (2024), directly on point for wearable-based
 personal experimentation: https://arxiv.org/abs/2412.15076.
- **Multimodal N-of-1 trials** for mHealth: https://arxiv.org/abs/2302.07547.
- **Design-based inference for time-series / switchback / N-of-1 experiments** (2025):
 https://arxiv.org/abs/2510.22864.

**Concrete application here (est. 4-8 hours, but must be designed BEFORE data collection):** randomise, per
morning, whether the agent uses policy A (always ask a clarifying question when a deviation is detected) or
policy B (ask only when expected information gain exceeds a threshold). Pre-register the randomisation
schedule. At the end, a randomisation test on the outcome (e.g. number of false alarms escalated to the
user, or user-rated usefulness) gives an exact p-value from n = 1. This is a genuinely rigorous claim from
one person's data and almost no student project does it.

**Related design literature worth one paragraph in the report:** micro-randomised trials and JITAIs.
Klasnja et al., *Microrandomized trials: An experimental design for developing just-in-time adaptive
interventions*, Health Psychology 2015, https://doi.org/10.1037/hea0000305. Nahum-Shani et al., *JITAIs in
Mobile Health*, Annals of Behavioral Medicine 2016, https://doi.org/10.1007/s12160-016-9830-8.
HeartSteps micro-randomised optimisation trial: https://doi.org/10.1093/abm/kay067. Cite these to show you
know what the properly-powered version of your experiment looks like, then explain why you are doing the
N-of-1 version instead.

---

## 5. Sequential decision making beyond myopic value of information

### 5.1 The key theoretical fact you should cite

**Non-myopic VoI is hard, and this is proved.** Krause and Guestrin, *Near-optimal Nonmyopic Value of
Information in Graphical Models*, https://arxiv.org/abs/1207.1394 (357 citations). They establish hardness
results for selecting the most informative subset of variables in a graphical model, and give near-optimal
approximation algorithms under specific structural conditions. Related: *Near-Optimal Sensor Placements in
Gaussian Processes*, https://doi.org/10.1145/1102351.1102385 (KDD 2005 version; JMLR 2008 journal version
also exists). The practical upshot for this project: **greedy one-step VoI is not just a lazy choice, it
is a principled one, and citing the hardness result is how you say that without sounding lazy.**

### 5.2 POMDP formulations and cheap approximations

- **The canonical medical POMDP.** Hauskrecht and Fraser, *Planning treatment of ischemic heart disease
 with partially observable Markov decision processes*, Artificial Intelligence in Medicine 2000,
 https://doi.org/10.1016/S0933-3657(99)00042-1 (178 citations). Cite this when you say "the fully general
 formulation of this problem is a POMDP".
- **Point-based value iteration.** Pineau, Gordon and Thrun, PBVI (IJCAI 2003, 933 citations per OpenAlex).
 Anytime approximate POMDP solver over a sampled belief set. OpenAlex returned no DOI and no OA URL for
 this record, so treat the exact citation string as UNVERIFIED.
- **What to actually do:** a **two-step lookahead** over an explicit belief state from the Bayesian network
 in 4.3. At each step: for each candidate question, enumerate possible answers, compute the resulting
 posterior, compute the expected value of the best terminal action, and optionally do one more level.
 With 5-7 causes and 4-6 candidate questions this is a trivial loop, runs in milliseconds, and lets you
 write "we implement a two-step lookahead approximation to the full POMDP, motivated by the hardness of
 non-myopic subset selection (Krause and Guestrin)". Est. 6-10 hours on top of the BN. **MEDIUM**.
- **QMDP** (assume full observability after one step) is even cheaper and is a reasonable second baseline.
 It is a well-known approximation, but I did not locate a canonical open-access primary URL during this
 session. UNVERIFIED as to a specific citation.
- **Bayesian optimal experimental design is the better framing than POMDP for this problem.** Rainforth,
 Foster, Ivanova and Bickford Smith, *Modern Bayesian Experimental Design*,
 https://arxiv.org/abs/2302.14545, is a review of exactly "which question should I ask next to maximise
 expected information gain". Amortised sequential design (Deep Adaptive Design):
 https://arxiv.org/abs/2103.02438 ; implicit-model version: https://arxiv.org/abs/2111.02329.
 **Read the review, cite it, implement the simple greedy EIG.** DAD itself is a trap: it requires
 training a design policy network.

### 5.3 Active inference / expected free energy: usable or theoretical?

**Verdict: mostly theoretical for your purposes, and a poor use of hours.**

- Active inference frames action selection as minimising expected free energy, which decomposes into an
 epistemic (information-seeking) term and a pragmatic (goal-seeking) term. Framed as convex MDP policy
 optimisation in 2026 work: https://arxiv.org/abs/2607.20152.
- **The comparison with RL has been done and does not favour AIF on practical grounds.** *Active inference:
 demystified and compared*, https://arxiv.org/abs/1909.10863, compares AIF and RL on the same
 discrete-state environments. *Deconstructing deep active inference*, https://arxiv.org/abs/2303.01618,
 examines what actually drives performance in scaled-up deep AIF.
- For a discrete hypothesis set with a small action set, the EFE epistemic term **is** expected information
 gain, which is what a greedy VoI policy already computes. You would be paying an unfamiliar vocabulary
 tax for no additional capability.
- **How to use it anyway, for free:** one paragraph in the report noting that the ask/don't-ask criterion
 can be read as expected-free-energy minimisation, with the epistemic term corresponding to expected
 information gain and the pragmatic term to the cost of interruption. That earns the intellectual credit
 without the implementation cost.

### 5.4 Cost-sensitive sequential feature acquisition and medical test selection

- Melville, Saar-Tsechansky, Provost and Mooney, *Active Feature-Value Acquisition*, Management Science
 2009, https://doi.org/10.1287/mnsc.1080.0952 ; earlier ICDM version https://doi.org/10.1109/ICDM.2004.10075
 (PDF: http://archive.nyu.edu/bitstream/2451/27801/2/CPP-06-04.pdf); *An Expected Utility Approach to
 Active Feature-Value Acquisition*, https://doi.org/10.1109/ICDM.2005.23. This is the right lineage:
 acquiring features has a cost, and you choose the acquisition that maximises expected utility.
- *Opportunistic Learning: Budgeted Cost-Sensitive Learning from Data Streams*,
 https://arxiv.org/abs/1901.00243: acquires features incrementally at prediction time under a budget via
 a context-aware feature-value function.
- *Cost-Sensitive Diagnosis and Learning Leveraging Public Health Data*, https://arxiv.org/abs/1902.07102:
 explicitly motivated by monetary cost, patient discomfort and privacy impact of data collection. The
 "patient discomfort" framing maps directly onto "cost of interrupting the user with a question", which is
 a nice bridge to section 9.

**Direct relevance:** your clarifying question *is* a feature acquisition with a non-monetary cost. Framing
it that way, with these citations, is worth more than any additional code.

### 5.5 Bandits with a query budget and notification timing

Covered for completeness, but see T4: this is a trap at your scale.

- Tewari and Murphy, *From Ads to Interventions: Contextual Bandits in Mobile Health*,
 https://doi.org/10.1007/978-3-319-51394-2_25.
- Liao, Greenewald, Klasnja and Murphy, *Personalized HeartSteps: A Reinforcement Learning Algorithm for
 Optimizing Physical Activity*, https://arxiv.org/abs/1909.03539.
- Thompson sampling for zero-inflated count outcomes, Drink Less mHealth study:
 https://arxiv.org/abs/2311.14359.
- Thompson sampling with BART for non-linear mHealth reward models (2026):
 https://arxiv.org/abs/2602.07767.
- Real-world receptivity to adaptive mental-health interventions, in-the-wild:
 https://arxiv.org/abs/2508.02817.
- Off-policy evaluation infrastructure if you ever had the data: Open Bandit Dataset and Pipeline,
 https://arxiv.org/abs/2008.07146 ; doubly robust with shrinkage, https://arxiv.org/abs/1907.09623 ;
 more robust DR, https://arxiv.org/abs/1802.03493 ; DR OPE for healthcare policies,
 https://arxiv.org/abs/2412.08052.

**Verdict:** cite Tewari and Murphy in a "what the properly-powered version looks like" paragraph, then
explain that with N = 3 over four weeks you have on the order of 100 decision points total, which is one to
two orders of magnitude short of what a contextual bandit needs. That paragraph is more impressive than a
bandit that does not work.

---

## 6. Rigorous evaluation of interactive and agentic systems

### 6.1 ANSWER TO QUESTION 4: what a genuinely credible ablation looks like

**The three properties that separate a credible ablation from a decorative one:**

1. **It includes a baseline that could beat you.** The canonical demonstration is Kapoor, Stroebl, Siegel,
 Nadgir and Narayanan, *AI Agents That Matter*, https://arxiv.org/abs/2407.01502. Their finding: they
 introduce "three new simple baseline agents and empirically show that they outperform many SoTA complex
 agent architectures on HumanEval while costing much less". Their conclusion, quoted: "SOTA agents are
 needlessly complex and costly, and the community has reached mistaken conclusions about the sources of
 accuracy gains." Every component you ablate must be compared against a cheap alternative that does the
 same job badly, not against nothing.
2. **It is cost-controlled.** Same paper: "AI agent evaluations must be cost-controlled" because "simply
 calling the underlying model multiple times can increase accuracy". If your clarifying-question module
 makes three extra LLM calls, it must be compared against a no-question variant that also makes three
 extra calls. Otherwise you are measuring compute, not design.
3. **It reports variance across repeated runs, not a single number.** Henderson et al., *Deep Reinforcement
 Learning that Matters*, https://arxiv.org/abs/1709.06560, and Dodge et al., *Show Your Work: Improved
 Reporting of Experimental Results*, https://arxiv.org/abs/1909.03004, which shows that test-set scores
 alone are insufficient for comparing methods and proposes reporting performance as a function of
 compute budget.

**Two published concrete examples you can copy the shape of:**

*Example A, the crossed ablation (closest structural analogue to your system).* Montazeralghaem,
Tennenholtz, Boutilier and Meshi (Google), *Asking Clarifying Questions for Preference Elicitation With
Large Language Models*, https://arxiv.org/abs/2510.12015. They evaluate a "Questioner" model against a
"user simulator", and critically they **cross both axes**: fine-tuned Questioner vs base Questioner, times
fine-tuned Gemma simulator vs non-fine-tuned Gemini simulator (their Figure 3a). The point of the crossing
is to show the gain is a property of the Questioner and not an artefact of a simulator that happens to be
easy for it. They also report "percentage of unanswered questions" as a secondary metric, i.e. they measure
the *failure mode of the interaction itself*, not just end accuracy.

**This is exactly the ablation you should run.** Your version:

| Variant | Deviation detector | Clarifying question | Probabilistic layer (BN) | Retrieval/grounding | Human checkpoint |
|---|---|---|---|---|---|
| V0 Trivial baseline | fixed z-score threshold | none | none | none | always escalate |
| V1 LLM-only | LLM reads raw numbers | LLM decides | none | none | yes |
| V2 + detector | statistical | LLM decides | none | none | yes |
| V3 + BN | statistical | LLM decides | yes | none | yes |
| V4 + VoI question policy | statistical | EIG-driven | yes | none | yes |
| V5 Full | statistical | EIG-driven | yes | yes | yes |

Run each variant over the frozen scenario suite x N simulated-user seeds x 2 user-simulator backends.
Report, for each cell: task metric, false-alarm rate, questions asked per episode, tokens, dollars,
wall-clock, and a paired bootstrap 95% CI on the difference from the variant one row above. The paired
bootstrap is essential: the variants see the same scenarios, so a paired test is far more powerful than an
unpaired one at your sample size.

*Example B, the "your gains vanish against tuned baselines" cautionary result.* Ferrari Dacrema, Cremonesi
and Jannach, *Are we really making much progress? A worrying analysis of recent neural recommendation
approaches*, RecSys 2019, https://doi.org/10.1145/3298689.3347058 (PDF: https://arxiv.org/pdf/1907.06902),
and Musgrave, Belongie and Lim, *A Metric Learning Reality Check*, ECCV 2020,
https://arxiv.org/abs/2003.08505. Cite one of these in your evaluation section as the reason you included
V0.

### 6.2 Simulated user design: how to model non-response, recall error and inconsistency

**The reference text.** Balog and Zhai, *User Simulation for Evaluating Information Access Systems*,
https://arxiv.org/abs/2306.08550. A full-length monograph on simulator design and validation for search,
recommendation and conversational assistants, and the right thing to cite for methodology.

**Mature practice from task-oriented dialogue:**
- LLM-based user simulators for TOD evaluation: https://arxiv.org/abs/2309.13233 ;
 https://arxiv.org/abs/2402.13374 ; metaphorical user simulators: https://arxiv.org/abs/2204.00763.
- **Non-cooperative and emotional users are an explicit research topic.** *Towards Emotion-Aware User
 Simulator for Task-Oriented Dialogue*, https://arxiv.org/abs/2011.09696, notes that "existing
 off-the-shelf user simulators generally assume an ideal and cooperative" user and that early termination
 in disappointing conversations is a real behaviour to model.
- Agent-user interaction benchmark with an LLM-simulated user: tau-bench,
 https://arxiv.org/abs/2406.12045. It introduces a reliability metric over repeated trials (pass^k).

**The critical skeptical evidence you must engage with:**
- **Seshadri et al. (Cohere / UC Irvine), *Lost in Simulation: LLM-Simulated Users are Unreliable Proxies
 for Human Users in Agentic Evaluations*, https://arxiv.org/abs/2601.17087.** Verified findings: agent
 success rates vary "up to 9 percentage points across different user LLMs"; simulated-user evaluation is
 "systematically miscalibrated, underestimating agent performance on challenging tasks and overestimating
 it on moderately difficult ones"; AAVE speakers get "consistently worse success rates and calibration
 errors" than SAE speakers; simulated users "introduce conversational artifacts and surface different
 failure patterns than human users", including increased question-asking and politeness.
- **Dou et al. (Georgia Tech / Microsoft), *SimulatorArena*, https://arxiv.org/abs/2510.05444.** More
 optimistic: a benchmark of 909 annotated human-LLM conversations finds that simulators **conditioned on
 explicit user profiles** (background, message style) reach Spearman's rho of 0.7 with human judgments on
 both tasks studied, and are "a practical, scalable alternative to human evaluation".

**Synthesis and concrete design for this project (est. 8-12 hours):** build a **persona-conditioned**
simulator (per SimulatorArena's finding that profiles are what makes simulators track humans) with an
explicit behaviour model rather than a free-form prompt:

- `p_nonresponse`: probability of not answering at all, varying by simulated time of day.
- `p_recall_error`: probability the answer is wrong about last night (e.g. reports "no alcohol" when the
 hidden state says two drinks). Recall error should be *asymmetric*, since under-reporting alcohol is more
 likely than over-reporting.
- `p_inconsistency`: probability of contradicting a previous session's answer.
- `verbosity` and `hedging`: some personas answer "maybe a bit", not "yes".
- `hostility`: some personas tell the agent to stop bothering them.
- A hidden ground-truth state that the simulator answers *about* but does not reveal, so you can score the
 agent's posterior against truth.

Then **run the whole ablation under two different simulator backends** and report both, explicitly citing
*Lost in Simulation* as the reason. Doing this, and stating the 9-percentage-point robustness figure as
your justification, is a stronger evaluation-methodology signal than any modelling technique in this
document.

### 6.3 Agent benchmarking practice in 2025-2026, and the standard criticisms

- **Kapoor et al., *AI Agents That Matter*, https://arxiv.org/abs/2407.01502.** Five criticisms: (1) narrow
 focus on accuracy without cost, leading to "needlessly complex and costly" agents; (2) conflation of
 model-developer and downstream-developer benchmarking needs; (3) inadequate or absent holdout sets,
 producing agents that "take shortcuts and overfit to the benchmark"; (4) lack of standardisation causing
 "a pervasive lack of reproducibility"; (5) the case for jointly optimising accuracy and cost as a Pareto
 curve.
- **Zhu et al., *Establishing Best Practices for Building Rigorous Agentic Benchmarks*,
 https://arxiv.org/abs/2507.02825.** Introduces the **Agentic Benchmark Checklist (ABC)**. Verified
 concrete findings: "SWE-bench-Verified uses insufficient test cases, while tau-bench counts empty
 responses as successful"; such issues "can lead to under- or overestimation of agents' performance by up
 to 100% in relative terms"; applying ABC to CVE-Bench "reduces the performance overestimation by 33%".
 **Use ABC as a literal checklist for your own eval harness.** Cheap and highly legible.
- **LLM-as-judge reliability is a live problem, with 2026 numbers.** *Reliability without Validity: A
 Systematic, Large-Scale Evaluation of LLM-as-a-Judge Models Across Agreement, Consistency, and Bias*,
 https://arxiv.org/abs/2606.19544, evaluates 21 judges from nine providers and argues that exact-match
 agreement "does not correct for chance and systematically overstates discriminative ability".
 *The Coin Flip Judge?*, https://arxiv.org/abs/2606.13685, characterises run-to-run reliability over 29
 tasks with 50 pairwise and 50 pointwise trials. Scoring bias: https://arxiv.org/abs/2506.22316.
 Automated bias detection: https://arxiv.org/abs/2602.09383. Aligning judges with humans: Shankar et al.,
 *Who Validates the Validators?*, https://arxiv.org/abs/2404.12272.
- **Practitioner guidance that matches the research.** Hamel Husain,
 https://hamel.dev/blog/posts/evals-faq/ : measure judge "TPR and TNR ... on a held out labeled test set";
 "Generic evaluations waste time and create false confidence"; for multi-turn, "Annotate only the first
 failure in the trace initially" since "downstream failures often cascade from the first issue".
 Eugene Yan on evaluating evaluators: https://eugeneyan.com/writing/llm-evaluators/ and
 https://eugeneyan.com/writing/eval-process/.

**Practical rule for this project:** if you use an LLM judge anywhere, you must hand-label 50-100 outputs
and report the judge's TPR/TNR against those labels. Without that, judge-based numbers are not evidence.

### 6.4 Statistical practice with small samples

- **Paired bootstrap** over scenarios is the workhorse: it exploits the pairing across variants and makes no
 distributional assumption. Report BCa or percentile 95% CIs on *differences*, not separate CIs per arm.
- **Permutation / randomisation tests** give exact p-values when you control the randomisation. Same
 machinery as the single-case designs in 4.4: https://doi.org/10.1016/j.jcbs.2013.10.002.
- **Bayesian estimation as an alternative to NHST.** Kruschke, *Bayesian estimation supersedes the t test*,
 Journal of Experimental Psychology: General 2013, https://doi.org/10.1037/a0029146. Kruschke and Liddell,
 *The Bayesian New Statistics*, Psychonomic Bulletin and Review 2018,
 https://doi.org/10.3758/s13423-016-1221-4 (PDF:
 https://link.springer.com/content/pdf/10.3758/s13423-016-1221-4.pdf). With n in the tens, reporting a
 posterior over the effect with a ROPE is more honest and more informative than a p-value.
- **Report compute-budget curves, not single numbers:** Dodge et al., https://arxiv.org/abs/1909.03004.
- **Beware of metric artefacts creating apparent effects:** Schaeffer, Miranda and Koyejo, *Are Emergent
 Abilities of Large Language Models a Mirage?*, https://arxiv.org/abs/2304.15004. Relevant if you use a
 thresholded or discontinuous metric.

---

## 7. Adversarial evaluation and red-teaming of agents

### 7.1 The attack taxonomy for an agentic/RAG setting

- **Indirect prompt injection (IPI)** is the central threat: instructions embedded in data the agent
 retrieves (tool outputs, web content, retrieved documents, and in your case potentially device API
 responses or third-party health content). Benchmark and taxonomy: Zhan et al., *InjecAgent*,
 https://arxiv.org/abs/2403.02691 (code: https://github.com/uiuc-kang-lab/InjecAgent).
- **AgentDojo** (Debenedetti et al., NeurIPS 2024 Datasets and Benchmarks), https://arxiv.org/abs/2406.13352,
 site https://agentdojo.spylab.ai, code https://github.com/ethz-spylab/agentdojo (777 stars, MIT).
 Verified contents: "97 realistic tasks ... 629 security test cases, and various attack and defense
 paradigms". Design point worth copying: it is "not a static test suite, but rather an extensible
 environment for designing and evaluating new agent tasks, defenses, and adaptive attacks". Verified
 finding: "state-of-the-art LLMs fail at many tasks (even in the absence of attacks), and existing prompt
 injection attacks break some security properties but not all."
- **Data exfiltration specifically:** *Simple Prompt Injection Attacks Can Leak Personal Data Observed by
 LLM Agents During Task Execution*, https://arxiv.org/abs/2506.01055. Directly relevant: your agent
 handles personal health data.
- **The practitioner taxonomy: the lethal trifecta.** Simon Willison,
 https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/. Three capabilities that are dangerous only in
 combination: (1) access to private data, (2) exposure to untrusted content, (3) ability to communicate
 externally. Your system has (1) by definition and likely (2) if it retrieves health information. **The
 cheapest and most defensible security claim you can make is that it structurally lacks (3).**
- **OWASP GenAI Security Project / Top 10 for LLM Applications:**
 https://github.com/OWASP/www-project-top-10-for-large-language-model-applications. Use its category names
 so your taxonomy is legible to a reviewer.

### 7.2 Which defences have measured evidence and which are theatre

**Theatre, with a citation.** Zhan, Fang, Panchal and Kang, *Adaptive Attacks Break Defenses Against
Indirect Prompt Injection Attacks on LLM Agents*, https://arxiv.org/abs/2503.00061: "we evaluate eight
different defenses and bypass all of them using adaptive attacks, consistently achieving an attack success
rate of over 50%." Their methodological point, which you should adopt verbatim: defences must be evaluated
against attacks *designed after the defence is fully disclosed*, following the standard from adversarial ML
(Athalye et al. 2018, Tramer et al. 2020). A detection classifier evaluated only against fixed attack
templates proves nothing.

Willison's version of the same point: guardrail products claiming high success rates are inadequate because
in security "95% is very much a failing grade", and LLMs are non-deterministic so "it's impossible to
guarantee protective prompts work consistently every time"
(https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/).

**Defences with a real argument behind them (architectural, not detection-based):**
- **CaMeL / *Defeating Prompt Injections by Design*, https://arxiv.org/abs/2503.18813**: creates a
 protective system layer so untrusted data cannot influence control flow. Design-by-construction.
- **Design Patterns for Securing LLM Agents against Prompt Injections**, https://arxiv.org/abs/2506.08837.
 A catalogue of architectural patterns. **This is the single most useful paper for your report's security
 section**, because it gives you named patterns to claim.
- **Architecting Secure AI Agents: system-level defenses** (2026 position paper),
 https://arxiv.org/abs/2603.30016.
- **Firewalls at the agent-tool interface:** *Indirect Prompt Injections: Are Firewalls All You Need, or
 Stronger Benchmarks?*, https://arxiv.org/abs/2510.05244.
- **Tool-dependency-graph defence (IPIGuard):** https://arxiv.org/abs/2508.15310.
- **Tool result parsing:** https://arxiv.org/abs/2601.04795.
- **MELON:** https://arxiv.org/abs/2502.05174.
- **RTBAS** (injection plus privacy leakage): https://arxiv.org/abs/2502.08966.
- **PromptArmor** (detection-based, included for contrast): https://arxiv.org/abs/2507.15219.

### 7.3 Open-source red-teaming and agent-security toolkits (verified live 2026-08-30)

| Tool | URL | Stars | Licence | Notes |
|---|---|---|---|---|
| **promptfoo** | https://github.com/promptfoo/promptfoo | 24,672 | MIT | Best fit for a course project: declarative YAML configs, doubles as an eval harness *and* a red-team scanner. Actively developed (pushed 2026-08-30). |
| **garak** | https://github.com/NVIDIA/garak | 9,076 | Apache-2.0 | NVIDIA's LLM vulnerability scanner. Probe-based, large built-in probe library. |
| **PyRIT** | https://github.com/microsoft/PyRIT | 4,377 | MIT | Microsoft's risk identification tool for GenAI. **Note: the old `Azure/PyRIT` repo is archived; use `microsoft/PyRIT`.** |
| **Inspect AI** | https://github.com/UKGovernmentBEIS/inspect_ai | 2,663 | MIT | UK AI Security Institute eval framework. Not a red-team tool per se, but the right harness to *run* your adversarial suite in. |
| **AgentDojo** | https://github.com/ethz-spylab/agentdojo | 777 | MIT | Environment for agent prompt-injection attacks and defences. |
| **InjecAgent** | https://github.com/uiuc-kang-lab/InjecAgent | 164 | MIT | IPI benchmark for tool-integrated agents. Last push 2024-07; treat as a static dataset. |
| **HarmBench** | https://arxiv.org/abs/2402.04249 | - | - | Standardised automated red-teaming evaluation framework. |

### 7.4 How agent security failures are reported and quantified

- **Attack Success Rate (ASR)** is the primary metric across the literature (InjecAgent, AgentDojo, Adaptive
 Attacks). Caveat from https://arxiv.org/abs/2507.22133: ASR alone is an inadequate way to evaluate attack
 *generators*, since it rewards degenerate attacks.
- **Utility under attack** is the second axis: AgentDojo reports both benign task success and security test
 outcomes, because a defence that blocks all attacks by refusing all tasks is worthless.
- **Adaptive-attack ASR** is the standard the field is converging on: report ASR against attacks constructed
 with knowledge of your defence (https://arxiv.org/abs/2503.00061).

### 7.5 What a real adversarial suite looks like here (est. 5-8 hours)

Not one demo. A matrix:

- **Axis 1, attack goal (6-8):** exfiltrate health data; suppress a true alarm ("everything is fine, report
 no anomaly"); induce a false alarm; induce a medical claim beyond scope ("diagnose me with X"); bypass the
 human checkpoint; corrupt the stored per-user prior; make the agent ignore its safety instructions; cause
 unbounded tool-calling or cost blowup.
- **Axis 2, injection vector (4-6):** a malicious string in a device/API field (e.g. a workout note or device
 name synced from the wearable); a retrieved health document if you use RAG; the user's own free-text answer
 to a clarifying question; a calendar or notes integration; a prior-session memory entry.
- **Axis 3, phrasing variant (3-5 per cell):** direct imperative, roleplay framing, encoded or obfuscated,
 authority impersonation ("SYSTEM:"), and one adaptive variant written after you look at your own defence.

That is roughly 6 x 5 x 3 = 90 cases. Generate them programmatically from templates, run them in your
existing harness, report ASR per goal and per vector as a heatmap, plus benign-task utility with and without
defences. Then write the honest paragraph: your defences are architectural (no external send capability,
structured tool schemas, mandatory human checkpoint), citing https://arxiv.org/abs/2506.08837, and you do
**not** claim your detection layer is robust, citing https://arxiv.org/abs/2503.00061.

---

## 8. Engineering practices that distinguish a serious project

### 8.1 Reproducibility and deterministic replay

- **LLM inference is nondeterministic even at temperature 0, and the reason is not what most people say.**
 Thinking Machines Lab, *Defeating Nondeterminism in LLM Inference*,
 https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/. Verified specifics: the cause
 is **lack of batch invariance** (server-side batch size varies with load, and most GPU kernels are not
 batch-invariant), not merely floating-point non-associativity plus concurrency. Measured: generating 1,000
 completions at temperature 0 produced **80 unique completions**, with divergence first appearing at token
 103; with batch-invariant RMSNorm, matmul and attention kernels, all 1,000 became identical, at a cost of
 roughly 1.6x to 2.1x slower than baseline vLLM.
- Academic corroboration: *Understanding and Mitigating Numerical Sources of Nondeterminism in LLM
 Inference*, https://arxiv.org/abs/2506.09501, shows reproducibility of benchmark scores is "fragile" and
 changes with system configuration such as evaluation batch size. Also *Beyond Reproducibility: Token
 Probabilities Expose Large Language Model Nondeterminism*, https://arxiv.org/abs/2601.06118.
- **What this means for you:** you cannot get bitwise determinism from a hosted API. **The correct and cheap
 answer is record/replay caching.** Inspect AI's caching design is a good model
 (https://inspect.aisi.org.uk/caching.html): the cache key includes model name and base URL, the complete
 message history, the epoch number, generation config (temperature, top_p), and active tools / tool choice;
 default expiry one week, configurable to `None` for permanent. It also warns to pin explicitly versioned
 model IDs (`openai/gpt-4-turbo-2024-04-09`, not an alias) so the cache invalidates when the model changes.
- **Minimum viable reproducibility stack for this project (est. 3-5 hours):** pin exact model IDs in config;
 hash (prompt template version + rendered messages + params) as the cache key; store every request/response
 pair as JSON in the repo or an artifact store; a `--replay` flag that runs the whole eval offline from
 cache with zero API calls; a `prompts/` directory with versioned prompt files and the version string
 recorded in every trace. Publishing the cache means an examiner can re-run your entire evaluation for
 free. That is a genuinely uncommon and impressive thing to be able to say.

### 8.2 Observability and tracing that is useful rather than decorative

- **OpenTelemetry GenAI semantic conventions.** Now in a dedicated repo:
 https://github.com/open-telemetry/semantic-conventions-genai. Verified: the docs directory contains
 `gen-ai-spans.md`, `gen-ai-agent-spans.md`, `gen-ai-metrics.md`, `gen-ai-events.md`,
 `gen-ai-exceptions.md`, `mcp.md`, plus provider files (`anthropic.md`, `openai.md`, `aws-bedrock.md`,
 `azure-ai-inference.md`). **Status: `Development`** (stated at the top of `gen-ai-spans.md`, retrieved via
 https://raw.githubusercontent.com/open-telemetry/semantic-conventions-genai/main/docs/gen-ai/gen-ai-spans.md).
 Span types include Inference, Embeddings, Retrievals, Fetch response, Memory, and **Execute tool span**.
 Using the standard attribute names rather than inventing your own is a cheap professionalism signal.
- **Platforms** (verified 2026-08-30): Langfuse https://github.com/langfuse/langfuse (33,922 stars, OSS
 observability + evals + prompt management + datasets, OTel-compatible); Arize Phoenix
 https://github.com/Arize-ai/phoenix (11,246); W&B Weave https://github.com/wandb/weave (1,122,
 Apache-2.0); DeepEval https://github.com/confident-ai/deepeval (17,961, Apache-2.0).
- **What makes tracing useful rather than decorative:** the trace must let you answer, for any single
 flagged morning, *why*. That means recording, per episode: the raw physiological deviation vector, the
 detector's output, the prior over causes, the question chosen and the EIG that justified it, the user's
 answer, the posterior after the update, the final message, and the token/cost/latency for every LLM call.
 Hamel Husain's rule applies: "Remove ALL friction from the process of looking at data", and he explicitly
 recommends building a small domain-specific viewer (Streamlit, Gradio or Shiny) rather than relying on a
 generic platform (https://hamel.dev/blog/posts/evals/). **A 100-line Streamlit trace viewer showing one
 episode end to end is worth more in a demo than any dashboard.**
- Research on step-level agent telemetry: https://arxiv.org/abs/2602.10133 (AgentTrace structured logging);
 *Real-Time Detection and Repair of LLM Agent Failures*, https://arxiv.org/abs/2608.02464, which asks "how
 much detection is achievable from observable step telemetry alone" using monitors costing far less than an
 LLM judge per step.

### 8.3 Cost and latency instrumentation

Record per LLM call: model ID, prompt tokens, completion tokens, cached tokens, latency, and computed dollar
cost. Aggregate per episode and per eval run. Then draw the **accuracy-vs-cost Pareto plot** across your
ablation variants. This is precisely what *AI Agents That Matter* argues is missing from the field
(https://arxiv.org/abs/2407.01502: "Visualizing evaluation results as a Pareto curve of accuracy and
inference cost opens up a new space of agent design"). Est. 2-3 hours if done alongside tracing.

Context on why agentic workloads differ from single-call inference: https://arxiv.org/abs/2608.15127
(characterisation of agentic serving workloads, where "latency, cost, and bottlenecks arise" differently).

### 8.4 Evaluation harness design

- Follow the **Agentic Benchmark Checklist** from https://arxiv.org/abs/2507.02825 literally. It exists to
 catch exactly the failure modes a course project eval will have (insufficient test cases; degenerate outputs
 scored as success).
- Structure per Hamel Husain (https://hamel.dev/blog/posts/evals/): "Write scoped tests" organised by feature
 and scenario with specific assertions; "Create test cases" using an LLM to generate synthetic input
 variations; "Run & track regularly" in CI. He notes explicitly that you do not need a 100% pass rate, since
 the threshold is a product decision.
- From https://hamel.dev/blog/posts/evals-faq/: review "20-50 LLM outputs whenever you make significant
 changes"; for ongoing analysis target "at least 100+ fresh traces each review cycle"; stop coding failure
 categories at theoretical saturation, heuristic "if ~20 traces don't turn up a new category, you can stop
 (but review at least 100 to start)". This gives you a *defensible, citable* answer to "how many did you
 look at", which most projects cannot give.
- **Do not use off-the-shelf generic metrics as your primary evidence.** Same source: "Generic evaluations
 waste time and create false confidence."
- Harness options: Inspect AI (https://inspect.aisi.org.uk/, datasets/solvers/scorers, eval logs, Inspect
 View, caching, agent checkpointing, over 200 pre-built evals) or promptfoo (declarative YAML, doubles as
 red-team runner). Either is defensible; Inspect is the more serious-looking choice for a project with a
 safety angle.

---

## 9. Proactive and interruption-aware agent systems outside health

### 9.1 ANSWER TO QUESTION 6: yes, and this is the canonical reference

**Horvitz, Jacobs and Hovel, *Attention-Sensitive Alerting*, UAI 1999.**
https://arxiv.org/abs/1301.6707 (arXiv mirror of the UAI proceedings paper; PDF at
https://arxiv.org/pdf/1301.6707). I extracted the following directly from the paper text during this
session:

- **Expected Cost of Alerting (ECA).** For alerting action `A_i` and user attentional focus state `F_j`,
 with cost function `C_a(A_i, F_j)`:

 `ECA = sum_j C_a(A_i, F_j) * p(F_j | E_a)` (their equation 1)

 where `E_a` is evidence relevant to inferring the user's attention.

- **Expected Cost of Delayed Action (ECDA).** Given a distribution `p(H | E)` over world states `H` with
 different time criticalities and a time-dependent utility `u(A_i, H_j, t)`:

 `ECDA = max_A sum_j u(A_i, H_j, t0) p(H_j | E) - max_A sum_j u(A_i, H_j, t) p(H_j | E)` (equation 2)

 i.e. the difference between taking the ideal action now versus delaying it to time `t`.

- **The decision rule.** The system alerts "when the net value of the alert (NEVA) is positive", where
 `NEVA = EVTA - ECA` (EVTA being the expected value of transmitting the alert). Under a constant-rate-of-loss
 assumption, ECDA reduces to an *expected cost of delayed review* (ECDR) with a per-message **expected
 criticality (EC)** acting as the loss rate.

- **Inference machinery.** A Bayesian model of attentional focus, extended to "a dynamic network model
 including a set of Markov temporal dependencies", fed at runtime by "an online calendar, and a stream of
 observations about room acoustics and user activity as reported by an event sensing system".

- **Deployed system.** The **PRIORITIES** family of prototypes, with **PRIORITIES-ATTEND** as the
 attention-aware testbed that alerts based on NEVA. The paper notes an early version was distributed and
 tested by multiple users.

- The paper also notes ECDA "has been applied in such domains as emergency medicine (Horvitz & Rutledge,
 1991; Horvitz & Seiver, 1997) and time-critical aerospace applications (Horvitz & Barry, 1995)".

**This is exactly the criterion your project needs, it is 27 years old, and it is almost never cited by
modern LLM-agent projects.** Implementing a NEVA-shaped rule (estimate cost of interrupting now given
inferred context, estimate expected cost of not asking, ask only if the difference is positive) is perhaps
4-6 hours on top of an existing belief state and is one of the highest-value citations in this entire
document.

### 9.2 The rest of the classic mixed-initiative and interruptibility literature

- **Horvitz, *Principles of Mixed-Initiative User Interfaces*, CHI 1999**,
 https://doi.org/10.1145/302979.303030 (1,445 citations). The canonical twelve principles, including
 considering uncertainty about a user's goals, employing dialog to resolve key uncertainties, and
 considering the cost of poorly timed action. These map almost one-to-one onto your design decisions, and
 quoting them is the cheapest way to show the project sits in a tradition.
- **Horvitz, Kadie, Paek and Hovel, *Models of attention in computing and communication*, CACM 2003**,
 https://doi.org/10.1145/636772.636798 (312 citations).
- **Horvitz and Apacible, *Learning and reasoning about interruption*, ICMI 2003**,
 https://doi.org/10.1145/958432.958440 (270 citations). Learned models of interruptibility cost.
- **Horvitz, Koch and Apacible, *BusyBody: creating and fielding personalized models of the cost of
 interruption*, CSCW 2004**, https://doi.org/10.1145/1031607.1031690 (149 citations).
- **Horvitz et al., *Coordinate: probabilistic forecasting of presence and availability*, 2002** (132
 citations). OpenAlex record found but no DOI located: treat the exact venue string as UNVERIFIED.
- **Horvitz et al., *Principles of Bounded Deferral for Balancing Information Awareness with Interruption*
 (2005).** An OpenAlex record exists with this exact title and year but no DOI and no OA link: treat the
 exact citation as UNVERIFIED. The concept (defer non-urgent notifications to a bounded time horizon rather
 than suppressing or delivering immediately) is directly applicable: your agent could batch a non-urgent
 clarifying question to the user's next natural break.
- **Fogarty et al., *Predicting human interruptibility with sensors*, TOCHI 2005**,
 https://doi.org/10.1145/1057237.1057243 (344 citations; CHI 2003 version
 https://doi.org/10.1145/642611.642657, 296 citations). Sensor-driven interruptibility prediction.
- **Iqbal and Bailey, *Understanding and developing models for detecting and differentiating breakpoints
 during interactive tasks*, CHI 2007**, https://doi.org/10.1145/1240624.1240732 (98 citations), and
 **Iqbal and Bailey, *Effects of intelligent notification management on users and their tasks*, CHI 2008**,
 https://doi.org/10.1145/1357054.1357070 (195 citations).
- **Mark, Gudith and Klocke, *The cost of interrupted work*, CHI 2008**,
 https://doi.org/10.1145/1357054.1357072 (669 citations). The empirical basis for "interruption has a real
 cost".
- **Mehrotra et al., *Designing content-driven intelligent notification mechanisms for mobile applications*,
 UbiComp 2015**, https://doi.org/10.1145/2750858.2807544 (182 citations), and **Beyond Interruptibility,
 IMWUT 2017**, https://doi.org/10.1145/3130956 (139 citations).

### 9.3 Modern RL and decision-theoretic work on when to interrupt

- **Cai, Iqbal and Teevan, *Quick Question: Interrupting Users for Microtasks with Reinforcement Learning*,
 https://arxiv.org/abs/2007.09515.** Directly on point: "Human attention is a scarce resource in modern
 computing", and the system learns when to surface a microtask. This is the closest modern analogue to your
 "should I ask now" problem and is outside health.
- **Industrial notification decisions:** *Should I send this notification? Optimizing push notifications
 decision making by modeling the future*, https://arxiv.org/abs/2202.08812, explicitly addresses the fact
 that "most recommender systems are myopic" and models long-term effects. *Multi-objective Optimization of
 Notifications Using Offline Reinforcement Learning*, https://arxiv.org/abs/2207.03029. *Generative
 Sequential Notification Optimization via Multi-Objective Decision Transformers*,
 https://arxiv.org/abs/2509.02458, which explicitly handles "message utility and user fatigue" constraints.
- **Proactive agents in the LLM era (2026):** *ProACT: Towards Breakdown-Aware Proactive Agent in Multi-User
 Collaboration*, https://arxiv.org/abs/2607.03730, which frames the problem as "recognizing moments when a
 team would benefit from timely intervention". *ProEvent: An Event-centric Benchmark for Proactive Agents*,
 https://arxiv.org/abs/2607.17701.
- **Clarifying-question literature (information seeking, not health):** Aliannejadi et al.,
 https://arxiv.org/abs/1907.06554 ; negative-feedback-driven clarification, https://arxiv.org/abs/2107.05760 ;
 LLM preference elicitation with clarifying questions (Google), https://arxiv.org/abs/2510.12015.

### 9.4 Agents that hold state over days and act asynchronously

- **Generative Agents: Interactive Simulacra of Human Behavior**, https://arxiv.org/abs/2304.03442. The
 memory stream plus retrieval (recency, importance, relevance) plus reflection plus planning architecture is
 the standard reference for long-horizon LLM agent state. Its *reflection* mechanism (periodically
 synthesising higher-level observations from raw memories) maps very well onto "the agent notices the user
 usually drinks on Fridays".
- **MemGPT: Towards LLMs as Operating Systems**, https://arxiv.org/abs/2310.08560. Virtual context
 management for state beyond the context window.
- **Query-Conditioned Graph Retrieval for Contextualized LLM Reasoning in Personalized Wearable Data**
 (2026), https://arxiv.org/abs/2605.18763. Directly on your problem: context selection over "long-term,
 multimodal, and highly personalized" wearable data, where "providing insufficient context limits reasoning,
 while including all available data leads to inefficiency and degraded generation quality". Worth reading
 even though wearable APIs are another agent's territory, because the *context selection* framing is an
 architectural decision you will have to make.

---

## 10. The "sounds impressive, will not work here" list

Ordered by how likely you are to be tempted.

1. **Online / adaptive conformal prediction (ACI) for drift.** Sounds perfect: "distribution-free coverage
 under distribution shift, for time series". Will not work: the update
 `alpha_{t+1} = alpha_t + gamma(alpha - err_t)` needs `err_t`, which needs the true label every step
 (https://arxiv.org/abs/2106.00170). You will not know daily whether the user was actually getting ill.
 Without labels, ACI is a random walk. The same objection applies to Conformal PID
 (https://arxiv.org/abs/2307.16895).

2. **Conformal prediction on the illness label with your real data.** See section 3.2. Below roughly 50
 labelled positives the realised-coverage spread makes the guarantee rhetorically true and practically
 empty (n = 102 needed for +/-0.05 at 90% probability;
 https://ar5iv.labs.arxiv.org/html/2107.07511). Additionally, exchangeability is violated by the
 autocorrelation and drift in personal physiology.

3. **Solving a POMDP.** No transition model, no observation model, no reward function, no way to validate.
 PBVI/SARSOP assume all three are given. Cite the formulation
 (https://doi.org/10.1016/S0933-3657(99)00042-1) and implement a two-step lookahead instead.

4. **Active inference / expected free energy.** For a small discrete problem, EFE reduces to information gain
 plus expected utility, which greedy VoI already gives you. Adds vocabulary, not capability. See
 https://arxiv.org/abs/1909.10863 and https://arxiv.org/abs/2303.01618.

5. **Contextual bandits or RL for notification timing.** Needs hundreds to thousands of decision points per
 user. mHealth bandit work runs micro-randomised trials over weeks with dozens of participants
 (https://doi.org/10.1093/abm/kay067). You will have on the order of 100 decision points total.

6. **Off-policy evaluation of the interaction policy.** Requires a logged stochastic behaviour policy with
 recorded propensities and enough episodes for finite-variance importance weights
 (https://arxiv.org/abs/2008.07146). You will have neither the propensities nor the episodes.

7. **Hierarchical Bayesian modelling across users, with 2 users.** With N = 2 the population-level variance is
 unidentified. It is a plot with two lines and a prior. With 3-5 users it becomes defensible but you must
 state the limitation.

8. **Bayesian network *structure* learning from your own data.** Needs thousands of samples to beat a
 hand-drawn graph. Hand-specify the DAG; that is where your domain reasoning is supposed to live.

9. **Optimisation-based automated red-teaming (GCG or PAIR style).** Needs white-box gradients or a large
 query budget and HarmBench-class infrastructure (https://arxiv.org/abs/2402.04249). Template-based
 systematic generation gets 90% of the credibility at 10% of the cost.

10. **A guardrail or injection-detection classifier presented as a defence.** Eight published defences were
 broken by adaptive attacks with ASR over 50% (https://arxiv.org/abs/2503.00061), and "95% is very much a
 failing grade" (https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/). Build one if you like, but
 present it as a speed bump and make your real argument architectural.

11. **Fine-tuning any model.** Destroys reproducibility of the rest of the pipeline, needs labelled data you
 do not have, and consumes hours that produce nothing a reviewer can see.

12. **A single LLM-as-judge score as your headline metric.** Judges are unreliable run-to-run
 (https://arxiv.org/abs/2606.13685), biased (https://arxiv.org/abs/2506.22316), and exact-match agreement
 overstates their discriminative ability (https://arxiv.org/abs/2606.19544). If you use one, you must
 report its TPR/TNR against 50-100 hand labels.

13. **Deep uncertainty methods (MC dropout, deep ensembles, Bayesian neural nets) on your physiology model.**
 Your per-user dataset is on the order of tens to hundreds of days. A hierarchical linear or Gaussian
 process model with a proper posterior is both more appropriate and more defensible.

14. **A "user study" with 3 participants who are the authors.** Not a user study. Reframe it explicitly as an
 N-of-1 / single-case design with a pre-registered randomisation schedule (section 4.4) and it becomes a
 legitimate methodological choice rather than a weakness.

15. **Building your own tracing or observability UI from scratch.** Langfuse, Phoenix and Inspect View exist
 and are free. A small *domain-specific episode viewer* on top of them is worth building; a generic
 dashboard is not.

16. **Claiming bitwise reproducibility of LLM outputs.** You cannot get it from a hosted API. Temperature 0
 produced 80 unique completions out of 1,000 in a controlled test
 (https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/). Claim *replay*
 reproducibility via caching instead, which you can actually deliver.

---

## 11. What makes a portfolio project impressive versus forgettable

### 11.1 ANSWER TO QUESTION 5: the common failure patterns, with practitioner sources

**Failure 1: it is undifferentiated.** Vicki Boykis,
https://vickiboykis.com/2019/02/13/data-science-is-different-now/: "Don't do what everyone else is doing,
because it won't differentiate you. You're competing against a stacked, oversaturated industry and just
making things harder for yourself." *Your project passes this test already.* Personal-physiology agents with
a decision-theoretic question policy are not a tutorial genre.

**Failure 2: it shows the artefact but not the decisions.** Eugene Yan on how he actually interviews,
https://eugeneyan.com/writing/how-to-interview/: "What's more important is _how_ the candidate solves it: Do
they break down the problem logically, write clean, readable, maintainable code, consider edge cases, respond
well to feedback". In depth interviews he probes rigour explicitly: "How did they evaluate and perform error
analysis? What constraints did they face? What trade-offs did they make?" He also values "intellectual
honesty, and the humility to share their past errors". **Implication: a documented `DECISIONS.md` with
rejected alternatives and why is worth more than another feature.**

**Failure 3: no evaluation infrastructure, only prompt tinkering.** Hamel Husain,
https://hamel.dev/blog/posts/evals/, lists as a primary team failure mode "Focusing exclusively on prompt
engineering ... while neglecting evaluation and debugging infrastructure", plus "Over-relying on vendor tools
instead of simple in-house solutions" and "Not looking at enough actual data". His positive framing: "If you
streamline your evaluation process, all other activities become easy."

**Failure 4: generic metrics substituting for real measurement.** https://hamel.dev/blog/posts/evals-faq/ :
"Generic evaluations waste time and create false confidence", and a quoted instructor: "All you get from
using these prefab evals is you don't know what they actually do and in the best case they waste your time."

**Failure 5: vague, unbackable claims.** From a Hacker News thread specifically about what reviewers want to
see (https://news.ycombinator.com/item?id=23780236), the top-voted framing was a list of red flags rather
than green ones, including: "Use high-level vague marketing speech like 'helped reduce customers acquisition
cost by $X' - The world is complex, who knows what that means in practice", and a preference for demonstrated
work over credentials: "If you wanted to learn, you would've created a project out of it, tried to implement
something, or written a blog post". Another commenter in the same thread: "avoid using adjectives. Instead of
saying 'good communicator', give an example of good communication."

**Failure 6: the project has no visible failure analysis.** Implicit across all of the above. A project that
reports only its successes reads as unexamined. A project with an explicit "here is where it fails and why"
section reads as engineered.

**Failure 7: unmeasured cost.** *AI Agents That Matter*, https://arxiv.org/abs/2407.01502, shows the whole
research field got this wrong. A project that reports dollars and latency per episode alongside accuracy is
instantly in a small minority.

### 11.2 What to do instead, concretely

Eugene Yan on portfolios, https://eugeneyan.com/writing/data-science-portfolio-how-why-what/: portfolios
demonstrate technical skills but more decisively "soft skills like discipline, drive, and empathy", and "When
deciding between two similar entry/mid-level candidates ... I'm more likely to hire on traits". He endorses
Vincent Warmerdam's criterion that good projects exist "because it is scratching an itch". Your project
scratches a real itch (the authors' own health) which is a genuine asset; make that explicit rather than
hiding it behind course project framing.

**The five artefacts that will carry this project (est. total 20-30 hours, mostly already in the table):**

1. A **README with a 60-second demo** showing one real episode end to end: deviation detected, question
 asked, posterior updated, assessment produced, human checkpoint.
2. An **evaluation section with the ablation table and paired bootstrap CIs**, including a trivial baseline
 that is not obviously worse.
3. An **accuracy-vs-cost Pareto plot** across variants.
4. A **limitations and failure-analysis section** that names the three things that most undermine the system
 (no ground-truth labels, N-of-1, LLM overconfidence) and shows you measured each.
5. A **`make eval` that any reader can run offline from the cached responses** and reproduce every number.

---

## 12. Full bibliography

All URLs resolved during this session, 2026-08-30.

### Conformal prediction and calibration
- Angelopoulos & Bates, A Gentle Introduction to Conformal Prediction: https://arxiv.org/abs/2107.07511 (HTML: https://ar5iv.labs.arxiv.org/html/2107.07511)
- Gibbs & Candes, Adaptive Conformal Inference Under Distribution Shift: https://arxiv.org/abs/2106.00170
- Angelopoulos et al., Conformal PID Control for Time Series: https://arxiv.org/abs/2307.16895
- Barber, Candes, Ramdas, Tibshirani, Conformal prediction beyond exchangeability: https://arxiv.org/abs/2202.13415
- Angelopoulos et al., Conformal Risk Control: https://arxiv.org/abs/2208.02814
- Conformal Risk Control for Ordinal Classification: https://arxiv.org/abs/2405.00417
- Selective Conformal Risk Control (2025): https://arxiv.org/abs/2512.12844
- Vovk & Petej, Venn-Abers predictors: https://arxiv.org/abs/1211.0025
- Venn-ABERS for NLU model calibration: https://arxiv.org/abs/2205.10586
- Classifier Calibration at Scale, model-agnostic post-hoc methods (2026): https://arxiv.org/abs/2601.19944
- Localized Conformal Prediction: https://arxiv.org/abs/2106.08460
- Self-Calibrating Conformal Prediction: https://arxiv.org/abs/2402.07307
- Conformal Prediction Sets Improve Human Decision Making: https://arxiv.org/abs/2401.13744
- Zaffran et al., Adaptive Conformal Predictions for Time Series: https://arxiv.org/abs/2202.07282
- Adaptive Conformal Anomaly Detection with Time Series Foundation Models (2026): https://arxiv.org/abs/2604.20122
- AdaptiveConformal R package: https://arxiv.org/abs/2312.00448
- Nixon et al., Measuring Calibration in Deep Learning: https://arxiv.org/abs/1904.01685
- Kumar, Liang, Ma, Verified Uncertainty Calibration: https://arxiv.org/abs/1909.10155
- Information-theoretic analysis of ECE estimation bias: https://arxiv.org/abs/2405.15709
- LLMs as Signal Detectors, sensitivity vs bias in calibration metrics (2026): https://arxiv.org/abs/2603.14893
- Gneiting & Raftery, Strictly Proper Scoring Rules: https://doi.org/10.1198/016214506000001437
- Proximity-Informed Calibration: https://arxiv.org/abs/2306.04590

### Conformal / calibration libraries
- MAPIE: https://github.com/scikit-learn-contrib/MAPIE (docs https://mapie.readthedocs.io/)
- crepes: https://github.com/henrikbostrom/crepes (docs https://crepes.readthedocs.io/en/latest/)
- TorchCP: https://github.com/ml-stat-Sustech/TorchCP
- puncc: https://github.com/deel-ai/puncc
- venn-abers: https://github.com/ip200/venn-abers
- nonconformist (unmaintained since 2021): https://github.com/donlnz/nonconformist
- awesome-conformal-prediction: https://github.com/valeman/awesome-conformal-prediction

### LLM uncertainty and confidence
- Xiong et al., Can LLMs Express Their Uncertainty? (ICLR 2024): https://arxiv.org/abs/2306.13063 (code https://github.com/MiaoXiong2320/llm-uncertainty)
- Tian et al., Just Ask for Calibration: https://arxiv.org/abs/2305.14975
- Survey of Confidence Estimation and Calibration in LLMs: https://arxiv.org/abs/2311.08298
- Complementing Self-Consistency with Cross-Model Disagreement (2026): https://arxiv.org/abs/2604.17112
- Calibrating Verbalized Confidence with Self-Generated Distractors: https://arxiv.org/abs/2509.25532
- ORCE, Order-Aware Alignment of Verbalized Confidence (2026): https://arxiv.org/abs/2605.12446
- Direct Confidence Alignment: https://arxiv.org/abs/2512.11998
- SPUQ, Perturbation-Based UQ for LLMs: https://arxiv.org/abs/2403.02509
- ConU, Conformal Uncertainty in LLMs: https://arxiv.org/abs/2407.00499
- Conformal Prediction with LLMs for Multi-Choice QA: https://arxiv.org/abs/2305.18404
- LLM validity via enhanced conformal prediction: https://arxiv.org/abs/2406.09714
- Domain-Shift-Aware Conformal Prediction for LLMs: https://arxiv.org/abs/2510.05566
- Variational Uncertainty Decomposition for In-Context Learning: https://arxiv.org/abs/2509.02327

### Communicating uncertainty to non-experts
- van der Bles et al., Communicating uncertainty about facts, numbers and science (RSOS 2019): https://doi.org/10.1098/rsos.181870
- van der Bles et al., The effects of communicating uncertainty on public trust (PNAS 2020): https://doi.org/10.1073/pnas.1913678117
- Gigerenzer & Edwards, Simple tools for understanding risks (BMJ 2003): https://doi.org/10.1136/bmj.327.7417.741
- Gigerenzer et al., Helping Doctors and Patients Make Sense of Health Statistics (2007): https://doi.org/10.1111/j.1539-6053.2008.00033.x
- Spiegelhalter, Pearson & Short, Visualizing Uncertainty About the Future (Science 2011): https://doi.org/10.1126/science.1191181
- Icon arrays for medical risk communication (2024): https://doi.org/10.1177/0272989X241263040
- Icon arrays vs bar charts (IEEE TVCG 2025): https://doi.org/10.1109/tvcg.2025.3634630
- Words of estimative probability in NWS forecasts: https://doi.org/10.15191/nwajom.2020.0805
- Probing neural LMs for understanding of words of estimative probability: https://aclanthology.org/2023.starsem-1.41.pdf

### Bayesian modelling, LLM + probabilistic hybrids, N-of-1
- Gelman et al., Bayesian Workflow: https://arxiv.org/abs/2011.01808
- Gabry et al., Visualization in Bayesian workflow: https://arxiv.org/abs/1709.01449
- Recommendations for visual predictive checks (2025): https://arxiv.org/abs/2503.01509
- Capstick et al., AutoElicit, LLMs for Expert Prior Elicitation: https://arxiv.org/abs/2411.17284
- Wong et al., From Word Models to World Models: https://arxiv.org/abs/2306.12672
- LLM-BI, Towards Fully Automated Bayesian Inference with LLMs: https://arxiv.org/abs/2508.08300
- LLM-Prior, Knowledge-Driven Prior Elicitation and Aggregation: https://arxiv.org/abs/2508.03766
- Eliciting the Priors of LLMs using Iterated In-Context Learning: https://arxiv.org/abs/2406.01860
- LLM Processes, Numerical Predictive Distributions Conditioned on Natural Language: https://arxiv.org/abs/2405.12856
- Lew et al., SMC Steering of LLMs using Probabilistic Programs: https://arxiv.org/abs/2306.03081
- Verbalized Particle Posterior (2026): https://arxiv.org/abs/2607.22961
- AdaptFuse, Externalized Bayesian Inference for sequential preference learning (2026): https://arxiv.org/abs/2604.03925
- Using Probabilistic Programs to Train Inductive Reasoning in LLMs (2026): https://arxiv.org/abs/2606.09856
- Shamseer et al., CENT 2015 Statement (BMJ): https://doi.org/10.1136/bmj.h1738 ; E&E https://doi.org/10.1136/bmj.h1793
- Tate et al., SCRIBE 2016 Statement: https://doi.org/10.1016/j.jclinepi.2016.04.006 ; E&E https://doi.org/10.1037/arc0000027
- Heyvaert & Onghena, Randomization tests for single-case experiments: https://doi.org/10.1016/j.jcbs.2013.10.002
- Bulte & Onghena, R package for single-case randomization tests: https://doi.org/10.3758/brm.40.2.467
- t-tests for N-of-1 trials with serial correlation: https://arxiv.org/abs/1904.01622
- Digital N-of-1 Trials in Experimental Physiology: https://arxiv.org/abs/2412.15076
- Multimodal N-of-1 trials: https://arxiv.org/abs/2302.07547
- Design-based inference for time-series experiments (2025): https://arxiv.org/abs/2510.22864
- Klasnja et al., Microrandomized trials: https://doi.org/10.1037/hea0000305
- Nahum-Shani et al., JITAIs in Mobile Health: https://doi.org/10.1007/s12160-016-9830-8
- HeartSteps micro-randomized optimization trial: https://doi.org/10.1093/abm/kay067
- Kruschke, Bayesian estimation supersedes the t test: https://doi.org/10.1037/a0029146
- Kruschke & Liddell, The Bayesian New Statistics: https://doi.org/10.3758/s13423-016-1221-4

### Bayesian / PGM libraries
- PyMC: https://github.com/pymc-devs/pymc
- NumPyro: https://github.com/pyro-ppl/numpyro
- pgmpy: https://github.com/pgmpy/pgmpy
- ArviZ: https://github.com/arviz-devs/arviz
- Bambi: https://github.com/bambinos/bambi

### Sequential decision making
- Horvitz, Jacobs & Hovel, Attention-Sensitive Alerting (UAI 1999): https://arxiv.org/abs/1301.6707
- Krause & Guestrin, Near-optimal Nonmyopic Value of Information in Graphical Models: https://arxiv.org/abs/1207.1394
- Krause, Singh & Guestrin, Near-optimal Sensor Placements in Gaussian Processes: https://doi.org/10.1145/1102351.1102385
- Hauskrecht & Fraser, POMDP planning for ischemic heart disease: https://doi.org/10.1016/S0933-3657(99)00042-1
- Rainforth et al., Modern Bayesian Experimental Design: https://arxiv.org/abs/2302.14545
- Foster et al., Deep Adaptive Design: https://arxiv.org/abs/2103.02438
- Ivanova et al., Implicit Deep Adaptive Design: https://arxiv.org/abs/2111.02329
- Melville et al., Active Feature-Value Acquisition (Management Science 2009): https://doi.org/10.1287/mnsc.1080.0952
- An Expected Utility Approach to Active Feature-Value Acquisition: https://doi.org/10.1109/ICDM.2005.23
- Opportunistic Learning, Budgeted Cost-Sensitive Learning: https://arxiv.org/abs/1901.00243
- Cost-Sensitive Diagnosis and Learning Leveraging Public Health Data: https://arxiv.org/abs/1902.07102
- Active inference: demystified and compared: https://arxiv.org/abs/1909.10863
- Deconstructing deep active inference: https://arxiv.org/abs/2303.01618
- Active Inference as a Convex MDP (2026): https://arxiv.org/abs/2607.20152
- Tewari & Murphy, From Ads to Interventions: https://doi.org/10.1007/978-3-319-51394-2_25
- Liao et al., Personalized HeartSteps: https://arxiv.org/abs/1909.03539
- Thompson sampling for zero-inflated counts (Drink Less): https://arxiv.org/abs/2311.14359
- Thompson Sampling with BART for mHealth (2026): https://arxiv.org/abs/2602.07767
- Open Bandit Dataset and Pipeline: https://arxiv.org/abs/2008.07146
- Doubly robust OPE with shrinkage: https://arxiv.org/abs/1907.09623
- More Robust Doubly Robust OPE: https://arxiv.org/abs/1802.03493
- CANDOR, DR OPE for healthcare policies: https://arxiv.org/abs/2412.08052

### Evaluation of agents and interactive systems
- Kapoor et al., AI Agents That Matter: https://arxiv.org/abs/2407.01502
- Zhu et al., Establishing Best Practices for Building Rigorous Agentic Benchmarks (ABC): https://arxiv.org/abs/2507.02825
- Yao et al., tau-bench: https://arxiv.org/abs/2406.12045
- Balog & Zhai, User Simulation for Evaluating Information Access Systems: https://arxiv.org/abs/2306.08550
- Seshadri et al., Lost in Simulation (2026): https://arxiv.org/abs/2601.17087
- Dou et al., SimulatorArena: https://arxiv.org/abs/2510.05444
- User Simulation with LLMs for Evaluating TOD: https://arxiv.org/abs/2309.13233
- Reliable LLM-based User Simulator for TOD: https://arxiv.org/abs/2402.13374
- Metaphorical User Simulators: https://arxiv.org/abs/2204.00763
- Towards Emotion-Aware User Simulator for TOD: https://arxiv.org/abs/2011.09696
- Montazeralghaem et al., Asking Clarifying Questions for Preference Elicitation with LLMs: https://arxiv.org/abs/2510.12015
- Aliannejadi et al., Asking Clarifying Questions in Open-Domain Information-Seeking: https://arxiv.org/abs/1907.06554
- Asking Clarifying Questions Based on Negative Feedback: https://arxiv.org/abs/2107.05760
- Henderson et al., Deep Reinforcement Learning that Matters: https://arxiv.org/abs/1709.06560
- Dodge et al., Show Your Work: https://arxiv.org/abs/1909.03004
- Ferrari Dacrema et al., Are we really making much progress?: https://doi.org/10.1145/3298689.3347058 (PDF https://arxiv.org/pdf/1907.06902)
- Musgrave et al., A Metric Learning Reality Check: https://arxiv.org/abs/2003.08505
- Schaeffer et al., Are Emergent Abilities a Mirage?: https://arxiv.org/abs/2304.15004
- Shankar et al., Who Validates the Validators?: https://arxiv.org/abs/2404.12272
- Reliability without Validity, LLM-as-a-Judge at scale (2026): https://arxiv.org/abs/2606.19544
- The Coin Flip Judge? (2026): https://arxiv.org/abs/2606.13685
- Evaluating Scoring Bias in LLM-as-a-Judge: https://arxiv.org/abs/2506.22316
- BiasScope (2026): https://arxiv.org/abs/2602.09383

### Adversarial evaluation and agent security
- Debenedetti et al., AgentDojo: https://arxiv.org/abs/2406.13352 ; https://agentdojo.spylab.ai ; https://github.com/ethz-spylab/agentdojo
- Zhan et al., InjecAgent: https://arxiv.org/abs/2403.02691 ; https://github.com/uiuc-kang-lab/InjecAgent
- Zhan et al., Adaptive Attacks Break Defenses Against IPI: https://arxiv.org/abs/2503.00061
- Debenedetti et al., Defeating Prompt Injections by Design (CaMeL): https://arxiv.org/abs/2503.18813
- Beurer-Kellner et al., Design Patterns for Securing LLM Agents against Prompt Injections: https://arxiv.org/abs/2506.08837
- Architecting Secure AI Agents (2026): https://arxiv.org/abs/2603.30016
- Are Firewalls All You Need, or Stronger Benchmarks?: https://arxiv.org/abs/2510.05244
- IPIGuard: https://arxiv.org/abs/2508.15310
- Defense Against IPI via Tool Result Parsing (2026): https://arxiv.org/abs/2601.04795
- MELON: https://arxiv.org/abs/2502.05174
- RTBAS: https://arxiv.org/abs/2502.08966
- PromptArmor: https://arxiv.org/abs/2507.15219
- Simple Prompt Injection Attacks Can Leak Personal Data: https://arxiv.org/abs/2506.01055
- Mazeika et al., HarmBench: https://arxiv.org/abs/2402.04249
- Holistic Automated Red Teaming: https://arxiv.org/abs/2409.16783
- Prompt Optimization and Evaluation for LLM Automated Red Teaming: https://arxiv.org/abs/2507.22133
- Willison, The lethal trifecta: https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/
- OWASP Top 10 for LLM Applications: https://github.com/OWASP/www-project-top-10-for-large-language-model-applications
- promptfoo: https://github.com/promptfoo/promptfoo
- garak: https://github.com/NVIDIA/garak
- PyRIT: https://github.com/microsoft/PyRIT
- Inspect AI: https://github.com/UKGovernmentBEIS/inspect_ai ; https://inspect.aisi.org.uk/

### Engineering, reproducibility and observability
- Thinking Machines Lab, Defeating Nondeterminism in LLM Inference: https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/
- Understanding and Mitigating Numerical Sources of Nondeterminism in LLM Inference: https://arxiv.org/abs/2506.09501
- Beyond Reproducibility, Token Probabilities Expose LLM Nondeterminism (2026): https://arxiv.org/abs/2601.06118
- Inspect AI caching: https://inspect.aisi.org.uk/caching.html
- OpenTelemetry GenAI semantic conventions: https://github.com/open-telemetry/semantic-conventions-genai (status: Development)
- Langfuse: https://github.com/langfuse/langfuse
- Arize Phoenix: https://github.com/Arize-ai/phoenix
- DeepEval: https://github.com/confident-ai/deepeval
- W&B Weave: https://github.com/wandb/weave
- AgentTrace, Structured Logging for Agent Observability (2026): https://arxiv.org/abs/2602.10133
- Real-Time Detection and Repair of LLM Agent Failures (2026): https://arxiv.org/abs/2608.02464
- From LLM Inference to Agentic Workloads (2026): https://arxiv.org/abs/2608.15127
- Husain, Your AI Product Needs Evals: https://hamel.dev/blog/posts/evals/
- Husain, AI Evals FAQ: https://hamel.dev/blog/posts/evals-faq/

### Proactive, interruption-aware and long-horizon agents
- Horvitz, Principles of Mixed-Initiative User Interfaces (CHI 1999): https://doi.org/10.1145/302979.303030
- Horvitz, Kadie, Paek, Hovel, Models of attention in computing and communication (CACM 2003): https://doi.org/10.1145/636772.636798
- Horvitz & Apacible, Learning and reasoning about interruption (ICMI 2003): https://doi.org/10.1145/958432.958440
- Horvitz, Koch, Apacible, BusyBody (CSCW 2004): https://doi.org/10.1145/1031607.1031690
- Fogarty et al., Predicting human interruptibility with sensors (TOCHI 2005): https://doi.org/10.1145/1057237.1057243 ; CHI 2003 version https://doi.org/10.1145/642611.642657
- Iqbal & Bailey, Detecting and differentiating breakpoints (CHI 2007): https://doi.org/10.1145/1240624.1240732
- Iqbal & Bailey, Effects of intelligent notification management (CHI 2008): https://doi.org/10.1145/1357054.1357070
- Mark, Gudith & Klocke, The cost of interrupted work (CHI 2008): https://doi.org/10.1145/1357054.1357072
- Mehrotra et al., Content-driven intelligent notification mechanisms (UbiComp 2015): https://doi.org/10.1145/2750858.2807544
- Mehrotra et al., Beyond Interruptibility (IMWUT 2017): https://doi.org/10.1145/3130956
- Cai, Iqbal & Teevan, Quick Question: Interrupting Users for Microtasks with RL: https://arxiv.org/abs/2007.09515
- Should I send this notification?: https://arxiv.org/abs/2202.08812
- Multi-objective Optimization of Notifications Using Offline RL: https://arxiv.org/abs/2207.03029
- Generative Sequential Notification Optimization: https://arxiv.org/abs/2509.02458
- ProACT, Breakdown-Aware Proactive Agent (2026): https://arxiv.org/abs/2607.03730
- ProEvent, Event-centric Benchmark for Proactive Agents (2026): https://arxiv.org/abs/2607.17701
- Park et al., Generative Agents: https://arxiv.org/abs/2304.03442
- Packer et al., MemGPT: https://arxiv.org/abs/2310.08560
- Query-Conditioned Graph Retrieval for Personalized Wearable Data (2026): https://arxiv.org/abs/2605.18763
- Real-World Receptivity to Adaptive Mental Health Interventions: https://arxiv.org/abs/2508.02817

### Practitioner sources on portfolios and hiring
- Eugene Yan, Why Have a Data Science Portfolio and What It Shows: https://eugeneyan.com/writing/data-science-portfolio-how-why-what/
- Eugene Yan, How to Interview and Hire ML/AI Engineers: https://eugeneyan.com/writing/how-to-interview/
- Eugene Yan, Evaluating the Effectiveness of LLM-Evaluators: https://eugeneyan.com/writing/llm-evaluators/
- Eugene Yan, An LLM-as-Judge Won't Save The Product, Fixing Your Process Will: https://eugeneyan.com/writing/eval-process/
- Eugene Yan, How to Test Machine Learning Code and Systems: https://eugeneyan.com/writing/testing-ml/
- Vicki Boykis, Data Science is Different Now: https://vickiboykis.com/2019/02/13/data-science-is-different-now/
- Hacker News, Ask HN: What do you want to see in a resume / GitHub profile?: https://news.ycombinator.com/item?id=23780236
- Hamel Husain, Your AI Product Needs Evals: https://hamel.dev/blog/posts/evals/
- Hamel Husain, AI Evals FAQ: https://hamel.dev/blog/posts/evals-faq/

### Marked UNVERIFIED
- **QMDP** as a named POMDP approximation: I did not locate a canonical open-access primary source URL during this session. The technique is standard, but treat any specific citation as unverified until checked.
- **Point-based value iteration (Pineau, Gordon, Thrun, IJCAI 2003)**: confirmed to exist via OpenAlex with 933 citations, but OpenAlex returned no DOI and no OA URL. Venue and author attribution are from the OpenAlex record only.
- **Horvitz et al., "Principles of Bounded Deferral for Balancing Information Awareness with Interruption" (2005)**: an OpenAlex record exists with this exact title and year but no DOI, no OA link and 1 citation. Venue could not be confirmed. The underlying concept is described in the verified Attention-Sensitive Alerting paper's deferral sections.
- **Coordinate: probabilistic forecasting of presence and availability (2002)**: OpenAlex record with 132 citations but no DOI located.
- **Near-Optimal Sensor Placements in Gaussian Processes (JMLR 2008)**: OpenAlex shows two records with no working DOI for the JMLR version; the KDD 2005 version DOI https://doi.org/10.1145/1102351.1102385 is verified.
- All **build-hour estimates** in section 2 and elsewhere are my engineering judgement, not sourced facts.
