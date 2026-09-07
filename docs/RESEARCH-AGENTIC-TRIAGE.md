# The evidence behind the conversation, the triage, and the handover

**Written 4 September 2026.** Every design decision in this document is traceable to a
published source, read in September 2026, and the citation sits next to the decision it
justifies. Where no evidence exists the choice is marked UNEVIDENCED and disclosed on
screen as well as here, per `docs/DISCLOSURES.md`.

This exists because the previous design of the safety floor was **literal keyword matching
on the person's own words**, and that is not triage. A clinician who hears "chest pain"
asks discriminating questions before deciding anything. This document is the research that
replaces the guesswork.

---

## 1. Why asking is the most valuable thing this system does

| Source | Finding |
|---|---|
| Peterson MC, Holbrook JH, Von Hales D, Smith NL, Staker LV. Contributions of the history, physical examination, and laboratory investigation in making medical diagnoses. *West J Med.* 1992;156(2):163-5. PMID 1536065 | History-taking alone produced the final diagnosis in **76%** of patients. Physical examination added 12%, laboratory investigation 11%. |
| Hampton JR, Harrison MJG, Mitchell JRA, Prichard JS, Seymour C. Relative contributions of history-taking, physical examination, and laboratory investigation to diagnosis and management of medical outpatients. *BMJ.* 1975;2:486-9. | History-taking was responsible for **82.5%** of diagnoses in 80 patients. |

**Decision.** A system whose only source of information beyond a heart rate is what the
person tells it should ask more than one question. Asking one question per episode and
stopping discards the single most informative instrument available to it.

---

## 2. How a conversational clinical agent is structured

**Tu T, Palepu A, Schaekermann M, et al. Towards conversational diagnostic artificial
intelligence. *Nature.* 2025;642:442-450. PMID 40205050.**

- AMIE uses a **three-step chain of reasoning at every turn**: "analysing patient
  information" to summarise symptoms, generate a differential, identify gaps and assess
  confidence; "formulating response and action" to answer, ask clarifying questions and
  recommend urgent care if needed; and "refining the response" for factual accuracy,
  empathy and formatting.
- Simulated consultations averaged **21.28 turns** (IQR 19-25). Real-world dialogues
  averaged 149.8 turns.
- Critically: **"both AMIE and the PCPs were able to acquire the information necessary for
  formulating an accurate differential in the early stages (first ten turns)"**, with
  comparable performance at all conversation lengths.
- Limitations the authors state: the text-chat interface is "unfamiliar in clinical
  practice", fairness and bias were insufficiently evaluated, performance was worse for
  patients with low English literacy, and it "requires substantial additional research"
  before deployment.

**Decisions.**
1. A conversation runs to a depth of **ten turns**, not one question. Ten is the figure at
   which this study found an accurate differential had been reached; going further showed
   no measured gain.
2. Each agent turn follows the same three steps: assess what is known and missing, respond
   and optionally ask one question, then run the deterministic checks. The third step here
   is code, not a prompt, because a model checking its own safety is not a check.

---

## 3. Why keyword matching is not triage

**Downie A, Williams CM, Henschke N, Hancock MJ, Ostelo RWJG, de Vet HCW, et al. Red flags
to screen for malignancy and fracture in patients with low back pain: systematic review.
*BMJ.* 2013;347:f7095.**

- "Many red flags in current guidelines provide virtually no change in probability of
  fracture or malignancy or have **untested diagnostic accuracy**."
- 29 red flags for fracture and 24 for malignancy were identified across 14 studies. Only
  **13 (25%) were evaluated in more than one study at all**.
- Individually most were uninformative. For malignancy, only "history of cancer" reached a
  meaningful post-test probability (33%); the other guideline-endorsed flags were **below
  3%**.
- **Combinations were informative where single features were not**: the probability of
  spinal fracture rose to 90% when multiple red flags were present.
- The authors recommend guidelines be revised toward **combined clinical patterns rather
  than individual findings**.

**Sutaria S, et al. Evaluating the use of red flags by online symptom checkers. *BMC Health
Serv Res.* 2025;25:1263. doi:10.1186/s12913-025-13353-w.**

- Online symptom checkers sought only **36.9%** of relevant red flags, against **71.8%**
  for primary care physicians.
