# Agent-returned summaries (verbatim)

**Why this file exists.** Each research agent wrote a long findings file *and* returned a condensed summary to the orchestrator. The raw agent transcripts were not retained on disk (zero bytes; they are streamed, not persisted), so these summaries exist nowhere else. They are the agents' own prioritisation of what mattered, which is not always recoverable by re-reading the long files.

Captured 2026-08-30. Verbatim, unedited. Where a summary conflicts with the corresponding full findings file, the full file wins.

---

## F1 - Clinical infection detection studies
Full file: `F1-clinical-infection-studies.md` (1,087 lines, 144 URLs)

1. **Claim 1 CORRECTED**: Mishra 2020 DOI is `10.1038/s41551-020-00640-6` (s41551 = Nat Biomed Eng). Title/journal/volume/pages were right; only the DOI prefix was wrong.
2. **Claim 2 VERIFIED** exactly: Alavi, Nat Med 28:175-184, `10.1038/s41591-021-01593-2`.
3. **Claim 3 LARGELY FABRICATED**: real sensitivities are NightSignal **80%** (67/84), CuSum **72%** (29/40), RHRAD **69%** (29/42) - not 78/54/44. Median 3-day lead time is correct. "0.3 false alerts/user-week" appears nowhere; the paper reports 1.15 alert-days per person per 21-day window, which contradicts its own 87.7% alert-day specificity.
4. **Claim 4 REFUTED**: NightSignal is a **6-state** DFA (S0-S5, three colours), verified in both the paper text and the DFA image; thresholds are baseline+3 (yellow) / +4 (red) bpm on streaming-median overnight RHR.
5. **Claim 5 VERIFIED**: repo exists, Apache-2.0, 63 commits, last push 2021-09-20, runnable `nightsignal.py` (674 lines) + Isolation Forest + sample data for exactly two participants.
6. **Claim 6 PART-CORRECTED**: 82% sens is on the **n=73 training set**; "63-80% specificity" wrongly merges training (63%, n=73) with a **10-person** validation group (80%); 2.75 days is before *seeking testing*, not symptom onset; **"51 +/- 12 hours" does not exist**; the 76% is real but means 38/50 subjects had a "fever-like day" somewhere in a **45-day** lookback.
7. **Claim 7 VERIFIED** - both Mason and Smarr citations exact.
8. **Claim 8 PART-CORRECTED**: sensor-only AUC is **0.72**, not 0.68 (0.68 was sleep alone). More importantly the task is positive-vs-negative among 333 **already-symptomatic, already-tested** people - not early detection.
9. **Claim 9 UNSUBSTANTIATED**: no source for "5-8%". The one real figure is Mason 2022, dermal temp **0.770 -> 0.819 (+4.9 pp)**, on training data.
10. **Claim 10**: 63,153 TemPredict VERIFIED; NightSignal was **3,318**, not 3,317.
11. **Biggest practical find**: the Stanford data is an **open, no-registration HTTP download**. Verified Phase 2 (5,537,624,129 bytes) and Phase 1 (378,380,920 bytes) by reading their ZIP central directories directly.
12. Phase 2 contains **2,123 participant folders, heart rate and steps only**, ~36 GB uncompressed. Phase 1 has 117 participants **plus 32 sleep files**.
13. **Neither open ZIP contains illness labels or confounder annotations** - Alavi collected alcohol/exercise/travel/stress/vaccination surveys but did not release them.
14. **The only dataset with explicit confounder annotations is COVID-RED** (daily diary of alcohol, drug, medication), gated behind a UMC Utrecht request form + DSA.
15. **TemPredict is effectively closed** (Oura data policy; classifier code blocked by the Department of Defense). **DETECT is gated** ("register and pledge, email the author"). **Warrior Watch has no data statement at all.** The **Li 2017 Lyme data URL is dead (HTTP 404)**.
16. Two gettable alternatives: **CovIdentify on PhysioNet** (DOI 10.13026/ncq1-vp79, credentialed + CITI + DUA, daily-aggregate RHR/steps, 132 pos / 1,157 neg) and the **Snyder Long COVID dataset** (Stanford Digital Repository, **ODC-By, openly downloadable, ships symptom surveys**).
17. **The most important paper nobody cites is COVID-RED** (PLoS ONE 2025, n=17,825, the only RCT): the wearable algorithm achieved 93.8-99.2% sensitivity at **0.8-4.2% specificity** - it alerted essentially everyone. This should anchor all scepticism.
18. **Subgroup flags**: Mishra's "63%" is 15/24 people with >=28 days of prior data; Alavi's "80%" pools 50 retrospective with 34 prospective cases and counts any alert in a 21-day window; Temple's "94%" uses a threshold fitted for zero false positives on the same data.
19. **Warrior Watch has no performance metric of any kind** - only p-values (.006/.01) on a +/-7-day window. The widely repeated "detects 7 days early" is a misreading of the analysis window.
20. **No study in this territory uses an LLM, agent, tool calls, or RAG** - schema fields J-M are "No" everywhere. Non-respiratory work does exist and is credible: IBD flares (n=309, signals 7 weeks pre-flare, objective CRP/calprotectin ground truth), malaria (Kenya, n=300, GAN imputation, pretrained on the open Stanford n=3,318), and Long COVID.

---

## F2 - Commercial wearable products
Full file: `F2-commercial-products.md` (603 lines, 317 URLs)

