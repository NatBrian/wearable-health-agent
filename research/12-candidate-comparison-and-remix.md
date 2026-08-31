# 12. Honest Comparison with the Archived Candidates, and a Remixed Set

**Status:** Phase 4b. Brainstorming input. No decision made.
**Date:** 2026-08-30
**Purpose:** The author judged the archived (lower-capability) candidate set more interesting and more novel than mine. That judgement is substantially right, and the reason matters. This document says why, then rebuilds.

---

## Part 1: The two sets, side by side

| Their candidate | My equivalent | Verdict |
|---|---|---|
| 1. Passive wearable illness early warning | C1 The original | Same. Both included it as a deliberately weak baseline |
| 2. Active-Disambiguation Anomaly Triage & Confounder Resolution Agent | C2 Confounder-resolving triage with ask policy | **Same idea.** They named it better |
| 3. Proactive Athletic Strain, Recovery & Overtraining Prevention | **(missing from mine)** | **They win a category I did not consider** |
| 4. Sleep Architecture Disruption & Circadian Phase Realignment | **(missing from mine)** | **They win a second category** |
| 5. Multimodal Sensor Conflict Resolution & Data Quality Auditor | C5 Refusal-first monitoring | Same. Mine reframed it around abstention |
| 6. Chronic Disease Flare / Long-COVID Tracker | C7 Chronic-condition pacing | Same |
| 7. Post-Vaccination & Medication Reactogenicity Tracker | C3 Known-event response + unexplained residual | **Mine generalises theirs.** They tracked one event type; mine keeps a ledger of all known events and alarms on the residual |
| 8. Unified "Biomarker Sentry" | My "combination worth considering" | Same conclusion, but they gave it a name and I did not |
| - | C4 Interruption policy as contribution | Mine only |
| - | C6 Return-to-baseline recovery | Mine only |
| - | C8 Cycle-aware baselines | Mine only |
| - | C9 Benchmark and harness | Mine only |
| - | C10 Care-team escalation triage | Mine only |

**The idea space overlaps by roughly 70%.** I produced five they did not, they produced two I did not. So the gap in how the two documents *feel* is not really a gap in ideas.

---

## Part 2: Why theirs reads better, and it is not the content

Four concrete differences, all of them presentational, all of them real.

**1. They named things.** "Biomarker Sentry" versus "Candidate 2". A project needs a name you want to say out loud. Mine had none, and that is a genuine failure, not a stylistic quibble. You cannot get excited about C2.

**2. They led with capability; I led with caveats.** Every one of my candidates put the failure mode in the reader's face immediately. That is correct for choosing and corrosive for imagining. Their candidate 8 reads like a product pitch; my candidate 2 reads like a risk register.

**3. They were decisive.** Scores, medals, a top recommendation, a final strategic verdict. I explicitly refused to average subjective scores, and I was right on the method and wrong on the effect: I removed the decisiveness without replacing the energy.

**4. They were maximalist.** Candidate 8 promises uncertainty-aware inference, active disambiguation, foundation models, code execution and grounded RAG in one system. That is thrilling to read. I kept trimming toward what I could defend.

---

## Part 3: Where mine is genuinely better, and it matters

Not defensiveness. These are the specific places where following their document would cause real damage.

**1. Their flagship cannot run on the hardware.** Candidate 8's core is the "biophysical triad": cardiac plus **thermal** plus **respiratory**. The Samsung Health Data SDK exposes **no HRV type and no respiratory-rate type**, and Samsung Health does not write HRV, breathing rate or resting HR into Health Connect. The Galaxy Watch gives us heart rate, sleep and activity. **Their flagship's central mechanism is not implementable on the author's watch.** This is the single most important correction.

**2. Their numbers are partly invented.** NightSignal's real sensitivities are 80/72/69, not the 78/54/44 they state. "0.3 false alerts per user-week" appears in no paper. TemPredict's "51 plus or minus 12 hours" does not exist. WHOOP's ">90% specificity" appears nowhere in the cited paper. Oura's "balanced random forest with 40-feature strain matrix" was never disclosed by Oura. Building a pitch on these means the pitch collapses when a reviewer checks one.

