# F3: LLM and Agent Systems over Personal Health, Wearable and Physiological Time-Series Data

Research territory F3. Compiled 2026-08-30. All claims carry a URL. Claims I could not confirm against a primary source are marked **UNVERIFIED**.

Method note: every arXiv ID was checked against both the arXiv abstract page and the arXiv Atom export API (`export.arxiv.org/api/query`), which is not summarised by an intermediate model. Every GitHub repository was checked against the GitHub REST API (`api.github.com`) for stars, licence and last commit, and source files were downloaded with `curl` and read directly rather than being summarised. Where a page-summarising fetch and the raw source disagreed, the raw source wins and I say so.

---

## 1. Executive summary

1. **The five citations flagged as possibly fabricated are all real.** All five arXiv IDs resolve to papers with exactly the claimed titles, including the two 2026 IDs (`2607.21019` HiMe, `2605.29483` VitalAgent) that looked suspicious. Verified independently via the arXiv API. The previous model's IDs were correct. See section 2.
2. **Two of the five performance claims are materially misstated.** PHIA's "<40% for zero-shot LLM baselines" is wrong (the real baselines are 22%, 53.6% and 74%). VitalAgent's "25-30% relative improvement" is wrong in framing (it is +25 to +31 *percentage points absolute*, and the "ReAct baseline" is PHIA, which the VitalAgent authors themselves say was handicapped by input format). See section 3.
3. **The single most important number in this literature is PHIA 84% vs code-generation-baseline 74%.** The whole "agent" contribution over a plain one-shot code generator is 10 percentage points on objective numerical queries. That is real but modest, and it is the strongest ablation in the field. https://arxiv.org/abs/2406.06464
4. **Nobody serialises raw numeric time series into the prompt if they can avoid it.** The dominant pattern is: give the LLM a *schema description* only, and let it emit code or SQL that computes over data it never sees. PHIA gives a pandas column dictionary; HiMe gives an EAV feature inventory and a SQL tool; SAGE gives a KQL query surface; VitalAgent gives typed signal-processing tools. Health-LLM (the outlier) does serialise raw arrays as text and is the weakest performer on numeric tasks. See section 6.
5. **The "code generation over dataframes is universally best" assertion in the prior notes is NOT supported.** The one paper that isolates this ("Can LLM Coding Agents Reason About Time Series?", arXiv:2606.16545) finds a *hybrid* (code + raw text) beats code-only by 8 to 12 points, and that a **direct text agent beats the code agent** on structural breaks (52.0 vs 44.0), outlier detection (74.0 vs 64.8) and anomaly detection (54.8 vs 48.8). Anomaly detection is exactly our task. See section 6.2.
6. **Proactive systems exist but are rare and shallow.** Of 14 systems reviewed, 5 are genuinely proactive (HiMe, VitalAgent, SAGE, ContextAgent, Project Hermes), and 3 of those 5 fire on a fixed or agent-authored threshold with a cooldown. See section 7.
7. **The "when to interrupt" gap is real but narrower than the prior notes imply.** No health system models the *cost of interrupting the user*. But two adjacent systems do treat the decision as a first-class learned problem: ContextAgent (NeurIPS 2025) trains a proactive-score classifier with a threshold at 3/5, and ProAgentBench (arXiv:2602.04482) formalises it as binary classification `B_t = f_when(U, O_1:t)` with precision/recall framed explicitly as alert-fatigue vs missed-need. Neither is health/physiological. Project Hermes (arXiv:2602.18643) is the only health system that *asks the user a question in order to decide whether the alert was real*. See section 8.
8. **Long-horizon state is a 2026 growth area, not a solved problem.** HealthClaw, MedMemoryBench, BALMS and RubricsTree all appeared in 2026 specifically because prior personal-health agents were single-session. HiMe is the only *deployed* system with months-long state and it ran a 9-participant, 2-month field study.
9. **No house agent framework.** PHIA uses Google's OneTwo `ReActAgent`. HiMe uses a hand-written single event loop. VitalAgent uses a custom planner/validator/replanner. openCHA uses its own Task Planner (ToT or ReAct). SAGE is the only one using LangGraph. BALMS used LangChain to reproduce baselines. See section 9.
10. **Reusable assets are concentrated in three repos**: PHIA (prompts + 4,000-question eval set + few-shots, CC BY-NC), HiMe (full production platform, 379 files, but PolyForm **Noncommercial**), VitalAgent (agent + tools + proactive rule engine, MIT, but only 2 stars).

---

## 2. Citation verification table

| # | Claimed ID / claim | Resolves to | Verdict | Correct citation | URL |
|---|---|---|---|---|---|
| 1 | `arXiv:2406.06464`, "Transforming Wearable Data into Personal Health Insights using Large Language Model Agents" (PHIA) | Exactly that title. v1 2024-06-10, v4 2025-09-08. Comment field: "Accepted to Nature Communications" | **VERIFIED** | Merrill, Paruchuri, Rezaei, Kovacs, Perez, Liu, Schenck, Hammerquist, Sunshine, Tailor, Ayush, Su, He, McLean, Malhotra, Patel, Zhan, Althoff, McDuff, Liu | https://arxiv.org/abs/2406.06464 |
| 1b | "PHIA published Nature Communications Jan 2026" | Crossref confirms: *Nature Communications* **17**, 1143, published **2026-01-12**, DOI 10.1038/s41467-025-67922-y | **VERIFIED** | Merrill, M.A., Paruchuri, A., Rezaei, N. et al. Nat Commun 17, 1143 (2026) | https://doi.org/10.1038/s41467-025-67922-y |
| 1c | GitHub `yahskapar/personal-health-insights-agent` | Exists. 62 stars, 13 forks, created 2025-08-04, last commit **2025-12-21** | **VERIFIED** | - | https://github.com/yahskapar/personal-health-insights-agent |
| 2 | `arXiv:2607.21019`, "HiMe: Real-Time Self-Hosted Personal Agent Platform for Health Insights with Wearable Devices" | Exactly that title. Published **2026-07-23**. Wei Liu, Siya Qi, Linhai Zhang, Lorainne Tudor Car, Yulan He. cs.AI. Licence CC BY 4.0 | **VERIFIED** | Liu, Qi, Zhang, Tudor Car, He (2026), arXiv:2607.21019 | https://arxiv.org/abs/2607.21019 |
| 2b | GitHub `thinkwee/HiMe` | Exists. 59 stars, 6 forks, created 2026-04-13, last commit **2026-08-10**, 379 tracked files, Python | **VERIFIED** | - | https://github.com/thinkwee/HiMe |
| 3 | `arXiv:2508.03436`, "AI on the Pulse", Gabrielli et al., ACM CIKM 2025 | Title is "AI on the Pulse: Real-Time Health Anomaly Detection with Wearable and Ambient Intelligence". Gabrielli, Prenkaj, Velardi, Faralli. **2025-08-05**. cs.LG | **VERIFIED (ID + authors); CIKM 2025 venue UNVERIFIED** | Gabrielli, Prenkaj, Velardi, Faralli (2025), arXiv:2508.03436. The arXiv record shows **no journal-ref or comment field** naming CIKM. Do not cite the venue. | https://arxiv.org/abs/2508.03436 |
| 4 | `arXiv:2605.29483`, "VitalAgent / VitalBench" | "VitalAgent: A Tool-Augmented Agent for Reactive and Proactive Physiological Monitoring over Wearable Health Data". Di Zhu, Yu Yvonne Wu, Hong Jia, Aaqib Saeed, Vassilis Kostakos, Ting Dang. v1 **2026-05-28**, v2 2026-06-18 | **VERIFIED** | Zhu, Wu, Jia, Saeed, Kostakos, Dang (2026), arXiv:2605.29483 | https://arxiv.org/abs/2605.29483 |
| 4b | GitHub (repo not named in prior notes) | `DKSEZD/VitalAgent` exists. 2 stars, MIT, created 2026-05-28, last commit **2026-07-13**. Real code: `agent/tools/` has 5 tool modules totalling ~98 KB; `agent/proactive/` has 9 modules including `intervention_decision.py` (29.6 KB) and `llm_judge.py` (28.5 KB) | **VERIFIED** | - | https://github.com/DKSEZD/VitalAgent |
| 5 | `arXiv:2401.06866`, "Health-LLM", Kim et al. | "Health-LLM: Large Language Models for Health Prediction via Wearable Sensor Data". Yubin Kim, Xuhai Xu, Daniel McDuff, Cynthia Breazeal, Hae Won Park. v1 **2024-01-12**, v2 2024-04-27 | **VERIFIED** | Kim, Xu, McDuff, Breazeal, Park (2024), arXiv:2401.06866 | https://arxiv.org/abs/2401.06866 |
| 5b | GitHub `mitmedialab/Health-LLM` | Exists. 104 stars, 20 forks, MIT, created 2024-04-27, **last push 2024-08-09** (dormant 2 years) | **VERIFIED** | - | https://github.com/mitmedialab/Health-LLM |

**Verdict on the prior model's notes: all five arXiv IDs are correct.** Nothing was fabricated at the identifier level. The one citation error is the "ACM CIKM 2025" venue attributed to AI on the Pulse, which does not appear on the arXiv record.

### Additional papers verified during this survey (not in the prior notes)

| Paper | ID | Verified date | URL |
|---|---|---|---|
| The Anatomy of a Personal Health Agent (Google PHA) | arXiv:2508.20148 | v1 2025-08-27, v2 2025-09-18 | https://arxiv.org/abs/2508.20148 |
| Towards a Personal Health Large Language Model (PH-LLM) | arXiv:2406.06474 | 2024-06-10 | https://arxiv.org/abs/2406.06474 |
| A personal health large language model for sleep and fitness coaching (PH-LLM journal version) | Nature Medicine, DOI 10.1038/s41591-025-03888-0, PMID 40813712 | 2025 | https://www.nature.com/articles/s41591-025-03888-0 |
| Conversational Health Agents (openCHA) | arXiv:2310.02374; JAMIA Open 8(4) ooaf067, DOI 10.1093/jamiaopen/ooaf067, 2025-07-06 | verified | https://academic.oup.com/jamiaopen/article/8/4/ooaf067/8186991 |
| SentinelBench: A Benchmark for Long-Running Monitoring Agents | arXiv:2606.05342 | 2026-06-03 | https://arxiv.org/abs/2606.05342 |
| ContextAgent: Context-Aware Proactive LLM Agents with Open-World Sensory Perceptions | arXiv:2505.14668, NeurIPS 2025 | verified | https://arxiv.org/abs/2505.14668 |
| ProAgentBench: Evaluating LLM Agents for Proactive Assistance with Real-World Data | arXiv:2602.04482 | 2026-02-09 (v2) | https://arxiv.org/abs/2602.04482 |
| SAGE: Sensor-Augmented Grounding Engine for LLM-Powered Sleep Care Agent | arXiv:2604.16342, CHI EA 2026 | verified | https://arxiv.org/abs/2604.16342 |
| Project Hermes: A Model-Agnostic Validation Layer for Wearable Health Prediction Systems | arXiv:2602.18643 | 2026-02-20 | https://arxiv.org/abs/2602.18643 |
| A Self-Evolving Agent for Longitudinal Personal Health Management (HealthClaw) | arXiv:2607.13940 | 2026-07-15 | https://arxiv.org/abs/2607.13940 |
| BALMS: Benchmarking Agentic LLMs for Longitudinal Mental Health Sensing | arXiv:2608.27219 | 2026-08-27 | https://arxiv.org/abs/2608.27219 |
| LifeAgentBench | arXiv:2601.13880 | 2026-01-20 | https://arxiv.org/abs/2601.13880 |
| Can LLM Coding Agents Reason About Time Series? | arXiv:2606.16545 | 2026-06-16 | https://arxiv.org/abs/2606.16545 |
| TimeSeriesExam: A time series understanding exam | arXiv:2410.14752 | 2024-10-18 | https://arxiv.org/abs/2410.14752 |
| TS-Agent: Understanding and Reasoning Over Raw Time Series via Iterative Insight Gathering | arXiv:2510.07432 | v1 2025-10-08, v2 2026-04-06 | https://arxiv.org/abs/2510.07432 |
| TS-Reasoner (Multi-Step Time Series Inference Agent) | arXiv:2410.04047 | verified | https://arxiv.org/abs/2410.04047 |
| Exploring Expert Perspectives on Wearable-Triggered LLM Conversational Support for Daily Stress Management (EmBot) | arXiv:2604.04915, IH '26 | 2026-04-06 | https://arxiv.org/abs/2604.04915 |
| RubricsTree | arXiv:2606.18203 | 2026-06-16 | https://arxiv.org/abs/2606.18203 |
| MedMemoryBench | arXiv:2605.11814 | 2026-05-12 | https://arxiv.org/abs/2605.11814 |
| Always-On Agents: A Survey of Persistent Memory, State, and Governance in LLM Agents | arXiv:2606.30306 | 2026-06-29 | https://arxiv.org/abs/2606.30306 |
| OpenMHC: Accelerating the Science of Wearable Foundation Models | arXiv:2607.16235 | v3 2026-08-08 | https://arxiv.org/abs/2607.16235 |
| A Survey of Reasoning and Agentic Systems in Time Series with LLMs | arXiv:2509.11575, TMLR 2026 | verified | https://github.com/blacksnail789521/Time-Series-Reasoning-Survey |

**"PHIA+": no such system found.** Searches surfaced nothing. Treat as **DOES NOT EXIST** unless someone produces a URL.

---

## 3. Performance claim verification table