- They matched physicians on emergency triage accuracy (76.9% vs 85.7%) but had
  significantly lower specificity, over-escalating non-emergencies.
- Their definition of a red flag is worth quoting, because it is a definition of an
  **action**, not a word: "additional relevant symptoms that would be **sought** to exclude
  serious illness, requiring a change in management".
- Conclusion: "diagnostic accuracy alone may not be an adequate measure of safety", and
  developers "should focus on improving red flag coverage".

**Manchester Triage System**, the human reference standard, reports sensitivity between
**0.47 and 0.87** and specificity 0.84 to 0.94 in adults, with acknowledged under-triage
and low safety on that measure (systematic review, *Int J Nurs Stud*; validity study, *PLOS
One* 2017;12(2):e0170811).

**Decisions.**
1. A red flag is something the system **asks about**, not something it waits to hear. The
   agent actively seeks the discriminators relevant to the current hypothesis.
2. **Combinations, not single words.** A lone matched phrase is an opening, not a verdict.
3. The system does not claim to beat the Manchester Triage System, and says so.

---

## 4. The one validated rule this system can actually run

Almost every emergency decision rule needs an ECG, bloods or an examination. Three do not,
and one of them fits this system exactly.

**Marburg Heart Score.** Ruling out coronary heart disease in primary care patients with
chest pain, using **history and self-palpation only**.

| Item | Points |
|---|---|
| Female aged 65 or over, or male aged 55 or over | +1 |
| Known coronary, cerebrovascular or peripheral vascular disease | +1 |
| Pain worse with exercise | +1 |
| Pain **not** reproducible by pressing on the chest wall | +1 |
| The person assumes the pain is cardiac | +1 |

- **0 to 2:** unstable coronary disease is highly unlikely, negative predictive value about
  **98%**. Outpatient evaluation is appropriate.
- **3 or more:** unstable coronary disease cannot be excluded; urgent evaluation warranted.

**Bösner S, Haasenritter J, Becker A, et al. Ruling out coronary artery disease in primary
care: development and validation of a simple prediction rule. *CMAJ.*
2010;182(12):1295-1300.** Derived on 1,199 consecutive patients aged 35 and over presenting
with chest pain across 74 German primary care practices. Area under the curve **0.87** (95%
CI 0.83-0.91) in derivation and **0.90** (0.87-0.93) in validation. At a cut-off of 3:
sensitivity **87.1%** (79.9-94.2), specificity **80.8%** (77.6-83.9).

**Haasenritter J, Bösner S, Vaucher P, et al. Ruling out coronary heart disease in primary
care: external validation of a clinical prediction rule. *Br J Gen Pract.*
2012;62(599):e415-21.** Independent external validation in a different population.

It has additionally been evaluated against **telephone triage for chest pain in
out-of-hours primary care**, which is the same remote, history-only situation this system
is in.

**Its stated contraindication is binding on us:** "Do not use in an emergency setting", and
"no decision rule should trump clinical gestalt... any patient with chest pain who is
clinically unstable warrants urgent or emergency inpatient admission".

**Decisions.**
1. Chest pain is no longer routed by a matched phrase. The agent collects the five Marburg
   items in conversation and a deterministic function computes the score.
2. **The rule is not allowed to run at all** when the presentation is one Marburg excludes:
   pain happening now alongside collapse, sweating, vomiting, breathlessness at rest, or an
   inability to speak in full sentences. Those remain an unconditional emergency with no
   questions asked, because delay is itself the harm and the rule was never validated there.
3. The LLM elicits. The rule decides. The agent can raise urgency at any time and can never
   lower it by reasoning, only by the deterministic rule returning a lower band.

---

## 5. Why a frontier model cannot be trusted to answer freely

**Draelos RL, Afreen S, Blasko B, Brazile TL, Chase N, Desai DP, et al. Large language
models provide unsafe answers to patient-posed medical questions. arXiv:2507.18905, 2025.**

Physician-led red teaming of four public chatbots (Claude, Gemini, GPT-4o, Llama3-70B) over
**222 patient-posed advice-seeking questions**, 888 responses. Problematic responses ranged
from **21.6%** (Claude) to **43.2%** (Llama3-70B). Outright **unsafe** responses ranged from
**5%** to **13%**. The authors report responses "with the potential to lead to serious
patient harm".