1. **No commercial illness-detection feature anywhere has published validation.** Oura Symptom Radar, WHOOP Health Monitor, Apple Vitals, Withings Vitality Indicator, Samsung Energy Score, Garmin Body Battery are all FDA **general wellness** products with "not a medical device" disclaimers.
2. **CONFIRMED:** Oura's 3 tiers are exactly "No signs / Minor signs / Major signs", with verbatim descriptions on Oura's support page.
3. **REFUTED:** "Balanced Random Forest with 40-feature heuristic strain matrix" is fabricated. Oura has never disclosed a model class. The "40" is marketing ("over 40 biometrics"). Oura *does* disclose: ~3M member illness tags for fine-tuning, on-device inference, demographic threshold calibration, 7-nights-in-14 baseline.
4. **REFUTED/corrected:** WHOOP's published algorithm (Miller, PLOS ONE 2020) is a **gradient boosted classifier**, not statistical process control. The **21-day baseline is correct**; one of its five features is z-score-like.
5. **20%/80% CONFIRMED** but COVID-19-specific, symptomatic-only, n=57 train / 24+190 validation. **">90% specificity" appears nowhere - the paper reports no specificity at all.** Treat as fabricated.
6. **REFUTED with nuance:** "commercial systems cannot ask clarifying questions" is false in 2026. Oura x Counsel Health medical AI (16 Jun 2026, 43 states) explicitly "asks thoughtful follow-up questions"; WHOOP Journal prompts a questionnaire every morning; WHOOP shipped "Proactive Check-Ins"; Oura Advisor has configurable check-ins.
7. **But the real gap survives:** nobody conditions questions on a detected anomaly. Apple's Vitals notification literally lists "medications, elevation, alcohol intake, or even illness" and then asks nothing. WHOOP's journal is fixed and unconditional. Reframe the premise as "nothing closes the loop between a detected deviation and a targeted disambiguating question."
8. **Best number in the field** (independent, Northwell/Fitbit, JMIR 2024): PPV **4%**, 665 alerts across 470 people; false alerts attributed to **stress 16.0%, poor sleep 13.7%, exercise 9.7%, alcohol 6.0%** - i.e. 45% had askable causes. Authors recommend pairing with symptom tracking. This is our strongest citation.
9. Oura's head of science conceded on record that Symptom Radar produces false positives and negatives; Wareable: "the company has yet to disclose accuracy data."
10. Regulatory line is disease-specificity: Apple holds DEN180042, K240929, K250507; Samsung DEN230041; WHOOP MG K243236 - all narrow cardiac/sleep. Illness detection is deliberately vague to stay unregulated.
11. **WHOOP FDA saga:** warning letter 14 Jul 2025 over Blood Pressure Insights (FDA cited "medical-grade" marketing and colour banding as diagnostic intent); FDA rewrote wellness guidance 6 Jan 2026; closeout 17 Jun 2026 after WHOOP rebanded the dial.
12. **Oura class action filed 20 Aug 2026** (N.D. Cal.) alleging 95%-accuracy sleep-staging marketing vs ~53% real - live evidence that unvalidated accuracy claims now carry legal risk.
13. **Google Loss of Pulse Detection (FDA-cleared Feb 2025)** is the only shipped wearable feature that asks the user a question in response to an anomaly and escalates autonomously - a useful precedent for our design.
14. **Ultrahuman "Jade"** is the most agentic shipped product: acts in real time, triggers breathwork and initiates AFib checks. Note the safe action space chosen - trigger a confirmatory measurement, not give advice.
15. **Apple solved false alarms without asking**, via a 2-of-5-metrics-outlier concordance rule. We need an argument for why asking beats that.
16. Apple's LLM health coach (Project Mulberry) was **scaled back Feb 2026 and has not shipped** - the best-resourced player couldn't deliver it.
17. All illness features are **overnight batch, delivered at wake**. Only Garmin Body Battery and Ultrahuman Jade are continuous.
18. **Sahha's MCP server** is the most directly reusable infrastructure: exposes scores/bioreviewers/archetypes as MCP tools and supports webhook-triggered agent invocation ("fire the agent when a trend turns").
19. PLOS Digital Health umbrella review (42 reviews, ~397 studies): "not sufficient evidence to recommend consumer wearables for self-monitoring"; **none of the 42 reviews reported adverse events**.
20. **Honest gap: Reddit is hard-blocked to my tooling** (fetch and search both). Section 6 uses Garmin/Samsung official forums, Trustpilot/BBB, the class action, and journalist accounts instead. Reddit quotes need manual collection - don't let anyone backfill them from memory.

---

## F3 - Health LLM agents
Full file: `F3-health-llm-agents.md` (709 lines, 172 URLs)

