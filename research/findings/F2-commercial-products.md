# F2 — Commercial Wearable Products & Health-Tech Companies
### Illness detection, health monitoring, and LLM-based health assistance

**Research date:** 2026-08-30 · **Scope:** commercial products only (research prototypes are F1's territory)

---

## 0. Methodological note and honest limitations

**Read this before trusting anything below.**

1. **Reddit was inaccessible.** `reddit.com` and `old.reddit.com` are blocked to this agent's fetcher, and the search API refuses `reddit.com` as an allowed domain. The task asked specifically for r/ouraring, r/whoop, r/Garmin, r/AppleWatch quotes. **I could not obtain them.** Section 6 therefore uses *substitute* complaint sources that I could actually reach and verify: Garmin's official forums, Samsung's official community, Trustpilot/BBB, a class-action complaint, and first-person journalist accounts. **Reddit evidence remains an open gap for a human to fill manually.** Do not let anyone quietly backfill this section with remembered or invented Reddit quotes.
2. **`whoop.com`, `support.whoop.com`, `wareable.com`, `mddionline.com`, `technology.org`, `androidheadlines.com` and `openai.com` returned HTTP 403** to the fetcher. WHOOP-specific claims below are therefore sourced from search-engine extracts of those pages plus independent third parties (PLOS ONE, FDA, BusinessWire, Healthcare Dive, SiliconANGLE). WHOOP claims are correspondingly **less well verified than Oura's** and are flagged where it matters.
3. **Search budget exhausted at 200 queries.** A handful of smaller players (Athlytic, Train Fitness, Evidation's current commercial product, CareEvolution/myDataHelps, Huma) are covered thinly and flagged as such.
4. Every factual claim below carries a URL. Anything I could not source is marked **UNVERIFIED** in bold.

**Evidence tiers used throughout:**

- **VALIDATED** — peer-reviewed study or regulatory clearance
- **DISCLOSED** — company published technical detail, no independent validation
- **MARKETING** — product-page claim with no supporting evidence
- **INFERRED** — my reasonable inference from user reports, screenshots, or app behaviour

---

## 1. Executive summary

**The headline finding: there is no commercially deployed illness-detection feature anywhere with published validation.** Oura's Symptom Radar, WHOOP's Health Monitor, Apple's Vitals, Withings' Vitality Indicator, Samsung's new Vitals, and Garmin's Body Battery are, without exception, **general wellness products** under FDA policy. None of them has a 510(k), De Novo, or published sensitivity/specificity for detecting infection. Every one carries a "not a medical device / not intended to diagnose" disclaimer. ([Oura](https://support.ouraring.com/hc/en-us/articles/35593651188115-Symptom-Radar), [Apple](https://support.apple.com/en-us/120142), [WHOOP/PRNewswire](https://www.prnewswire.com/news-releases/whoop-leverages-respiratory-rate-technology-to-predict-covid-19-301081096.html))

Meanwhile the *same companies* hold real FDA clearances for narrow cardiac and sleep features — Apple's irregular-rhythm De Novo [DEN180042](https://www.accessdata.fda.gov/cdrh_docs/pdf18/DEN180042.pdf), Apple's sleep-apnea 510(k) [K240929](https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K240929), Apple's hypertension notification [K250507](https://www.accessdata.fda.gov/cdrh_docs/pdf25/K250507.pdf), Samsung's sleep-apnea De Novo [DEN230041](https://www.accessdata.fda.gov/cdrh_docs/reviews/DEN230041.pdf), WHOOP MG's ECG [K243236](https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K243236). **The regulatory line is drawn around named diseases with a clear clinical referent, not around "you might be getting sick."** That is precisely why illness detection ships as vague "signs of strain" language rather than "you have an infection."

**Six things that matter for our project:**

1. **Oura Symptom Radar's 3-tier output is confirmed verbatim**, but Oura has **never disclosed the model class, feature count, or any accuracy figure**. Oura's own head of science, Shyamal Patel, publicly conceded "the algorithm isn't 100 percent accurate, and as such false positive and negative readings are possible" ([Engadget](https://www.engadget.com/wearables/oura-is-rolling-out-its-sickness-detection-feature-to-ring-gen-3-and-ring-4-users-155820702.html)).
2. **WHOOP's famous "20% / 80%" numbers are real and peer-reviewed** — [Miller et al., PLOS ONE 2020](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0243693) — but they are COVID-19-specific, come from a **gradient boosted classifier** (not statistical process control), and the paper **reports no specificity at all**.
3. **The "commercial systems can't ask questions" premise is now partly false.** As of 16 June 2026, Oura ships an in-app medical AI (via Counsel Health) explicitly described as "asking thoughtful follow-up questions" ([Counsel Health](https://www.counselhealth.com/blog/introducing-a-new-era-of-care-our-partnership-with-oura)). WHOOP added "Proactive Check-Ins" in 2026. Ultrahuman shipped "Jade," a real-time agent that *triggers actions*.
4. **But the specific gap is still open.** No product I could find does **anomaly-triggered confounder disambiguation** — detect a deviation, then ask a *targeted* question ("did you drink last night?") to separate alcohol/exercise/cycle from infection. Apple *lists* confounders as static text and asks nothing. WHOOP asks a *fixed* daily journal checklist regardless of whether anything is anomalous. Oura's tags are passive. **The gap is narrower than a 2024-era assumption would suggest, but it is real.**
5. **The confounder problem is quantified in the literature and it is large.** The best available validation of a consumer-wearable respiratory-infection alarm ([Northwell/Fitbit, JMIR 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11292157/)) attributed false alerts to **stress (16.0%), poor sleep (13.7%), intense exercise (9.7%), and alcohol (6.0%)** and reported a **positive predictive value of 4%**. That is the single most useful number in this document.
6. **Trust is actively eroding.** Oura was hit with a proposed class action on 20 August 2026 alleging its accuracy marketing was misleading ([TechCrunch](https://techcrunch.com/2026/08/21/oura-faces-lawsuit-accusing-it-of-misleading-consumers-about-sleep-tracking-accuracy/)). WHOOP received an FDA warning letter in July 2025 that was only closed in June 2026 after the FDA rewrote its wellness guidance ([Healthcare Dive](https://www.healthcaredive.com/news/fda-drops-whoop-warning-letter-over-blood-pressure-feature/823737/)).

---

## 2. Verification verdict table

| # | Claim from previous model | Verdict | Evidence |
|---|---|---|---|
| 1 | "Oura Symptom Radar outputs a 3-tier categorical status: No signs / Minor signs / Major signs" | **CONFIRMED — verified against primary source** | Oura Member Care gives the exact strings: **"No signs"** = "There are no obvious signs in your biometrics of something straining your body"; **"Minor signs"** = "There are small signs in your biometrics of something straining your body"; **"Major signs"** = "There are stronger signs in your biometrics of something straining your body." [support.ouraring.com](https://support.ouraring.com/hc/en-us/articles/35593651188115-Symptom-Radar) |
| 2 | "Oura uses a Balanced Random Forest with a 40-feature heuristic strain matrix" | **REFUTED (fabricated detail); the "40" is half-true** | Oura has **never** published the model class. Its own engineering post, ["Inside the Ring: Developing Symptom Radar"](https://ouraring.com/blog/inside-the-ring-symptom-radar/), discloses signals, training-tag volume and on-device inference but **no algorithm family, no feature count, no metrics**. The number 40 comes from marketing copy — "analyzing over 40 biometrics" ([ouraring.com/blog/symptom-radar](https://ouraring.com/blog/symptom-radar/)) — a count of *biometrics considered*, not model features. "Balanced Random Forest" and "heuristic strain matrix" appear in **no** Oura source, patent, or press item I could locate. Treat as hallucination. |
| 3 | "WHOOP uses statistical process control on z-scores relative to a 21-day baseline" | **PARTIALLY CORRECT, materially mischaracterised** | The only published WHOOP illness algorithm ([Miller et al., PLOS ONE 2020](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0243693)) is a **gradient boosted classifier** ("A gradient boosted classifier was trained using Python Language Software (version 3.6.2)"), **not** statistical process control. **21 days of prior respiratory-rate data is correct** — it is the required baseline window. Of the **five** derived features, one is a z-score-style term `(mu2 - mu_tilde)/sigma`; the others are ratios, differences and a 6-day regression slope. Also: this is a 2020 research algorithm, **not** documented as the algorithm behind today's Health Monitor, which WHOOP has never technically described. |
| 4 | "WHOOP: 20% pre-symptom detection, 80% by day 3, >90% specificity for lower airway infection" | **20%/80% CONFIRMED but scoped wrongly. ">90% specificity" NOT FOUND — treat as fabricated.** | PLOS ONE: "20% of COVID-19 positive individuals were identified prior to symptom onset and 80% of COVID-19 positive individuals were correctly identified by the third day of symptoms." Identical wording in the [June 2020 press release](https://www.prnewswire.com/news-releases/whoop-leverages-respiratory-rate-technology-to-predict-covid-19-301081096.html). These are **COVID-19** figures, not "lower airway infection." The paper **reports no specificity, AUC, or PPV** — it gives a threshold of 0.3 and per-subject hit rates only. Validation sets were small (24 and 190 individuals; training n=57). Authors state the model "has not been evaluated for its performance in fully asymptomatic cases." |
| 5 | "Commercial systems are purely passive and cannot ask clarifying questions" | **REFUTED as stated (2026), but the underlying gap survives in narrower form** | Counterexamples: (a) **Oura x Counsel Health medical AI**, rolling out 16 June 2026 in 43 US states, "asking thoughtful follow-up questions" ([Counsel Health](https://www.counselhealth.com/blog/introducing-a-new-era-of-care-our-partnership-with-oura), [Oura](https://ouraring.com/blog/counsel-integration-oura-app/)); (b) **WHOOP Journal** prompts a personalised behaviour questionnaire *every morning* after sleep processing ([WHOOP](https://www.whoop.com/us/en/thelocker/the-whoop-journal/)); (c) **WHOOP Proactive Check-Ins** (2026, [SiliconANGLE/Wareable coverage](https://www.wareable.com/wearable-tech/whoop-healthex-partnership-my-memory-ai-features-navigator-bands)); (d) **Oura Advisor** has user-configurable proactive check-ins ([Oura](https://ouraring.com/blog/oura-advisor/)); (e) **Sahha's MCP server** can "fire the agent on a webhook when a trend turns" ([sahha.ai](https://sahha.ai/solutions/ai/)). **However:** none is *anomaly-triggered confounder disambiguation*. WHOOP's questionnaire is fixed and asked unconditionally. Counsel's AI is user-initiated symptom triage, not deviation-driven. Apple lists confounders as static prose and asks nothing. **Refine the premise from "they can't ask" to "nothing closes the loop between a detected deviation and a targeted question that would explain it."** |

---

## 3. Per-product A–V write-ups

### 3.1 Oura — Symptom Radar (and Health Radar)

Launched in Oura Labs April 2024; general release December 2024; V2 algorithm subsequently; folded into the new **Health Radar** dashboard from June 2026. ([Oura blog](https://ouraring.com/blog/symptom-radar/), [Health Radar support](https://support.ouraring.com/hc/en-us/articles/52627030482707-Health-Radar))

- **A. Problem being solved.** Give the wearer 1–2 days' advance warning that "something is straining your body," framed as early signs of common respiratory illness (cold, flu), so they can rest before symptoms hit. Deliberately *not* framed as diagnosis. **MARKETING/DISCLOSED**
- **B. Input data.** Overnight biometrics plus demographics. Oura marketing says "50+ wellness metrics" on the launch blog and "over 40 biometrics" elsewhere; the support page names the actual drivers: **average body temperature, respiratory rate, resting heart rate, heart rate variability, inactive time**, plus **age, sex assigned at birth, height, weight**, and (per the engineering post) **menstrual cycle phase**. ([support](https://support.ouraring.com/hc/en-us/articles/35593651188115-Symptom-Radar), [Inside the Ring](https://ouraring.com/blog/inside-the-ring-symptom-radar/)) **DISCLOSED**
- **C. Device.** Oura Ring Gen3, Ring 4, Ring 5 (Ring 5 shipped 4 June 2026, from $399). Requires active membership. ([BusinessWire](https://www.businesswire.com/news/home/20260528686853/en/URA-Introduces-The-Worlds-Smallest-Smart-Ring-Oura-Ring-5), [TechCrunch](https://techcrunch.com/2026/05/28/oura-unveils-its-ring-5-with-a-thinner-lighter-design-starting-at-399/))
- **D. Physiological signals.** Skin/body temperature deviation, respiratory rate, RHR, HRV, inactivity — all derived from **sleep-window** measurement. **DISCLOSED**
- **E. Data processing.** Requires **at least seven nights of sleep data within the past 14 days** before it will produce output — that is the personal baseline requirement. Oura states the V2 algorithm "runs on a member's device — i.e. smartphone — instead of in the cloud." ([Inside the Ring](https://ouraring.com/blog/inside-the-ring-symptom-radar/), [support](https://support.ouraring.com/hc/en-us/articles/35593651188115-Symptom-Radar)) **DISCLOSED**
- **F. Personalization.** Per-person baseline from the trailing 7-of-14 nights, plus **demographic threshold calibration**: "We've calibrated the algorithm to provide similar experiences for different demographic groups, adjusting thresholds accordingly," and it incorporates cycle-phase data. Explicitly degraded for pregnancy: "Pregnancy also impacts biometric baselines and may reduce the accuracy of Symptom Radar," and "may not work optimally with pre-existing medical conditions." ([Inside the Ring](https://ouraring.com/blog/inside-the-ring-symptom-radar/), [Oura blog](https://ouraring.com/blog/symptom-radar/)) **DISCLOSED**
- **G. ML model / statistical method.** **NOT DISCLOSED.** Oura says only "machine learning" and "algorithm." No architecture, no hyperparameters, no feature list, no ablations. The previous model's "Balanced Random Forest" claim has **no source**. What *is* disclosed: the algorithm was fine-tuned on **approximately three million illness-related member tags**. ([Inside the Ring](https://ouraring.com/blog/inside-the-ring-symptom-radar/))
- **H. Training required?** Yes, supervised training on member-tagged illness labels (3M tags) plus the TemPredict cohort lineage. Per-user, no training — only baseline estimation. **DISCLOSED**
- **I. Pretrained models available?** No. Nothing released.
- **J. LLM used?** **No** in Symptom Radar itself. Oura's LLM sits alongside it (Oura Advisor — see 3.2).
- **K. Agent?** No. Symptom Radar is a batch classifier that writes a card to the Today screen. No tool calling, no dialogue, no autonomy.
- **L. Agent tools/actions.** None. The only in-app action is a *suggestion* to enable Rest Mode (which pauses Activity Score targets); the user must do it. ([support](https://support.ouraring.com/hc/en-us/articles/35593651188115-Symptom-Radar))
- **M. RAG / external knowledge?** Not in Symptom Radar. (Oura's separate women's-health LLM does retrieve from a curated corpus — see 3.2.)
- **N. User interaction design.** Push/card **once per morning**, on the Today screen, only when there is a "clear sign of strain." User can tap the card for which biometrics deviated, toggle the whole feature off, and enable Rest Mode. **The user is never asked anything.** Illness "tags" exist but are entirely user-initiated and passive. **DISCLOSED + INFERRED**
- **O. Real-time vs batch.** **Strictly overnight batch.** Output appears "the following morning" after sleep processing. There is no intra-day monitoring. This is a hard architectural constraint of the entire product category. ([support](https://support.ouraring.com/hc/en-us/articles/35593651188115-Symptom-Radar))
- **P. Output produced.** Three tiers, exact strings quoted in section 2 row 1, plus a list of "biometrics from the previous night that show a significant deviation from your baseline." From June 2026 the card also lives inside the **Health Radar** tab (US, India, UAE); elsewhere it lives in the Vitals tab. ([Health Radar](https://support.ouraring.com/hc/en-us/articles/52627030482707-Health-Radar))
- **Q. Evaluation methodology.** Internal only. Oura says it "partnered with external partners, such as UCSF, to analyze two years' worth of anonymized member data" and validated detection "up to two days before a member selects an illness-related tag." **The label is a self-reported app tag, not a clinical diagnosis.** The scientific ancestry is the UCSF **TemPredict** study (>63,000 participants), published as [Mason et al., *Scientific Reports* 2022](https://www.nature.com/articles/s41598-022-07314-0) — but that validates a *different, earlier* COVID model, not Symptom Radar. **MARKETING for Symptom Radar; VALIDATED for TemPredict-the-study.**
- **R. Reported performance.** **None for Symptom Radar.** Wareable: "The company has yet to disclose accuracy data for Symptom Radar." Oura head of science Shyamal Patel to The Verge: "the algorithm isn't 100 percent accurate, and as such false positive and negative readings are possible." The only number in circulation, "76% pre-symptomatic fever detection," is from the 2020 TemPredict fever work and is routinely mis-attributed to Symptom Radar. ([Wareable](https://www.wareable.com/wearable-tech/oura-symptom-radar-launch), [Engadget](https://www.engadget.com/wearables/oura-is-rolling-out-its-sickness-detection-feature-to-ring-gen-3-and-ring-4-users-155820702.html)) **MARKETING**
- **S. Open source.** None.
- **T. Reusable code/models/APIs.** Oura Cloud API v2 exposes sleep, readiness, activity, HRV, temperature deviation, SpO2, tags. **Symptom Radar output itself is not, to my knowledge, exposed via the public API — UNVERIFIED.** Third-party aggregators (Terra, Vital, Rook, Spike) resell Oura data.
- **U. Limitations and complaints.** Requires 7 nights in 14. Degraded in pregnancy and pre-existing conditions. Oura itself warns "Your Readiness Score may not always correlate with Symptom Radar," which users find confusing. Independent reviewers report alcohol-driven false alarms (section 6). Oura is defending a proposed class action over accuracy marketing ([TechCrunch](https://techcrunch.com/2026/08/21/oura-faces-lawsuit-accusing-it-of-misleading-consumers-about-sleep-tracking-accuracy/)).
- **V. Architectural lesson.** Oura ships the strongest illness feature in the market with **zero published performance data**, an overnight-batch cadence, a **self-reported tag** as ground truth, and a three-word output. The three-tier categorical output is a deliberate regulatory hedge — it is uninterpretable enough to stay outside device regulation. **If our project outputs anything more specific than "signs of strain," we inherit a regulatory claim Oura has spent two years carefully avoiding.** Their honest constraint is also ours: the ring only sees you at night, so the decision point is once per day, at wake.

---

### 3.2 Oura — Advisor (LLM assistant) and the Counsel Health medical AI

- **A.** Translate ring data into conversational guidance; from 2026, route users into actual clinical care.
- **B/C/D.** All Oura ring data (sleep, activity, readiness, resilience, stress, cycle, pregnancy), plus user-supplied "Memories."
- **E/F.** Advisor stores user-disclosed facts as **Memories** ("Information you share with Advisor is stored as memories, helping personalize the interactions"); users can view/delete them in Settings. Tone is configurable (**"conversational"** vs **"direct"**), as is **check-in frequency**. ([Oura Advisor support](https://support.ouraring.com/hc/en-us/articles/39512345699219-Oura-Advisor), [Oura Advisor blog](https://ouraring.com/blog/oura-advisor/)) **DISCLOSED**
- **G/H/I.** Base LLM/vendor for general Advisor: **not disclosed**. In **February 2026** Oura announced its **first proprietary LLM, specialised for women's health**, rolled out via Oura Labs, "hosted entirely on Oura-controlled infrastructure," curated by in-house board-certified clinicians. Base model and fine-tuning method **not disclosed**. ([TechCrunch, 24 Feb 2026](https://techcrunch.com/2026/02/24/oura-launches-a-proprietary-ai-model-focused-on-womens-health/))
- **J.** Yes — LLM. Vendor undisclosed for the general assistant; proprietary for women's health.
- **K. Agent?** **Weakly.** It is closer to a data-grounded chatbot with scheduled check-ins than an agent. Oura support states Advisor **cannot take actions** — no setting goals, no enabling Rest Mode; "It offers insights and suggestions only." It *can* generate data visualisations of your metrics, which implies some structured data access. **DISCLOSED + INFERRED**
- **L. Tools/actions.** Read user biometrics; render charts; read/write Memories. No external actuation.
- **M. RAG?** **Yes, for the women's-health model:** "When members ask Advisor a women's health question, it prompts the new model to reference its curated body of women's health research and knowledge sources, while also analyzing relevant biometric signals and longitudinal trends." ([TechCrunch](https://techcrunch.com/2026/02/24/oura-launches-a-proprietary-ai-model-focused-on-womens-health/)) **DISCLOSED**
- **N. Interaction design.** Multiple entry points (Today tab, Readiness insights, "+"). Pre-written prompt suggestions. **Configurable proactive check-ins** based on daily activity and metrics.
- **O. Real-time vs batch.** Conversational and on-demand; check-ins are scheduled, not event-driven, as far as documentation shows.
- **P. Output.** Free text plus charts. Beta metrics quoted by Oura: 60% of beta testers used it weekly; 83% found answers reliable; 60% reported improved understanding of their metrics. **MARKETING** (self-reported beta survey, no methodology).
- **Q/R. Evaluation.** None published. Oura's own caveat: "Like all current LLM-based assistants, Advisor can make mistakes and is still growing in its knowledge." **MARKETING**
- **S/T.** No open source. No API.
- **U.** Not a medical device: "Oura Ring and Advisor are not medical devices and are not intended to diagnose, treat, cure, monitor, or prevent medical conditions or illnesses." ([Oura/Counsel](https://ouraring.com/blog/counsel-integration-oura-app/))

**The Counsel Health integration — the single most important competitive fact in this report.**

From **16 June 2026**, in Oura Labs, in **43 US states** (not AR, DC, KS, MS, RI, WA, WV, WI), Oura surfaces a **medical AI plus licensed physicians inside the Oura app**. Counsel's own description: the medical AI is "designed to assess symptoms and think like a physician: reviewing your medical history, incorporating your biometric Oura data, **asking thoughtful follow-up questions**, identifying likely diagnoses, and helping guide next steps." Oura's version is more conservative: "Counsel's medical AI can gather relevant context and answer initial questions… but it does not replace human clinical judgment." Medical AI chat is included in Oura Membership; physician visits cost extra. Counsel discloses only "HIPAA compliant & SOC2 secure" — **no FDA status, no model disclosed, no validation**. ([Oura](https://ouraring.com/blog/counsel-integration-oura-app/), [Counsel Health](https://www.counselhealth.com/blog/introducing-a-new-era-of-care-our-partnership-with-oura), [Modern Healthcare](https://www.modernhealthcare.com/health-tech/mh-oura-counsel-health-physicians-ai-chatbot/))

- **V. Architectural lesson.** Oura's answer to "what do we do after we detect something?" is **hand off to a separate, clinically-branded, separately-liable AI + human loop**. They keep Symptom Radar deliberately dumb and non-committal, then bolt a questioning agent on top that is legally someone else's product. That is a very deliberate liability architecture and worth copying in spirit: *separate the detector from the interrogator from the advisor.* Note also the key asymmetry we can exploit — **Counsel's AI asks questions to reach a diagnosis, not to explain away an anomaly.** Nobody is asking "was it the wine?"

---

### 3.3 WHOOP — Health Monitor, respiratory rate, MG, Advanced Labs

*(Caveat: whoop.com and support.whoop.com returned 403 to the fetcher; primary WHOOP page content below is via search-engine extracts, cross-checked against FDA, PLOS ONE and BusinessWire.)*

- **A.** Show daily physiological metrics against a personal baseline so deviation is visible; historically, detect COVID-19 pre-symptomatically.
- **B/C/D.** WHOOP 5.0 / WHOOP MG strap. Health Monitor surfaces **five core metrics: resting heart rate, respiratory rate, skin temperature, HRV, blood oxygen**, all from sleep. ([WHOOP Health Monitor](https://www.whoop.com/us/en/thelocker/health-monitor-feature/), [support](https://support.whoop.com/s/article/WHOOP-Health-Monitor-Report))
- **E. Data processing.** WHOOP states that "after two weeks, WHOOP calibrates your sleep, strain, recovery, and Health Monitor baselines." Healthspan unlocks after 21 recoveries. Beyond that, **no algorithmic detail is published for Health Monitor.** ([developer.whoop.com WHOOP 101](https://developer.whoop.com/docs/whoop-101/)) **DISCLOSED (thin)**
- **F. Personalization.** Purely intra-individual baseline: "WHOOP learns your unique baseline over time… any unexplained deviation from your personal baseline can be one of the earliest indicators that something may be off." **MARKETING**
- **G. ML model.** For **Health Monitor: NOT DISCLOSED.** For the **2020 COVID algorithm** (a separate, research artefact): **gradient boosted classifier** over five respiratory-rate-derived features requiring a **21-day** baseline, threshold 0.3. ([Miller et al., PLOS ONE 2020](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0243693)) **VALIDATED (as research), not shipped as-is.**
- **H/I.** Training required (n=57 training individuals in the 2020 work). No pretrained artefacts released.
- **J. LLM.** **Yes — WHOOP Coach, built on OpenAI GPT-4**, announced September 2023. WHOOP states GPT-4 was **fine-tuned with anonymised member data and proprietary WHOOP algorithms**, and that OpenAI operates under **zero data retention** so member health data is not used for training. ([WHOOP](https://www.whoop.com/us/en/thelocker/whoop-unveils-the-new-whoop-coach-powered-by-openai/), [OpenAI customer story](https://openai.com/index/whoop/) — 403 to fetcher, summarised via search index) **DISCLOSED**
- **K. Agent?** **Increasingly yes, but shallow.** 2026 additions: **Strength Trainer AI** that builds structured workout plans from a text prompt or a *screenshot* of a routine (multimodal parse-to-structured-plan — a genuine tool-like capability); **My Memory** (persistent user context); **Proactive Check-Ins** that "suggest sleep timing or training changes based on travel." On the backend WHOOP disclosed adopting Snowflake's agentic tooling (incl. Snowflake CoCo) over a >3 PB data lake ingesting ~20 TB/day. ([Wareable](https://www.wareable.com/wearable-tech/whoop-healthex-partnership-my-memory-ai-features-navigator-bands), [SiliconANGLE, 3 Jun 2026](https://siliconangle.com/2026/06/03/agentic-ai-maturity-whoop-snowflake-ai-scaling-snowflakesummit/)) **DISCLOSED + INFERRED**
- **L. Tools/actions.** Generate/modify a training plan; parse an uploaded lab PDF or screenshot; write to My Memory. **No autonomous action on the user's behalf outside the app — UNVERIFIED whether any tool call mutates state without confirmation.**
- **M. RAG?** WHOOP describes Coach as drawing on "the latest performance science," which implies retrieval, but **no retrieval architecture is documented — INFERRED at best.**
- **N. Interaction design.** Two distinct loops. **(1) WHOOP Journal:** "Each morning after your Sleep is processed, WHOOP will prompt you to answer your Journal questions" — a *personalised but fixed* checklist drawn from 140–300+ behaviours (caffeine, alcohol, medication, sunlight, etc.). **This is the closest thing in the market to confounder capture — and it is unconditional, not anomaly-triggered.** ([WHOOP Journal](https://www.whoop.com/us/en/thelocker/the-whoop-journal/)) **(2) Coach chat:** free-text, plus 2026 Proactive Check-Ins.
- **O. Real-time vs batch.** Recovery and Health Monitor are computed **on waking** and are static for the day unless sleep is edited. Same once-a-day decision point as Oura. ([developer.whoop.com](https://developer.whoop.com/docs/whoop-101/))
- **P. Output.** Health Monitor shows each metric with a **green check** ("within or near the typical range") or an **orange / red exclamation point** ("outside of the typical range and you may want to keep an eye on the metric over the next few days"). Exportable as a **Health Monitor Report** (built during COVID for sharing with clinicians). **The thresholds behind green/orange/red are not published.** ([WHOOP](https://www.whoop.com/us/en/thelocker/health-monitor-feature/))
- **Q/R. Evaluation.** Two genuinely validated things and one heavily marketed thing.
 - **VALIDATED:** WHOOP respiratory-rate *measurement* accuracy — third-party study in the *Journal of Clinical Sleep Medicine* found WHOOP within one breath per minute of gold standard, plus University of Arizona third-party agreement. (Company summary: [WHOOP](https://www.whoop.com/us/en/thelocker/understanding-respiratory-rate-what-it-is-whats-normal-and-why-you-should/); **exact citation UNVERIFIED — I could not open whoop.com to extract the DOI.**)
 - **VALIDATED (research):** the COVID detection model, [PLOS ONE 2020](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0243693): 20% pre-symptomatic, 80% by day 3, **no specificity reported**, symptomatic cases only, n=271 total.
 - **MARKETING:** everything about Health Monitor as an illness detector. WHOOP has published **no** performance figures for the shipped feature.
- **S/T.** No open source. **Public developer API** at [developer.whoop.com](https://developer.whoop.com/) exposing cycles, recovery, sleep, workouts, body measurements — this is the most reusable asset.
- **U. Limitations/complaints.** Wareable's assessment: "there's a way to go to make Health Monitor a true illness detection system… The current version doesn't have features like linking poor sleep to out-of-range metrics or allowing users to tag symptoms within the app." Regulatory friction (below) is the other major limitation.
- **V. Architectural lesson.** WHOOP is the only company that has published a real algorithm and real numbers — and those numbers (20% pre-symptomatic sensitivity) are **honest and unimpressive**. That is the realistic performance ceiling for single-signal, respiratory-rate-only detection. WHOOP also demonstrates the value of a **daily structured behaviour log** as a covariate source; the missed opportunity is that they never condition the questions on the anomaly.

**WHOOP regulatory saga (critical precedent for our project):**
- **14 July 2025** — FDA issues a warning letter to WHOOP Inc. over **Blood Pressure Insights (BPI)**. FDA's position: BP values are "inherently associated with the diagnosis of hypo- and hypertension" and therefore BPI meets the device definition under FD&C §201(h) **regardless of wellness framing**; marketing language including "medical-grade health & performance insights" and the green/yellow/orange UI banding evidenced diagnostic intent under 21 CFR 801.4. Cited adulteration §501(f)(1)(B) and misbranding §502(o). ([FDA warning letter](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/whoop-inc-709755-07142025), [FDA Group analysis](https://insider.thefdagroup.com/p/fda-warning-letter-breakdown-whoop))
- CEO Will Ahmed publicly refused to withdraw the feature, invoking the 21st Century Cures Act general-wellness exemption.
- **6 January 2026** — FDA issues a revised *General Wellness: Policy for Low Risk Devices* guidance stating that non-invasive PPG-based blood-pressure estimation **can** qualify as a general wellness product if strictly wellness-framed. ([Oura's commentary](https://ouraring.com/blog/new-fda-guidance/))
- **17 June 2026** — FDA issues a **closeout letter**; WHOOP had modified "the dial boundaries to prevent any confusion that the feature is classifying blood pressure in a clinical manner." Ahmed: "When the FDA first issued the warning letter, many experts advised Whoop that removing the feature was the only path forward, but we believed in the strength of science." ([Healthcare Dive](https://www.healthcaredive.com/news/fda-drops-whoop-warning-letter-over-blood-pressure-feature/823737/), [STAT](https://www.statnews.com/2026/06/23/fda-drops-enforcement-against-wearable-maker-whoop/), [MassDevice](https://www.massdevice.com/fda-closes-warning-letter-whoop-blood-pressure/))
- **Separately:** WHOOP MG's **ECG feature is FDA-cleared, [K243236](https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K243236), decision 4 April 2025**, Class II cardiovascular, outputs limited to: *Normal Sinus Rhythm; AFib; Low Heart Rate; High Heart Rate; Inconclusive; Unsuccessful Reading* ([510(k) summary PDF](https://www.accessdata.fda.gov/cdrh_docs/pdf24/K243236.pdf)). **That clearance covers ECG only and does not extend to BPI, Health Monitor, or Coach.**

**WHOOP Advanced Labs** (30 September 2025, US; UAE Feb 2026): a **65-biomarker** blood panel via Quest Diagnostics, clinician-reviewed, plus free "Advanced Labs Uploads" where members upload any bloodwork PDF/screenshot in any language and WHOOP Coach reasons over it alongside biometrics. 350,000+ waitlist. ([BusinessWire](https://www.businesswire.com/news/home/20250930178710/en/WHOOP-Launches-Clinician-Reviewed-Advanced-Labs-Unlocking-a-Comprehensive-View-of-Human-Health), [Quest newsroom](https://newsroom.questdiagnostics.com/2025-09-30-WHOOP-Launches-Clinician-Reviewed-Advanced-Labs,-Unlocking-a-Comprehensive-View-of-Human-Health), [UAE launch](https://www.businesswire.com/news/home/20260211439032/en/WHOOP-Launches-Advanced-Labs-in-the-UAE-with-Diagnostic-Partner-Unilabs-Delivering-A-Comprehensive-View-of-Health-For-Members)) **This is the "multimodal document ingestion into an LLM health assistant" pattern, already shipped.**

---

### 3.4 Apple — Vitals app, and the wider Apple Watch health stack

- **A.** Establish overnight baselines for five metrics and tell the user, the next morning, when several are simultaneously abnormal — with *possible explanations*.
- **B/C/D.** Apple Watch (Series 9/10/11, Ultra 2/3) worn to sleep. Five metrics: **heart rate, respiratory rate, wrist temperature, blood oxygen, sleep duration**. ([Apple Support 120142](https://support.apple.com/en-us/120142))
- **E. Data processing.** "It takes a week of sleep data measurements to gather enough information to determine what your typical ranges are." Each metric is then labelled **Typical** or **Outlier**. **The statistical definition of "typical range" is not published.** **DISCLOSED (thin)**
- **F. Personalization.** Per-user typical range from 7 nights, recomputed continuously. **DISCLOSED**
- **G. ML model.** **NOT DISCLOSED.** No paper, no whitepaper. **INFERRED:** given the rule is "N of 5 metrics outside personal range," this is almost certainly a per-metric threshold rule on a rolling personal distribution, not a learned classifier.
- **H/I.** No user-level training. No pretrained artefacts.
- **J/K/L/M.** No LLM, no agent, no RAG in Vitals. Apple's AI health coach, internally **Project Mulberry / "Health+"**, was **scaled back in February 2026**, missed iOS 26.4, and as of the reporting had **not shipped**; features are expected to be released piecemeal inside the Health app rather than as a coach product. ([Business Standard](https://www.business-standard.com/technology/tech-news/apple-ai-health-coach-shelved-project-mulberry-features-arrive-updates-126020601028_1.html), [9to5Mac, 24 May 2026](https://9to5mac.com/2026/05/24/apple-improving-heart-rate-tracking-in-watchos-27-mulberry-health-coach-delays/), [9to5Mac, 29 Aug 2026](https://9to5mac.com/2026/08/29/apple-health-revamp-ai-coach-new-apple-watch-next-month/)) **This is a significant data point: the best-resourced company in consumer health could not ship an LLM health coach.**
- **N. Interaction design — important for our premise.** Notification fires **only when two or more metrics are outliers on the same night**, delivered **the next morning**. Apple's own explanatory copy names confounders: "Factors such as your medications, elevation, alcohol intake, or even illness can impact your metrics." **Apple states these as possibilities in prose. It does not ask the user which one applies, and there is no confounder logging UI in Vitals.** Outlier notifications can be turned off. ([Apple Support](https://support.apple.com/en-us/120142), [Apple Watch User Guide](https://support.apple.com/guide/watch/vitals-apd15aa7ed96/watchos)) **DISCLOSED**
- **O. Real-time vs batch.** Overnight batch, morning delivery. Same cadence as Oura and WHOOP.
- **P. Output.** Per-metric **Typical / Outlier** chips, plus a morning notification listing the outlying metrics and possible contributing factors. **The exact notification string is UNVERIFIED — I could not obtain a screenshot-level source.**
- **Q/R. Evaluation.** **None for Vitals.** Disclaimer: "Vitals app measurements are not intended for medical use. Please consult your healthcare provider prior to making any decisions related to your health."
- **S/T.** No open source. HealthKit is the reuse surface (on-device, user-consented).
- **U.** The "2-of-5 metrics" rule is a crude but effective specificity hack. Third-party writers note "A single outlier on a single metric for one night is almost always noise… two metrics out of range on the same night often point to a real physiological event." ([XDA](https://www.xda-developers.com/guide-to-the-vitals-app-in-watchos-11/), [Wareable](https://www.wareable.com/apple/how-vitals-app-finally-makes-apple-watch-a-wellness-powerhouse))
- **V. Architectural lesson.** **Apple solved the false-alarm problem by requiring multi-signal concordance rather than by asking the user anything.** That is the cheapest possible alternative to our proposed approach and we must be able to say why asking beats requiring 2-of-5. Also note: Apple *knows* the confounders — they are literally printed in the notification — and still chose not to elicit them. Either they judged the interaction cost too high, or they judged that a wellness product must not appear to be gathering clinical history. Both are real design constraints.

**Apple's cleared features (contrast with Vitals):**
| Feature | Pathway | Number | Note |
|---|---|---|---|
| Irregular Rhythm Notification | De Novo | [DEN180042](https://www.accessdata.fda.gov/cdrh_docs/pdf18/DEN180042.pdf) | Created the Class II "photoplethysmograph analysis software" OTC category |
| AFib History | 510(k) | K213971 | For users **already diagnosed** with AFib, 22+; later granted MDDT qualification for clinical trials ([FDA MDDT](https://www.fda.gov/media/178230/download), [Fierce Biotech](https://www.fiercebiotech.com/medtech/apple-watchs-afib-history-feature-ripens-fda-clearance)) |
| Sleep Apnea Notification | 510(k) | [K240929](https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K240929), cleared 13 Sep 2024 | OTC, 18+, not previously diagnosed; accelerometer-based breathing disturbance ([Apple Newsroom](https://www.apple.com/newsroom/2024/09/apple-introduces-groundbreaking-health-features/)) |
| Hypertension Notification | 510(k) | [K250507](https://www.accessdata.fda.gov/cdrh_docs/pdf25/K250507.pdf), cleared 11 Sep 2025 | PPG-based, OTC, 22+, not previously diagnosed; 202-day review ([MobiHealthNews](https://www.mobihealthnews.com/news/apple-receives-fda-nod-hypertension-notification-feature)) |
| **Vitals app** | **none** | **n/a** | **General wellness** |

---

### 3.5 Samsung — Galaxy Watch health stack, Energy Score, and the new Vitals

- **A/B/C/D.** Galaxy Watch (BioActive sensor). Sleep, HR, HRV, skin temperature, SpO2, plus 2025–26 additions **Vascular Load** (circulatory stress during sleep; needs 3 of the last 14 nights) and **Antioxidant Index** (5-second thumb press measuring skin carotenoids — a genuinely novel optical modality). ([Samsung Newsroom, Antioxidant Index development](https://news.samsung.com/global/the-era-of-healthy-aging-%E2%91%A1-a-health-check-in-five-seconds-inside-the-development-of-galaxy-watch8-series-antioxidant-index), [One UI 8 Watch features](https://news.samsung.com/global/new-features-on-one-ui-8-watch-help-users-build-healthier-habits))
- **E/F/G.** Energy Score is a Galaxy-AI-computed daily readiness figure. **Algorithm not disclosed.** Vascular Load and Antioxidant Index algorithms not disclosed.
- **H/I/J/K/L/M.** Samsung Health has Galaxy AI features; **no evidence of an agentic health assistant with tool calling — UNVERIFIED.**
- **N/O/P.** Morning delivery of Energy Score and sleep score. **Samsung is reported to have added a "Vitals" overnight-health screen with One UI 9 Watch, positioned as illness pre-warning** — [Explosion](https://www.explosion.com/205347/samsung-galaxy-watches-can-now-warn-you-before-you-get-sick/), [SamMobile One UI 9 Watch](https://www.sammobile.com/news/samsung-one-ui-9-watch-everything-to-know/). **I could not confirm this against a Samsung primary source — treat as INFERRED/UNVERIFIED.** If real, it is a direct Apple-Vitals clone and the third major platform to ship overnight-deviation alerting.
- **Q/R.** Sleep apnea is **VALIDATED via regulation**: FDA **De Novo DEN230041**, granted February 2024, creating the Class II generic "over-the-counter device to assess risk of sleep apnea"; detects moderate-to-severe OSA signs in adults 22+, requiring >4 hours' tracking on two nights within a ten-day window. ([FDA decision summary](https://www.accessdata.fda.gov/cdrh_docs/reviews/DEN230041.pdf), [Samsung Newsroom](https://news.samsung.com/global/samsungs-sleep-apnea-feature-on-galaxy-watch-first-of-its-kind-cleared-by-us-fda), [MedTech Dive](https://www.medtechdive.com/news/samsung-fda-watch-sleep-apnea/707335/)). Samsung reports a World Sleep Day 2026 study finding 23% of participants at risk of sleep apnea ([Samsung Mobile Press](https://www.samsungmobilepress.com/articles/samsung-sleep-apnea-study-for-world-sleep-day-2026)). Energy Score / Vascular Load / Antioxidant Index: **no published validation — MARKETING**.
- **S/T.** Samsung Health Data SDK / Health Connect on Android is the reuse surface.
- **U.** See section 6 — Samsung's own community forum is full of Energy Score complaints.
- **V. Architectural lesson.** Samsung's Antioxidant Index shows there is still headroom in *new sensing modalities* rather than smarter inference on the same PPG. Also: Samsung's De Novo is the reason Apple could clear sleep apnea via 510(k) — **the first company through a regulatory door creates the predicate for everyone else.** If our project ever wanted a claim, the predicate landscape matters.

---

### 3.6 Fitbit / Google — Daily Readiness, Health Metrics, and the Gemini health coach

- **A/B/C/D.** Fitbit/Pixel Watch/**Fitbit Air**. Daily Readiness Score combines **HRV, recent sleep, and resting heart rate**; the activity term was removed when the score went free, "so it's no longer determined by the level of activity you did the day before, but how hard your body is working to recover." Health Metrics dashboard shows breathing rate, HRV, RHR, SpO2, skin temperature variation. ([Google Health Help](https://support.google.com/fitbit/answer/14236710), [Android Central](https://www.androidcentral.com/what-fitbit-daily-readiness-score-and-how-do-i-use-it), [DC Rainmaker teardown](https://www.dcrainmaker.com/2021/11/fitbit-readiness-review.html))
- **E/F.** **7 nights** minimum for a first score; **~14-day** baseline for stability; a full month for a complete baseline. Bands: **low 1–29, good 30–64, excellent 65–100**. **DISCLOSED**
- **G.** Not disclosed beyond the input list.
- **J. LLM — the big 2026 change.** On **19 May 2026 the Fitbit app became the Google Health app**, launching alongside the **$99.99 screenless Fitbit Air** and a **Gemini-built personal health coach**. Public preview ran from **28 October 2025**. Premium is **$9.99/mo or $99.99/yr**, bundled into Google AI Pro/Ultra. ([Google blog](https://blog.google/products-and-platforms/products/google-health/google-health-fitbit/), [TechCrunch, 7 May 2026](https://techcrunch.com/2026/05/07/googles-9-99-per-month-ai-health-coach-launches-may-19/), [Google blog preview](https://blog.google/products-and-platforms/devices/fitbit/fitbit-ai-personal-health-coach-preview/), [MobiHealthNews](https://www.mobihealthnews.com/news/google-debuts-gemini-powered-ai-health-coach-fitbit-and-pixel-watch-users))
- **K. Agent?** **Partially.** It builds and *adaptively adjusts* multi-week workout plans from continuous feedback, and reads **Health Connect, Apple Health and medical records**. Google's blog does **not** state whether it does tool calling or takes autonomous action. Premium tier is described as including "adaptive plans, clinical record summaries and predictive analysis on sleep, recovery and fitness." **DISCLOSED (plan adaptation) + UNVERIFIED (tool calling)**
- **M. RAG?** Reading clinical records into summaries implies retrieval over the user's own records. **INFERRED.**
- **N/O.** Conversational plus generated plans. Underlying metrics remain morning-batch.
- **Q/R.** No published evaluation of the coach. Google describes it as "backed by science" — **MARKETING**. Fitbit's **AFib PPG algorithm is VALIDATED**: FDA-cleared April 2022; in the Fitbit Heart Study, of the 4,728 participants (1%) who received an irregular-heart-rhythm detection, **98.2% had AF confirmed on a simultaneous ECG patch**. ([Google blog](https://blog.google/products-and-platforms/devices/fitbit/irregular-heart-rhythm-notifications/), [AASM](https://aasm.org/fda-clears-fitbit-feature-to-detect-a-fib/), [Healio](https://www.healio.com/news/cardiology/20220411/fitbit-receives-fda-clearance-for-algorithm-to-detect-af)). Pixel Watch 3's **Loss of Pulse Detection received FDA clearance 26 February 2025** — first of its kind — using PPG plus IR/red confirmation, an AI movement check, an on-watch check-in prompt, then an automatic emergency call if unresponsive. ([Google](https://blog.google/feed/pixel-watch-3-loss-of-pulse-detection-fda/), [Engadget](https://www.engadget.com/wearables/pixel-watch-3-receives-fda-clearance-for-loss-of-pulse-detection-210458883.html))
- **S/T.** Health Connect (Android) is a genuinely reusable, permissioned data layer. Web API for Fitbit data exists.
- **U.** **No illness-detection feature.** Google has readiness and metrics, but has never shipped a Symptom Radar equivalent.
- **V. Architectural lesson.** **Loss of Pulse Detection is the only shipped consumer wearable feature that asks the user a question in response to a detected anomaly** — "are you OK?" — and escalates autonomously if there is no answer. It is a one-bit question with a life-safety justification, but it is the existence proof that anomaly→question→autonomous-action is shippable in a regulated consumer wearable. **Cite this in our design rationale.**

---

### 3.7 Garmin — Body Battery, Health Snapshot, Sleep Coach

- **A/B/C/D.** Garmin watches and the **Index Sleep Monitor** armband (a screenless sleep-only band marketed with illness-prediction framing, [Tom's Guide](https://www.tomsguide.com/wellness/sleep-tech/garmin-launches-new-index-sleep-monitor-for-screenless-sleep-tracking)). Body Battery is a 0–100 energy score from HRV, stress, activity and sleep. Health Snapshot is a **user-initiated 2-minute guided reading** capturing HR, HRV, SpO2, respiration and stress into a single shareable report. ([Garmin blog](https://www.garmin.com/en-US/blog/health/top-10-features-to-monitor-your-health/), [Sleep Coach](https://www.garmin.com/en-US/garmin-technology/health-science/sleep-coach/))
- **E/F/G.** Body Battery derives from Firstbeat Analytics physiology models. Documented rule of thumb from Garmin's own forums: **if stress values are above 25, Body Battery will not recharge**, with nicotine, alcohol, late training, sickness and heart conditions listed as drivers of high stress. Body Battery floors at 5. ([Garmin Forums](https://forums.garmin.com/apps-software/mobile-apps-web/f/garmin-connect-mobile-ios/353140/illness-and-body-battery)) **DISCLOSED (community/support level)**
- **H–M.** No LLM, no agent, no RAG in the core Garmin experience. **UNVERIFIED** whether Garmin has shipped an LLM assistant as of Aug 2026.
- **N/O/P.** Body Battery updates continuously through the day (**the only genuinely continuous score in this comparison**). Garmin's framing of deviation: "If metrics are above or below your usual range, it may indicate added stress to the body and could be related to physical activity, potential illness and more," and skin temperature change "can be an early predictor of illness." No dedicated illness alert tier.
- **Q/R.** Garmin ECG app is FDA-cleared (separate). Body Battery / Health Snapshot: **no published illness validation — MARKETING**.
- **S/T.** Garmin Health API and Connect IQ — the most developer-open of the major watch platforms.
- **U/V.** **Architectural lesson: Garmin is the counter-example on cadence.** Body Battery is continuous, which is what our project would want — but continuous also means Garmin never issues a discrete "you may be sick" event, and users are left to interpret. Garmin also demonstrates the confounder problem *in Garmin's own words on Garmin's own forums* (section 6): alcohol and illness produce **the same** Body Battery signature, and Garmin's official answer is essentially "the watch is right, you poisoned yourself."

---

### 3.8 Withings — Vitality Indicator (the closest direct competitor to our concept)

- **A.** Predict illness before symptoms and explain energy/fatigue.
- **B/C/D.** ScanWatch 2 / Nova / Light + **HealthSense 4** OS, announced at IFA, September 2025. Monitors **35 health parameters**, specifically combining **HRV, physical activity, body temperature, SpO2, respiratory rate and sleep quality**. ([Withings ScanWatch 2 press release PDF](https://media.withings.com/press/press-releases/scanwatch-2/PR_ScanWatch2_US.pdf), [Android Police](https://www.androidpolice.com/withings-scanwatch-2-advanced-ai-health-monitoring/), [Gadgets & Wearables](https://gadgetsandwearables.com/2025/09/16/healthsense-4-withings/))
- **E/F/G.** "Predictive AI." **Model not disclosed.**
- **H/I/J/K/L/M.** No LLM/agent disclosed.
- **N/O/P.** "Sends personalized notifications to help users target and improve the factors that affect energy." Marketing claims it "can detect early changes in health status — from signs of impending illness to the next menstrual cycle to falling energy levels." **Explicitly bundles cycle prediction and illness prediction in the same feature — i.e. Withings treats the menstrual cycle as a signal to model, not a confounder to exclude.** ([BigGo summary of the IFA announcement](https://biggo.com/news/202509052122_Withings_ScanWatch_2_AI_Health_Prediction))
- **Q/R.** **No published validation — MARKETING.** Requires **Withings+** at $10/mo or $100/yr.
- **The one genuinely different thing Withings does:** the Withings+ subscription includes **Cardio Check-Up**, connecting users to **board-certified cardiologists who review heart data and respond within 24 hours** — up to four per year on the annual plan. Like Oura×Counsel, this is a human-in-the-loop escalation path bolted onto a wellness product.
- **S/T.** Withings Health Cloud API exists.
- **U/V.** **Architectural lesson: Withings is doing almost exactly what our project proposes and has published nothing to justify it.** That is simultaneously validation of the concept's market appeal and a warning about the evidentiary standard nobody is meeting. It also shows a subscription-gated escalation-to-clinician model is commercially viable.

---

### 3.9 Ultrahuman — Ring PRO and "Jade" (the most agentic product shipped)

- **A/B/C/D.** Ultrahuman Ring AIR / **Ring PRO** (third gen, 2026), plus **M1 CGM** glucose, **Blood Vision** (120+ blood bioreviewers), and **Ultrahuman Home** environmental sensors. Ring PRO: 15-day battery, 250 days on-device storage, **dual-core processor with on-chip machine learning**, redesigned HR sensing. ([Ultrahuman press release](https://cyborg.ultrahuman.com/press-releases/ultrahuman-unveils-ring-pro-with-category-defining-15-day-battery-and-jade-worlds-first-real-time-biointelligence-ai), [Digital Health News](https://www.digitalhealthnews.com/ultrahuman-launches-ring-pro-with-real-time-biointelligence-ai-jade))
- **J. LLM.** Yes — "Jade," marketed as the "world's first real-time biointelligence AI." **Base model not disclosed.** Two modes: **Standard** and **Deep Research**.
- **K. Agent — YES, and this is the most explicit agentic claim in the consumer market.** Jade is "designed to interpret health signals in real time and **trigger actions** within its app ecosystem," and is "designed to act on data as it comes in." ([FutureFive](https://futurefive.com.au/story/ultrahuman-unveils-ring-pro-jade-ai-health-coach), [Wellworthy hands-on](https://wellworthy.com/ultrahuman-just-launched-its-most-advanced-ring-yet-alongside-an-ai-that-acts-on-your-health-data-in-real-time/))
- **L. Tools/actions (documented today).** Start a breathwork session; **initiate AFib detection**. Roadmap claims (**MARKETING, not shipped**): ordering food, changing room temperature, "proactively flagging health issues before they occur." Separately, the **UltraSphere** engine turns ring + CGM + weather data into "60-plus daily health actions."
- **M. RAG.** Not disclosed. Cross-source grounding (ring + CGM + blood panel + environment) is disclosed.
- **N/O.** Real-time, in contrast to the overnight-batch incumbents.
- **Q/R.** **No validation for Jade.** AFib detection is powered by **FDA-cleared FibriCheck technology** (i.e. Ultrahuman licensed someone else's clearance), announced July 2024; the feature is available in Australia, EU, KSA, Singapore, UK and UAE. ([TechCrunch](https://techcrunch.com/2024/07/16/ultrahumans-smart-ring-gets-fda-approved-afib-detection), [Medical Device Network](https://www.medicaldevice-network.com/news/ultrahuman-adds-afib-detection-feature-to-ring-air-smart-ring/))
- **U.** Ring PRO is **not available in the US**; Ultrahuman was subject to a US import ban from October 2025 following Oura's ITC patent win, returning to US pre-order in 2026 with the Ring PRO. ([The Gadgeteer](https://the-gadgeteer.com/2026/03/25/ultrahumans-banned-smart-ring-is-back-with-a-point-to-prove/))
- **V. Architectural lesson.** Ultrahuman is the only company shipping the **detect → act** loop rather than **detect → tell**. Note what actions they chose: *breathwork* and *run an AFib check*. Both are (a) zero-risk and (b) inside their own app. **That is the safe action space for an agent in this domain, and it's a good template: an agent that triggers a further measurement is far more defensible than one that gives advice.** "Trigger a confirmatory measurement" is arguably a better agent action than "ask a question" — or a good complement to it.

---

### 3.10 Smaller and adjacent players (brief)

| Company | Product | What it does | Evidence tier |
|---|---|---|---|
| **Polar** | Nightly Recharge | Two components: **Sleep Charge** and **ANS Charge** (how well the autonomic nervous system calmed in the early hours). Documentation explicitly notes "Higher breathing rate values than usual may indicate a fever or impending illness" — but there is no illness *alert*. ([Polar](https://www.polar.com/us-en/smart-coaching/nightly-recharge)) | DISCLOSED, no illness feature |
| **Circular** | Circular Ring 2 | First smart ring with **on-ring ECG and FDA-cleared AFib detection**, launched Aug 2025, 140+ biometric reviewers, subscription-free. ([TechCrunch CES 2025](https://techcrunch.com/2025/01/05/circular-unveils-its-next-gen-ring-2-with-ecg-functionality-and-afib-detection-at-ces-2025), [Techlicious](https://www.techlicious.com/blog/circular-ring-2-ces-2025/)) | VALIDATED (AFib only) |
| **Bevel** | Bevel AI Health Coach | Third-party app layering an LLM ("Bevel Intelligence") over Apple Health / wearable data; users ask about sleep, recovery, nutrition, workouts, bioreviewers. Raised a $10M Series A from General Catalyst, Oct 2025. ([bevel.health](https://www.bevel.health/), [TechCrunch](https://techcrunch.com/2025/10/30/bevel-raises-10m-series-a-from-general-catalyst-for-its-ai-health-companion)) | MARKETING |
| **Sahha** | Health Data API + **MCP server** | **Most directly reusable for our architecture.** Exposes **scores** (`sleep.state`, `readiness.state`, `wellbeing.state`), **bioreviewers** (`sleep_duration`, `activity_steps`), **archetypes** (`activity_level`, `sleep_pattern`) and **insights** as **structured MCP tools** callable from OpenAI/Claude/Gemini/any MCP framework — "no glue code." Critically, it supports **event-driven agent invocation**: "Fire the agent on a webhook when a trend turns," e.g. "your sleep's slipped five days running." Free 30-day sandbox, 25 dev users. HIPAA/GDPR/SOC 2. ([sahha.ai/solutions/ai](https://sahha.ai/solutions/ai/)) | DISCLOSED |
| **Terra / Vital (Junction) / Spike / Rook** | Wearable data aggregation APIs | Terra has the widest device coverage; Spike claims 300+ devices; **Rook computes its own sleep/recovery/stress/strain/chronotype scores against a 21-day rolling baseline** (note: the same 21-day window as WHOOP's published work). Indicative 2026 pricing: Rook Core $399/mo for 750 active users + ROOKScore $249/mo; Vital ~$0.50/user/mo, $300 minimum. ([Open Wearables comparison](https://www.openwearables.io/compare), [Sahha vs Terra](https://sahha.ai/compare/terra-alternatives/), [Sahha vs Spike](https://sahha.ai/compare/spike-api-alternatives/) — note these last two are competitor-authored, treat with suspicion) | DISCLOSED / vendor-biased |
| **Empatica** | EmbracePlus + Health Monitoring Platform | Medical-grade research wearable. FDA clearance Nov 2022 for the platform; **six FDA-cleared digital bioreviewers** (EDA, SpO2, skin temperature, movement during sleep, pulse rate, respiratory rate) among 128 supported digital measures. ([Empatica](https://www.empatica.com/blog/empatica-receives-new-fda-clearance-for-cardiac-digital-bioreviewers/), [PR Newswire](https://www.prnewswire.com/news-releases/empatica-receives-new-fda-clearance-for-its-health-monitoring-platform-and-announces-series-b-financing-301685344.html)) | VALIDATED |
| **Biobeat** | RPM patch/watch | FDA-cleared cuffless BP, SpO2, HR; later clearances for stroke volume and cardiac output; markets early-deterioration detection from its vital-sign database. ([PR Newswire 2022](https://www.prnewswire.com/news-releases/fda-clears-the-biobeat-remote-patient-monitoring-device-and-platform-for-additional-vital-signs-301511494.html), [2023](https://www.prnewswire.com/news-releases/biobeat-remote-patient-monitoring-devices-and-platform-receive-additional-fda-clearances-for-stroke-volume-and-cardiac-output-301715553.html)) | VALIDATED (measurement), MARKETING (deterioration) |
| **Current Health** (Best Buy Health) | RPM wearable | FDA-cleared AI-powered wearable for post-acute care; continuous monitoring to determine health trajectory for earlier clinician intervention. ([BioSpace](https://www.biospace.com/current-health-receives-fda-clearance-for-its-remote-patient-monitoring-solution-enables-earlier-intervention-and-improved-patient-outcomes)) | VALIDATED (clearance) |
| **Evidation Health** | Person-generated health data platform | Runs the **WAVE (Wearable Assisted Viral Evidence)** decentralised study on wearable data vs respiratory viral infection. ([ClinicalTrials NCT06207929](https://clinicaltrials.gov/study/NCT06207929)) | **Current commercial product state UNVERIFIED — search budget exhausted** |
| **CareEvolution / myDataHelps, Huma, Athlytic, Train Fitness** | — | **NOT RESEARCHED — search budget exhausted. Open gap.** | **UNVERIFIED** |

---

## 4. Regulatory status table

**The core rule:** FDA's *General Wellness: Policy for Low Risk Devices* lets a product make general-wellness claims if it does not reference a specific disease. The moment a feature names a disease or produces a clinically-actionable measurement, it becomes a device. FDA **revised this guidance on 6 January 2026** to explicitly allow non-invasive PPG blood-pressure *estimation* as general wellness — a direct consequence of the WHOOP fight. ([Oura commentary](https://ouraring.com/blog/new-fda-guidance/), [MedTech Dive](https://www.medtechdive.com/news/oura-to-add-blood-pressure-feature-following-fda-policy-change/821427/))

| Product | Feature | Classification | Clearance number | What it is allowed to claim |
|---|---|---|---|---|
| Oura | **Symptom Radar** | **General wellness** | none | "Signs of something straining your body." Explicit disclaimer: "not intended for use in the diagnosis of disease… or in the cure, mitigation, treatment, or prevention of disease." May **not** say cold/flu/infection as a finding. |
| Oura | Health Radar / Blood Pressure Signals | **General wellness** (post-Jan-2026 guidance) | none | Overnight BP *trend/dipping patterns*, not a cuff-equivalent measurement, not hypertension. Auto-disabled in pregnancy. Oura is separately pursuing an actual clearance for hypertension detection, expected late 2026–2027 ([MedTech Dive](https://www.medtechdive.com/news/oura-fda-clearance-smart-ring-blood-pressure/803181/)) |
| Oura | Advisor / women's-health LLM | **General wellness** | none | "Not medical devices and are not intended to diagnose, treat, cure, monitor, or prevent medical conditions or illnesses." |
| Oura × Counsel | Medical AI + physicians | Practice of medicine (telehealth), not a cleared device | none; "HIPAA compliant & SOC2 secure" only | Counsel physicians may diagnose. The AI itself has **no disclosed regulatory status** — a notable grey zone. |
| WHOOP | **Health Monitor** | **General wellness** | none | "Not medical devices, are not intended to diagnose COVID-19, the flu or any other disease." |
| WHOOP | Blood Pressure Insights | **General wellness after remediation** | Warning letter [709755, 14 Jul 2025](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/whoop-inc-709755-07142025); **closeout 17 Jun 2026** | Wellness BP estimates only; dial boundaries rebanded so it does not appear to classify BP clinically |
| WHOOP MG | ECG | **Class II, cleared** | **[K243236](https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K243236)**, 4 Apr 2025 | Outputs restricted to: Normal Sinus Rhythm / AFib / Low HR / High HR / Inconclusive / Unsuccessful |
| Apple | **Vitals app** | **General wellness** | none | "Vitals app measurements are not intended for medical use." Lists possible factors; makes no finding. |
| Apple | Irregular Rhythm Notification | **Class II, De Novo** | **[DEN180042](https://www.accessdata.fda.gov/cdrh_docs/pdf18/DEN180042.pdf)** | Notify of irregular rhythm suggestive of AFib, OTC |
| Apple | AFib History | **Class II, 510(k)** | K213971 | Estimate AFib burden, 22+, **already diagnosed** only |
| Apple | Sleep Apnea Notification | **Class II, 510(k)** | **[K240929](https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K240929)**, 13 Sep 2024 | Notify of sleep-apnea risk, OTC, 18+, not previously diagnosed |
| Apple | Hypertension Notification | **Class II, 510(k)** | **[K250507](https://www.accessdata.fda.gov/cdrh_docs/pdf25/K250507.pdf)**, 11 Sep 2025 | Notify of patterns suggestive of hypertension, OTC, 22+, not previously diagnosed |
| Samsung | Sleep Apnea Feature | **Class II, De Novo** | **[DEN230041](https://www.accessdata.fda.gov/cdrh_docs/reviews/DEN230041.pdf)**, Feb 2024 | Assess risk of moderate-to-severe OSA, OTC, 22+ |
| Samsung | Energy Score, Vascular Load, Antioxidant Index, "Vitals" | **General wellness** | none | Wellness framing only |
| Fitbit/Google | Irregular Heart Rhythm Notifications (PPG) | **Class II, cleared** | Apr 2022 (K-number **UNVERIFIED**) | Notify of AFib signs, 22+, not previously diagnosed |
| Google | Pixel Watch 3 Loss of Pulse Detection | **Class II, cleared** | 26 Feb 2025 (De Novo; number **UNVERIFIED**) | Detect pulselessness, prompt user, auto-call emergency services |
| Google | Daily Readiness, Gemini Health Coach | **General wellness** | none | Wellness coaching |
| Garmin | Body Battery, Health Snapshot, Sleep Coach | **General wellness** | none | Wellness only |
| Withings | **Vitality Indicator** | **General wellness** | none | Energy/fatigue framing; illness prediction is in marketing copy, not in a cleared indication |
| Ultrahuman | AFib detection | Cleared via licensed **FibriCheck** technology | FibriCheck's clearance | AFib detection, in AU/EU/KSA/SG/UK/UAE |
| Ultrahuman | Jade | **General wellness** | none | Wellness guidance and in-app actions |
| Circular | Ring 2 ECG/AFib | Cleared | number **UNVERIFIED** | AFib detection |
| Empatica | Health Monitoring Platform | **Cleared** | Nov 2022 + cardiac biomarker clearance | Six cleared digital bioreviewers for clinical research/monitoring |

**Implication for our project:** a system that outputs "you may be developing an infection" is a **disease-specific claim** and would be a medical device. Every commercial player avoids this by outputting an abstraction ("strain," "outlier," "vitality"). If our project is academic, we can be more specific than any of them — and we should explicitly note in our writeup *why* commercial products are vaguer than they need to be.

---

## 5. "Does it ask the user anything?" table

This is the table that directly tests the project premise. Columns distinguish four very different behaviours.

| Product | Passive tagging available? | Asks anything at all? | Asks *unprompted*? | **Anomaly-triggered targeted confounder question?** | Source |
|---|---|---|---|---|---|
| **Oura Symptom Radar** | Yes (Tags, user-initiated) | **No** | No | **NO** | [support](https://support.ouraring.com/hc/en-us/articles/35593651188115-Symptom-Radar) |
| **Oura Advisor** | n/a | Yes (conversational) | **Yes — configurable check-ins**, based on daily activity/metrics | **NO** — check-ins are scheduled, not deviation-conditioned | [Oura](https://ouraring.com/blog/oura-advisor/), [support](https://support.ouraring.com/hc/en-us/articles/39512345699219-Oura-Advisor) |
| **Oura × Counsel medical AI** | n/a | **Yes — "asking thoughtful follow-up questions"** | Surfaced as an option, incl. alongside Advisor/health signals | **Closest thing that exists — but it is diagnostic triage of a symptom the user reports, not disambiguation of a sensor anomaly** | [Counsel](https://www.counselhealth.com/blog/introducing-a-new-era-of-care-our-partnership-with-oura), [Oura](https://ouraring.com/blog/counsel-integration-oura-app/) |
| **WHOOP Journal** | Yes | **Yes — prompts a questionnaire every morning after sleep processing**, 140–300+ selectable behaviours incl. alcohol, caffeine, medication | Yes, daily and unconditional | **NO — the question set is fixed and identical whether or not anything is anomalous** | [WHOOP](https://www.whoop.com/us/en/thelocker/the-whoop-journal/) |
| **WHOOP Coach** | n/a | Yes (chat); **My Memory** stores volunteered context | **Yes — "Proactive Check-Ins" (2026)**, e.g. suggesting sleep-timing changes based on travel | **NO** | [Wareable](https://www.wareable.com/wearable-tech/whoop-healthex-partnership-my-memory-ai-features-navigator-bands) |
| **WHOOP Health Monitor** | via Journal | No | No | **NO**. Wareable explicitly notes it lacks "allowing users to tag symptoms within the app" | [Wareable](https://www.wareable.com/wearable-tech/how-whoops-health-monitor-guided-me-through-a-nasty-bug) |
| **Apple Vitals** | No confounder log in Vitals | **No — it *tells* you possible factors** ("medications, elevation, alcohol intake, or even illness") | No | **NO. Apple names the exact confounders our project would ask about and chooses to state rather than ask.** | [Apple](https://support.apple.com/en-us/120142) |
| **Apple Health app** | Yes (manual logging categories) | No | No | **NO** | — |
| **Google Pixel Watch Loss of Pulse** | n/a | **Yes — an on-watch check-in prompt after detecting pulselessness** | **Yes, anomaly-triggered**, and escalates autonomously on no reply | **Structurally yes, but it is a 1-bit liveness check, not confounder disambiguation** | [Google](https://blog.google/feed/pixel-watch-3-loss-of-pulse-detection-fda/) |
| **Google Health Coach (Gemini)** | Yes | Yes (chat, onboarding, feedback loop for plan adaptation) | **UNVERIFIED** | **NO evidence** | [Google](https://blog.google/products-and-platforms/products/google-health/google-health-fitbit/) |
| **Samsung Health** | Yes (limited) | No | No | **NO** | — |
| **Garmin** | Yes (Health Snapshot is user-initiated) | No | No | **NO** | [Garmin](https://www.garmin.com/en-US/blog/health/top-10-features-to-monitor-your-health/) |
| **Withings Vitality Indicator** | Yes | No (sends notifications) | Notifications only | **NO** | [Withings PR](https://media.withings.com/press/press-releases/scanwatch-2/PR_ScanWatch2_US.pdf) |
| **Ultrahuman Jade** | Yes | Chat; **triggers actions** (breathwork, AFib check) | **Yes — acts on data in real time** | **NO — it acts rather than asks** | [Ultrahuman](https://cyborg.ultrahuman.com/press-releases/ultrahuman-unveils-ring-pro-with-category-defining-15-day-battery-and-jade-worlds-first-real-time-biointelligence-ai) |
| **Sahha (API/MCP)** | n/a | n/a — infrastructure | **Supports it: "Fire the agent on a webhook when a trend turns"** | **Enables it; does not implement it** | [sahha.ai](https://sahha.ai/solutions/ai/) |

### Verdict on the project premise

**The gap is REAL but must be stated precisely.** The defensible formulation is:

> No commercial wearable product conditions its questions on the anomaly it has just detected. Products either (a) ask nothing (Oura Symptom Radar, Apple Vitals, Withings, Samsung, Garmin), (b) ask the same fixed questionnaire every day regardless of state (WHOOP Journal), (c) ask questions only once the *user* has already volunteered a symptom (Oura×Counsel), or (d) act instead of asking (Ultrahuman Jade). Apple's Vitals notification is the sharpest illustration: it enumerates the exact confounders — medications, elevation, alcohol, illness — and then does not ask which one applies.

**Do NOT claim "commercial systems cannot ask questions."** That is now false and a reviewer will catch it.

---

## 6. User complaint evidence

**Reddit is unavailable to this agent (see section 0).** What follows is verified, quotable evidence from sources I could actually reach. This section is **weaker than the task required** and should be topped up manually from r/ouraring, r/whoop, r/AppleWatch and r/Garmin.

### 6.1 Confounders producing indistinguishable signals — alcohol

**This is the best-evidenced complaint category, and it validates the project premise directly.**

Quantified, peer-reviewed evidence from the largest real-world deployment study of a wearable respiratory-infection alarm ([Wearables-based respiratory infection detection in Northwell Health care workers, JMIR/PMC11292157](https://pmc.ncbi.nlm.nih.gov/articles/PMC11292157/)) — 577 enrolled, 470 completed, Fitbit Sense/Versa 3, Jan–Jul 2022:

> False alerts were attributed to **stress (16.0%), poor sleep (13.7%), intense exercise (9.7%), and alcohol consumption (6.0%)**.

Other numbers from the same study: **665 positive alerts generated; 23% not acted upon; positive predictive value 4%**; false-positive rate 2% per prediction day; SARS-CoV-2 detection 90% (28/31); all respiratory viruses 79% (63/80); **one participant received 8 false alerts out of 102 predictions**. Author conclusion: physiological changes from physical and emotional stress limit real-world performance, and **pairing with symptom tracking is recommended to improve specificity**. **That recommendation is, in essence, our project.**

Garmin's own official forum, on alcohol vs recovery — *["alcohol sleep and body battery", fenix 7 Series](https://forums.garmin.com/outdoor-recreation/outdoor-recreation/f/fenix-7-series/343820/alcohol-sleep-and-body-battery)*:

> **Farron:** "Because 5 h of sleep is clearly too little to let the body recover. In addition, there is the alcohol."

> **KrapfenKringel:** "Because it's odd to assume you're body recovers well if you poison it, and the watch seems to notice."

A first-person Oura Symptom Radar account — [Lord of the Smart Rings](https://www.lordofthesmartrings.com/oura-symptom-radar-am-i-getting-sick-and-what-actually-helps/):

> "Sometimes it's a false alarm, sometimes it's predicting where I'll be sleeping the next night"

(the accompanying embed makes the alcohol reference explicit), and:

> "it doesn't always nail the prediction, but it's a useful heads-up that something might be going on."

Apple, in its own support documentation, concedes the same class of confounding without acting on it — [Apple Support](https://support.apple.com/en-us/120142):

> "Factors such as your medications, elevation, alcohol intake, or even illness can impact your metrics."

### 6.2 Confounders — illness vs training vs stress, and unactionable floors

Garmin official forum, *["Illness and body battery"](https://forums.garmin.com/apps-software/mobile-apps-web/f/garmin-connect-mobile-ios/353140/illness-and-body-battery)*:

> **user 5510785:** "I have been sick for 2 days and body battery is stuck at 5. Why?"
> …
> **user 5510785:** "Of course! But why stuck at 5?"

The answer given is that 5 is the floor value; when HRV drops far enough the device registers no recovery at all. **The complaint is not that the device is wrong — it is that a saturated metric conveys no further information exactly when the user most needs it.** Design lesson: bounded scores lose resolution in the regime that matters.

Garmin's own documented behaviour, from the same forum threads: **Body Battery does not recharge while stress is above 25**, and nicotine, alcohol, late training, sickness and heart conditions all drive stress high. **One score, many causes, no disambiguation.**

### 6.3 Scores that contradict lived experience — Samsung

Samsung's official US community forum:

- *["Sleep timing causing inaccurate energy score"](https://us.community.samsung.com/t5/Galaxy-Watch/Sleep-timing-causing-inaccurate-energy-score/td-p/3131770)* — users report the watch's "ideal sleep window" of 11pm–2am conflicts with its own 7–9 hour recommendation, and that shift workers get a **sleep score of 99 alongside an energy score in the 50s**.
- *["Samsung Sleep score is not accurate"](https://us.community.samsung.com/t5/Galaxy-Watch/Samsung-Sleep-score-is-not-accurate/td-p/3568262)* — users report scores of "66 – Fair" after excellent sleep, with sub-metrics described as **"completely unreliable and useless"** and sleep graphs "all over the place."
- *["Moderate to vigorous exercise range is deadly"](https://us.community.samsung.com/t5/Galaxy-Watch/Moderate-to-vigorous-exercise-range-is-deadly/m-p/3444292/highlight/true)* — a user reports the MVPA range shifted from 121–146 bpm to 150–219 bpm and the app recommended up to 78 minutes at 219 bpm. **This is a live example of an unvalidated wellness recommendation producing dangerous advice.**
- *["Energy score and sleep scores"](https://eu.community.samsung.com/t5/galaxy-s25-series/energy-score-and-sleep-scores/td-p/12962468)* (EU forum).

### 6.4 Alert fatigue, health anxiety and abandonment

- **Alert burden as a first-class evaluation problem** — Ding, Guo, Rudin, Xiao, Nahab & Hu, *"Reconsideration on evaluation of machine learning models in continuous monitoring using wearables"*, [arXiv:2312.02300](https://arxiv.org/abs/2312.02300). Abstract: "…the complexities posed by real-world variability, disease dynamics, user-specific characteristics, and **the prevalence of false notifications**, necessitating novel evaluation strategies." **Cite this in our evaluation design — conventional AUC/accuracy is the wrong frame for a continuous alarm.**
- **Abandonment mechanics** — [Ignitec, "Predictive health wearables: what the hype got wrong"](https://www.ignitec.com/insights/predictive-health-wearables-what-the-hype-got-wrong/): users abandon wearables when alerts feel intrusive or ambiguous, insights lack actionable guidance, and monitoring becomes mentally exhausting; systems that demand constant attention train users to ignore them.
- **Health anxiety** — [MD+DI, "Are wearables making us sick with worry?"](https://www.mddionline.com/wearable-medical-devices/are-wearables-making-us-sick-with-worry-) (403 to fetcher; indexed summary): individuals with chronic conditions are especially vulnerable to health anxiety from inaccurate data.

### 6.5 Trust and marketing-accuracy complaints

- **Class action, filed 20 August 2026, N.D. Cal.** against Oura: alleges Oura marketed rings as "built for accuracy" with "unparalleled accuracy" in sleep-stage tracking and represented ~95% accuracy vs clinical sleep labs, when the true figure is nearer **50%**; cites a 2025 Nature-published study finding **~53% sleep-stage accuracy across 45 nights**, and Oura's own self-funded research acknowledging significant over/under-estimation of sleep stages. Oura: "We dispute the allegations in this complaint and intend to defend against them." ([TechCrunch](https://techcrunch.com/2026/08/21/oura-faces-lawsuit-accusing-it-of-misleading-consumers-about-sleep-tracking-accuracy/), [MobiHealthNews](https://www.mobihealthnews.com/news/oura-faces-class-action-lawsuit-over-sleep-tracking-accuracy), [MedCity News](https://medcitynews.com/2026/08/oura-wearable-ring-lawsuit/), [9News](https://www.9news.com/article/news/nation-world/class-action-lawsuit-accuses-oura-ring-overstating-sleep-tracking-accuracy/507-04d45f43-863c-4d6f-bb05-09f65f1052ea))
- **Consumer reviews** — Trustpilot ([ouraring.com](https://www.trustpilot.com/review/ouraring.com)) and BBB ([Oura Ring profile](https://www.bbb.org/us/ca/san-francisco/profile/jewelry-designers/oura-ring-1116-928639/customer-reviews)) show recurring complaints about mandatory subscription, connectivity failures, warranty/claims friction, and finish durability. **These are product complaints, not algorithm complaints — the algorithm complaints live on Reddit, which I could not reach.**

### 6.6 Systematic evidence that the whole category is under-evidenced

[PLOS Digital Health umbrella review, "Can consumer wearables support outpatient health monitoring for patients with post-acute infection syndromes?"](https://journals.plos.org/digitalhealth/article?id=10.1371%2Fjournal.pdig.0001124) — 42 reviews, 30+ brands, 150+ device series, ~397 primary studies:

- Reviews met only **~44% of applicable AMSTAR 2.0 criteria** on average (6.14 of 16).
- Heart rate and AFib are the only well-evidenced measures; **energy expenditure errors exceed 200%** in some populations; **sleep metrics are highly inconsistent**; for SpO2 and EDA "no device-level information about accuracy was found."
- **"None of the 42 reviews were found to report on adverse events."**
- Race/ethnicity examined in only 7% of reviews (3 of 42).
- Authors' conclusion: **"There is not sufficient evidence to recommend the use of consumer wearables for self-monitoring."**

---

## 7. Comparison table

| | Oura Symptom Radar | WHOOP Health Monitor | Apple Vitals | Withings Vitality Indicator | Samsung Energy Score | Garmin Body Battery | Ultrahuman Jade |
|---|---|---|---|---|---|---|---|
| **Purpose** | Illness pre-warning | Metric deviation display | Overnight outlier alert | Illness/fatigue prediction | Daily readiness | Continuous energy | Real-time agent |
| **Signals** | Temp, RR, RHR, HRV, inactivity (+cycle, demographics) | RHR, RR, skin temp, HRV, SpO2 | HR, RR, wrist temp, SpO2, sleep duration | HRV, activity, temp, SpO2, RR, sleep (35 params) | Sleep, HR, HRV, activity | HRV, stress, activity, sleep | Ring + CGM + 120 blood bioreviewers + environment |
| **Baseline requirement** | 7 nights in last 14 | ~14 days | 7 nights | not disclosed | not disclosed | continuous | not disclosed |
| **Model disclosed?** | No ("ML", 3M training tags, on-device) | No (2020 research model was gradient boosting, 21-day baseline) | No | No | No | Firstbeat physiology models | No |
| **Cadence** | Overnight batch, morning card | Overnight batch, morning | Overnight batch, morning notification | Notifications | Morning | **Continuous** | **Real-time** |
| **Output** | No / Minor / Major signs | Green check / orange / red exclamation per metric | Typical / Outlier per metric + morning notification | Energy notifications | 0–100 | 0–100 (floors at 5) | Guidance + triggered actions |
| **Alert trigger rule** | Not disclosed | Not disclosed | **2+ metrics outlier same night** | Not disclosed | n/a | n/a | Not disclosed |
| **LLM alongside?** | Advisor (+ women's-health LLM) | Coach (GPT-4, fine-tuned) | None shipped (Mulberry scaled back) | None | Galaxy AI | None | Jade |
| **Agentic?** | No | Partial (plan building, memory, proactive check-ins) | No | No | No | No | **Yes (triggers actions)** |
| **Asks about confounders?** | **No** | Fixed daily journal only | **No — states them** | **No** | **No** | **No** | **No** |
| **Published validation?** | **None** | COVID model only (PLOS ONE 2020) | **None** | **None** | **None** (sleep apnea is separate) | **None** | **None** |
| **Regulatory** | Wellness | Wellness (ECG separately cleared) | Wellness (other features cleared) | Wellness | Wellness (sleep apnea separately De Novo) | Wellness | Wellness (AFib via FibriCheck) |
| **Reusable API** | Oura API v2 | developer.whoop.com | HealthKit | Withings API | Health Connect / Samsung SDK | Garmin Health API | limited |

---

## 8. Marketing versus demonstrated capability

| Claim as marketed | Actual evidentiary status |
|---|---|
| Oura: Symptom Radar detects "early signs of common respiratory illnesses — like a cold or the flu" | **MARKETING.** No published sensitivity, specificity, PPV or AUC. Ground truth in internal validation is a **self-selected app tag**, not a clinical diagnosis. Oura's head of science concedes false positives and negatives. |
| Oura: "analyzing over 40 biometrics" / "50+ wellness metrics" | **MARKETING.** A count of tracked signals, not model features. Do not restate as an architectural fact. |
| Oura: "validated with UCSF over two years of anonymized member data" | **MARKETING with a VALIDATED ancestor.** TemPredict is a real, published, >63,000-participant study ([Sci Rep 2022](https://www.nature.com/articles/s41598-022-07314-0)) — but it validated an earlier COVID/fever model, not the shipped Symptom Radar. |
| Oura: "76% pre-symptomatic fever detection" | **VALIDATED but misapplied.** It is a 2020 TemPredict fever result, routinely quoted as if it were Symptom Radar's performance. |
| WHOOP: "20% pre-symptomatic, 80% by day 3" | **VALIDATED (peer-reviewed, PLOS ONE 2020), but narrow:** COVID-19 only, symptomatic cases only, n=57 train / 24+190 validation, no specificity reported, and not the shipped Health Monitor algorithm. |
| WHOOP: ">90% specificity for lower airway infection" | **NOT FOUND ANYWHERE. Treat as fabricated.** |
| WHOOP: "medical-grade health & performance insights" | **The FDA specifically cited this phrasing as evidence of diagnostic intent** in the July 2025 warning letter. ([FDA Group analysis](https://insider.thefdagroup.com/p/fda-warning-letter-breakdown-whoop)) |
| WHOOP: respiratory-rate accuracy within 1 breath/min | **VALIDATED** (third-party, *J Clin Sleep Med*) — but this validates *measurement*, not *inference*. **Exact citation UNVERIFIED.** |
| Apple: Vitals flags when "something may be off" | **DISCLOSED rule (2-of-5 outliers), no validation.** No study, no clearance. |
| Withings: "detect early changes in health status — from signs of impending illness" | **MARKETING.** Zero published evidence. |
| Samsung/Garmin readiness and energy scores | **MARKETING.** No published validation; Samsung's own forum documents systematic user disagreement. |
| Ultrahuman Jade: "world's first real-time biointelligence AI" that will order food and change room temperature | **MARKETING/roadmap.** Shipped actions are breathwork and initiating an AFib check. |
| Oura Advisor: "83% of beta testers found answers reliable" | **MARKETING.** Self-reported beta survey, no methodology, no benchmark, no adversarial testing. |
| Google: Gemini health coach "backed by science" | **MARKETING.** No evaluation published. |
| Any wearable sleep-stage accuracy claim | **Actively contested in court.** Independent evidence puts Oura sleep-staging near 53%. ([TechCrunch](https://techcrunch.com/2026/08/21/oura-faces-lawsuit-accusing-it-of-misleading-consumers-about-sleep-tracking-accuracy/)) |

### The one honest number in the industry

Everything above is either unvalidated or validated on a proxy label. **The only credible real-world performance figure for a wearable illness alarm is the independent Northwell study: 90% detection of PCR-confirmed SARS-CoV-2, 79% across all respiratory viruses, and a positive predictive value of 4% with 665 alerts across 470 people.** ([PMC11292157](https://pmc.ncbi.nlm.nih.gov/articles/PMC11292157/)) A 4% PPV means **24 of every 25 alerts are wrong**. This is the number our project should be benchmarked against, and it is the strongest possible argument for confounder disambiguation: the false alerts had *identifiable, askable causes* — stress, poor sleep, exercise, alcohol — accounting for **45.4%** of them.

---

## 9. Bibliography

### Oura
- Symptom Radar launch blog — https://ouraring.com/blog/symptom-radar/
- Symptom Radar support (tier wording, requirements, disclaimers) — https://support.ouraring.com/hc/en-us/articles/35593651188115-Symptom-Radar
- Inside the Ring: Developing Symptom Radar (engineering) — https://ouraring.com/blog/inside-the-ring-symptom-radar/
- Health Radar support — https://support.ouraring.com/hc/en-us/articles/52627030482707-Health-Radar
- Introducing Health Radar — https://ouraring.com/blog/introducing-health-radar/
- Oura Advisor blog — https://ouraring.com/blog/oura-advisor/
- Oura Advisor support — https://support.ouraring.com/hc/en-us/articles/39512345699219-Oura-Advisor
- Oura × Counsel Health — https://ouraring.com/blog/counsel-integration-oura-app/
- Counsel Health partnership post — https://www.counselhealth.com/blog/introducing-a-new-era-of-care-our-partnership-with-oura
- Oura on the Jan 2026 FDA guidance — https://ouraring.com/blog/new-fda-guidance/
- Oura Labs launch — https://www.businesswire.com/news/home/20240403398484/en/URA-Introduces-Oura-Labs-A-New-In-App-Innovation-Hub-for-Members
- Oura Ring 5 announcement — https://www.businesswire.com/news/home/20260528686853/en/URA-Introduces-The-Worlds-Smallest-Smart-Ring-Oura-Ring-5
- Oura Ring 5, TechCrunch — https://techcrunch.com/2026/05/28/oura-unveils-its-ring-5-with-a-thinner-lighter-design-starting-at-399/
- Oura women's-health LLM, TechCrunch — https://techcrunch.com/2026/02/24/oura-launches-a-proprietary-ai-model-focused-on-womens-health/
- TemPredict: Detection of COVID-19 using multimodal data from a wearable device, *Sci Rep* 2022 — https://www.nature.com/articles/s41598-022-07314-0
- Engadget on Symptom Radar rollout (Patel quote) — https://www.engadget.com/wearables/oura-is-rolling-out-its-sickness-detection-feature-to-ring-gen-3-and-ring-4-users-155820702.html
- Wareable on Symptom Radar launch — https://www.wareable.com/wearable-tech/oura-symptom-radar-launch
- Oura BP FDA-clearance intent, MedTech Dive — https://www.medtechdive.com/news/oura-fda-clearance-smart-ring-blood-pressure/803181/
- Oura adds BP after FDA policy change, MedTech Dive — https://www.medtechdive.com/news/oura-to-add-blood-pressure-feature-following-fda-policy-change/821427/
- Oura class action, TechCrunch — https://techcrunch.com/2026/08/21/oura-faces-lawsuit-accusing-it-of-misleading-consumers-about-sleep-tracking-accuracy/
- Oura class action, MobiHealthNews — https://www.mobihealthnews.com/news/oura-faces-class-action-lawsuit-over-sleep-tracking-accuracy
- Oura class action analysis, MedCity News — https://medcitynews.com/2026/08/oura-wearable-ring-lawsuit/
- First-person Symptom Radar account — https://www.lordofthesmartrings.com/oura-symptom-radar-am-i-getting-sick-and-what-actually-helps/
- Tech Advisor, "I should have listened" — https://www.techadvisor.com/article/2575433/oura-symptom-radar-i-should-have-listened-to-new-smart-ring-feature.html
- Oura Trustpilot — https://www.trustpilot.com/review/ouraring.com
- Oura BBB reviews — https://www.bbb.org/us/ca/san-francisco/profile/jewelry-designers/oura-ring-1116-928639/customer-reviews

### WHOOP
- Miller et al., "Analyzing changes in respiratory rate to predict the risk of COVID-19 infection," *PLOS ONE* 2020 — https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0243693
- WHOOP COVID algorithm press release, June 2020 — https://www.prnewswire.com/news-releases/whoop-leverages-respiratory-rate-technology-to-predict-covid-19-301081096.html
- WHOOP Health Monitor feature page — https://www.whoop.com/us/en/thelocker/health-monitor-feature/
- WHOOP Health Monitor & Report support — https://support.whoop.com/s/article/WHOOP-Health-Monitor-Report
- WHOOP Journal — https://www.whoop.com/us/en/thelocker/the-whoop-journal/
- WHOOP Coach powered by OpenAI — https://www.whoop.com/us/en/thelocker/whoop-unveils-the-new-whoop-coach-powered-by-openai/
- OpenAI customer story: WHOOP — https://openai.com/index/whoop/
- Wareable, WHOOP GPT-4 coach hands-on — https://www.wareable.com/wearable-tech/whoop-launches-gpt-4-ai-coach
- Wareable, WHOOP 2026 AI features / HealthEx / My Memory — https://www.wareable.com/wearable-tech/whoop-healthex-partnership-my-memory-ai-features-navigator-bands
- Wareable, "How Whoop's Health Monitor guided me through a nasty bug" — https://www.wareable.com/wearable-tech/how-whoops-health-monitor-guided-me-through-a-nasty-bug
- SiliconANGLE, WHOOP agentic AI on Snowflake — https://siliconangle.com/2026/06/03/agentic-ai-maturity-whoop-snowflake-ai-scaling-snowflakesummit/
- WHOOP 5.0 / MG press — https://www.whoop.com/us/en/press-center/whoop-unveils-5.0-MG/
- WHOOP MG ECG 510(k) K243236 — https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K243236 · summary PDF https://www.accessdata.fda.gov/cdrh_docs/pdf24/K243236.pdf
- FDA warning letter to WHOOP, 14 Jul 2025 — https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/whoop-inc-709755-07142025
- FDA Group breakdown of the warning letter — https://insider.thefdagroup.com/p/fda-warning-letter-breakdown-whoop
- FDA closes warning letter, Healthcare Dive — https://www.healthcaredive.com/news/fda-drops-whoop-warning-letter-over-blood-pressure-feature/823737/
- FDA drops enforcement, STAT — https://www.statnews.com/2026/06/23/fda-drops-enforcement-against-wearable-maker-whoop/
- MassDevice on the closeout — https://www.massdevice.com/fda-closes-warning-letter-whoop-blood-pressure/
- WHOOP Advanced Labs launch — https://www.businesswire.com/news/home/20250930178710/en/WHOOP-Launches-Clinician-Reviewed-Advanced-Labs-Unlocking-a-Comprehensive-View-of-Human-Health
- Quest Diagnostics newsroom — https://newsroom.questdiagnostics.com/2025-09-30-WHOOP-Launches-Clinician-Reviewed-Advanced-Labs,-Unlocking-a-Comprehensive-View-of-Human-Health
- Advanced Labs UAE — https://www.businesswire.com/news/home/20260211439032/en/WHOOP-Launches-Advanced-Labs-in-the-UAE-with-Diagnostic-Partner-Unilabs-Delivering-A-Comprehensive-View-of-Health-For-Members
- WHOOP developer docs — https://developer.whoop.com/docs/whoop-101/

### Apple
- Track your overnight vitals with Apple Watch — https://support.apple.com/en-us/120142
- Apple Watch User Guide, Vitals — https://support.apple.com/guide/watch/vitals-apd15aa7ed96/watchos
- Apple Newsroom, groundbreaking health features (sleep apnea) — https://www.apple.com/newsroom/2024/09/apple-introduces-groundbreaking-health-features/
- Irregular Rhythm Notification De Novo DEN180042 — https://www.accessdata.fda.gov/cdrh_docs/pdf18/DEN180042.pdf
- Sleep Apnea 510(k) K240929 — https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K240929 · PDF https://www.accessdata.fda.gov/cdrh_docs/pdf24/K240929.pdf
- Hypertension Notification 510(k) K250507 — https://www.accessdata.fda.gov/cdrh_docs/pdf25/K250507.pdf
- MobiHealthNews on hypertension clearance — https://www.mobihealthnews.com/news/apple-receives-fda-nod-hypertension-notification-feature
- AFib History MDDT qualification — https://www.fda.gov/media/178230/download
- Fierce Biotech on AFib History — https://www.fiercebiotech.com/medtech/apple-watchs-afib-history-feature-ripens-fda-clearance
- Project Mulberry scaled back, Business Standard — https://www.business-standard.com/technology/tech-news/apple-ai-health-coach-shelved-project-mulberry-features-arrive-updates-126020601028_1.html
- 9to5Mac on Mulberry delays — https://9to5mac.com/2026/05/24/apple-improving-heart-rate-tracking-in-watchos-27-mulberry-health-coach-delays/
- 9to5Mac, Aug 2026 status — https://9to5mac.com/2026/08/29/apple-health-revamp-ai-coach-new-apple-watch-next-month/
- XDA guide to Vitals — https://www.xda-developers.com/guide-to-the-vitals-app-in-watchos-11/
- Wareable on Vitals — https://www.wareable.com/apple/how-vitals-app-finally-makes-apple-watch-a-wellness-powerhouse

### Samsung
- Sleep Apnea De Novo DEN230041 decision summary — https://www.accessdata.fda.gov/cdrh_docs/reviews/DEN230041.pdf
- Samsung Newsroom, FDA authorisation — https://news.samsung.com/global/samsungs-sleep-apnea-feature-on-galaxy-watch-first-of-its-kind-cleared-by-us-fda
- MedTech Dive on the De Novo — https://www.medtechdive.com/news/samsung-fda-watch-sleep-apnea/707335/
- Antioxidant Index development — https://news.samsung.com/global/the-era-of-healthy-aging-%E2%91%A1-a-health-check-in-five-seconds-inside-the-development-of-galaxy-watch8-series-antioxidant-index
- One UI 8 Watch features — https://news.samsung.com/global/new-features-on-one-ui-8-watch-help-users-build-healthier-habits
- World Sleep Day 2026 study — https://www.samsungmobilepress.com/articles/samsung-sleep-apnea-study-for-world-sleep-day-2026
- One UI 9 Watch overview, SamMobile — https://www.sammobile.com/news/samsung-one-ui-9-watch-everything-to-know/
- Samsung illness-warning report (secondary, unconfirmed) — https://www.explosion.com/205347/samsung-galaxy-watches-can-now-warn-you-before-you-get-sick/
- Community: inaccurate energy score — https://us.community.samsung.com/t5/Galaxy-Watch/Sleep-timing-causing-inaccurate-energy-score/td-p/3131770
- Community: sleep score not accurate — https://us.community.samsung.com/t5/Galaxy-Watch/Samsung-Sleep-score-is-not-accurate/td-p/3568262
- Community: MVPA range complaint — https://us.community.samsung.com/t5/Galaxy-Watch/Moderate-to-vigorous-exercise-range-is-deadly/m-p/3444292/highlight/true
- EU community: energy and sleep scores — https://eu.community.samsung.com/t5/galaxy-s25-series/energy-score-and-sleep-scores/td-p/12962468

### Fitbit / Google
- Google Health app + Fitbit Air launch — https://blog.google/products-and-platforms/products/google-health/google-health-fitbit/
- $9.99 AI health coach launches 19 May 2026, TechCrunch — https://techcrunch.com/2026/05/07/googles-9-99-per-month-ai-health-coach-launches-may-19/
- Personal health coach preview — https://blog.google/products-and-platforms/devices/fitbit/fitbit-ai-personal-health-coach-preview/
- MobiHealthNews on the Gemini coach — https://www.mobihealthnews.com/news/google-debuts-gemini-powered-ai-health-coach-fitbit-and-pixel-watch-users
- Readiness score help — https://support.google.com/fitbit/answer/14236710
- DC Rainmaker, Daily Readiness teardown — https://www.dcrainmaker.com/2021/11/fitbit-readiness-review.html
- Irregular heart rhythm notifications — https://blog.google/products-and-platforms/devices/fitbit/irregular-heart-rhythm-notifications/
- AASM on the Fitbit AFib clearance — https://aasm.org/fda-clears-fitbit-feature-to-detect-a-fib/
- Healio on the Fitbit AF algorithm — https://www.healio.com/news/cardiology/20220411/fitbit-receives-fda-clearance-for-algorithm-to-detect-af
- Loss of Pulse Detection FDA clearance — https://blog.google/feed/pixel-watch-3-loss-of-pulse-detection-fda/
- Engadget on Loss of Pulse — https://www.engadget.com/wearables/pixel-watch-3-receives-fda-clearance-for-loss-of-pulse-detection-210458883.html

### Garmin
- Top 10 health monitoring features — https://www.garmin.com/en-US/blog/health/top-10-features-to-monitor-your-health/
- Sleep Coach technology — https://www.garmin.com/en-US/garmin-technology/health-science/sleep-coach/
- Forum: illness and body battery — https://forums.garmin.com/apps-software/mobile-apps-web/f/garmin-connect-mobile-ios/353140/illness-and-body-battery
- Forum: alcohol, sleep and body battery — https://forums.garmin.com/outdoor-recreation/outdoor-recreation/f/fenix-7-series/343820/alcohol-sleep-and-body-battery
- Index Sleep Monitor launch — https://www.tomsguide.com/wellness/sleep-tech/garmin-launches-new-index-sleep-monitor-for-screenless-sleep-tracking

### Withings, Polar, Circular, Ultrahuman, Bevel
- Withings ScanWatch 2 / HealthSense 4 press release — https://media.withings.com/press/press-releases/scanwatch-2/PR_ScanWatch2_US.pdf
- Android Police on HealthSense 4 — https://www.androidpolice.com/withings-scanwatch-2-advanced-ai-health-monitoring/
- BigGo on the Vitality Indicator — https://biggo.com/news/202509052122_Withings_ScanWatch_2_AI_Health_Prediction
- Gadgets & Wearables on HealthSense 4 — https://gadgetsandwearables.com/2025/09/16/healthsense-4-withings/
- Withings Body Scan 2 — https://www.prnewswire.com/news-releases/withings-redefines-preventive-health-with-body-scan-2-the-worlds-first-science-backed-longevity-station-302652358.html
- Polar Nightly Recharge — https://www.polar.com/us-en/smart-coaching/nightly-recharge · manual https://support.polar.com/us-en/nightly-recharge-recovery-measurement
- Circular Ring 2, TechCrunch — https://techcrunch.com/2025/01/05/circular-unveils-its-next-gen-ring-2-with-ecg-functionality-and-afib-detection-at-ces-2025
- Circular Ring 2, Techlicious — https://www.techlicious.com/blog/circular-ring-2-ces-2025/
- Ultrahuman Ring PRO + Jade press release — https://cyborg.ultrahuman.com/press-releases/ultrahuman-unveils-ring-pro-with-category-defining-15-day-battery-and-jade-worlds-first-real-time-biointelligence-ai
- FutureFive on Ring PRO and Jade — https://futurefive.com.au/story/ultrahuman-unveils-ring-pro-jade-ai-health-coach
- Digital Health News on Jade — https://www.digitalhealthnews.com/ultrahuman-launches-ring-pro-with-real-time-biointelligence-ai-jade
- Wellworthy hands-on with Jade — https://wellworthy.com/ultrahuman-just-launched-its-most-advanced-ring-yet-alongside-an-ai-that-acts-on-your-health-data-in-real-time/
- Ultrahuman AFib via FibriCheck, TechCrunch — https://techcrunch.com/2024/07/16/ultrahumans-smart-ring-gets-fda-approved-afib-detection
- Medical Device Network on Ultrahuman AFib — https://www.medicaldevice-network.com/news/ultrahuman-adds-afib-detection-feature-to-ring-air-smart-ring/
- Ultrahuman US import ban and return — https://the-gadgeteer.com/2026/03/25/ultrahumans-banned-smart-ring-is-back-with-a-point-to-prove/
- Bevel — https://www.bevel.health/ · Series A https://techcrunch.com/2025/10/30/bevel-raises-10m-series-a-from-general-catalyst-for-its-ai-health-companion

### Platforms, APIs, RPM
- Sahha AI agents / MCP server — https://sahha.ai/solutions/ai/
- Open Wearables API comparison — https://www.openwearables.io/compare
- Sahha vs Terra (vendor-authored) — https://sahha.ai/compare/terra-alternatives/
- Sahha vs Spike (vendor-authored) — https://sahha.ai/compare/spike-api-alternatives/
- Empatica cardiac digital biomarker clearance — https://www.empatica.com/blog/empatica-receives-new-fda-clearance-for-cardiac-digital-bioreviewers/
- Empatica platform clearance + Series B — https://www.prnewswire.com/news-releases/empatica-receives-new-fda-clearance-for-its-health-monitoring-platform-and-announces-series-b-financing-301685344.html
- Biobeat additional vital signs clearance — https://www.prnewswire.com/news-releases/fda-clears-the-biobeat-remote-patient-monitoring-device-and-platform-for-additional-vital-signs-301511494.html
- Biobeat stroke volume / cardiac output clearances — https://www.prnewswire.com/news-releases/biobeat-remote-patient-monitoring-devices-and-platform-receive-additional-fda-clearances-for-stroke-volume-and-cardiac-output-301715553.html
- Current Health FDA clearance — https://www.biospace.com/current-health-receives-fda-clearance-for-its-remote-patient-monitoring-solution-enables-earlier-intervention-and-improved-patient-outcomes
- Evidation WAVE study — https://clinicaltrials.gov/study/NCT06207929

### Independent evidence, validation and critique
- Detection of common respiratory infections incl. COVID-19 using consumer wearables in health care workers (Northwell, Fitbit) — https://pmc.ncbi.nlm.nih.gov/articles/PMC11292157/
- Grzesiak et al., "Assessment of the feasibility of using noninvasive wearable biometric monitoring sensors to detect influenza and the common cold before symptom onset," *JAMA Netw Open* 2021 — https://pubmed.ncbi.nlm.nih.gov/34586364/ · full text https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8482058/ · DOI https://dx.doi.org/10.1001/jamanetworkopen.2021.28534
- PLOS Digital Health umbrella review of consumer wearables — https://journals.plos.org/digitalhealth/article?id=10.1371%2Fjournal.pdig.0001124
- Ding, Guo, Rudin, Xiao, Nahab, Hu, "Reconsideration on evaluation of ML models in continuous monitoring using wearables" — https://arxiv.org/abs/2312.02300
- Lancet Digital Health, ML prediction of systemic inflammatory response after live attenuated influenza vaccine using multimodal wearables — https://www.thelancet.com/journals/landig/article/PIIS2589-7500(25)00068-8/fulltext
- Ignitec, "Predictive health wearables: what the hype got wrong" — https://www.ignitec.com/insights/predictive-health-wearables-what-the-hype-got-wrong/
- MD+DI, "Are wearables making us sick with worry?" — https://www.mddionline.com/wearable-medical-devices/are-wearables-making-us-sick-with-worry-

---

## 10. Open gaps for a human to close

1. **Reddit evidence (r/ouraring, r/whoop, r/AppleWatch, r/Garmin).** Blocked to this agent. Highest-value missing input.
2. **App Store / Play Store review mining** for Oura, WHOOP, Fitbit/Google Health, Withings.
3. **Exact citation for WHOOP's *J Clin Sleep Med* respiratory-rate validation** (DOI).
4. **Confirmation that Samsung shipped a "Vitals" overnight illness screen in One UI 9 Watch** against a Samsung primary source.
5. **K-numbers** for Fitbit's 2022 PPG AFib clearance, Google's Loss of Pulse De Novo, and Circular Ring 2.
6. **Whether Oura's API exposes Symptom Radar output** (relevant if we want to build on top of Oura rather than raw signals).
7. **Evidation Health, CareEvolution/myDataHelps, Huma, Athlytic, Train Fitness** — not researched; search budget exhausted.
8. **Screenshot-level capture** of the exact Apple Vitals notification string and the exact Oura Symptom Radar card.