A separate longitudinal analysis (*npj Digital Medicine* 2025) found medical safety
messaging and disclaimers **declining** in generative models over time.

**Decisions.**
1. Every clinical sentence the model produces is either **grounded in a cited passage** or
   **visibly labelled as not coming from a cited source**. Never silently asserted.
2. The deterministic red-flag and output checks run over **every** model turn, not once at
   the end.
3. The model can never state a diagnosis, and can never reduce an urgency the rules set.
4. Disclaimers are rendered by the application, not left to the model to remember.

---

## 6. Why the interruption budget was the wrong shape

Alarm fatigue evidence concerns **unsolicited** alarms: 72-99% of clinical monitor alarms
are technically false or non-actionable, only 5-13% are actionable, and the consequence is
desensitisation and delayed response (systematic review, *Front Digit Health.*
2022;4:843747).

That is an argument about how often a system may **interrupt a person who is not asking**.
It is not an argument for cutting off a conversation the person is already having. Treating
both as one counter meant that a follow-up question inside a live conversation consumed the
same allowance as a push notification on an unrelated day, which is why the agent could
never ask more than two questions in a week.

**Decision.** Two separate resources:

| Resource | Budget | Basis |
|---|---|---|
| Unsolicited interruptions, where the system contacts a person who did not initiate | **2 per week**, unchanged | Alarm fatigue evidence above |
| Turns inside a conversation the person is engaged in | **10** | AMIE: accurate differential reached within the first ten turns |

---

## 7. What the doctor handover should contain

**Structure: SBAR.** Situation, Background, Assessment, Recommendation is recognised by the
WHO, the Joint Commission, AHRQ and the IHI as the standard handover structure. Systematic
reviews report low-certainty evidence that it improves patient safety outcomes and
consistently that it improves the clarity and completeness of handover communication. The
ISBARQ variant adds introductions and an explicit **questions** section, and was associated
with improved handover content and provider satisfaction.

**Add a Question Prompt List.** A 2025 systematic review and meta-analysis of randomised
controlled trials found QPL interventions significantly increased the number of questions
patients asked and their engagement in shared decision-making, **without increasing
consultation time**, and that QPLs accompanied by instructions outperformed bare lists.

**Keep it short and relevant.** Across studies of patient-generated health data in clinical
encounters, the dominant barrier to clinician adoption is **perceived relevance**, followed
by workflow and time (systematic review of PGHD use by health care professionals; *npj
Digital Medicine* 2025 survey of professional attitudes).

**Decisions.**
1. The handover is SBAR, with a question prompt list, in that order.
2. Everything in it is either measured by the device or said by the person, quoted
   verbatim with a timestamp. Nothing is inferred.
3. It states plainly, at the top, that it is not a diagnosis and what the device is and is
   not validated for.
4. Probabilities from the belief model are included but **behind a heading that says they
   are not clinical probabilities**, because relevance is the adoption barrier and a bare
   ranked list of causes reads as a diagnosis to a reader who did not ask for one.

---

## 8. The regulatory line, which is also the safety line

FDA, *General Wellness: Policy for Low Risk Devices* (2019, revised January 2026): software
intended for maintaining or encouraging a healthy lifestyle **and unrelated to the
diagnosis, cure, mitigation, prevention or treatment of a disease or condition** is not a
device under the FD&C Act.

**Decision.** The agent explains, contextualises, elicits and prepares the person for a
clinician. It does not diagnose, and the interface says so where a reader might mistake it.
This is not caution for its own sake: combined with the Draelos finding above, an
unhedged diagnostic claim from this system would be both unlawful to market and, 5 to 13
percent of the time, wrong in a way that could hurt someone.

---

## 10. Silence is not a benign finding

**Handler R, Bedi S, Shah N. Quantifying and mitigating premature closure in frontier LLMs.
arXiv:2605.15000, 2026.**

Their definition is this system's bug word for word: premature closure is "inappropriate
commitment under uncertainty: providing an answer, recommendation, or clinical guidance
when the safer response would be clarification, abstention, escalation, or refusal". They
measured **55 to 81 percent false-action rates** across five frontier models on MedQA
questions whose correct answer had been removed, **78 percent** on physician-authored
adversarial queries, and about 30 percent on open-ended health questions. Their closing
question is whether medical models "know when not to answer".