1. **All five "possibly fabricated" arXiv IDs are REAL**, including the suspicious 2026 ones. Verified twice: abstract page plus the arXiv Atom export API. The prior model's identifiers were correct; nothing was invented.
2. Only citation error found: "ACM CIKM 2025" for AI on the Pulse. No journal-ref or comment field on arXiv names CIKM. Do not cite that venue.
3. PHIA is genuinely published: *Nature Communications* **17**, 1143, 2026-01-12, DOI 10.1038/s41467-025-67922-y (confirmed via Crossref).
4. **Two performance claims are wrong.** "PHIA vs <40% zero-shot baselines" is false: the actual baselines are 74% (code gen), 53.6% (GPT-4 CoT), 22%, 0%. The honest headline is **84% vs 74%, a 10-point gain over one-shot code generation.**
5. **VitalAgent's "25-30% relative improvement" is wrong in framing.** It is +25 to +31 *percentage points absolute*, and the "ReAct baseline" is PHIA, which VitalAgent's own authors say was handicapped by input format.
6. HiMe's "90%+ cost reduction" is verified and understated (49x-121x token savings) but the notes omit that **trigger recall got worse for 2 of 4 backbones** (0.57->0.43, 0.58->0.52).
7. AI on the Pulse's 22% F1 is verified, but the "anomalies" are a 3rd/97th-percentile heuristic, deployment is **n=6 patients reviewed by one geriatrician**, and the LLM does no detection at all.
8. **The "code-gen over dataframes is universally best" premise is NOT supported.** arXiv:2606.16545 (the only controlled ablation) finds hybrid > code-only, and **direct text beats code on anomaly detection (54.8 vs 48.8), outlier detection (74.0 vs 64.8) and structural breaks (52.0 vs 44.0)** - exactly our task.
9. BALMS (Aug 2026) is worse news: **"zero-shot agents rarely outperform a simple mean baseline."**
10. Serialization consensus: **describe the schema, never paste the data.** PHIA ships a pandas column dictionary; HiMe an EAV feature inventory plus SQL; SAGE a KQL surface; openCHA pass-by-reference handles; VitalAgent typed DSP tools. Verbatim prompts extracted from source.
11. The two systems that *do* serialize raw numbers (Health-LLM, PH-LLM) are exactly the two scoring 22% and **0%** on PHIA's numeric benchmark.
12. Proactive vs reactive: **5 of 14 are genuinely proactive** (HiMe, VitalAgent, SAGE, Project Hermes, AI on the Pulse partially). The "almost all reactive" claim was true for 2024-25 but **three proactive systems shipped in 2026**, so novelty is eroding fast.
13. **Nobody models the cost of interrupting the user.** SAGE = hardcoded +/-30% vs 7-day moving average. HiMe = agent-authored thresholds with `cooldown_minutes`. VitalAgent = three clinical threshold rules plus an LLM judge cached and force-refreshed every 20 windows. All three policies read in source.
14. Closest to a learned policy: **ContextAgent** (NeurIPS 2025, 1-5 proactive score, fire at >=3, metrics Acc-P/MD/FD/RMSE) and **ProAgentBench** (binary `B_t = f_when(U, O_1:t)`, best zero-shot 64.4%). **Neither is health or physiological** - that transplant is our gap.
15. **Project Hermes** (arXiv:2602.18643) is the only health system that asks the user to *decide*: LLM question + Bayesian update cut false positives 61.7%->12.5% at 89% sensitivity. Single-author preprint, no code, treat cautiously.
16. Long-wait state: **not all single-session.** HiMe (months, 9-user 2-month field study), VitalAgent (bounded memory tuple), HealthClaw (L2/L3/L4 memory with induction). But HealthClaw's honest result: structured retrieval is **15 points worse than pasting full history** (45.7% vs 61.2%); memory buys cost, not accuracy.
17. **No house framework.** PHIA uses Google's OneTwo; HiMe and VitalAgent hand-rolled custom loops; openCHA its own planner; **SAGE is the only LangGraph user** and has no released code.
18. Repos: PHIA (62 stars, CC BY-NC, real, last commit 2025-12-21), HiMe (59 stars, **PolyForm Noncommercial**, 379 files, production-grade), VitalAgent (2 stars, **MIT**, real - an earlier fetch wrongly called it a skeleton), openCHA (143 stars, MIT), HealthClaw (148 stars, MIT). AI on the Pulse is 12 stars, **no licence**, abandoned after 3 days.
19. Flag: **PH-LLM, Health-LLM and AI on the Pulse are not agents** - no loop, no tools. VitalAgent's own ablation shows its validate and replan stages do nothing (w/o validation is *better* on Tier B); only the planner matters.
20. Best methodological find for our own eval: **RubricsTree** raised inter-rater ICC3 from 0.291 to 0.876 by replacing 1-5 Likert with atomic Boolean rubrics. One caution: WebFetch's page summarizer hallucinated twice (claimed PHIA uses "Claude Agent SDK"; called VitalAgent a stub) - both corrected by reading raw source with curl.

---

## F4 - Time-series and physiological foundation models
Full file: `F4-foundation-models.md` (526 lines, 125 URLs)