**3. Their ranking did not rank.** Candidate 8 is defined as containing candidates 2, 7 and 1, and then wins. A method that selects the union of the options is not selecting. Their own table is also internally inconsistent: candidate 6 scores 7.2 and is ranked 8th, below three candidates scoring 5.5.

**4. My C3 is a real improvement on their C7.** They tracked reactogenicity after a vaccine. Generalising to a ledger of *all* known events, and alarming only on the residual that nothing explains, is a better formulation and it makes the project testable in two weeks because you can trigger events deliberately.

**Summary: take their framing and ambition, keep my facts and hardware reality.**

---

## Part 4: The reframe I got wrong

The author's stated purpose was: *"the reason I asked you to conduct research using subagents is to learn products that already in production and proven reliable, so the project we are making is novel and feasible."*

I used the research as a **filter** (what can I defend?) instead of as a **parts catalogue** (what already works that we can borrow and twist?). That is the actual error behind the boring candidates. Below is the catalogue.

### Proven, in-production parts worth stealing

| Part | Who shipped it | Why it is worth taking |
|---|---|---|
| **Ask the user, then escalate autonomously if they do not answer** | **Google Loss of Pulse Detection**, FDA-cleared Feb 2025 | The only shipped wearable feature that responds to an anomaly by *asking* and then acting alone on silence. A regulator-approved agentic escalation pattern, never applied to illness |
| **Order a confirmatory measurement instead of giving advice** | **Ultrahuman "Jade"** | When it sees something, it triggers an AFib check rather than talking. **This is the best single idea in the whole catalogue.** It gives an agent a real physical action |
| **LLM writes and runs code over your own health data** | **Google PHIA**, Nature Communications 2026, open code, 84% versus 74% | Proven, published, reusable. But it is purely reactive: it only answers questions you ask |
| **Statistical triggers gate LLM wakeups** | **HiMe**, open source | 49x to 121x token savings. Under a free API tier this is what makes the project run at all |
| **A visible avatar that reflects your physiological state** | **HiMe** ("HiMeow") | Slightly silly, extremely memorable in a demo |
| **Three-tier illness output** | **Oura Symptom Radar** | Proven output format: no signs / minor signs / major signs. It just never says why |
| **Concordance rule: alert only if 2 of 5 metrics are outliers** | **Apple Vitals** | Elegant, silent, zero user burden. Any asking policy must beat this |
| **Adaptive questioning that stops early** | **PROMIS / CAT**, deployed across healthcare | 22 of 60 items for the same answer. FAMCAT, FRIDA at r = 0.94 to 0.97. Proven machinery, never pointed at a wearable |
| **Deterministic 6-state automaton on overnight resting HR** | **Stanford NightSignal**, Apache-2.0, deployed n=3,318 | Free, under 100 lines, 80% sensitivity, 3-day median lead. Borrow wholesale |
| **Wearable data exposed as agent tools with webhook triggering** | **Sahha MCP server** | "Fire the agent when a trend turns" as infrastructure |
| **LLM question plus Bayesian update** | **Project Hermes** (preprint) | False positives 61.7% to 12.5% at 89% sensitivity. Unread, and a blocking read |

---

## Part 5: The remixed candidates

Named. Confident. Built only on channels the Galaxy Watch actually provides (nocturnal heart rate, sleep, activity), plus what the user tells us.

---

### R1. **Morning Rounds** - the agent that can order a test

**The pitch.** Every morning the agent does what a doctor doing ward rounds does. It reviews the night, forms hypotheses, checks your own history for similar past nights, and when it is unsure it does two things nothing else does: it **interviews you adaptively**, and it **orders a measurement**. "Your resting heart rate has been up 7 bpm for three nights. Take a one-minute reading on your watch now." It then re-reasons on the new evidence, argues against its own conclusion, and gives you a tiered verdict with sources and an action, escalating to a doctor on red flags.

**The twist, stated plainly.** Every wearable product either measures passively or chats. **None of them can order a test.** Ultrahuman proved the pattern works by triggering AFib checks. Google proved the escalate-on-silence pattern is approvable. Nobody has combined them for illness. The agent's action space becomes *observe, ask, order a test, escalate*, which is a clinician's loop, not a chatbot's.