This build did it deterministically, without a model being involved. A question that timed
out became a declined answer; a declined answer contributes no likelihood factor; the
belief therefore never moved and the episode fell through to LIKELY_BENIGN. The system
asked the single most informative question it had, heard nothing back, and reported that
things were probably fine.

**Decision.** An unanswered question forces UNRESOLVED. The check sits after the illness
threshold, so silence can prevent a reassurance and can never talk an escalation down. A
recorded event, such as a workout the watch itself logged, still explains a night, because
that is positive evidence from the device rather than an absence.

---

## 11. Blood oxygen: a threshold for action, not evidence about cause

Two findings pull in opposite directions and both are load-bearing.

**For using it.** "Silent hypoxia" is documented in COVID: oxygen saturation falls while
the person still feels well. That is exactly the pre-symptomatic window this system exists
to catch, and resting heart rate alone cannot see it. An actionable threshold exists:
**NHS England's COVID Oximetry @home pathway**, where 92 percent or less means attend an
emergency department within the hour or call 999, and 93 or 94 percent means contact 111 or
a GP. The upper bound of 94 to 98 percent is the British Thoracic Society's target range for
oxygen therapy in adults.

> **CORRECTED 5 September 2026.** This paragraph credited these levels to "WHO guidance, as
> reported across the wearable SpO2 literature". They are not WHO's. WHO's January 2021
> guidance recommends *using* home pulse oximetry and publishes no such numbers. A reader
> who followed the citation would have found nothing, which in a document whose header
> promises every decision is traceable to a published source is the worst kind of error.
> **And the population matters more than the attribution:** that pathway is written for
> people *already diagnosed with COVID-19* and being monitored at home. This system applies
> it to somebody who is well, which is using a rule outside the population it was written
> for. That is why the rule may only ever raise urgency, and why it says "get a proper
> reading taken" rather than naming a condition.

**Against trusting it.** A systematic review and meta-analysis (*J Med Internet Res*
2024;26:e62769) reports accuracy root-mean-square error of 3.96 to 4.71 percent, with
pooled mean bias of 0.70 percent for light, 0.27 for medium and **1.27 for dark
pigmentation**. Melanin absorbs at the wavelengths these sensors use and is misread as
oxygenated haemoglobin, so readings are biased **high** in darker skin, and occult
hypoxaemia went undetected roughly three times more often in Black patients during COVID.
The FDA issued skin-tone subgroup guidance in January 2025. Reviews of wearables for
SARS-CoV-2 also note that comparative work on the incremental value of SpO2 over heart rate
alone is limited.

**Decision.** It gets a **cited threshold rule in the deterministic floor**, and **no
likelihood in the belief model**. No published study relates a wearable oxygen reading to
any of the twelve causes, so a likelihood would be invented clinical content.

Three constraints follow directly from the evidence:

1. It requires **a night of readings, not a spot check**. The real device produced six
   readings across four days, including an 80 percent followed by a 92 percent sixty-six
   seconds later. Below ten readings inside the sleep window the rule returns no opinion,
   which the interface states rather than rendering as normal.
2. It uses the **median** of the night, not the minimum, because the minimum fires on every
   movement artefact this sensor produces.
3. A normal reading is **explicitly not an all-clear**, because the bias direction means a
   genuine fall can be missed, and that caveat is shown every time.

---

## 9. What remains unevidenced

Stated here and on screen rather than buried.

- **The tier A and tier B phrase lists in `red_flags.yaml`** are fixed routing rules. Apart from chest pain, which now has Marburg, none of them carries a diagnostic
  accuracy figure. Downie's finding applies directly: their accuracy is untested.
- **No validated history-only rule was found** for syncope, meningism, gastrointestinal
  bleeding or new confusion that does not require an ECG, bloods or examination. Those
  remain unconditional escalations, which is the conservative direction.
- **The ten-turn conversation depth** is taken from the point at which AMIE had an accurate
  differential. It is a reasonable transfer, not a measured property of this system.
- **The SOCRATES frame** used to structure symptom follow-up questions is standard clinical
  teaching rather than a validated instrument.