1. **Recommendation: Chronos-Bolt/Chronos-2 only.** Sole family that is simultaneously bucket-2 zero-shot, Apache-2.0, CPU-documented, short-context tolerant, and NaN-native. 2-5 hours to first output.
2. **Prior claim REFUTED: MOMENT is MIT, not Apache-2.0** (HF cardData, GitHub API, PyPI all say `mit`).
3. **Prior claim REFUTED: NormWear is 193.8M params, not 85-110M** (HF safetensors total).
4. **Prior claim UNVERIFIED: Chronos-Bolt "<15ms CPU"** - the AWS blog gives *no* CPU timings; the 250x figure is a GPU benchmark. Same for TimesFM's "~800MB / 100-300ms CPU" (2.0-500m is ~2.0 GB fp32).
5. **MOMENT param counts:** paper says 40/125/385M; actual weights are 37.9/113.5/346.4M. Context is **fixed** at 512 (zero-pad left), not "capped".
6. **MISSED BY PRIOR RESEARCH: Chronos-2 exists** (Oct 2025, 119.5M, context 8192, **joint multivariate + covariates zero-shot**, 29.6M downloads) and **TimesFM 3.0 shipped 2026-08-28**.
7. **NEW LICENCE TRAP: TimesFM 3.0 is `timesfm-non-commercial-license-v1.0`.** Use TimesFM **2.5** (Apache-2.0) instead. Moirai is **CC-BY-NC-4.0** across all checkpoints.
8. **"AI on the Pulse +22% F1" VERIFIED BUT MISLEADING:** UniTS was **fine-tuned** (80:20 split, 20 epochs, plus per-patient tuning), all 12 baselines were deep-learning AD models, **zero statistical baselines**, data was 10-second HR/HRV - not zero-shot, not daily cadence.
9. **HeartBEiT weights withheld: VERIFIED** (HF search returns zero models).
10. **UniTS confirmed stale** - last push 2024-09-26 (~23 months), bash+YAML+full dataset download, 15-25h. Skip.
11. **The one on-point positive result** (arXiv 2607.20027): Chronos MASE **0.82 vs EWMA 0.84** on consumer-smartwatch HRV, zero-shot. Significant (p<0.001) but only **~2.4% over a one-line baseline**.
12. **That paper used context 32 and 64** - direct proof Chronos works at short wearable contexts; kills the "you need 512 points" framing.
13. **Counter-evidence is substantial:** TSFMs "outperformed consistently by simple linear baselines" on cloud data; GIFT-Eval shows AutoTheta beating most TSFMs sub-hourly; NeurIPS'25 workshop finds no consistent gain over small dedicated models.
14. **Anomaly-detection evidence is compromised.** MOMENT's notebook scores with `adjbestf1` - point-adjusted **best** F1, which needs labels to set the threshold and on which **random noise scores ~0.89** (Kim et al. AAAI'22). Wu & Keogh: a one-line moving average finds 86% of Yahoo anomalies.
15. **MOMENT failure mode that directly hits this use case:** authors state it "struggles to differentiate between vertically shifted time series as it normalizes signals prior to modeling" - a sustained resting-HR elevation *is* a vertical shift.
16. **Context-length reality check:** at nightly cadence, 512 timesteps = **1.40 years**. **TTM has a hard 512 minimum -> disqualified for nightly data** despite being the most CPU-friendly (805,280 params). MOMENT at 90 nights runs on 82% padding.
17. **All wearable-native models are bucket 5:** Apple WBM (2.5B hours, 27 daily behavioural metrics), Google LSM-2, Google SensorFM - **no weights, no API**. The models that fit our data are unavailable; the available models don't fit our data.
18. **NormWear/PaPaGei/Pulse-PPG are bucket 3 and wrong-shaped:** raw waveforms at 64-125 Hz, embeddings requiring a trained head. Consumer APIs don't export raw PPG. NormWear has **22 HF downloads**.
19. **Useful positive lesson from Apple WBM:** a model over *derived daily metrics* beat a raw-PPG sensor model on most dynamic health tasks - justifies working at metric level as a strength, not a compromise.
20. **Two scale-skeptic data points worth citing:** IBM TTM competes at **0.8M params**, and TabPFN-TS ranks **1st on GIFT-Eval with 11M params and zero time-series pretraining**. Suggested framing: report the TSFM-vs-classical comparison honestly with a label-free threshold - defensible either way, and more rigorous than most papers cited.

---

## F5 - Wearable APIs and real-time latency
Full file: `F5-wearable-apis-and-latency.md` (936 lines, 238 URLs)

1. **LATENCY ANSWER: vendor cloud APIs cannot be made real-time. Only device-direct paths can.** Three tiers exist, separated by orders of magnitude.
2. **Tier 1 (~1-15 s, real-time):** a Wear OS app written against the Samsung Health Sensor SDK on the Galaxy Watch - HR+IBI 1 Hz, raw PPG green/IR/red 25 Hz, accel 25 Hz, skin temp 1 Hz, batched ~12 s. Also WHOOP's BLE Heart Rate Broadcast (~1 s, BPM + RR only).
3. **Tier 2 (minutes-hours):** Samsung Health Data SDK / Health Connect. Samsung explicitly refuses to specify the watch->phone sync interval and says continuous HR is *deliberately* delayed.
4. **Tier 3 (once per night, 6-14 h):** WHOOP REST, Oura, Fitbit. **WHOOP recovery does not exist until the sleep cycle closes** - there is no in-sleep query, ever.
5. **For a nocturnal early-warning demo, WHOOP REST / Oura / Fitbit / Garmin / Health Connect are all disqualified** for the live half.
6. **Best news of the research:** Samsung **developer mode** removes all gating. Reading Samsung Health needs no partner request; the watch-side Sensor SDK runs unregistered in dev mode. No fee, no NDA, no approval for a non-distributed demo.
7. **Worst news:** Samsung Health Data SDK has **no HRV type and no respiratory-rate type**. Samsung Health also does not write HRV/breathing/resting-HR to Health Connect.
8. **WHOOP is trivially easy to start:** self-serve dashboard, **10 members with no approval**, OAuth2, 100 req/min & 10k req/day. ~2-4 h to first data in Python.
9. **WHOOP gives 5 scalars per night:** `hrv_rmssd_milli`, `resting_heart_rate`, `spo2_percentage`, `skin_temp_celsius`, `respiratory_rate` + sleep-stage totals. **No heart-rate time series at all.**
10. **WHOOP BLE broadcast is the sleeper finding** - standard BLE HR Service, `bleak` in Python, BPM + RR intervals live. Whether it survives a full night is **undocumented and must be tested.**
11. **Effort:** WHOOP REST 2-4 h; WHOOP BLE 1-3 h; Galaxy Watch custom Wear OS app **2-5 working days**.
12. **Verified:** Fitbit legacy API dies **September 2026** -> Google Health API.
13. **Refuted:** Oura Personal Access Tokens are **deprecated** - new integrations must use OAuth2. The "instant self-serve PAT" claim is stale.
14. **Refuted/updated:** Garmin is enterprise-only *and* **new access requests are paused as of 2026** - form removed, no waitlist, no ETA. FAQ says "no licensing or maintenance fees" (contradicting the fee claim); NDA undocumented.
15. **Partially refuted:** "Apple HealthKit has no real-time streaming" is too strong - no cloud API is correct, but `HKObserverQuery` + background delivery with `.immediate` exists on-device.
16. **Verified with caveats:** Fitbit 1 s / 1 min HR and 5 min HRV are real, but 1 s often only inside recorded exercise and HRV is sleep-only.
17. **Samsung Health export is real and useful:** ZIP with ~19 CSVs + JSON blobs containing **per-minute heart rate**. Zero gating. Perfect for offline model development, useless for live demo.
18. **Skip aggregators.** Terra ~$399/mo, Rook $399+, Spike $450+, Junction $300 min; Sahha has the only usable free tier (25 users, 30 days). All sit downstream of the same vendor clouds.
19. **Documentation optimism confirmed:** Samsung says HC data arrives "as soon as data is created" - true only for the phone->HC hop; developers report Samsung Health taking **>1 day** to start writing, and some users get nothing.
20. **Caveat:** the session hit its WebSearch cap partway through, so ~12 items are flagged **UNVERIFIED** in section 12 with exact URLs to browser-check - notably Oura's rate limit/webhook latency and Fitbit's current rate limits. Section 10 lists four cheap overnight experiments that would resolve the biggest remaining unknowns with the team's own hardware.