**Where each technology does real work.** Pretrained model forecasts the expected night. Statistical detector gates everything so the LLM sleeps. The LLM runs the adaptive interview, extracts symptoms, and writes the explanation. The **agent** chooses between staying silent, asking, ordering a measurement, and escalating, and holds state across nights while it waits. **RAG** grounds the differential, because naming any condition is only defensible if every claim is source-linked.

**Feasible on the hardware?** Yes. Galaxy Watch supports on-demand spot measurements. Detection needs only heart rate and sleep.
**Demo value:** highest of anything here. Watching an agent decide to order a test, receive the result, and change its mind is memorable.
**Risk:** the measurement round-trip must work live. Mitigate with replay.

---

### R2. **Sick or Wrecked?** - separating illness from overtraining

**The pitch.** Your recovery score is low. WHOOP and Garmin will tell you that. **Neither will tell you whether it is because you trained hard or because you are getting ill**, and those two demand opposite responses: train through it, or stop and rest. The agent resolves which.

**Why this is better than the archived candidate 3.** They framed it as generic training-readiness coaching and correctly called that commercially saturated. The saturated part is the *score*. The **discrimination problem is unsolved and nobody ships it**, and the evidence says why it is hard: maximal strain 0 to 2 hours before sleep produces +5.94 bpm and -17.02 ms rMSSD, while acute infection produces only +1.1 to +2.1 bpm. **The confounder is bigger than the signal.**

**The twist.** Two causes, opposite advice, identical sensor signature. Genuinely useful and immediately legible to any athlete on a hiring panel.

**Where the technologies work.** Exercise data gives a partly-separable prior (the watch already knows you trained). The agent asks only for what the sensors cannot see: soreness location, sore throat, appetite, motivation. RAG grounds return-to-play guidance, which is real, citable and safety-relevant.

**Feasible?** Strongly. Galaxy Watch records workouts, and the events are **inducible on purpose**, so it is provable in two weeks.
**Risk:** narrower audience than general illness.

---

### R3. **Biomarker Sentry v2** - their flagship, rebuilt on hardware we have

**The pitch.** Keep their ambition exactly: uncertainty-aware, actively disambiguating, grounded, tiered early warning. Replace the mechanism that cannot run.

**What changes.** Their triad (cardiac + thermal + respiratory) becomes **cardiac + sleep + activity + your answers**. The missing information does not come from more sensors, it comes from the interview. That is a stronger story anyway, because it explains *why* the agent must ask rather than simply asserting that asking is nice.

**Risk:** without R1's order-a-test twist, this is their idea with corrected numbers. Good, not distinctive.

---

### R4. **Twin** - a model of you that gets ill on screen

**The pitch.** Build a forecast model of your own physiology. Each morning it predicts what today should have looked like. When reality diverges, the twin visibly changes state, and you can interrogate it: why do you think that, what would change your mind, what happens if I rest today versus train.

**The twist.** Counterfactuals. "If you rest, here is your predicted trajectory; if you train, here is the other one." That is actionable in a way a score never is.

**Where the technologies work.** Chronos does genuine forecasting. PHIA-style code execution answers arbitrary questions about your own history. The avatar is HiMe's trick.
**Risk:** the prettiest and the thinnest. Divergence-from-forecast is a repackaged anomaly detector unless the counterfactual half is real.

---

## Part 6: Recommendation

**Build R1, Morning Rounds, with R2 as its sharpest worked example.**

R1 carries the one twist nobody has shipped (an agent that orders a test), it uses every required technology for something load-bearing, it runs on the hardware we actually have, and it demos better than anything else on the list. R2 slots inside it as the discrimination case that is most legible and most provable, since training sessions can be induced deliberately.

R3's ambition is absorbed into R1. R4's counterfactual is a stretch goal if hours remain.

**One-line pitch:** *an agent that does a morning ward round on your body, and when it is not sure, it asks you a question or orders you a test before it decides.*

**Before committing:** read Project Hermes, and run the Samsung Health export to confirm which spot measurements this specific watch exposes.