| Claim as written in prior notes | What the primary source actually says | Verdict |
|---|---|---|
| "PHIA: 84% accuracy on objective numerical queries" | "PHIA achieves an exact match accuracy of 84%". Metric: exact match "to within two digits of precision". | **VERIFIED** https://arxiv.org/abs/2406.06464 |
| "...versus <40% for zero-shot LLM baselines" | The paper's four baselines: Code Generation **74%**, Numerical Reasoning **22%**, custom GPT-4 chain-of-thought **53.6%**, PH-LLM **0%**. Only one of four is below 40%. | **WRONG.** The honest framing is 84% vs 74% for the strongest baseline, a 10 point gain. Do not repeat "<40%". |
| "83% favourable ratings on open-ended interpretation" | "earning 83% favorable ratings while being twice as likely to achieve the highest quality rating." Favourable = rated "Fair" or better on a 1-5 Likert. | **VERIFIED** but note the bar is "Fair or better", not "Good or better". |
| "evaluated on >4,000 questions across 650 expert-hours" | "we create and share two benchmark datasets with over 4000 health insights questions. A 650-hour human expert evaluation..." Composition: 4,000 auto-evaluated objective questions plus 172 human-evaluated open-ended questions (sampled from ~3,000 survey-collected). 650 h = ~600 h open-ended (12 annotators, >5,500 responses, min 3 raters each, blinded) plus ~50 h code quality (7 data scientists, mean 9 yrs experience, 595 responses). | **VERIFIED** |
| PHIA inter-rater agreement | Main text says agreement was "considerable"; the actual statistics are in supplementary material and I could not retrieve a kappa/ICC value. | **UNVERIFIED (numeric)** |
| "HiMe: 90%+ reduction in LLM inference cost via statistical event triggers" | Paper Table 2 reports **tokens saved of 121x, 76x, 83x, 49x** for Qwen3-1.7b / Qwen3-8b / Gemma-4-26b-a4b / Qwen3-30b-a3b vs a fixed-schedule polling baseline. 49x = 98.0% reduction. | **VERIFIED and understated**, BUT with a caveat the prior notes omit: **detection recall got worse for 2 of 4 backbones** under triggering (Gemma-4-26b 0.57 to 0.43; Qwen3-30b 0.58 to 0.52). It improved for the other two (Qwen3-1.7b 0.00 to 0.29; Qwen3-8b 0.69 to 0.89). n = 47 injected events per backbone, 5 participants per corpus across PMData/LifeSnaps/MMASH. Small. |
| "AI on the Pulse: ~22% improvement in F1 over 12 baseline models" | UniTS average F1 **0.821 +/- 0.049** vs second-best DAGMM **0.673 +/- 0.066**, i.e. +22% relative. 12 named baselines: LSTM-NDT, MSCRED, HypAD, TranAD, OmniAnomaly, MTAD-GAT, CAE-M, MAD-GAN, TadGAN, USAD, GDN, DAGMM. Datasets: DREAMER, HCI, WESAD(ECG), WESAD(BVP). Anomalies defined as points below the 3rd or above the 97th percentile. | **VERIFIED**, but note the "anomaly" ground truth is a **percentile heuristic, not a clinical label**, and none of this involves the LLM. See section 4.6. |
| "VitalAgent: 25-30% relative improvement in diagnostic reasoning accuracy over ReAct and direct prompting" | Abstract: "over 25% improvement over prompt-based and ReAct baselines". Results text: VitalAgent 0.860 (Tier A) / 0.557 (Tier B) "improves over the strongest signal-derived baseline LifeAgent* by **0.315 and 0.270** respectively", i.e. **absolute percentage points**, which is +58% relative on Tier A. | **WRONG IN FRAMING.** It is not "25-30% relative"; it is +25 to +31 points absolute. Worse, the nominal ReAct baseline is PHIA at 0.395/0.246, and the VitalAgent authors explicitly write that "its lower performance should not be interpreted as a general weakness of PHIA, but rather as evidence" of an input-format mismatch. **This is not a fair ReAct comparison.** |
| "Health-LLM: context enhancement improved accuracy by up to 23.8%" | Abstract claims "up to 23.8% performance improvement". I could not locate the specific task/model/comparison producing exactly 23.8% in the body; Figure 2 shows scattered gains and a 44.58% figure for Palmyra-Med with temporal context on one task. | **PARTIALLY VERIFIED.** The number is in the abstract but I could not trace it to a single labelled cell. Treat as an abstract-level claim. |
| "HealthAlpaca 7B/13B outperformed GPT-4 and Gemini Pro on 8 of 10 tasks" | Section 5.2: "our fully fine-tuned model, HealthAlpaca, shows the best performance in 8 out of 10 consumer health tasks (Table 17)", best-of across 12 LLMs plus MLP/SVM/RandomForest/BERT. The abstract's own phrasing is "achieving comparable results to GPT-3.5, GPT-4 and Gemini-Pro, excelling in 8 of 10 tasks". | **VERIFIED with nuance.** "Best in 8 of 10" is a best-of-field claim across all baselines, not specifically a head-to-head against GPT-4 and Gemini Pro. The authors' own summary word is "comparable". |

---

## 4. Per-system A-V writeups

### 4.1 PHIA (Personal Health Insights Agent), Google Research

Primary: https://arxiv.org/abs/2406.06464 | Journal: https://doi.org/10.1038/s41467-025-67922-y (Nat Commun 17, 1143, 2026-01-12) | Code: https://github.com/yahskapar/personal-health-insights-agent

- **A. Problem.** Consumer wearable users cannot get numerically correct, personalised answers about their own data; base LLMs fail at multi-step numerical reasoning over long tabular records.
- **B. Input data.** Fitbit daily aggregates and per-activity records for a single user, plus a small demographic profile. Both synthetic and deidentified real wearable users are shipped in the repo.
- **C. Device.** Fitbit (Sense / Versa class). Not a raw-signal device: everything is Fitbit-computed daily metrics.
- **D. Signals.** `resting_heart_rate`, `heart_rate_variability`, active-zone minutes (fatburn/cardio/peak), `steps`, sleep stage minutes (REM/deep/light/awake) and percentages, `bed_time`, `wake_up_time`, `stress_management_score`; per-activity `averageHeartRate`, distance, duration, elevation gain, calories, speed.
- **E. Time-series to LLM.** **The LLM never sees the numbers.** It sees a natural-language *schema dictionary* in the preamble and writes pandas code. Verbatim from `prompt_templates.py`: *"I am going to ask you a question about Fitbit data. Assume that you have access to pandas through `pd` and numpy through `np`. You DO NOT have access to matplotlib or other python libraries."* followed by a bulleted column list with dtypes and units, e.g. *"`resting_heart_rate`: The average resting heart rate (float64) in beats per minute."* Data is injected into the executor scope only: `sandbox_globals = {"pd": pd, "np": np, "summary_df": summary_df, "activities_df": activities_df, "profile": profile_df}`.
- **F. Personalisation.** Entirely through the user's own dataframes plus a profile row (age, gender, averageDailySteps, elderly flag, height_cm, weight_kg). No fine-tuning, no persistent user model, no memory.
- **G. Model/method.** No ML model of its own. Statistics are whatever pandas code the LLM writes.
- **H. Training required.** No. Zero fine-tuning, by design ("to study the benefits of agent frameworks and tool use in isolation").
- **I. Pretrained weights.** N/A (Gemini 1.0 Ultra, closed). The open-source repo defaults to a substitutable model.
- **J. LLM.** **Gemini 1.0 Ultra**, fixed. The authors explicitly decline to test other LLMs: "Due to the substantial cost incurred through 650 hours of human evaluation it was not feasible to verify the central claims of this paper with other language models."
- **K. Agent architecture.** **ReAct.** Verbatim loop format from the prompt: `[Question] -> [Thought] -> [Act] -> [Observe] -> ... -> [Finish]`. Implemented as `react.ReActAgent(exemplars=..., environment_config=python_tool_use.PythonToolUseEnvironmentConfig(tools=agent_tools), max_steps=10, stop_prefix="")`. Few-shot: 20 exemplars selected by K-means over sentence-T5 embeddings, stored as Jupyter notebooks and parsed into `ReActState` objects.
- **L. Tools (read from `phia_agent.py`, exact).** Exactly three:
 1. `tool_code`: *"Python interpreter. Executes code on pandas DataFrames (summary_df, activities_df, profile)."* Implemented as a hand-rolled `exec`/`eval` sandbox with stdout capture, not a container.
 2. `search`: *"Web search engine for finding health, wellness, and fitness information."* Backed by **Tavily** in the open release (`search_depth="advanced"`, `max_results=5`). The paper used the Google Search API.
 3. `finish`: *"Returns the final answer."*