---

## F7 - Agentic governance, security and medical RAG
Full file: `F7-agentic-governance-rag.md` (863 lines, 254 URLs)

1. **Bounded workflow, question 1:** the cleanest published pattern is **Plan-Then-Execute with a typed terminal disposition + iteration cap + `interrupt()` checkpoint**. Anthropic's *Building Effective Agents* (19 Dec 2024) names stopping conditions and human checkpoints explicitly and gives the workflow-vs-agent distinction doc 09 already reached independently.
2. **The strongest single finding:** Plan-Then-Execute appears independently in Anthropic's taxonomy *and* in Beurer-Kellner et al.'s security patterns (arXiv:2506.08837). The same architecture that bounds the workflow is also the best prompt-injection defence - one decision, two requirements.
3. **LangGraph, question 2: yes, cheaply.** Checkpointer + `thread_id` = state across waits; `interrupt()` + `Command(resume=...)` = the human gate. 1.2.11 (11 Aug 2026), production-stable since 1.0 (17 Oct 2025).
4. LangGraph's **checkpointers (thread-scoped) vs Stores (cross-thread)** split maps exactly onto our episode-state vs personal-baseline split.
5. LangChain's `HumanInTheLoopMiddleware` has `allowed_decisions: ["approve","edit","reject","respond"]` - **literally the brief's vocabulary** - plus a `when` predicate for risk-proportionate gating (EU AI Act Art. 14(3)).
6. **Key gotcha:** resuming an interrupt **re-runs the node from the top**; pre-interrupt operations must be idempotent. LangGraph also has **no built-in timeout** on a human wait (Temporal does).
7. **Audit log, question 3:** no ratified standard exists. Proposed a ~22-field schema; the brief's six fields map onto **EU AI Act Art. 12** minimum logging (reference database = our `sources`; natural persons verifying = our `human_decision`).
8. **Biggest implementation consequence:** design the graph state so the audit log *falls out of the checkpointer* rather than being a parallel logger that drifts.
9. **Injection, question 4:** prompt-level defences are mitigation, not protection. Spotlighting cuts ASR >50%-><2%, but Zhan et al. broke **eight** defences with >50% adaptive success. Architectural defences (CaMeL: 77% of AgentDojo tasks with provable guarantees vs 84% undefended) are what hold.
10. **We do not have the lethal trifecta** - private data + untrusted content but no exfiltration vector. Naming that and showing the tool table that keeps it true is stronger than any prompt-hardening, and costs zero hours.
11. Designed a **four-condition injection test** whose pass state is positively observable (poisoned `doc_id` appears in `sources`; injected text logged as extracted *data*; disposition matches clean-corpus control; `injection_contained` safety event) plus two negative controls, including one the detector deliberately misses.
12. **Over-permissioning:** OWASP LLM06 mitigation 3 ("avoid open-ended extensions ... run a shell command") is the citation that closes gate G5 against the archived pandas sandbox. Mitigation 7 (authorize in downstream systems, not in the LLM) is the deeper principle most projects miss.
13. **OWASP Top 10 for Agentic Applications 2026** (published 9 Dec 2025) adds ASI01 Goal Hijack, ASI06 Memory/Context Poisoning, ASI09 Human-Agent Trust Exploitation - all three directly ours.
14. **Alert fatigue, question 5:** Drew 2014 - 2,558,760 alarms/31 days/77 beds, **187 audible alarms per bed per day**, **88.8% of annotated arrhythmia alarms false**. Joint Commission SEA 50 (read from PDF) - **98 events, 80 deaths**, "between 85 and 99 percent of alarm signals do not require clinical intervention", 566 MAUDE deaths.
15. **No dose-response curve exists** ("after N alerts, response drops to X%"). Do not invent one.
16. **EMA compliance:** 75.06% (95% CI 72.37-77.65, k=126, n=19,431) and 78.3% in youth. Prompt frequency was **not** a significant moderator in one and **reversed sign** by clinical status in the other - so "ask less" is not evidence-backed; **event-contingent beats time-contingent**, which is the regime our design is already in.
17. **Corpora, question 6:** PMC's legacy FTP/Cloud datasets were **removed the week of 24 Aug 2026** - any plan citing the old bulk FTP is now wrong. Best options: **MedlinePlus XML** (~29 MB, daily, attribution-only), then **NCBI Bookshelf/LitArch** (StatPearls is **CC BY-NC-ND 4.0**). NICE and CDC both 403'd and need a human to check.
18. **FDA moved the boundary on 6 Jan 2026:** wellness alerts are now permissible if they do not name a disease, characterise output as pathological, include clinical thresholds, or provide ongoing disease monitoring. Those four convert directly into deterministic output checks - a refusal spec derived from a regulator.
19. **Question 7:** no published test suite for consumer agentic health monitoring. AgentClinic's finding (static QA overestimates competence; sequential decision-making under incomplete information is much harder) and AgentDojo's benign-utility-vs-utility-under-attack split are the two transferable ideas. Drafted a 13-case suite mapped to every requirement.
20. **Nine open items in Appendix A** for a human to close by hand - chiefly the two FDA PDFs, the OWASP agentic PDF, NICE's licence, the Apple Heart Study numbers, and a Singapore HSA check, since the regulatory section is currently FDA-only.

---

## F6 - Detection methods, datasets, evaluation
Full file: `F6-detection-datasets-evaluation.md` (1,039 lines, 108 KB)

1. **Q1 answer: NO open-download dataset has both illness labels and confounder annotations.** Every downloadable dataset is in one of two camps: illness labels with no lifestyle confounders (Stanford COVID-19-Wearables, Homekit2020, CovIdentify) or rich confounders with zero illness episodes (PMData, TILES-2018, LifeSnaps, MMASH).
2. The only genuine "both" resource is **All of Us Controlled Tier**, which co-locates `heart_rate_minute_level` / `steps_intraday` with EHR diagnoses and lifestyle surveys for >59,000 Fitbit contributors (46% also have EHR). Institutional agreement, workbench-only, no bulk export. Too slow for course project.
3. Closest obtainable partial: **CovIdentify** (PhysioNet, credentialed + DUA + CITI), 132 self-reported COVID-positive, daily symptom surveys, **vaccination** annotations, but no alcohol/menstrual/medication, and only day-level RHR/steps.
4. **Major structural finding, first-hand:** downloaded and unpacked the 378 MB Stanford COVID-19-Wearables zip. It contains **280 CSVs and no label file at all** (120 hr, 120 steps, 32 sleep, 8 longterm), 119 unique IDs, 3.64 GB unzipped, 87.6M HR rows, **11,186 participant-days**, median 88.5 d/person. Labels live only in the paper's Supplementary Data 1.
5. Also first-hand: dates are **shifted per participant** (observed 2022 to 2030 for a 2020 study), so only within-participant relative time is valid. Steps files are zero-filled and gap-free, so **non-wear can only be inferred from HR**; HR minute coverage in a 6-person sample was 88.2% to 98.6%.
6. **Q2 answer:** the strongest sub-100-line baseline is **NightSignal** (overnight RHR vs streaming median, +3/+4 bpm state machine): 78% of symptomatic COVID cases alerted at or before onset, median 3 days lead, 86.9% specificity per person-day (Alavi, Nat Med 2022).
7. Runner-up is Snyder-lab **RHR-AD**: resting HR = HR where rolling 12-min step sum is 0, 400-sample smooth, hourly, seasonal decompose, 744-hour trailing window, EllipticEnvelope; 81% detection, 88% pre-symptomatic among detected, median 4 days, **0.29 false alarms per 30 days**.
8. Flagged weakness to pre-empt in the report: `EllipticEnvelope(contamination=0.1)` **forces ~10% of every window to be flagged regardless of health**. Easiest thing for a reviewer to attack.
9. **Q4 answer:** baseline window evidence converges on **28 days** (Mishra) and **744 hours = 31 days** (released implementation default), but **no published head-to-head of 7 vs 14 vs 21 vs 28** exists. Running that sweep is a genuine contribution.
10. **Q3 answer, the load-bearing critique:** Kim et al. (AAAI 2022) showed a **random score gets F1_PA = 0.969 on SWaT vs unadjusted F1 = 0.216**. Never report point-adjusted F1.
11. Wu and Keogh (TKDE 2021) showed standard benchmarks are trivial, mislabelled or have unrealistic anomaly density. TSB-AD (NeurIPS 2024) re-curated 1,070 series and names **VUS-PR** the most reliable measure, and found simple statistical methods beat deep architectures.
12. The replacements are not safe either: Lyu (2026) shows **affiliation-F1 becomes gameable at N=3 and hits 0.98 at N=41** under best-of-N seed shopping, while **PR-based metrics and PA%K stay flat**. Recommendation: single-run, disclose N, prefer PR-based.
13. For early warning specifically, the canonical health-domain design is the **PhysioNet 2019 Sepsis utility function**: reward window 12 h before to 3 h after onset, penalties for too-early and late, normalised so 0 = never alert and 1 = optimal.
14. False alerts are counted three ways in the literature and at least two should be reported: **alarms per 30 days** (Mishra), **fraction of person-days alerting** (Alavi: ~13%), and **number needed to evaluate** (Wong: NNE 8 at admission, 109 at 4 h).
15. Cautionary tale to cite: the Epic Sepsis Model's published AUC 0.76 to 0.83 was reproducible **only by letting predictions up to 3 h after onset count**; with correct timing it was **0.63**. The whole result leaked through the detection-window definition.
16. Section 5 gives precise, drop-in definitions: alert event (min 2 consecutive days), detection window `[onset - 7d, onset + 1d]` with a pre-registered sweep, episode detected on the **first** alerting day, lead time conditioned on detection, and seven metrics to report.
17. **Q for few positives:** with 20 to 50 episodes it is descriptive plus exact intervals. Use Clopper-Pearson (26/32 gives 63.6% to 92.8%), **cluster-bootstrap over users not days**, leave-one-user-out, permutation tests. Homekit2020's own protocol (hierarchical bootstrap, 200 resamples, critical-difference diagrams, DeLong variance proportional to 1/((N-m)m)) is the model to copy.
18. Calibration: Van Calster's hierarchy needs **~200 events per class** for a curve, so at 30 events report only the observed-to-expected ratio and say a curve is not estimable. Do not use Hosmer-Lemeshow. Raw Brier is base-rate dominated at 0.1% prevalence.
19. **Q5 answer:** three usable precedents. The **UVA/Padova T1D simulator** (FDA-accepted 2008 as a substitute for animal trials) legitimises simulator-as-oracle; **block-gap injection** into real data (Sci Rep 2024) legitimises semi-synthetic perturbation; **UCR Anomaly Archive / TSB-AD** legitimise curated injected anomalies.
20. **Strongest single evaluation idea in the document:** inject a **+4 bpm, 4-day overnight-RHR bump** (the effect size NightSignal actually thresholds on, with the observed 4.3-day red-cluster duration) into **PMData**, whose daily records include alcohol consumption, meals, training load, stress, mood and sleep quality, and test whether the agent separates it from genuine confounder days. Pair that with hiding PMData's or TILES's real daily self-reports and revealing one only when the agent asks, which is a **simulated-oracle evaluation backed by real answers** rather than invented ones.