- **M. RAG.** No vector store. Live web search only, over the open web via Tavily/Google.
- **N. UX.** Single-user conversational Q&A. The preamble anticipates multi-turn ("You can expect questions to be conversational and multi-turn"), but there is no persistent memory between sessions.
- **O. Real-time vs offline.** **Offline / on-demand.** Nothing runs unless a question is asked.
- **P. Output.** Free-text answer with embedded reasoning, optionally grounded in web sources.
- **Q. Evaluation.** Two benchmarks the authors built. (i) 4,000 template-generated objective questions with expert-authored ground truth, auto-scored by exact match to 2 digits. (ii) 172 open-ended questions sampled from ~3,000 collected by survey, rated by **12 annotators** familiar with wearable sleep/fitness data, blinded to method, min 3 raters per response, 1-5 Likert on relevance / accuracy / personalisation / domain knowledge / logic / harm avoidance / clarity, >5,500 responses, ~600 h. (iii) Code quality: 595 responses, 7 data scientists (mean 9 years experience), ~50 h. Inter-rater agreement described as "considerable"; numeric value in supplementary, **UNVERIFIED**.
- **R. Performance.** Objective: PHIA **84%**, Code Generation **74%**, Numerical Reasoning (markdown tables in context) **22%**, GPT-4 CoT **53.6%**, PH-LLM **0%**. Open-ended reasoning score (scaled Likert): PHIA **68** vs Code Generation **52**; 83% of PHIA responses "Fair or better"; 2x as likely to be rated "Excellent". Code errors: PHIA error rate **0.192** vs Code Generation **0.395**; fatal-error recovery **11.4%** vs **0%**.
- **S. Open source.** Repo exists, 62 stars, 13 forks, created 2025-08-04, **last commit 2025-12-21**, 1 open issue, not archived. GitHub API reports licence as `NOASSERTION`; the repo page and the 19 KB LICENSE file indicate **CC BY-NC 4.0**. Contents: `phia_agent.py` (9.0 KB), `prompt_templates.py` (13.5 KB), `data_utils.py` (14.4 KB), `phia_demo.ipynb`, `few_shots/`, `synthetic_wearable_users/`, `real_wearable_users/` (deidentified), `Objective Query - PHIA.xlsx` (89.7 KB), `Open-Ended Query - PHIA.xlsx`. **Real, runnable code, not a stub.** Requires a Tavily API key and an LLM. Depends on `onetwo` (Google DeepMind's prompting library), not LangChain. No model weights (none exist).
- **T. Reusable assets.** The dataframe schema preamble (copy it), the ReAct `[Thought]/[Act]/[Observe]/[Finish]` template, the 20 few-shot notebooks, the 4,000-question objective eval set, the 172 open-ended queries, the K-means-over-T5 exemplar selection trick, `simple_python_executor` (a ~50-line last-expression-aware exec sandbox).
- **U. Limitations (authors' own).** No real-world effectiveness or behaviour-change evidence; no health-expert validation of recommendation accuracy; not for clinical diagnosis; **single LLM tested, generalisation hypothesised but not proven**; annotators lacked programming background so Python-to-English translation may add noise; arbitrary curation thresholds (31-day aggregation window, 10-day minimum).
- **V. Architectural lesson.** Describe the schema, not the data. Let the model write code. But be honest that the agent loop buys you 10 points over one-shot code generation, and its main measurable benefit is **error recovery** (11.4% vs 0%), not raw accuracy.

---

### 4.2 PH-LLM (Personal Health Large Language Model), Google

Primary: https://arxiv.org/abs/2406.06474 | Journal: *Nature Medicine*, https://www.nature.com/articles/s41591-025-03888-0, DOI 10.1038/s41591-025-03888-0, PMID 40813712

- **A.** Can a fine-tuned LLM produce expert-quality sleep and fitness coaching from wearable data?
- **B/C/D.** Fitbit-class aggregated daily metrics: sleep patterns, physical activity, physiological responses (HRV, respiratory rate, resting HR).
- **E. Time-series to LLM.** Two paths. (i) **Text**: metrics rendered in native units in the prompt (e.g. steps per day), presented as tables/figures in the case study. (ii) **Multimodal adapter**: "wearable data for each user was stored as a matrix in which the rows represent wearable measurement devices and the columns represent measurements at a specific time"; mean and variance across 15 days for 20 measurements gives a 20x2 matrix, z-scored, passed through an **MLP with hidden sizes 1024 / 4096 / 1024 producing 22 tokens**, prepended as a **prefix** to the text input.
- **F.** Fine-tuning on domain case studies plus the user's own data in-context.
- **G/H.** Supervised fine-tuning of **Gemini Ultra 1.0**. 1,371 sleep and 1,500 fitness prompt-response pairs, 70/15/15 split, max 1,500 steps, global batch 4, LR 2.5e-7, cosine decay, weight decay 1e-2.
- **I.** **No weights released.**
- **J.** Gemini Ultra 1.0.
- **K. Agent architecture. NONE.** This is a fine-tuned model, not an agent. No tools, no loop. Flag: **the word "agent" does not apply here.**
- **L.** No tools.
- **M.** No retrieval.
- **N.** Case-study report generation.
- **O.** Offline.
- **P.** Personalised sleep/fitness insights and recommendations; sleep-quality outcome predictions.
- **Q.** 857 case studies (507 sleep, 350 fitness) written with domain experts; 50 holdout per vertical expert-evaluated. **6 sleep experts and 7 fitness experts** authored responses and rated three responses per case (Gemini Ultra, PH-LLM, human expert) on a 15-question 1-5 rubric, assigned so they never rated their own. Plus MCQ exams: sleep N=629, fitness N=99. Inter-rater agreement computed but relegated to Appendix A.4; **numeric values UNVERIFIED**.
- **R.** Sleep insights PH-LLM **4.61/5** vs expert **4.75/5** (p=3.3e-11, statistically significant, small effect). Fitness **not statistically different** from expert (p=0.48). Exams: sleep **79%** vs human-expert mean 76%; fitness **88%** vs 71%. Adapter beat prompt-based approaches on AUROC and AUPRC for **12 of 16** self-reported traits.
- **S.** No code. Case study inputs and responses promised "upon peer-reviewed publication" (now published, availability **UNVERIFIED**).
- **T.** The 15-question rubric design; the MLP-adapter-as-token-prefix pattern.
- **U.** Rubric ratings highly skewed, compressing model differences; confabulation and incorrect referencing of user data "still occasionally occurred"; case studies may not represent broader populations; no behaviour-change evaluation.
- **V.** **PH-LLM scored 0% on PHIA's objective numerical benchmark.** Fine-tuning for coaching prose destroys numerical capability over long tabular inputs. This is the strongest single argument in the literature against fine-tuning for our task and for tool use instead.

---

### 4.3 PHA, "The Anatomy of a Personal Health Agent", Google

Primary: https://arxiv.org/abs/2508.20148 | Blog: https://research.google/blog/the-anatomy-of-a-personal-health-agent/

Note: the arXiv HTML renderer returns 404 for both v1 and v2 and the PDF exceeds the fetch size limit, so the depth here is lower than for PHIA. Items below come from the abstract page and the Google Research blog, both cited.

- **A.** Build a comprehensive personal health agent for daily non-clinical settings over wearables plus personal health records. Needs derived from an analysis of web-search and health-forum queries plus user-centred design with users and health experts.
- **B/C/D.** Multimodal: consumer wellness device time series plus blood bioreviewers and personal health records.
- **E.** The **data science sub-agent** uses a **two-stage** process: first produce a statistical analysis *plan* from an underspecified query, then generate and execute code. So: code generation over dataframes, with an explicit planning stage in front, which is the notable delta vs PHIA.
- **F.** Per-user data plus orchestrator-maintained memory updates.
- **G/H/I.** No new ML model; no fine-tuning reported; no weights.
- **J.** "a base model (e.g., Gemini)". Exact model **UNVERIFIED**.
- **K. Agent architecture.** **Orchestrated multi-agent with dynamic role assignment.** Per the Google blog, the orchestrator "analyzes the user's need, dynamically assigns a 'main' agent and 'supporting' agents, and facilitates an iterative workflow of collaboration, reflection, and memory updates to synthesize a single, comprehensive response." Three specialists: data science agent, health domain expert agent, health coach agent.
- **L. Tools.** DS agent: time-series wearable data and blood bioreviewers, code execution. Domain expert agent: search over authoritative sources including **NCBI**. Health coach agent: modular architecture built on motivational interviewing. Exact tool signatures **UNVERIFIED** (no code release).
- **M. RAG.** Yes, over trusted medical literature databases (NCBI named).
- **N.** Conversational, user-initiated.
- **O.** Offline / on-demand.
- **P.** Personalised insights, recommendations, goal tracking.
- **Q.** 10 benchmark tasks, automated plus human evaluation, **>7,000 annotations, 1,100 hours** from health experts and end users. Described by the authors as "the most comprehensive evaluation of a health agent to date". Inter-rater agreement reported as "considerable"; numeric values **UNVERIFIED**.
- **R.** DS agent statistical analysis plan quality **75.6%** vs base model **53.7%**. Other numbers **UNVERIFIED**.
- **S.** **No code release found.** Not in the paper, not on the blog, not in the Awesome-AI-Agents-for-Healthcare index.
- **T.** The three-role decomposition; the two-stage plan-then-code pattern; the psychological-strategy coach module.
- **U.** Not extracted (paper body inaccessible via the fetch tools available). **UNVERIFIED**.
- **V.** Plan first, then generate code. Separate "what does the data say" from "what does medicine say" from "how do I get the user to act". The plan-then-code split is the reusable idea; the coach agent is out of scope for an early-warning system.

---

### 4.4 HiMe, self-hosted real-time personal health agent platform

Primary: https://arxiv.org/abs/2607.21019 | Code: https://github.com/thinkwee/HiMe

This is the closest existing system to the project brief and the most inspectable. Everything below marked "(code)" was read directly from source.

- **A.** No open-source, locally deployable platform exists that can process personal health data in real time with an LLM agent. Privacy-first, self-hosted.
- **B/C.** Real-time ingestion from **Apple Watch and iPhone** via companion iOS and watchOS apps. Public datasets (LifeSnaps, PMData, MMASH, CovIdentify, GLOBEM) are replayed through per-user adapters for evaluation.
- **D. Signals (code, `prompts/data_schema.md`).** ~50 feature types in an EAV `samples` table. Cardiovascular/respiratory: `heart_rate`, `resting_heart_rate`, `walking_heart_rate_avg`, `heart_rate_variability`, `blood_oxygen`, `respiratory_rate`, `vo2max`. Energy: `active_energy`, `resting_energy`. Rings: `exercise_time`, `stand_time`. Gait: `steps`, `distance`, `flights_climbed`, `walking_speed`, `walking_step_length`, `walking_asymmetry`, `walking_double_support`, `walking_steadiness`, `stair_ascent_speed`, `stair_descent_speed`, `six_minute_walk`. Running dynamics: `running_power`, `running_stride_length`, `running_vertical_oscillation`, `running_ground_contact`. Sleep: `sleep_in_bed`, `sleep_asleep`, `sleep_core`, `sleep_deep`, `sleep_rem`, `sleep_awake`, `sleeping_wrist_temp`. Body: `body_mass`, `body_mass_index`. Plus `mindful_session`, `time_in_daylight`, `water`, workout summaries.
- **E. Time-series to LLM (code).** **SQL over an EAV table, plus a stateful code tool.** The prompt gives a *feature inventory with stored units and conversion notes*, not data. Verbatim: *"You query `health_data` via the `sql` tool, read-only. The `samples` table is EAV with exactly 3 data columns, `timestamp`, `feature_type`, `value`. Feature names are **values in the `feature_type` column**, never column names."* Units are documented for conversion, e.g. *"`blood_oxygen`, decimal fraction 0-1 (x100 -> %)"*, *"`sleep_deep`, seconds (/60 -> min; slow-wave, N3)"*. The code tool holds "Jupyter-style state across calls".
- **F. Personalisation.** Long-term user model in a unified per-user database: `memory`, `user.md` (stable communication preferences and user-stated facts), `experience.md` (the agent's own learned data quirks), profiles, reports, scheduled tasks and monitoring rules.
- **G.** Statistical trigger rules (below) plus whatever the LLM computes. Five bundled analysis "skills" (code, `skills/`): `baseline_change_point.md`, `circadian_alignment.md`, `respiratory_screen.md`, `sedentary_behavior_audit.md`, `sleep_regularity_index.md`.
- **H.** No fine-tuning.
- **I.** Uses off-the-shelf open weights via vLLM.
- **J. LLMs.** 22 backbones swept. Local: Qwen 2.5/3/3.5/3.6 (1.5B to 35B), Gemma-4 (to 26B), Nemotron-3-nano, Granite-4.1-8b, GLM-4.7-flash. Hosted references: GPT-5-mini, DeepSeek-V4-flash, Gemini-3.5-flash. Provider adapters in code: `anthropic_provider.py`, `openai_provider.py`, `gemini.py`, `bedrock.py`, `zhipuai_provider.py`.
- **K. Agent architecture (code).** **Custom single event loop, hierarchical router plus sub-agents. Not LangGraph, not LangChain.** Paper: "The agent server runs a single loop that interleaves user messages, real-time monitor triggers, and scheduled tasks." A **chat orchestrator** is a pure dispatcher: verbatim from `prompts/rules_chat.md`, *"Your tools: `analyze`, `manage`, `reply_user`, `finish_chat`. You do NOT have `sql`, `code`, `update_md`, or `create_page`, every read of health data goes through `analyze`, every write side-effect goes through `manage`. You are a thin coordinator on top of two specialist sub-agents."* Sub-agents are one-shot executors: *"you are a one-shot executor, not a conversational agent."* Completion signal is a text response with no tool calls.
- **L. Tools (code, `backend/agent/tools/registry.py`, exact class list).** `SQLTool`, `CodeTool`, `PushReportTool`, `ReplyUserTool`, `CreatePageTool` (generates HTML plus Python-backed custom dashboards), `UpdateMdTool` (append/edit/replace on `user.md` and `experience.md`), `FinishChatTool`, `ReadSkillTool` (loads an analysis playbook on demand). Outbound messaging goes through a `GatewayRegistry` (Telegram, Feishu, iOS push). A `FactVerifier` classifies outbound messages and stores an evidence trail.
- **M. RAG.** No external corpus. Retrieval is over the user's own memory database and the on-demand skill files.
- **N. UX.** Chat via Telegram/Feishu, a Vue.js web dashboard, and native iOS/watchOS apps. Persona is a pixel-art cat.
- **O. Real-time vs offline.** **Real-time, always-on.** This is the whole point.
- **P.** Chat replies, pushed reports (full markdown report stored in DB plus a short `im_digest` one-liner for the messaging channel, with charts base64-inlined), generated dashboard pages, scheduled plans.
- **Q. Evaluation.** Replay of 5 public wearable corpora (10 random participants each) with **terminal-state oracles**: because every capability leaves a database state, the resulting state is compared against a gold state computed independently from the same trace. Metrics: per-role pass@1 (Route, Analysis, Memory, Plan, Hallucination), multi-turn MT, S5 (fraction of flawless 5-turn sessions), a data-to-report rubric judged against the participant's held-out self-report, trigger recall vs polling, on-device latency on an H200. Plus a **two-month field study with nine non-technical participants**.
- **R. Performance.** Analysis role: Qwen3.6-27b and Qwen3.5-35b-a3b reach **0.91**, above GPT-5-mini (0.76) and DeepSeek-V4-flash (0.85). **S5 (flawless 5-turn session) best is 0.44** (Gemma-4-26b-a4b) and **most backbones score 0**. Data-to-report rubric best is **45.8%** (DeepSeek-V4-flash, on 16 PMData participants), so cross-modal narration is weak even for frontier models. Triggers: tokens saved **49x to 121x**, recall 0.00->0.29, 0.69->0.89, 0.57->**0.43**, 0.58->**0.52**. Field study Likert: usability **4.67**, proactivity **4.56**, plan fit **4.00** (n=9).
- **S. Open source.** 59 stars, 6 forks, 11 open issues, created 2026-04-13, **last commit 2026-08-10**, Python 3.11+, 379 tracked files. Contents: `backend/`, `frontend/`, `ios/`, `docker/`, `docker-compose.yml`, `Dockerfile.backend/frontend/watch`, `prompts/` (14 markdown prompts), `skills/` (5 playbooks), `tests/`, `docs/`, `hime.sh`, `setup.sh`. **Real, production-grade, runnable.** **Licence: PolyForm Noncommercial 1.0.0** (verbatim first line of LICENSE: "Required Notice: Copyright 2026 HiMe Organisation"). Academic course project use should be fine; commercialisation is not. Note the arXiv paper is CC BY 4.0 but the code is not.
- **T. Reusable assets.** `prompts/data_schema.md` (best EAV-schema-to-LLM prompt I found), `trigger_evaluator.py` (a complete, small, readable statistical trigger engine), the dispatcher/sub-agent prompt split (`rules_chat.md`, `sub_analysis.md`, `sub_manage.md`), the terminal-state-oracle evaluation idea, the `im_digest` vs full-report two-body notification pattern, the `experience.md` self-learned-quirks file.
- **U. Limitations (authors').** Multi-turn reliability is "an open frontier" (S5 mostly 0); cross-modal time-series-to-narrative understanding is weak (best 45.8%); the field study is small and self-selected (n=9); scheduled plans are "slow to adapt to a changed routine"; models at or below 1.5B are insufficient.
- **V. Architectural lesson.** **The two-stage gate is the key idea.** A free deterministic statistical rule watches the stream at full rate; only when it fires does an expensive LLM analysis wake up. That is 49x to 121x cheaper than polling. But it is not free: recall dropped for half the backbones tested, because a trigger that never fires is a trigger that never detects. The trade-off between gate sensitivity and LLM cost is an explicit design axis, not a solved problem.

---

### 4.5 VitalAgent / VitalBench

Primary: https://arxiv.org/abs/2605.29483 | Code: https://github.com/DKSEZD/VitalAgent

- **A.** Existing mHealth systems are either task-specific prediction pipelines or reactive QA over static summaries. They lack temporal reasoning, persistent physiological context, and proactive monitoring over long signal streams.
- **B/C.** Public ECG/PPG corpora, not a live device: Icentia11k (556 QA), AF-PPG-ECG (556), PPG-DaLiA (400), WESAD (350). Plus 90.2 hours of continuous recording for the proactive track.
- **D.** Raw ECG and PPG; derived heart rate, HRV, RR-interval variability (coefficient of variation, normalised Shannon entropy, turning-point ratio), rhythm class (N / AF / AFL / Other), signal quality.
- **E. Time-series to LLM.** **Raw signals never reach the LLM.** Tools perform deterministic DSP and return "structured outputs (e.g., numerical summaries, temporal trends, or event annotations)". The LLM sees tool names, execution status, and returned structured data or errors. Explicitly: the design "decouples signal processing from language-based reasoning by externalizing physiological computations into dedicated tools."
- **F.** A compact temporal memory `M_t = (x_<t, s_<t, e_<t)`: history of raw signal windows, a streaming health-state tracker (HR, HRV, rhythm labels), and previous proactive alert records. Updated by `M_{t+1} = f_update(M_t, x_t, s_t, e_t)`.
- **G.** Deterministic DSP plus a rule-based rhythm classifier (`agent/proactive/rhythm_classifier.py`, 10 KB).
- **H.** **No fine-tuning.** Temperature 0, max 2048 output tokens.
- **I.** N/A.
- **J.** **DeepSeek-V4 Flash** for planning, evidence integration and response generation.
- **K. Agent architecture.** **Dual-mode.** Reactive: query -> LLM **planner** selects tools -> execute -> **validation** -> **replan** if needed -> response. That is plan-and-solve with a validate/replan loop, not vanilla ReAct. Proactive: streaming 10-second non-overlapping windows -> deterministic rule layer -> LLM judge -> merge -> episode-level alert.
- **L. Tools.** Paper claims 29 across 5 categories (Signal Analysis 13, Data Processing 3, Record Lookup 6, Proactive Context 5, Medical Knowledge 2). I enumerated **18 `@register_tool` decorators** in `agent/tools/`: `state_get_current_monitoring_state`, `state_get_previous_monitoring_state`, `state_get_monitoring_window`, `state_get_longitudinal_trend`, `state_get_evidence`, `state_get_dataset_capabilities`, `state_list_contexts`, `state_load_monitoring_states`, `state_build_from_ecg_record`, `state_build_from_ppg_patient`, `state_build_from_ppg_dalia_pickle`, `state_build_from_wesad_pickle`, `proactive_get_recent_alerts`, `proactive_explain_last_alert`, `proactive_list_patient_contexts`, `proactive_load_patient_context`, `medical_info_search`, `medical_knowledge`. The remaining signal-analysis tools (`analyze_heart_rate`, `ecg_diagnosis`, `analyze_hrv`) presumably live in `agent/mhealth/` or `agent/ecg/`; **the 29 count is UNVERIFIED against the code.** `ecg_diagnosis` is feature-flagged off by default (`get_config().tools.enable_ecg_diagnosis`).
- **M. RAG.** `medical_info_search` and `medical_knowledge` tools plus `agent/proactive/guidelines/`. Corpus not fully characterised.
- **N.** QA plus alerts.
- **O. Real-time.** Streaming replay at 10-second windows.
- **P.** Answers; alerts with urgency level and a natural-language rationale; `explain_last_alert`.
- **Q. Evaluation.** **Self-built benchmark.** 1,862 QA pairs (906 Tier A window-local, 956 Tier B multi-window), split 30/70 dev/test (557/1,305) with a fixed hash seed. Questions generated by an LLM from dataset annotations using templates; three types (`single_verify`, `single_choose`, `single_query`). Answers "grounded in annotations or signal-derived parameters", "directly provided or computed via deterministic rule-based extraction". **No human validation and no inter-rater agreement reported.** Two context settings: *leakage-free* (parameters derived from signals) and *oracle* (ground-truth annotations given).
- **R. Performance (leakage-free).** VitalAgent Tier A **0.860**, Tier B **0.557**. LifeAgent* 0.545 / 0.287 (paper text says the gap is 0.315 / 0.270). PHIA 0.395 / 0.246. Health-LLM few-shot 0.488 / 0.300. Ablations: w/o planner 0.701 / 0.342 (**the planner is the whole contribution**); w/o validation 0.849 / 0.569; w/o replan 0.855 / 0.563 (**validation and replan do essentially nothing, and w/o validation is actually better on Tier B**). Proactive: false alerts/hour 1.81 (rule only) -> 2.95 (plus LLM judge); alert latency 220 s -> 105 s; AF balanced accuracy 66.7%.
- **S. Open source.** Exists, **2 stars**, MIT, created 2026-05-28, **last commit 2026-07-13**. Real code: `agent/tools/` (5 modules, ~98 KB), `agent/proactive/` (9 modules incl. `intervention_decision.py` 29.6 KB, `llm_judge.py` 28.5 KB, `patient_context.py` 26.3 KB, `pipeline.py`, `replay.py`, `tracker.py`, `aggregator.py`, `rhythm_classifier.py`), `agent/web_demo.py` (39.7 KB), `config.py`, `schemas.py`, `uv.lock`, `tests/`. Note: a page-summarising fetch initially called this "a skeleton project"; **that was wrong**, direct API listing shows substantive code. VitalBench derives from 4 public datasets under their own licences (Icentia11k CC BY-NC-SA 4.0, PPG-DaLiA CC BY 4.0, WESAD UCI, AF-PPG-ECG non-commercial). A recent commit message reads "Fix VitalBench licensing update, Removed detailed description of the VitalBench...", so **benchmark redistribution may be restricted**.
- **T. Reusable assets.** `intervention_decision.py` is the single most reusable artefact in this whole survey for our project (see 4.5.1). Also the two-tier (window-local vs multi-window) benchmark design and the episode-level dedup logic.
- **U. Limitations (authors').** ECG/PPG only; **"relies on predefined monitoring criteria and domain-informed rules"**, adaptive policies unexplored; controlled benchmark environment, real-world noise and device heterogeneity untested; long horizons and complex health management need further work. Also: the authors themselves caveat the PHIA comparison as an input-format artefact.
- **V. Architectural lesson.** Two-layer alerting: a cheap deterministic guideline-grounded rule layer sets a floor, and an LLM judge is invoked **only when the rule outcome changes**, with the verdict cached and force-refreshed every 20 windows. Adding the LLM judge halved latency (220 s -> 105 s) but **raised false alerts 63%** (1.81 -> 2.95/hour). That is the timeliness-vs-burden trade-off quantified, which is directly relevant to us.

#### 4.5.1 VitalAgent's alerting policy, read from source

From `agent/proactive/intervention_decision.py` (verbatim docstring extracts):

- Two judge layers over the same tracked state: `RuleBasedJudge` (deterministic, guideline-grounded) and `ProactiveLLMJudge` (contextual). `InterventionDecision.evaluate` merges both into an `InterventionDecisionOutcome` holding rule, LLM and final merged results.
- *"Every rule is grounded in a specific clinical guideline. Each `ClinicalRule` carries a `GuidelineCitation` that names the guideline, section ID, recommendation class where applicable, and a short paraphrase."*
- *"Rules are data, not code shape. Adding a rule means appending one `ClinicalRule` instance to the default registry; the dispatch loop is unchanged."*
- Registry split into `CORE_RULES` (any cardiac signal), `ECG_EXTRA_RULES`, `PPG_EXTRA_RULES`, selected by a `Modality` enum (ECG/PPG). ECG_EXTRA and PPG_EXTRA are **empty in Phase 1**.
- Phase 1 ships **three** live rules: `_trigger_extreme_bradycardia` (urgency CRITICAL), `_trigger_extreme_tachycardia` (CRITICAL), `_trigger_sustained_tachycardia` (MEDIUM). One staged rule `long_af_episode` (HIGH) fires at >= 24 h sustained AF.
- `Urgency` enum: `NONE < LOW < MEDIUM < HIGH < CRITICAL`, merged by max rank (`_urgency_rank`).
- LLM-judge invocation control, verbatim: *"Force the LLM judge to re-evaluate even when the rule outcome has not changed, after this many windows. At the default 10-second window length this is roughly 3.3 minutes: short enough that a stable reading cannot silently persist for many minutes without LLM re-evaluation, long enough to amortise LLM cost across repeated windows."* `_JUDGE_FORCE_REFRESH_WINDOWS = 20`.

**This is the state of the art for "when to alert" in a health agent, and it is a threshold table with a caching policy.** There is no model of user interruption cost, no user state, no learned policy. That is the gap.

---

### 4.6 AI on the Pulse (@HOME)

Primary: https://arxiv.org/abs/2508.03436 | Code: https://github.com/davegabe/ai-on-the-pulse

- **A.** Continuous anomaly detection for elderly patients at home, without requiring continuous labelling.
- **B/C.** Consumer smartwatches (5-day battery, **1-minute sampling**) plus ambient room sensors, in real homes. Offline experiments additionally used DREAMER, HCI, WESAD.
- **D.** Heart rate, HRV, CVRR, respiration rate, SpO2, systolic/diastolic BP, steps, sleep phases; ambient temperature, humidity, CO2, air pressure, luminosity, TVOC, room location.
- **E. Time-series handling.** **UniTS**, a multivariate time-series foundation model, adapted for *contextual* anomaly detection by reformulating it as an **imputation** problem: mask future values while preserving past values and contextual tokens. Sliding windows of 16 samples with 8 masked. Architecture: multi-head self-attention, dynamic FFN, gating, "Tower" reconstruction module. **The LLM plays no part in detection.**
- **F.** Per-patient unsupervised baseline learned from that patient's own history.
- **G.** UniTS. **H.** Trained/adapted per deployment. **I.** UniTS is public; @HOME weights **UNVERIFIED**.
- **J. LLM.** **GPT-4o**, used only post hoc: "explanations generated via GPT-4o are provided alongside each anomaly for review", tailored to "each clinician's expertise, terminology, and workflow". The prompt and serialisation format are **not published**. **UNVERIFIED.**
- **K. Agent architecture. NONE.** **Flag: the LLM here is a one-shot explainer.** There is no loop, no tool, no decision. An ordinary function call would do exactly this.
- **L/M.** No tools, no retrieval.
- **N.** Clinician-facing dashboard, not patient-facing.
- **O. Real-time.** Yes, deployed continuously.
- **P.** Anomaly flags with GPT-4o natural-language explanations for clinicians.
- **Q. Evaluation.** (i) Offline: 80:20 split, 5-fold CV on DREAMER/HCI/WESAD(ECG)/WESAD(BVP); "anomaly" defined as points below the 3rd or above the 97th percentile, i.e. **a synthetic percentile heuristic, not a clinical label**. (ii) Deployment: **6 elderly patients**, 3 months, 32 detected anomalies, reviewed by **a single senior geriatrician**; 93.75% confirmed true positives, 6.25% sensor errors. **n=1 rater, so no inter-rater agreement is possible.**
- **R.** UniTS average F1 **0.821 +/- 0.049** vs DAGMM **0.673 +/- 0.066** (second best), ~+22% relative, over 12 baselines.
- **S. Open source.** Exists, **12 stars**, 2 forks, **no licence**, created 2025-06-03, **last push 2025-06-06** (three days of activity, and two months *before* the paper appeared). Contents: `analysis.py` (11.9 KB), `results.py` (19.0 KB), `preprocess.py` (0.5 KB), `run.py` (0.5 KB), `README.md` (12 KB), plus `data/`, `examples/`, `src/`. **Real code but small, unlicensed, and abandoned.** Do not depend on it. No LLM prompts included.
- **T.** The imputation-reformulation trick for contextual anomaly detection; the baseline list for benchmarking anomaly detectors on physiological data.
- **U.** n=6 patients, 3 months, single reviewer; missing-data handling limited to <=5 consecutive samples; no comparison to standard clinical monitoring; the offline "anomaly" ground truth is a percentile artefact.
- **V.** **This is the honest architecture for the detection half of an early-warning system, and it deliberately does not use an LLM to detect.** A specialist time-series model detects; an LLM explains. It also shows the field's evidentiary ceiling: 6 patients and one geriatrician.

---

### 4.7 Health-LLM and HealthAlpaca (MIT Media Lab plus Google)

Primary: https://arxiv.org/abs/2401.06866 | Code: https://github.com/mitmedialab/Health-LLM

- **A.** Can LLMs make health inferences from wearable sensor data plus context?
- **B/C/D.** Four datasets: PMData (16 participants, 5 months, Fitbit Versa 2), LifeSnaps (71, 4+ months, Fitbit Sense plus surveys), GLOBEM (497 participants, 705 user-years, mobile plus wearable plus survey), AW_FB (49, 104 h lab, multiple devices). Signals: steps, calories, resting HR, sleep minutes, mood.
- **E. Time-series to LLM.** **Direct natural-language string serialisation.** Verbatim basic-context template: *"The analysis of recent period: {14} days averaged sensor readings show: Steps: {812.0} steps, Burned Calories: {97.0} calories, Resting Heart Rate: {66.54} beats/min, Sleep Minutes: {487.0} minutes, Mood: {3} out of 5."* Temporal context replaces the averages with raw arrays: *"Steps: {"NaN, 991.0, ..., NaN"} steps, Burned Calories: {"NaN, 94.0 ..., NaN"} calories"*. Missing values are kept as literal `NaN` with no imputation.
- **F. Personalisation.** Four context enhancement strategies: user context (age, sex, height), health context (mechanism definitions, e.g. *"Readiness score is decided by activity, recent sleep and heart rate variability"*), temporal context (raw sequences), and all combined.
- **G/H.** Supervised fine-tuning. HealthAlpaca-7b/13b (full) and -lora-7b/13b. 4x A100 80GB, batch 128, cross-entropy, Adam, LR 2e-5, 3-5 epochs, ~3.4 h.
- **I. Weights.** Repo says "will be made publicly available upon the release of the camera-ready version"; actual availability **UNVERIFIED**.
- **J.** 12 LLMs evaluated including GPT-3.5, GPT-4, Gemini-Pro, MedAlpaca, Palmyra-Med.
- **K. Agent architecture. NONE.** **Flag: no agent, no tools, no function calling, no retrieval.** Pure prompting plus fine-tuning.
- **L/M.** None.
- **N.** Batch prediction, not interactive.
- **O.** Offline.
- **P.** Ten task outputs: stress (MAE), readiness (MAE), fatigue (Acc), sleep quality (MAE), stress resilience (MAE), sleep disorder (Acc), anxiety (MAE), depression (MAE), activity recognition (Acc), calorie burn (MAE).
- **Q.** Fully automatic against dataset labels (self-reported). No human raters, so no inter-rater question arises. Traditional baselines: MLP, SVM, RandomForest, BERT.
- **R.** "Context enhancement can yield up to 23.8% performance improvement" (abstract; specific cell not traced). HealthAlpaca "shows the best performance in 8 out of 10 consumer health tasks". Palmyra-Med gained 44.58% from temporal context on one task.
- **S. Open source.** 104 stars, 20 forks, **MIT**, created 2024-04-27, **last push 2024-08-09**, Python. **Dormant for two years.**
- **T.** The serialisation templates are directly copyable and are the cleanest published example of naive text serialisation. The 10-task / 4-dataset benchmark suite is reused by BALMS and VitalBench.
- **U. Limitations (authors').** Self-reported labels limit clinical applicability; black-box nature complicates clinical validation; documented cases of "false and hallucinated reasoning"; inconsistent cross-dataset generalisation; privacy and bias unresolved.
- **V. This is the control condition.** It shows what raw serialisation buys you, and PHIA's 22% "Numerical Reasoning" baseline shows what it costs on precise numeric queries. Cite it as the thing tool use is supposed to beat.

---

### 4.8 openCHA (Conversational Health Agents)

Primary: https://arxiv.org/abs/2310.02374 | Journal: JAMIA Open 8(4) ooaf067, 2025-07-06, DOI 10.1093/jamiaopen/ooaf067, https://academic.oup.com/jamiaopen/article/8/4/ooaf067/8186991 | Code: https://github.com/Institute4FutureHealth/CHA

- **A.** Conversational health agents lack multi-step problem solving, personalisation and multimodal analysis. Provide a framework so developers can wire external sources into an LLM agent.
- **B/C/D.** Pluggable. Demonstrated on PPG (heart rate, 32 HRV parameters via NeuroKit), activity, sleep, stress, plus nutrition via Nutritionix.
- **E. Time-series to LLM.** **Typed tool outputs, documented in the tool description.** Read from `src/openCHA/tasks/affect/ppg_analysis.py`: the `PPGAnalysis` task declares `outputs` as a documented JSON key list, e.g. *"returns an array of json objects which contains the following keys: **HRV_MeanNN**: The mean of the RR intervals. **HRV_SDNN**: The standard deviation of the RR intervals. **HRV_RMSSD**: ... **HRV_pNN50**: The proportion of RR intervals greater than 50ms..."*. Data itself passes between tasks by reference through the **DataPipe** (`datapipe:datapipe_key`), never through the LLM context.
- **F.** Per-patient data source binding.
- **G.** External signal-processing and ML models as tasks.
- **H/I.** No fine-tuning.
- **J.** Model-agnostic: GPT-4, Claude, Mistral, Gemini.
- **K. Agent architecture.** **Orchestrator with a Task Planner using Tree-of-Thought or ReAct**, plus Task Executor, Data Pipe, Promptist, Response Generator.
- **L. Tools (read from repo, `src/openCHA/tasks/`).** `affect_ppg_get`, `affect_ppg_analysis`, `affect_activity_get`, `affect_activity_analysis`, `affect_sleep_get`, `affect_sleep_analysis`, `affect_stress_analysis`, `Predictor`, `AE`, `ask_user`, `extract_text`, `google_search`, `google_translator`, `serpapi`, `run_python_code`, `query_nutritionix`, `calculate_food_risk_factor`, `initialize_task`.
- **M. RAG.** Knowledge bases, literature, healthcare websites, knowledge graphs, as pluggable external sources.
- **N. UX.** Multimodal chat (text, audio, images). **Notable: `ask_user` is a first-class task.** Verbatim description: *"This task is asking question back to the user and stops planning. When needed, the planner will decide to ask question from user and use the user's answer to proceed to the planning."* `return_direct: bool = True`.
- **O.** Reactive, on-demand.
- **P.** Empathy-tuned conversational responses.
- **Q/R.** Diabetes management accuracy **92.1%** vs GPT-4 51.8%; mental-health evaluator MAE **0.31** vs GPT-4 2.29; PPG heart-rate MAE **2.83** vs GPT-4o 8.93; empathy detection 89%. All are the framework's own case studies.
- **S. Open source.** 143 stars, 40 forks, **MIT**, created 2023-12-02, **last commit 2025-11-05**, Python, 221 tracked files, `src/`, `tests/`, `examples/`, `docs/`, Dockerfile, pre-commit config. **Real, well-structured, most permissively licensed option.** Docs at https://docs.opencha.com/
- **T.** The `ask_user` task (the only clean implementation of "agent decides to ask the user" I found), the DataPipe pass-by-reference pattern, the typed-output-in-tool-description convention, the affect task family.
- **U.** Latency from multiple external source calls; token limits constrain task complexity; planning robustness depends on the LLM; accuracy bounded by external source quality.
- **V. Pass data by reference, not by value.** The DataPipe means a 30-day PPG record never enters the context window; only a key does. And `ask_user` shows that "ask the user" can be just another tool the planner may select. But note: in openCHA this is *clarification within a session*, not an unprompted interruption.

---

### 4.9 SAGE (Sensor-Augmented Grounding Engine for LLM-Powered Sleep Care Agent)

Primary: https://arxiv.org/abs/2604.16342 (CHI EA 2026). Lee, Cho, Kwak, Calvo (Imperial College London, KIST).

**This is the closest published system to the project's proactive-monitoring premise, and it is the only one using LangGraph.**

- **A.** Ground an LLM sleep-care agent in real sensor data and deliver selective, non-fatiguing proactive notifications.
- **B/C.** Two Withings devices: **Sleep Analyzer** (under-mattress, sleep stages Light/Deep/REM, WASO, apnea, snoring) and **ScanWatch** (30-day battery, steps, calories, HR extremes). Ingested from the Withings Cloud API as JSON.
- **D.** Sleep stages, WASO, respiratory reviewers, daytime steps/calories/HR.
- **E. Time-series to LLM.** **Text-to-query, not code and not serialisation.** Data is normalised into a queryable time-series layer in **Azure Data Explorer**; the LLM emits **Kusto Query Language (KQL)**; ADX returns exact numbers; the LLM only explains them. The authors say KQL was chosen over SQL because "its pipeline-based logic suits LLM step-by-step reasoning", and the design confines the LLM to "question interpretation" and "explanation of retrieved facts" with ADX as single source of truth.
- **F.** Personal baselines (7-day moving average).
- **G.** Deviation thresholds over personal baselines.
- **H/I.** No fine-tuning.
- **J.** GPT-5.2 and GPT-5 mini.
- **K. Agent architecture.** **State machine on LangGraph.** User input is classified into `chat` / `data` / `unsupported` and routed. Three components: data pipeline, conversational interface, monitoring module.
- **L. Tools.** KQL generation and execution against ADX; a temporal normalisation framework the authors describe as "When / Compared to What / Which Metric"; WhatsApp delivery via Twilio and Azure Functions.
- **M. RAG.** None over an external corpus; grounding is over the user's own ADX store.
- **N. UX.** **WhatsApp.** Text only.
- **O. Real-time.** Continuous ingestion with a monitoring module.
- **P.** Answers plus system-initiated notifications.
- **Q. Evaluation.** **90 synthesised questions** (30 simple retrieval, 30 comparative, 30 null-data), scored on M1 executable query rate, M2 query intent match, M3 data retrieval correctness, M4 response faithfulness. **No human study, no real users, synthetic queries.**
- **R.** "100% success in M1-M4 for simple retrieval and most comparative queries", with three named failure modes: complex period comparisons cause syntax errors (fix: explicit filter-then-aggregate rules); relative time expressions cause semantic errors (fix: a time normalisation module); multi-device metric conflicts cause logic errors (fix: sensor priority policies).
- **S. Open source.** **None found.** Research prototype, CHI extended abstract.
- **T.** The "When / Compared to What / Which Metric" query decomposition frame; the intent classifier as a state-machine router; the KQL-instead-of-pandas choice; the three named failure modes, which are exactly the failure modes we will hit.
- **U.** No multi-turn clarification for ambiguous queries; ignores context like caffeine and stress; uses API-level aggregates rather than beat-to-beat signals; text-only interface; synthetic validation only; needs a field study.
- **V. Notification policy, in the authors' words: "selective system-initiated monitoring that triggers notifications only upon detecting meaningful deviations against personal baselines to reduce alert fatigue."** Concretely: **>= +/-30% change from the 7-day moving average, or critical sleep debt.** That is the entire policy. It is a hardcoded percentage. This is the current bar to beat.

---

### 4.10 ContextAgent (NeurIPS 2025)

Primary: https://arxiv.org/abs/2505.14668

**The most rigorous published treatment of "should I proactively help right now", though not health-specific.**

- **A.** Existing proactive agents either observe only enclosed environments (desktop UIs) or use rule-based notifications, giving poor intent understanding and limited functionality.
- **B/C/D.** Wearable-captured egocentric **video** and **audio**, plus smartphone notifications (calendar, reservations). Not physiological.
- **E. Serialisation.** Modalities are converted to *text descriptions* first: Qwen-2.5-VL for visual context via in-context learning, Whisper for speech/acoustic descriptions, structured notification data. Combined as `C = [C_V, C_A, N]`. The authors list "relies on textual descriptions rather than raw multimodal data" as a limitation.
- **F.** Personas from historical data.
- **G/H.** **Supervised fine-tuning with chain-of-thought**, reasoning traces distilled from Claude-3.7-Sonnet. Fine-tuning limited to models <= 7B.
- **I.** Weights availability **UNVERIFIED**.
- **J.** 10 models evaluated: GPT-4o, GPT-3.5-Turbo, Llama-3.1 8B/70B, Qwen2.5 1.5B/3B/7B/72B, DeepSeek-R1 variants.
- **K. Agent architecture.** Context extraction -> **proactive predictor** -> conditional tool calling.
- **L. Tools.** 20, e.g. `GoogleMap`, `GetCurrentGPS`, `CheckAgendaTimeConflict`, `GetOnlineProductPrice`, `BookUber`, `WikipediaSearch`, `GoogleSearch`, `SetTimer`, `PlayMusic`.
- **M.** Web search among the tools.
- **N.** Unobtrusive proactive assistance.
- **O.** Real-time streaming sensory context.
- **P.** Either silence, or a proactive service with tool calls.
- **Q. Evaluation.** ContextAgentBench: **1,000 samples, 9 daily scenarios, 20 tools**. Built from 200 human-created exemplars, expanded by an LLM diversification pipeline (GPT-4o, Claude-3.7, Gemini-2.0-Flash), then annotators checked rationality and scripts verified tool-argument format. A 300-sample "Lite" split has raw sensor data (Pexels footage plus self-collected egocentric video/audio, IRB approved). **Self-built benchmark, LLM-expanded.**
- **R.** Metrics for the *decision to act*: **Acc-P** (proactive prediction accuracy), **MD** (missed detections), **FD** (false detections), **RMSE** on the 1-5 score. Tool metrics: precision, recall, F1, Acc-Args. Llama-3.1-8B backbone: Acc-P **87.4%** (+8.5 over best baseline), F1 **62.6%** (+7.0), Acc-Args **44.8%** (+6.0). Baselines: Proactive Agent, Vanilla ICL, CoT, ICL-P, ICL-All, Vanilla SFT.
- **S.** **No repository URL in the paper.** **UNVERIFIED / likely unavailable.**
- **T.** **The 1-5 "proactive score" with a fire-at->=3 threshold, and the MD/FD/RMSE metric set for evaluating an interruption decision.** That metric set is directly transplantable to a health early-warning agent and I did not find it used anywhere in the health literature.
- **U.** Requires fine-tuning, restricting deployment to small models; text-description bottleneck; synthetic data generation may hurt generalisation; privacy concerns for always-on wearable capture.
- **V. Treat "should I speak" as a supervised prediction problem with its own accuracy, its own miss rate and its own false-alarm rate, separate from "what should I say".** No health agent does this. This is the strongest evidence that our project's premise targets a real gap.

---

### 4.11 Project Hermes

Primary: https://arxiv.org/abs/2602.18643. Richik Chakraborty, 2026-02-20, q-bio.QM. Single author.

**The only health system found that asks the user a question in order to decide whether an alert is real.**

- **A.** Wearable prediction systems produce too many false positives. Validate alerts downstream of an arbitrary upstream predictor.
- **B/C/D.** Model-agnostic; demonstrated on migraine prediction from wearables.
- **E/G.** Post-prediction validation, not detection.
- **K. Architecture.** A validation layer with three mechanisms: **(1) LLM-generated contextual questions, (2) targeted user feedback collection, (3) Bayesian confidence update** to separate true positives from false alarms.
- **N. UX.** The system asks the user a question when it is unsure. This is the interruption-as-evidence-gathering pattern.
- **O.** Real-time, downstream of a live predictor.
- **Q/R.** 60-day migraine prediction study: **false positive rate 61.7% -> 12.5%** (a 34-point absolute reduction, reported by the author as "34% reduction"), sensitivity maintained at **89%**, mean lead time **4.2 hours** before symptom onset. Study size, recruitment and rater details **UNVERIFIED**.
- **S.** **No code found.**
- **U.** Single-author preprint, no journal venue found, no code, study details not surfaced. **Treat the numbers with caution.**
- **V. Asking the user is not a cost, it is a measurement.** A cheap question can collapse a false positive rate by 5x. If our project wants a defensible reason to interrupt, this is it: interrupt to *acquire information that changes the posterior*, not merely to inform.

---

### 4.12 HealthClaw (self-evolving longitudinal health agent)

Primary: https://arxiv.org/abs/2607.13940 | Code: https://github.com/HC-Guo/HealthClaw

- **A.** "Personal health management unfolds over repeated encounters, yet most health AI systems treat each request in isolation."
- **E/F. Memory architecture (the contribution).** Five layers: **L0-L1** shared behavioural rules, safety constraints, domain knowledge; **L2** durable profile facts (conditions, allergies, medications, preferences); **L3** reusable procedures for recurring tasks; **L4** time-stamped episodic traces and feedback. Separating shared governance from private longitudinal memory enables selective retrieval without exposing the whole record.
- **K. Agent loop.** Perception (assemble request plus health signals plus context) -> Reasoning (plan with task-specific memory and safety rules) -> Action (tool invocation) -> **Induction** (decide post-episode what updates L2, revises L3, stays in L4, or is excluded). Induction is the self-evolution mechanism.
- **L. Tools.** General: lifestyle logging, trend summarisation, medication management, interaction checking, report interpretation. Task-specific: medical imaging classifiers, EHR prediction models, protein/genomics tools. External: biomedical references, MyGene.info, Ensembl, variant lookup, web search.
- **O/N.** **Reactive.** Responds to requests; does not autonomously initiate.
- **Q. Evaluation.** Synthetic year-long benchmark: 20 simulated users x 365 daily interactions, 1,000 probes (900 longitudinal support plus 100 privacy), hidden event ledger as ground truth, plus 9 biomedical tasks x 200 cases. **Graded by a Qwen-3.7 evaluator with fixed rubrics. "No human ratings were used."** LLM-as-judge throughout, so self-preference bias is a live concern.
- **R.** Longitudinal support accuracy **0.2% (current-query only) -> 45.7% (HealthClaw) vs 61.2% (full-history)**. Note **full history still wins**; HealthClaw's selling point is that it uses **71.7% fewer prompt characters**. Privacy probes: answer accuracy 64.0% vs 44.0%/40.0%; constraint violations 24% vs 41-53%; unauthorised disclosure 5% vs 15-18%. Biomedical tasks: mean **+27.0 pp**, 7 of 9 significant after FDR correction; NoduleMNIST3D +61.5 pp, GeneTuring +52.5 pp; SOFA (+5.0) and diabetes readmission (+4.5) not significant.
- **S.** 148 stars, 6 forks, **MIT**, created 2026-03-22, **last commit 2026-07-27**, Python. Includes core framework, demo workflows, evaluation scripts. **Best-licensed longitudinal-memory codebase found.**
- **U.** Offline simulated trajectories only; no human ratings; a documented failure mode where weak evidence reinforced an incorrect prior; some task tools sourced near benchmark origins, weakening zero-shot claims.
- **V. The L2/L3/L4 split (durable facts / reusable procedures / episodic traces) with an explicit induction step is a concrete answer to "what do you carry across days".** But note the honest result: retrieving from structured memory is still 15 points *worse* than just pasting the whole history, and the win is cost, not accuracy.

---

### 4.13 SentinelBench (Microsoft Research plus University of Florida)

Primary: https://arxiv.org/abs/2606.05342 | Code: https://github.com/microsoft/sentinel_environments | Site: https://sentinelbench.com/

Not health, but it is the only benchmark that measures **whether an agent can wait properly**.

- **A.** "The default model of agent behavior is continuous action... this is the wrong approach for many long-running tasks", which are better served by sustained attention: monitor, notice when an external event makes progress possible, then respond promptly without wasting resources while waiting.
- **Q. Design.** 100 tasks across **10 synthetic web environments** (email, team messaging, professional networking, music streaming, photo sharing, stock trading, code hosting, calendar, academic search, video streaming). **No health domain.** Each environment exposes a live web interface and replays a scripted event sequence.
- **R. Metrics.** **Task completion** (passive tasks after target events; active tasks by correct DB state; no-op tasks by continuing to monitor to simulation end), **reaction time** (task completion time minus target event time), **resource utilisation** (input tokens, output tokens, monetary cost). The paper notes token metrics "require a cooperative agent that self-reports token use".
- **Key finding.** Two tool designs are contrasted: `sleep(time)` (unconditional wait) vs `wait_for(condition, timeout)` (event-driven). `wait_for` costs **9.7x less** while completing more tasks. GPT-5.4 reaches **75%** success with `wait_for` vs **48%** for GPT-4o; Qwen 3.5:9B local matches GPT-4o at 48%. GPT-5.4 with `sleep` costs **5.1x more** per task. At 40-minute durations, success drops to 56% (sleep) vs 69% (`wait_for`).
- **S.** Public: https://github.com/microsoft/sentinel_environments, including environments, task scenarios, synthetic catalogs and the data-generation pipeline. Stars/licence **UNVERIFIED**.
- **V. `wait_for(condition, timeout)` is a better primitive than `sleep` plus polling, by roughly 10x on cost.** That is the same lesson HiMe's trigger gate teaches, arrived at independently in a completely different domain. Strong convergent evidence for a condition-driven wake-up architecture.

---

### 4.14 Other systems, briefly

**BALMS** (arXiv:2608.27219, Dartmouth plus Cambridge, 2026-08-27). Benchmarks three paradigms on longitudinal mental-health sensing: prompt-based (Health-LLM style text arrays, verbatim example `[Steps]: [4664, 3035, NaN, ...]`), tool-based (PHIA-style ReAct over pre-loaded pandas DataFrames), and memory-based (Chunk RAG and RAPTOR hierarchical chunking). Datasets: DiversityOne (782 participants, 28 days, 1,355 samples), PMData (16, 5 months, 1,448), GLOBEM (497, multi-year, 1,640). **Damning headline: "Zero-shot agents rarely outperform a simple mean baseline, except with stronger backbones."** Claude-Haiku-4.5 with Health-LLM got 0.42 MAE vs 0.58 mean baseline on DiversityOne. Long-horizon scaling (7 to 28 day look-back): retrieval benefits most, prompt-based **degrades** as context grows. T2 uses LLM-as-judge rubrics. Retrospective, not proactive; authors state "we do not test agents in real-world interactive or intervention settings". Used standard LangChain implementations for baselines. Code availability **UNVERIFIED**. https://arxiv.org/abs/2608.27219

**LifeAgentBench / LifeAgent** (arXiv:2601.13880, UCSD, 2026-01-20). 22,573 questions for long-horizon, cross-dimensional, multi-user lifestyle health reasoning; 11 LLMs evaluated; bottlenecks identified in "long-horizon aggregation and cross-dimensional reasoning". LifeAgent baseline "integrates multi-step evidence retrieval with deterministic aggregation". Benchmark at an anonymous 4open.science URL; **VitalAgent's authors report the LifeAgent code is not public and they reproduced the pipeline.** https://arxiv.org/abs/2601.13880

**ProAgentBench** (arXiv:2602.04482, Tsinghua, 2026-02-09). >28,000 events from 500+ hours of real continuous working sessions captured with a "LifeTrace" app (1 Hz screenshots plus app logs). Formalises the timing decision as binary classification `B_t = f_when(U, O_1:t) in {0,1}`, and states the cost model explicitly: *"Low precision leads to alert fatigue, excessive false alarms causing users to ignore or disable"* vs *"low recall means missed assistance opportunities"*. Best zero-shot timing accuracy **64.4%** (DeepSeek-V3.2); fine-tuned LLaMA-3.1-8B reaches **74.0%** with real data vs 62.1% with synthetic. Desktop, not physiological. Code released but anonymised at time of writing. https://arxiv.org/abs/2602.04482

**EmBot expert study** (arXiv:2604.04915, IH '26). Semi-structured interviews with **15 mental health experts** who used a functional mobile probe combining wearable stress detection with LLM conversation. Findings on triggering: **capped alerts, adaptive pacing, disengagement detection**; incorporate location/activity/sleep for relevance; **explicitly explain detection rationale** and let users query the source ("what heart rate change?"); include a **confirmation/rejection step before the LLM engages**. The authors offer no formal policy, only "preliminary design considerations". Stress detection in the probe was **simulated, not validated**. This is the best available requirements evidence for an interruption policy. https://arxiv.org/abs/2604.04915

**Can LLM Coding Agents Reason About Time Series?** (arXiv:2606.16545, 2026-06-16; Rechtorik, Dusek, Kasner). See section 6.2. Code: https://github.com/DekuD2/can-llm-coding-agents-reason-about-time-series (2 stars, MIT, created 2026-05-25, last commit 2026-06-11).

**TS-Agent** (arXiv:2510.07432, J.P. Morgan AI Research). "LLMs exhibit strong symbolic and compositional reasoning, yet they struggle with time series question answering as the data is typically transformed into an LLM-compatible modality, e.g., serialized text, plotted images, or compressed time series embeddings. Such conversions impose representation bottlenecks, often require cross-modal alignment or finetuning, and can exacerbate hallucination and knowledge leakage." Solution: LLM does only iterative evidence-based reasoning; statistical and structural extraction is delegated to tools on raw sequences. This is the clearest published statement of the anti-serialisation position. https://arxiv.org/abs/2510.07432

**TS-Reasoner** (arXiv:2410.04047). LLM for high-level task decomposition, external programs for numerical computation, statistics and data retrieval. Three mechanisms: in-context learning for unseen tasks, self-correction via error feedback, program-aided execution for numerical precision. Reports an 87% improvement over the best baseline on causality analysis, attributed to program-aided statistical tools. https://arxiv.org/abs/2410.04047

**TimeSeriesExam** (arXiv:2410.14752). 700+ procedurally generated MCQs from 104 templates across pattern recognition, noise understanding, similarity, anomaly detection, causality. 7 LLMs. Closed-source models understand simple concepts better; **all models struggle with causality**. Reused as a benchmark by arXiv:2606.16545. Follow-up: TimeSeriesExamAgent (arXiv:2604.10291) scales generation to real datasets in healthcare, finance and weather. https://arxiv.org/abs/2410.14752

**RubricsTree** (arXiv:2606.18203, Google-affiliated authors incl. Palangi, McDuff, Patel, Metwally). Hierarchical taxonomy of **100+ atomic, clinically-verifiable Boolean rubrics** for open-ended evaluation of personal health agents across medical knowledge, communication, safety guardrails, personalisation and factual grounding, including "health memory". 532-query internal set curated from 4,000 user queries; HealthBench-Hard subset 362. **ICC3 improved 0.291 -> 0.876** (i.e. Boolean atomic rubrics dramatically improve rater reliability over holistic scoring), perturbation detection 93-100%, downstream optimisation gains +18.6% to +66.7%. "Code will be released after official publication." **This is the best available answer to "how do we evaluate an open-ended health agent reliably".** https://arxiv.org/abs/2606.18203

**MedMemoryBench** (arXiv:2605.11814). ~2,000 sessions, 16,000 turns of synthesised long-horizon medical trajectories from clinically grounded synthetic archetypes, expert-validated. Introduces an "evaluate-while-constructing" streaming protocol and formalises **memory saturation**, "where sustained information influx actively degrades retrieval and reasoning robustness". No wearable content. https://arxiv.org/abs/2605.11814

**Always-On Agents survey** (arXiv:2606.30306). Six diagnostic axes per state item: authority, scope, mutability, provenance, recoverability, actionability. State lifecycle: written, validated, organized, retrieved, acted upon, updated, forgotten, audited, rolled back. Concludes the literature "concentrates more heavily on accumulating and retrieving state than on governing, recovering, or relinquishing it". **Does not cover interruption or notification policy** (checked). https://arxiv.org/abs/2606.30306

**Apple.** No peer-reviewed Apple personal-health-agent paper found. "Health+" AI coaching for 2026 is **press rumour only, UNVERIFIED**, sourced to sites like wareable.com. The nearest real artefact is **OpenMHC** (arXiv:2607.16235, "OpenMHC: Accelerating the Science of Wearable Foundation Models", v3 2026-08-08), from the My Heart Counts study: >60 million hours of wearable data, 19 sensor channels, 169 linked health variables, 11,894 participants, with released dataset (to qualified researchers), model implementations, benchmark and **open weights**, CC BY 4.0. Author list includes Xin Liu and Akshay Paruchuri (also PHIA authors). Affiliation appears Stanford-led; **Apple affiliation UNVERIFIED**. https://arxiv.org/abs/2607.16235

---

## 5. Repository inspection table

All figures from the GitHub REST API on 2026-08-30.

| Repo | Exists | Stars | Forks | Last commit | Licence | Real code or stub | Runnable | What is reusable |
|---|---|---|---|---|---|---|---|---|
| [yahskapar/personal-health-insights-agent](https://github.com/yahskapar/personal-health-insights-agent) (PHIA) | Yes | 62 | 13 | 2025-12-21 | CC BY-NC 4.0 (API: NOASSERTION) | **Real.** `phia_agent.py` 9.0K, `prompt_templates.py` 13.5K, `data_utils.py` 14.4K, demo notebook, 2 eval spreadsheets, few-shots, synthetic plus real user data | Yes, needs Tavily key plus an LLM. Depends on `onetwo` | Dataframe schema preamble, ReAct template, 20 few-shots, 4,000-question objective eval set, 172 open-ended queries, `simple_python_executor` |
| [thinkwee/HiMe](https://github.com/thinkwee/HiMe) | Yes | 59 | 6 | 2026-08-10 | **PolyForm Noncommercial 1.0.0** | **Real, production grade.** 379 files: backend, Vue frontend, iOS/watchOS, Docker, 14 prompts, 5 skills, tests | Yes, `docker-compose`, setup wizard, iOS app | `prompts/data_schema.md`, `trigger_evaluator.py`, dispatcher/sub-agent prompt split, `im_digest` pattern, terminal-state oracle eval |
| [DKSEZD/VitalAgent](https://github.com/DKSEZD/VitalAgent) | Yes | **2** | - | 2026-07-13 | **MIT** | **Real.** `agent/tools/` 5 modules ~98K, `agent/proactive/` 9 modules, `web_demo.py` 39.7K, `config.py`, `schemas.py`, tests, uv.lock | Likely, needs dataset downloads plus a DeepSeek key | **`intervention_decision.py`** (clinical rule registry, urgency enum, LLM judge caching), `llm_judge.py`, tool registry pattern, two-tier benchmark design |
| [davegabe/ai-on-the-pulse](https://github.com/davegabe/ai-on-the-pulse) | Yes | 12 | 2 | **2025-06-06** (3 days of activity, abandoned) | **None** | **Real but thin.** `analysis.py` 11.9K, `results.py` 19.0K, `preprocess.py` 0.5K, `run.py` 0.5K | Doubtful | Baseline list for anomaly-detection comparison. **No licence, do not vendor.** |
| [mitmedialab/Health-LLM](https://github.com/mitmedialab/Health-LLM) | Yes | 104 | 20 | **2024-08-09** (dormant) | **MIT** | Real | Probably | Serialisation prompt templates, 10-task/4-dataset benchmark harness |
| [Institute4FutureHealth/CHA](https://github.com/Institute4FutureHealth/CHA) (openCHA) | Yes | 143 | 40 | 2025-11-05 | **MIT** | **Real, well structured.** 221 files, `src/openCHA/`, tests, examples, docs, Dockerfile, pre-commit | Yes, pip installable, docs at docs.opencha.com | **`ask_user` task**, DataPipe pass-by-reference, typed-output tool descriptions, affect/PPG/sleep/stress task family |
| [HC-Guo/HealthClaw](https://github.com/HC-Guo/HealthClaw) | Yes | 148 | 6 | 2026-07-27 | **MIT** | Real: framework, demo workflows, eval scripts, year-long benchmark | Likely | L2/L3/L4 memory schema, induction step, year-long synthetic benchmark generator |
| [microsoft/sentinel_environments](https://github.com/microsoft/sentinel_environments) | Yes (paper-stated) | UNVERIFIED | - | UNVERIFIED | UNVERIFIED | Stated to include environments, tasks, synthetic catalogs, data-gen pipeline | UNVERIFIED | `wait_for` vs `sleep` tool comparison, reaction-time and resource metrics |
| [DekuD2/can-llm-coding-agents-reason-about-time-series](https://github.com/DekuD2/can-llm-coding-agents-reason-about-time-series) | Yes | 2 | - | 2026-06-11 | MIT | Real (Python) | Likely | The direct/code/hybrid three-arm harness over TimeSeriesExam and TSFU |
| Google PHA (arXiv:2508.20148) | **No repo found** | - | - | - | - | - | - | Paper only |
| PH-LLM | **No repo found** | - | - | - | - | - | - | Rubric design only |
| SAGE | **No repo found** | - | - | - | - | - | - | Paper only |
| ContextAgent | **No repo URL in paper** | - | - | - | - | - | - | Metric set only |
| Project Hermes | **No repo found** | - | - | - | - | - | - | Bayesian validation concept |

---

## 6. Time-series-to-LLM serialization comparison

### 6.1 How each system does it

| System | Approach | What the LLM literally receives | Evidence |
|---|---|---|---|
| **PHIA** | **Schema description plus code generation** | A markdown bullet list of column names, dtypes and units. **Zero data values.** Data lives only in `sandbox_globals`. | Read from `prompt_templates.py:AGENT_PREAMBLE` and `phia_agent.py`. https://github.com/yahskapar/personal-health-insights-agent |
| **Google PHA** | **Plan, then code generation** | Two stages: produce a statistical analysis plan from the query, then generate and execute code. | https://research.google/blog/the-anatomy-of-a-personal-health-agent/ |
| **HiMe** | **EAV schema description plus SQL plus stateful code tool** | A feature inventory with stored units and conversion arithmetic, plus the instruction that feature names are *values* in a `feature_type` column. Numbers arrive only as SQL result sets. | Read from `prompts/data_schema.md`. https://github.com/thinkwee/HiMe |
| **SAGE** | **Text-to-KQL over a time-series database** | Nothing but the question and a schema; the LLM emits KQL, ADX returns exact numbers, the LLM explains them. LLM confined to "question interpretation" and "explanation of retrieved facts". | https://arxiv.org/abs/2604.16342 |
| **VitalAgent** | **Typed tool outputs from deterministic DSP** | Tool name, execution status, and structured returns (numerical summaries, temporal trends, event annotations). Raw ECG/PPG never enters context. | https://arxiv.org/abs/2605.29483, confirmed by `agent/tools/` |
| **openCHA** | **Pass-by-reference plus documented JSON output keys** | A `datapipe:key` handle plus a tool description enumerating the returned keys (e.g. `HRV_MeanNN`, `HRV_SDNN`, `HRV_RMSSD`, `HRV_pNN50`). | Read from `src/openCHA/tasks/affect/ppg_analysis.py` |
| **PH-LLM** | **Text metrics plus MLP-adapter soft tokens** | Native-unit text (steps per day etc.) plus a 22-token prefix produced by an MLP (1024/4096/1024) over a z-scored 20x2 mean/variance matrix from 15 days. | https://arxiv.org/abs/2406.06474 |
| **Health-LLM** | **Raw natural-language string serialisation** | Literal numbers in prose: *"Steps: {812.0} steps, Burned Calories: {97.0} calories, Resting Heart Rate: {66.54} beats/min..."*, or raw arrays with `NaN` for the temporal-context variant. | https://arxiv.org/abs/2401.06866 |
| **BALMS** | Compares all three | Prompt-based `[Steps]: [4664, 3035, NaN, ...]`; tool-based pandas DataFrames; memory-based embeddings via Chunk RAG / RAPTOR. | https://arxiv.org/abs/2608.27219 |
| **AI on the Pulse** | **LLM never sees the series** | Anomaly scores and signal context are passed to GPT-4o for explanation only; format not published. | https://arxiv.org/abs/2508.03436 |
| **ContextAgent** | Modality-to-text descriptions | VLM and ASR captions concatenated as `C = [C_V, C_A, N]`. Authors flag this as a limitation. | https://arxiv.org/abs/2505.14668 |
| **TS-Agent / TS-Reasoner** | **Tools on raw sequences, LLM reasons over evidence only** | Statistical and structural extraction delegated to tools; LLM used "strictly for iterative evidence-based reasoning". | https://arxiv.org/abs/2510.07432, https://arxiv.org/abs/2410.04047 |

**The consensus is unambiguous: describe the schema, do not paste the data.** Six of the eight production-oriented systems put a computational layer (pandas, SQL, KQL, or typed DSP tools) between the numbers and the context window. The two that do not (Health-LLM, PH-LLM) are exactly the two that score 22% and 0% respectively on PHIA's objective numerical benchmark.

But note the *interface* varies more than the principle. PHIA and PHA use Python. HiMe and SAGE use a query language. VitalAgent and openCHA use fixed typed tools. Query languages and fixed tools trade expressiveness for a much smaller failure surface; SAGE's three named failure modes are all query-generation bugs, which is a smaller and more fixable class than "arbitrary pandas code was subtly wrong".

### 6.2 What is the actual evidence that code generation beats other approaches?

There are exactly **three** experiments that isolate this, and none of them supports the strong universal claim in the prior notes.

**Experiment 1: PHIA, arXiv:2406.06464.** Objective numerical queries, Gemini 1.0 Ultra held fixed. Numerical Reasoning (markdown tables pasted into context) **22%**; custom GPT-4 chain-of-thought over text-rendered wearable data **53.6%**; single-step Code Generation **74%**; PHIA (ReAct with code plus search) **84%**; PH-LLM (fine-tuned, no tools) **0%**.
- What this shows: code beats in-context numerical reasoning, decisively (74 vs 22).
- What this does **not** show: that the agent loop matters much (84 vs 74 is 10 points). And PHIA's own code-quality analysis says the main agent benefit is error recovery (11.4% vs 0% recovery from fatal errors), not first-attempt correctness.
- Caveat: single LLM, authors' own benchmark, and the strongest baseline (74%) is itself a code generator, so this is code-vs-code plus a loop.

**Experiment 2: "Can LLM Coding Agents Reason About Time Series?", arXiv:2606.16545.** The only paper that directly ablates representation. Three arms: **Direct** (raw text serialisation only), **Code** (pandas DataFrame plus iterative Python), **Hybrid** (both).

| Benchmark | Model | Code | Direct | Hybrid | Random |
|---|---|---|---|---|---|
| TimeSeriesExam (746 MCQs) | gpt-oss-120b | 70.4% | 65.3% | **78.0%** | 40.1% |
| TimeSeriesExam | Qwen3-Next-80B | 56.4% | **63.5%** | **68.1%** | 40.1% |
| TSFU (2,000 questions) | gpt-oss-120b | 63.0% | 55.6% | **65.6%** | 29.3% |

Three findings that contradict the prior notes:
1. **Hybrid beats code-only in every case** (+7.6, +11.7, +2.6 points).
2. **For Qwen3-Next-80B, the Direct text agent beats the Code agent outright** (63.5 vs 56.4). Code generation is not universally better; it is model-dependent.
3. **Per-category, Direct beats Code on precisely the categories we care about**: structural breaks **52.0 vs 44.0**, outlier detection **74.0 vs 64.8**, anomaly detection **54.8 vs 48.8**.

Failure-mode finding: even when code executes correctly, agents misinterpret results in **95%** of "wrong method within strategy" error cases; they "overtrust the returned numbers and often miss crucial details".
Limitations the authors state: multiple-choice format only; open-weight models only; no plots/vision arm; no specialist time-series foundation models.
https://arxiv.org/abs/2606.16545

**Experiment 3: BALMS, arXiv:2608.27219.** Compares prompt-based (Health-LLM serialisation), tool-based (PHIA ReAct plus pandas) and memory-based (RAG) on three real longitudinal wellbeing-prediction datasets. Headline: **"Zero-shot agents rarely outperform a simple mean baseline, except with stronger backbones."** The best reported cell (Claude-Haiku-4.5, 0.42 MAE vs 0.58 mean baseline on DiversityOne) is a **prompt-based** Health-LLM configuration, not the tool-based one. Retrieval, not code, is what benefits from longer look-back windows; prompt-based degrades as context grows.

**Conclusion for our project.** Code generation over dataframes is well evidenced for **precise numeric retrieval and aggregation** (PHIA's 74 vs 22). It is **not** evidenced for **anomaly and change detection**, where the one controlled study finds direct text reasoning *ahead* of code, and where a hybrid beats both. Since anomaly and change detection is our core task, adopting code-gen-only on the strength of the prior notes would be adopting it against the only evidence that tested it. A hybrid (give the model a compact summary *and* a computation tool) is the evidence-backed default.

---

## 7. Proactive versus reactive table

| System | Proactive? | What initiates | Evidence |
|---|---|---|---|
| PHIA | **Reactive** | User question only. No scheduler, no monitor. `max_steps=10` per question, then done. | Code plus paper, https://arxiv.org/abs/2406.06464 |
| Google PHA | **Reactive** | User query. The blog frames the system as responding to user needs rather than initiating. | https://research.google/blog/the-anatomy-of-a-personal-health-agent/ |
| PH-LLM | **Reactive** | Case study input. Not an agent at all. | https://arxiv.org/abs/2406.06474 |
| Health-LLM | **Reactive** (batch) | Offline prediction over a fixed window. | https://arxiv.org/abs/2401.06866 |
| openCHA | **Reactive** | User query. `ask_user` exists but only as mid-plan clarification. | Code, https://github.com/Institute4FutureHealth/CHA |
| HealthClaw | **Reactive** | User request. Memory evolves after episodes, but does not initiate them. | https://arxiv.org/abs/2607.13940 |
| BALMS | **Reactive** (retrospective benchmark) | Authors: "we do not test agents in real-world interactive or intervention settings." | https://arxiv.org/abs/2608.27219 |
| LifeAgentBench | **Reactive** (QA benchmark) | Question. | https://arxiv.org/abs/2601.13880 |
| AI on the Pulse | **System-initiated detection, clinician-facing** | Continuous UniTS scoring flags anomalies. But the LLM only explains after the fact, and the recipient is a clinician, not the patient. The paper frames it as enabling "reactive home-care interventions". | https://arxiv.org/abs/2508.03436 |
| **HiMe** | **Yes, genuinely** | Three initiators in one loop: user messages, **real-time monitor triggers**, and **scheduled tasks**. Persona prompt: *"Proactive. You do not wait to be asked. When the data reveals something meaningful, you bring it forward."* Pushes to phone and watch. | Code (`trigger_evaluator.py`, `push_report_tool.py`, `prompts/soul.md`), https://arxiv.org/abs/2607.21019 |
| **VitalAgent** | **Yes** | Streaming 10-second windows through a rule layer plus LLM judge; emits episode-level alerts. Explicitly dual-mode "reactive and proactive". | Code (`agent/proactive/`), https://arxiv.org/abs/2605.29483 |
| **SAGE** | **Yes** | Monitoring module fires on deviation from personal baseline, pushes via WhatsApp. | https://arxiv.org/abs/2604.16342 |
| **ContextAgent** | **Yes** (not health) | Continuous wearable video/audio, proactive-score classifier decides to act. | https://arxiv.org/abs/2505.14668 |
| **Project Hermes** | **Yes** (interrogative) | Fires downstream of an upstream predictor's alert, and initiates a question to the user. | https://arxiv.org/abs/2602.18643 |
| SentinelBench | **Yes, by construction** (not health) | The benchmark's whole subject is agents that watch and wake. | https://arxiv.org/abs/2606.05342 |
| ProAgentBench | **Yes** (not health, desktop) | Timing classifier over 1 Hz screen/app observations. | https://arxiv.org/abs/2602.04482 |

**Score: 5 genuinely proactive health systems out of 14 (HiMe, VitalAgent, SAGE, Project Hermes, and AI on the Pulse in a limited clinician-facing sense).** The prior notes' claim that "almost all health LLM work is reactive" is **CONFIRMED for 2024-2025 work but is becoming dated**: three of the five proactive systems appeared in 2026 (SAGE Mar 2026, VitalAgent May 2026, HiMe Jul 2026). The field is moving into this space right now, which raises the novelty bar for our project.

---

## 8. "Does it decide when to ask the user?" table

This directly tests the project premise. I distinguish four levels:
- **L0** Never initiates.
- **L1** Fixed threshold / fixed schedule, hand-coded.
- **L2** Threshold plus a suppression policy (cooldown, dedup, caching) and/or an LLM confirmation step.
- **L3** Learned or explicitly optimised decision with its own accuracy / miss / false-alarm metrics, or an explicit model of interruption cost.

| System | Level | Actual mechanism | Models interruption cost? | Evidence |
|---|---|---|---|---|
| PHIA | L0 | None. | No | Code |
| Google PHA | L0 | None. | No | https://arxiv.org/abs/2508.20148 |
| PH-LLM | L0 | None. | No | - |
| Health-LLM | L0 | None. | No | - |
| HealthClaw | L0 | None (reactive). | No | https://arxiv.org/abs/2607.13940 |
| openCHA | **L0.5** | `ask_user` is a first-class task the planner may select mid-plan: *"When needed, the planner will decide to ask question from user and use the user's answer to proceed to the planning."* But this is clarification inside a user-initiated session, never an unprompted interruption. | No | Code: `src/openCHA/tasks/ask_user.py` |
| AI on the Pulse | L1 | Percentile-threshold anomaly flags to a clinician dashboard. | No | https://arxiv.org/abs/2508.03436 |
| SAGE | **L1** | Hardcoded: **>= +/-30% change from the 7-day moving average**, or critical sleep debt. Rationale given is alert-fatigue avoidance, but no cost model. | No, only motivated by it | https://arxiv.org/abs/2604.16342 |
| **HiMe** | **L2** | Agent-authored plain-language trigger rules compiled into deterministic conditions: `gt`, `lt`, `gte`, `lte`, `avg_gt`, `avg_lt`, `spike` (latest > avg + k*std), `drop` (latest < avg - k*std), `delta_gt`, `absent`. Each rule carries a signal, threshold or std condition, a window and a **`cooldown_minutes`**. Plus a global `_min_eval_interval = 10.0` s debounce and feature-filtered evaluation. When a rule fires it queues a **goal string** for the analysis sub-agent, which then decides whether to `push_report`. So the *firing* is deterministic and the *notification* is an LLM judgement. | **No.** No user state, no interruption budget, no learning. | Code: `backend/agent/trigger_evaluator.py`, `tools/push_report_tool.py` |
| **VitalAgent** | **L2** | Guideline-grounded `ClinicalRule` registry (extreme bradycardia CRITICAL, extreme tachycardia CRITICAL, sustained tachycardia MEDIUM, staged long-AF-episode HIGH at >= 24 h), urgency merged by max rank across a rule judge and an LLM judge. LLM judge invoked **only when the rule outcome changes**, verdict cached, force-refreshed every `_JUDGE_FORCE_REFRESH_WINDOWS = 20` windows (~3.3 min). Episode-level dedup: continuous detections of the same abnormality do not re-alert. | **No.** Authors admit: "relies on predefined monitoring criteria and domain-informed rules"; adaptive policies "unexplored". | Code: `agent/proactive/intervention_decision.py` |
| **Project Hermes** | **L2.5** | The only health system that **asks in order to decide**: LLM generates a contextual question, collects user feedback, and performs a **Bayesian confidence update** to separate true from false positives. Cut FPR 61.7% -> 12.5% at 89% sensitivity. | Implicitly, by treating the question as evidence rather than output. Not an explicit cost model. | https://arxiv.org/abs/2602.18643 |
| **ContextAgent** | **L3** (not health) | Fine-tuned context-reasoner emits a **1-5 proactive score**; act if **>= 3**. Evaluated with dedicated metrics: **Acc-P 87.4%**, **MD** (missed detections), **FD** (false detections), **RMSE**. | Not a monetary/attention cost model, but MD and FD are first-class evaluation targets. | https://arxiv.org/abs/2505.14668 |
| **ProAgentBench** | **L3** (not health, desktop) | Explicit binary classification `B_t = f_when(U, O_1:t) in {0,1}` with the cost asymmetry stated: low precision causes alert fatigue and users disabling the system; low recall means missed needs. Measured by precision, recall, F1, accuracy. Best zero-shot **64.4%**; fine-tuned 8B reaches **74.0%**. | Yes, qualitatively and in the metric design. | https://arxiv.org/abs/2602.04482 |
| **SentinelBench** | **L3-adjacent** (not health) | Does not decide *whether* to interrupt a user, but formalises **when to wake**: `wait_for(condition, timeout)` vs `sleep(t)`, scored on completion, **reaction time**, and **resource cost**. `wait_for` is 9.7x cheaper and completes more. | Yes, as a resource cost. | https://arxiv.org/abs/2606.05342 |
| **EmBot expert study** | Requirements only | 15 experts recommended **capped alerts, adaptive pacing, disengagement detection**, explaining the detection rationale, and a **user confirmation/rejection step before the LLM engages**. No implementation. | Recommends it; nobody has built it | https://arxiv.org/abs/2604.04915 |

### Verdict on the project premise

**The gap is real, and it is narrower and better-defined than "nobody has thought about this".**

What already exists (do not claim these as novel):
- Deterministic thresholds with cooldown and dedup: HiMe, VitalAgent, SAGE. Solved, and you should reuse their code.
- LLM confirmation of a threshold hit: HiMe (analysis sub-agent decides whether to push), VitalAgent (LLM judge merged with rule judge). Solved, with a measured cost: VitalAgent's LLM judge halved latency (220 s -> 105 s) but raised false alerts 63% (1.81 -> 2.95/h).
- Asking the user to disambiguate an alert: Project Hermes only, single-author preprint, no code.
- A learned when-to-act policy with MD/FD metrics: ContextAgent and ProAgentBench, **neither health nor physiological**.

What does **not** exist anywhere I could find:
1. **Any health or physiological agent that treats the decision to interrupt as a learned or optimised policy** with its own accuracy, miss rate and false-alarm rate. ContextAgent's Acc-P / MD / FD / RMSE metric set has never been applied to wearable physiological monitoring.
2. **Any system with an explicit interruption budget or model of user attention cost.** The closest is expert *advice* to cap alerts (EmBot, arXiv:2604.04915), which nobody has implemented.
3. **Any system that chooses between "stay silent", "notify", and "ask a question"** as three distinct actions with different costs. Project Hermes does asking; HiMe and VitalAgent do notifying; nobody arbitrates between them.
4. **Any system that conditions the interruption decision on user state** (asleep, driving, in a meeting, recently dismissed a similar alert). ContextAgent conditions on sensed context but for a different purpose, and it is not physiological.

Items 1, 3 and 4 are defensible novel contributions for a course project. Item 2 is the weakest, since it is easy to assert and hard to evaluate.

### Does any system handle state across long waits (days)?

| System | Cross-session state | Horizon | Evidence |
|---|---|---|---|
| PHIA | **None.** Stateless per question. | Single session | Code |
| PH-LLM, Health-LLM | None | Single inference | - |
| Google PHA | Orchestrator performs "memory updates" | Within-conversation, cross-session **UNVERIFIED** | Google blog |
| openCHA | DataPipe holds intermediate results within a plan | Single session | Code |
| **HiMe** | **Yes, strongest.** Unified per-user database: memory tables, `user.md`, `experience.md`, profiles, reports, scheduled tasks, monitoring rules. Long-term user modelling is design principle 3. | **Months.** 2-month field study, n=9. | Code plus paper |
| **VitalAgent** | **Yes, bounded.** `M_t = (x_<t, s_<t, e_<t)`: signal window history, streaming health-state tracker, prior alert records. | Hours to days (90.2 h of continuous recording) | Code plus paper |
| **HealthClaw** | **Yes, most explicit schema.** L2 durable facts / L3 reusable procedures / L4 episodic traces, with a post-episode induction step deciding what promotes. | **A year** (synthetic, 365 daily interactions x 20 users) | https://arxiv.org/abs/2607.13940 |
| SAGE | Personal 7-day rolling baselines in ADX | Days to weeks | https://arxiv.org/abs/2604.16342 |
| AI on the Pulse | Per-patient learned baseline in UniTS | 3 months deployed | https://arxiv.org/abs/2508.03436 |
| MedMemoryBench | Benchmark only. Formalises **memory saturation**: sustained influx degrades retrieval and reasoning. | ~2,000 sessions | https://arxiv.org/abs/2605.11814 |
| BALMS | Benchmark only. Long-horizon scaling 7 to 28 days: retrieval benefits, prompt-based degrades. | 28 days to multi-year datasets | https://arxiv.org/abs/2608.27219 |

**Answer: no, they are not all single-session, but only three systems (HiMe, VitalAgent, HealthClaw) carry real state, all three shipped in 2026, and the honest result from HealthClaw is that structured retrieval is still 15 points worse than pasting the full history (45.7% vs 61.2%). Memory buys cost, not accuracy, at current capability.**

---

## 9. Comparison table

| System | Year | Proactive | Serialisation | Agent loop | Framework | LLM | Fine-tune | Eval type | Code | Licence |
|---|---|---|---|---|---|---|---|---|---|---|
| PHIA | 2024-2026 (NatComm) | No | Schema plus pandas code | ReAct, max_steps=10, 20 few-shots | **OneTwo** (Google DeepMind) | Gemini 1.0 Ultra | No | Own benchmark plus 12 human raters, 650 h | Yes | CC BY-NC 4.0 |
| Google PHA | 2025 | No | Plan then code | Orchestrator, dynamic main/support roles, reflection plus memory updates | Unstated | "e.g. Gemini" | No | 10 tasks, 7,000 annotations, 1,100 h | **No** | - |
| PH-LLM | 2024 / NatMed 2025 | No | Text plus MLP adapter (22 soft tokens) | **None** | - | Gemini Ultra 1.0 | **Yes** (SFT) | 857 case studies, 6+7 experts, MCQ exams | **No** | - |
| Health-LLM | 2024 | No | **Raw text arrays** | **None** | - | 12 LLMs plus HealthAlpaca | **Yes** (SFT plus LoRA) | 4 datasets, 10 tasks, automatic | Yes (dormant) | MIT |
| openCHA | 2023 / JAMIA Open 2025 | No | DataPipe reference plus typed JSON keys | Task Planner (ToT or ReAct) plus Executor | **Custom** | Model-agnostic | No | 4 own case studies | Yes | **MIT** |
| HiMe | 2026-07 | **Yes** | EAV schema plus SQL plus stateful code | **Custom single event loop**, dispatcher plus one-shot sub-agents | **Custom** | 22 backbones, local via vLLM | No | Terminal-state oracle on 5 replayed corpora plus 9-user 2-month field study | Yes | **PolyForm Noncommercial** |
| VitalAgent | 2026-05 | **Yes** | Typed DSP tool outputs | Planner -> tools -> validate -> replan; separate proactive rule plus LLM judge | **Custom** | DeepSeek-V4 Flash | No | Own benchmark, 1,862 LLM-generated QA, **no human validation** | Yes | **MIT** |
| SAGE | 2026-03 | **Yes** | **Text-to-KQL** over Azure Data Explorer | State machine, intent router | **LangGraph** | GPT-5.2 / GPT-5 mini | No | 90 synthetic questions, M1-M4 | **No** | - |
| AI on the Pulse | 2025-08 | Partly | LLM only sees anomaly output | **None** (LLM is a one-shot explainer) | - | GPT-4o | UniTS adapted | 12 baselines plus 6-patient 3-month deployment, 1 geriatrician | Yes (thin) | **None** |
| HealthClaw | 2026-07 | No | Not detailed | Perceive -> Reason -> Act -> Induct | Custom | Unstated | No | Synthetic year-long, **LLM-as-judge only** | Yes | **MIT** |
| ContextAgent | NeurIPS 2025 | **Yes** | VLM/ASR captions | Context -> proactive score -> tools | Custom | 10 models, SFT <= 7B | **Yes** | Own benchmark, 1,000 LLM-expanded samples | **No** | - |
| Project Hermes | 2026-02 | **Yes** | N/A | Validation layer, Bayesian update | Unstated | Unstated | No | 60-day migraine study | **No** | - |
| SentinelBench | 2026-06 | **Yes** | N/A (web) | Benchmark | - | GPT-5.4, GPT-4o, Qwen 3.5:9B | No | 100 tasks, 10 synthetic web envs | Yes | UNVERIFIED |

**On agent frameworks: there is no house standard.** OneTwo (PHIA), LangGraph (SAGE only), LangChain (BALMS baselines only), and hand-rolled custom loops everywhere else. The two most capable proactive systems (HiMe, VitalAgent) both wrote their own loop, which is a signal that off-the-shelf frameworks did not fit the always-on, multi-initiator, long-lived-state shape. If we pick LangGraph we will be following SAGE, which is a CHI extended abstract with no released code.

### Papers where the "agent" does nothing an ordinary function call could not do

- **AI on the Pulse** (arXiv:2508.03436). GPT-4o receives an anomaly and emits a paragraph. No loop, no tool, no decision, no state. This is `explain(anomaly) -> str`. The paper itself does not overclaim, but the prior notes' framing of it as an agent system is wrong.
- **PH-LLM** (arXiv:2406.06474). A fine-tuned model. There is no agent. It is listed under "agents" in the prior notes; it should not be.
- **Health-LLM** (arXiv:2401.06866). Prompting plus SFT. No tools, no retrieval, no function calling. Not an agent.
- **VitalAgent's validate/replan stages** deserve scrutiny. The ablation shows `w/o validation` and `w/o replan` cost essentially nothing (0.860 -> 0.849 and 0.855 on Tier A; **on Tier B `w/o validation` is actually better**, 0.569 vs 0.557). Only `w/o planner` matters (0.860 -> 0.701). So two of the three agentic components are decorative, and the paper's own ablation says so.
- **HiMe's sub-agents** are explicitly one-shot: *"you are a one-shot executor, not a conversational agent."* The agentic behaviour lives in the orchestrator and the event loop, not the sub-agents. That is an honest design, but it means "multi-agent" here means "prompt specialisation with a router".

### Evidence-quality classification

| Evidence type | Systems | Strength |
|---|---|---|
| **Human expert evaluation with n and blinding** | PHIA (12 raters, blinded, min 3/response, 650 h), PH-LLM (6+7 experts, cross-assigned), Google PHA (7,000 annotations, 1,100 h) | **Strongest in the field.** But all three are Google-authored, all three use authors' own benchmarks, and none publishes a numeric inter-rater statistic in the main text. |
| **Real deployment with real users** | HiMe (9 participants, 2 months), AI on the Pulse (6 patients, 3 months, **1 rater**) | Real but tiny. n=9 and n=6. |
| **Self-built benchmark, no human validation** | VitalAgent/VitalBench (1,862 LLM-generated QA), ContextAgent/ContextAgentBench (1,000 LLM-expanded), LifeAgentBench (22,573 auto-generated) | **Weak.** Authors create the benchmark, generate the questions with an LLM, and then win on it. VitalBench reports no human validation and no inter-rater agreement at all. |
| **LLM-as-judge only** | HealthClaw ("No human ratings were used", Qwen-3.7 evaluator), BALMS T2 | **Weakest.** Self-preference bias unaddressed. |
| **Ablation that genuinely isolates the contribution** | arXiv:2606.16545 (three-arm direct/code/hybrid), VitalAgent (planner/validation/replan, and it disconfirms two of three), HiMe (trigger vs polling, and it shows recall loss), PHIA (agent vs single-shot code gen) | **These four are the papers worth trusting.** |
| **Ablation that does not isolate** | Health-LLM's "context enhancement" (mixes user context, health context and temporal context; the headline 23.8% is not traced to a cell), VitalAgent vs PHIA (authors admit the input format handicaps PHIA) | Discount. |

**On evaluation design for our own project**, RubricsTree (arXiv:2606.18203) is the most useful methodological finding in this survey: replacing holistic Likert scoring with 100+ **atomic Boolean clinically-verifiable rubrics** raised inter-rater ICC3 from **0.291 to 0.876**. If we run any human evaluation, use atomic Boolean rubrics, not 1-5 Likert scales.

---

## 10. Full bibliography

**Core systems**
1. Merrill, M.A., Paruchuri, A., Rezaei, N., Kovacs, G., Perez, J., Liu, Y., Schenck, E., Hammerquist, N., Sunshine, J., Tailor, S., Ayush, K., Su, H.-W., He, Q., McLean, C.Y., Malhotra, M., Patel, S., Zhan, J., Althoff, T., McDuff, D., Liu, X. "Transforming wearable data into personal health insights using large language model agents." *Nature Communications* 17, 1143 (2026-01-12). DOI 10.1038/s41467-025-67922-y. https://www.nature.com/articles/s41467-025-67922-y | Preprint: https://arxiv.org/abs/2406.06464 | Code: https://github.com/yahskapar/personal-health-insights-agent
2. Cosentino, J., Belyaeva, A., Liu, X., Furlotte, N.A., et al. "Towards a Personal Health Large Language Model." arXiv:2406.06474 (2024-06-10). https://arxiv.org/abs/2406.06474 | Journal version: "A personal health large language model for sleep and fitness coaching", *Nature Medicine*, DOI 10.1038/s41591-025-03888-0, PMID 40813712. https://www.nature.com/articles/s41591-025-03888-0
3. Heydari, A.A., Gu, K., Srinivas, V., Yu, H., Zhang, Z., Zhang, Y., Paruchuri, A., He, Q., Palangi, H., et al. "The Anatomy of a Personal Health Agent." arXiv:2508.20148 (v1 2025-08-27, v2 2025-09-18). https://arxiv.org/abs/2508.20148 | Blog: https://research.google/blog/the-anatomy-of-a-personal-health-agent/
4. Liu, W., Qi, S., Zhang, L., Tudor Car, L., He, Y. "HiMe: Real-Time Self-Hosted Personal Agent Platform for Health Insights with Wearable Devices." arXiv:2607.21019 (2026-07-23). https://arxiv.org/abs/2607.21019 | Code: https://github.com/thinkwee/HiMe
5. Zhu, D., Wu, Y.Y., Jia, H., Saeed, A., Kostakos, V., Dang, T. "VitalAgent: A Tool-Augmented Agent for Reactive and Proactive Physiological Monitoring over Wearable Health Data." arXiv:2605.29483 (v1 2026-05-28, v2 2026-06-18). https://arxiv.org/abs/2605.29483 | Code: https://github.com/DKSEZD/VitalAgent
6. Gabrielli, D., Prenkaj, B., Velardi, P., Faralli, S. "AI on the Pulse: Real-Time Health Anomaly Detection with Wearable and Ambient Intelligence." arXiv:2508.03436 (2025-08-05). https://arxiv.org/abs/2508.03436 | Code: https://github.com/davegabe/ai-on-the-pulse
7. Kim, Y., Xu, X., McDuff, D., Breazeal, C., Park, H.W. "Health-LLM: Large Language Models for Health Prediction via Wearable Sensor Data." arXiv:2401.06866 (v1 2024-01-12, v2 2024-04-27). https://arxiv.org/abs/2401.06866 | Code: https://github.com/mitmedialab/Health-LLM
8. Abbasian, M., et al. "Conversational health agents: a personalized large language model-powered agent framework." *JAMIA Open* 8(4) ooaf067 (2025-07-06). DOI 10.1093/jamiaopen/ooaf067. https://academic.oup.com/jamiaopen/article/8/4/ooaf067/8186991 | Preprint: https://arxiv.org/abs/2310.02374 | Code: https://github.com/Institute4FutureHealth/CHA | Docs: https://docs.opencha.com/
9. Lee, H., Cho, Y., Kwak, S.S., Calvo, R.A. "SAGE: Sensor-Augmented Grounding Engine for LLM-Powered Sleep Care Agent." arXiv:2604.16342, CHI EA 2026. https://arxiv.org/abs/2604.16342
10. Li, H., Deng, J., Jin, T., Han, J., Wang, Y., Wang, Z., Si, Q., Gong, W., Zhuang, X., You, J., Cheng, W., Feng, J., Guo, H. "A Self-Evolving Agent for Longitudinal Personal Health Management" (HealthClaw). arXiv:2607.13940 (2026-07-15). https://arxiv.org/abs/2607.13940 | Code: https://github.com/HC-Guo/HealthClaw
11. Chakraborty, R. "Project Hermes: A Model-Agnostic Validation Layer for Wearable Health Prediction Systems." arXiv:2602.18643 (2026-02-20). https://arxiv.org/abs/2602.18643

**Proactivity and interruption**
12. "ContextAgent: Context-Aware Proactive LLM Agents with Open-World Sensory Perceptions." arXiv:2505.14668, NeurIPS 2025. https://arxiv.org/abs/2505.14668 | Poster: https://neurips.cc/virtual/2025/poster/115593
13. Tang, Y., Tang, H., Cao, T., et al. (Tsinghua). "ProAgentBench: Evaluating LLM Agents for Proactive Assistance with Real-World Data." arXiv:2602.04482 (2026-02-09). https://arxiv.org/abs/2602.04482
14. Kunzler Maldaner, M., Fourney, A., Sweargnin, A., Mozannar, H., Bansal, G., Murad, M., Hosn, R., Amershi, S. "SentinelBench: A Benchmark for Long-Running Monitoring Agents." arXiv:2606.05342 (2026-06-03). https://arxiv.org/abs/2606.05342 | Code: https://github.com/microsoft/sentinel_environments | https://sentinelbench.com/
15. Dongre, P., Neupane, S., Jadhav, P., Donekal Chandrashekar, N., Webb, C., Kumar, S., Gracanin, D. "Exploring Expert Perspectives on Wearable-Triggered LLM Conversational Support for Daily Stress Management." arXiv:2604.04915, IH '26. https://arxiv.org/abs/2604.04915

**Time-series reasoning**
16. Rechtorik, F., Dusek, O., Kasner, Z. "Can LLM Coding Agents Reason About Time Series?" arXiv:2606.16545 (2026-06-16). https://arxiv.org/abs/2606.16545 | Code: https://github.com/DekuD2/can-llm-coding-agents-reason-about-time-series
17. Liu, P., Fons, E., Vapsi, A., Ghassemi, M., Vyetrenko, S., Borrajo, D., Potluru, V.K., Veloso, M. "TS-Agent: Understanding and Reasoning Over Raw Time Series via Iterative Insight Gathering." arXiv:2510.07432 (v1 2025-10-08, v2 2026-04-06). https://arxiv.org/abs/2510.07432
18. "TS-Reasoner: Domain-Oriented Time Series Inference Agents / Multi-Step Time Series Inference Agent for Reasoning and Automated Task Execution." arXiv:2410.04047. https://arxiv.org/abs/2410.04047
19. "TimeSeriesExam: A time series understanding exam." arXiv:2410.14752 (2024-10-18). https://arxiv.org/abs/2410.14752
20. "TimeSeriesExamAgent: Creating Time Series Reasoning Benchmarks at Scale." arXiv:2604.10291. https://arxiv.org/abs/2604.10291
21. "A Survey of Reasoning and Agentic Systems in Time Series with Large Language Models." arXiv:2509.11575, TMLR 2026. https://github.com/blacksnail789521/Time-Series-Reasoning-Survey

**Benchmarks, memory and evaluation**
22. Wu, Y.Y., Pillai, A., Chen, Y., Zhang, Y., Regmi, S., Griffin, T.Z., Heinz, M.V., Marsch, L.A., Jacobson, N.C., Campbell, A. "BALMS: Benchmarking Agentic LLMs for Longitudinal Mental Health Sensing." arXiv:2608.27219 (2026-08-27). https://arxiv.org/abs/2608.27219
23. Tian, Y., Wang, Z., Gungor, O., Fan, X., Rosing, T. "LifeAgentBench: A Multi-dimensional Benchmark and Agent for Personal Health Assistants in Digital Health." arXiv:2601.13880 (2026-01-20). https://arxiv.org/abs/2601.13880
24. Zhang, W., Li, Z., Palangi, H., Graef, B., Heydari, A.A., Lee, S.A., Rahman, S., Luo, R., Esmaeilpour, Z., Schenck, E., Zhang, C., Li, Y., Zhou, M., Yu, P.S., McDuff, D., Sunden, L., Malhotra, M., Patel, S., Metwally, A.A. "RubricsTree: Scalable and Evolving Open-Ended Evaluation of Personal Health Agents across Health Memory and Medical Skills." arXiv:2606.18203 (2026-06-16). https://arxiv.org/abs/2606.18203
25. Wang, Y., Xu, H., Gu, R., Ye, Y., Chen, X., Mu, X., Gao, Y., Guo, C., Wei, P., Gu, J., Li, H., Chen, K., Shou, L. "MedMemoryBench: Benchmarking Agent Memory in Personalized Healthcare." arXiv:2605.11814 (2026-05-12). https://arxiv.org/abs/2605.11814
26. Ding, T., Nannapaneni, A., Liu, B., Zhang, L. "Always-On Agents: A Survey of Persistent Memory, State, and Governance in LLM Agents." arXiv:2606.30306 (2026-06-29). https://arxiv.org/abs/2606.30306
27. Schuetz, N., Bai, Y., Pan, L., Eggert, E., Nerrise, F., Delgado-SanMartin, J., Rosenblattl, M., Gurbanova, M., Asadi, M., Johnson, A., Schmiedmayer, P., Wang, D., Lawrie, A., Kim, D.S., Liu, X., Paruchuri, A., Adeli, E., Ashley, E., Zhang, K.W. "OpenMHC: Accelerating the Science of Wearable Foundation Models." arXiv:2607.16235 (v3 2026-08-08). https://arxiv.org/abs/2607.16235
28. Awesome-AI-Agents-for-Healthcare index (1.2k stars). https://github.com/AgenticHealthAI/Awesome-AI-Agents-for-Healthcare

**Announcements**
29. Google Research, "Advancing personal health and wellness insights with AI" (2024-06-11). https://research.google/blog/advancing-personal-health-and-wellness-insights-with-ai/
30. Apple "Health+" AI coaching for 2026: **press rumour only, no primary source, UNVERIFIED.** Example secondary source: https://www.wareable.com/apple/apple-quartz-health-plus-ai-coaching-service-2026-launch-rumor