## F8 - Confounder physiology and active sensing
Full file: `F8-confounders-and-active-sensing.md` (~1,100 lines, 92 citations)

1. **Separability verdict: five confounders are genuinely NOT separable from early infection using consumer wearable channels alone** - acute alcohol on night 1, acute psychological stress, luteal phase (in a user without cycle history), vaccine reactogenicity, and medication changes. Asking is the only resolution for these.
2. **The worst case is the luteal phase**: Goodale 2019 (n=193, 708 cycles) measures wrist temp **+0.44 C**, HR **+3.91 bpm**, resp rate **+0.60 br/min**, HRV **-0.32 ms** - all four channels move in the infection direction, at ~45% of days for a menstruating user.
3. **Acute stress is nearly as bad**: Bloomfield 2024 (n=525 students, Oura) - RHR OR 1.036/bpm, resp rate OR **1.230**/breath, HRV OR 0.988/ms. The only theoretical discriminator (vasoconstriction giving lower distal temp) is **unvalidated in wearables**.
4. **Vaccination is physiologically indistinguishable** (Gepner 2022: HR +9.85% within 48 h, temp up, RR up, SpO2 unchanged, resolved day 3) but is the cheapest to resolve - one binary question, near a full bit.
5. **Separable ones**: altitude (SpO2 drops ~10 points, unique), late meals (+0.73 bpm, below noise floor), sensor artifact (if SQI exposed), recovery tail (from system state).
6. **Partly separable**: exercise (steps up vs infection down, but fails for non-step exercise and day-2 residual), sleep restriction, travel (sleep-midpoint phase jump ~1 h), caffeine (sleep-only footprint).
7. **The killer quantitative fact**: infection's population-mean RHR rise is **+1.1 to +2.1 bpm**, which is *smaller* than alcohol at one drink (+2.4 to 2.8), moderate evening exercise (+3.34), and the luteal phase (+3.91). Detection only works because it is multi-channel, within-person and multi-day.
8. **Alcohol done properly**: Grosicki 2026 (n=20,968, 5.1M person-days) **+2.4 to 2.8 bpm and -3.3 to -3.8 ms per drink**, saturating; Struven 2025 **+3.0 bpm (95% CI 1.37-4.77)** at 40-60 g, normalising the next night. The circulating **"+10 bpm" figure is folklore** - no controlled study supports it.
9. **Exercise magnitudes exceed infection**: Leota 2025 (n=14,689, 4.08M nights) - maximal strain 0-2 h pre-sleep gives **+5.94 bpm / -17.02 ms / +40 min sleep onset delay**; effects vanish at 4 h or more.
10. **Base rates settle the argument**: alcohol on **29.9% of person-days**; 34.8% of adults short-sleep; 64% of student-weeks high stress; new ARI prodrome approx **2.5% of nights**. Confounders outnumber the target **20-40 : 1**.
11. **Direct corroboration**: Alavi 2022 (Nature Medicine, deployed, n=3,318) measured **1.15 non-COVID alert-days per person per 21 days** (approx 20/year) and explicitly named alcohol, stress, exercise, travel, poor sleep, vaccination and altitude as triggers - and the system asks the user nothing.
12. **Q1 (EIG cost): trivially cheap.** Exact myopic EIG over K=10 causes x M=8 questions x R=4 answers is **Theta(M.K.R) = 320 multiply-adds + ~320 logs** - microseconds. Two-step lookahead ~9,000 ops, also free. Full-horizon is 2.6e9 and is where it stops being free.
13. **The real bottleneck is the likelihood table** p(answer | cause, question) - 320 conditional probabilities, mostly unsupported, and it must encode *answer recall noise* or the system will over-value questions (Benish's channel-capacity result bounds this).
14. **Q2 (cost trade-off): five standard formulations** - Howard's ENGS = EVSI - c(q) (gold standard, utility units, zero-value-if-no-action-change); Lagrangian EIG - lambda.c(q) (used in CwCF/AAAI 2019); EIG/c(q) ratio; budget-constrained; full POMDP. Key honesty point: **entropy-based EIG lacks the "worthless if it cannot change the decision" property that EVSI has.**
15. **Q3 (published info-theoretic asking policy): partial yes, and a real gap.** Yes for *which* question - PROMIS/CAT is deployed at scale in healthcare (FAMCAT: 22 of 60 items; FRIDA: 11 items, r = 0.94-0.97), plus Pathfinder, Benish's framework, and RL symptom-checkers.
16. **Closest published work**: Li, Ponnada, Wang, Dunton and Intille, IMWUT 2024, "Ask Less, Learn More" - explicit information-gain question-skipping in EMA, **34-56% survey-length reduction, 72-95% skip-prediction accuracy**. But it shortens an already-triggered survey; it does not decide whether to interrupt.
17. **The gap**: no published system monitors a passive physiological stream, holds a posterior over candidate causes, computes explicit EIG per question against an interruption cost, and asks only when net value is positive. Horvitz and Apacible 2003 models interruption *cost* with no gain term; JITAIs decide when to *intervene*, not when to *acquire information*. State as "found no published instance", not "does not exist".
18. **Q4 (burden numbers)**: EMA pooled compliance **75.06% (126 studies, n=19,431)**, **78.3%** in youth, **79% (477 articles, N=677,536, avg 6 prompts/day over 7 days)**. Frequency is a **weak** predictor (not significant in two meta-analyses); Wen's non-clinical stratification shows **91.7% at 2-3/day falling to 75.0% at 6+/day**. Users already get **63.5 notifications/day** baseline.
19. **Habituation, not compliance, is the binding constraint**: HeartSteps (5 prompts/day, 6 weeks) effect decayed **+66% to +24%**. And there is **essentially no evidence beyond 6 weeks** - every EMA meta-analysis covers 2-42 day protocols. A defensible budget is 2 or fewer questions per week.
20. **Q5 (test-selection transfer)**: Pauker-Kassirer's threshold model is the most useful - ask only when posterior sits between the testing and test-treatment thresholds; Benish's information graphs give the same shape information-theoretically (peaks at p approx 0.5, zero at extremes); Wald's SPRT / Kulldorff's MaxSPRT (deployed in the Vaccine Safety Datalink) give the "watch one more night vs decide" stopping rule. Section 10 lists 14 things that could not be sourced - including alcohol's effect on resp rate/skin temp, the "2-3 colds a year" figure, and ambient-temperature contamination - flagged so they do not get filled with folklore.

## F9 - Advanced techniques for differentiation
Full file: `F9-advanced-techniques.md` (1,377 lines, 479 URLs, all 12 sections, all 6 questions answered)

**Top five by impressiveness-per-hour:**
1. **Frozen scenario suite + cached/replayed LLM responses in CI** (6-10h) - needs zero labels, makes every number re-derivable offline.
2. **Adversarial persona-conditioned simulated user** (8-12h) - non-response, asymmetric recall error, inconsistency, hostility; the only way to evaluate the interaction policy.
3. **LLM extracts evidence, small hand-specified pgmpy Bayesian network does the inference** (6-10h) - the "beyond intro course" centrepiece; precedent: AutoElicit (arXiv 2411.17284), Word Models to World Models (arXiv 2306.12672).
4. **Ablation matrix with paired bootstrap CIs plus a cost-controlled trivial baseline** (5-8h) - per *AI Agents That Matter* (arXiv 2407.01502).
5. **Systematic ~90-case adversarial matrix** (goal x injection vector x phrasing) (5-8h).

**Key findings:**
- **Conformal prediction (Q2): usable only as a literacy demo.** Angelopoulos and Bates give exact numbers: coverage conditional on the calibration set is Beta(n+1-l, l); you need **n=102** for +/-0.05 at 90% probability, **n=2,491** for +/-0.01, guideline n=1000. Below ~50 labels the "90% guarantee" is rhetorically true and practically empty. Exchangeability is also violated by physiological autocorrelation.
- **Adaptive/online conformal (ACI) is a hard trap:** its update needs the true label *every step* (arXiv 2106.00170 eq. 2). We will not have daily illness ground truth.
- **Q6 has a definitive 1999 answer:** Horvitz, Jacobs and Hovel, *Attention-Sensitive Alerting* (arXiv 1301.6707). Formulas extracted from the PDF: ECA = sum_j C_a(A_i,F_j) p(F_j|E_a); ECDA = max_A sum u(A_i,H_j,t0)p - max_A sum u(A_i,H_j,t)p; alert iff **NEVA = EVTA - ECA > 0**. Deployed as PRIORITIES / PRIORITIES-ATTEND.
- **LLM verbalised confidence:** Xiong et al. (ICLR 2024) find systematic overconfidence, ECE > 0.25 on hard tasks, black-box vs white-box AUROC gap only 0.522 to 0.605. Tian et al. find verbalised beats RLHF logits, "relative 50%" ECE reduction. Both true; recalibrate.
- **Injection defences are theatre with numbers:** eight published defences broken by adaptive attacks, ASR > 50% (arXiv 2503.00061). Go architectural (arXiv 2506.08837, CaMeL).
- **Simulated users need validation:** *Lost in Simulation* (arXiv 2601.17087) shows a 9 percentage-point success-rate swing across simulator LLMs and systematic miscalibration. Run the ablation under two backends.
- **Reproducibility:** temperature-0 gave 80 unique completions in 1,000 due to batch non-invariance (Thinking Machines). Claim replay reproducibility via caching, not determinism.

**16-item "will not work here" list** includes POMDP solving, active inference / expected free energy, contextual bandits (~100 decision points available versus thousands needed), off-policy evaluation, Bayesian-network structure learning, and hierarchical Bayes with only 2 users.

**Method note:** the WebSearch budget was exhausted before this agent started, so all research went through arXiv / OpenAlex / Crossref / GitHub APIs via curl plus direct PDF fetch-and-extract. Every URL in the document was resolved live; five citations lacking resolvable DOIs are explicitly flagged UNVERIFIED.
