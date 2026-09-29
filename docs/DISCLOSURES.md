# What is disclosed, and where

> ## This is an obligation, not a reference document.
>
> Every limitation this system has, the evidence for it, and **the screen where the person
> is told**. This project's rule is that a limitation living only in a markdown file is not
> disclosed at all.
>
> **If you find or add a limitation, it goes here, and it goes on a screen.** If you cannot
> name the screen, it is not disclosed yet.
>
> This is also the live record of what the system cannot do. It replaced `BLOCKERS.md`,
> which is now in `archive/`.

Every clinical design decision in this system is either backed by a citation or explicitly
recorded as unevidenced, and **each one is stated on screen as well as in this repository**.
A limitation that lives only in a markdown file is not disclosed to the person using the
system.

This page is the index. It exists so the rule can be checked rather than assumed.

---

## The standing disclaimer

`DISCLAIMER.md` has been in this repository since the beginning and **nothing in the
interface ever showed it**, so a person using the dashboard was never told it is not a
medical device. It was rendered on the Streamlit Home page, where a person lands, as a red
banner plus an expandable "What this system can and cannot do".

Source of that wording: `explain.py` and `Home.py`, in `archive/streamlit-ui-2026-09-27/`.
The Streamlit dashboard this describes was archived on that date and replaced by the React
client under `frontend/`.

> **This table began as an inventory of disclosures on the archived Streamlit dashboard.**
> The "Shown on" column now records the corresponding destination in the Vite dashboard.
> Each destination is checked against the frontend parity inventory and should remain
> visible as the interface evolves. Values that can change are read from the API or
> settings rather than copied into UI prose.

## Each limitation, its evidence, and where it appears in the Vite dashboard

| Limitation | Evidence | Shown in the dashboard |
|---|---|---|
| Not a medical device; cannot diagnose | `DISCLAIMER.md` | **Home**, red banner |
| Needs 7 nights before it can alert at all | Alavi et al. 2022 (NightSignal): baseline established for over 80% of participants within seven nights | **Home** expander; **Today**, a warning while below the threshold; **History**, on the chart |
| Compares against your own median, not an average adult | Alavi et al. 2022: "the streaming median of average overnight RHR" per individual | **History**, chart notes; the source passage is in **The record**, baseline step |
| A repeat notice can follow worsening or a sustained reading that has not improved | Not a clinical threshold. Both conditions use configured system units: a worsening step in robust deviations, or a reading that has not improved by that step after the configured number of nights | **Today**, under Conversation and notification limits |
| Dizziness and light-headedness raise no alarm on their own, but are now tracked over time | Still no routing evidence, and none is claimed: no source says how many nights of dizziness in an otherwise well person warrants care. It is a `tracked:` symptom in `red_flags.yaml`, which records it and asks about it without asserting a threshold | **Today**, in the safety note under the verdict; **The record**, step 8 and the 'Checking what you have told us' topic |
| Two symptoms count as co-occurring within 2 nights of each other | DERIVED, not measured. It is the shortest `persist_nights` already in `red_flags.yaml` (`rf_poor_intake` and `rf_persistent_vomiting`). A wider window escalates more often, so the error is an unnecessary appointment rather than a missed deterioration | **The record**, step 8 detail and the 'Checking what you have told us' topic |
| A symptom's run ends after 7 days of silence, or when you say it has gone | CITED. Respiratory illness surveillance separates two episodes by at least seven symptom-free days; checked against saddleback dengue, whose second fever peak arrives 1 to 2 days after defervescence | **The record**, step 8 caption and the 'Checking what you have told us' topic |
| At most 3 symptom follow-ups per investigation | ASSUMED. No source measures how often to ask an unwell person how they are. Small so it cannot become a nightly alarm; bounded on the other side by the person saying the symptom has gone | **The record**, the decide step rationale |
| A recurrence within 7 days is treated as the same illness, not a new one | CITED, the same episode-separation convention. Contains the dengue saddleback gap so a biphasic fever stays one illness | **History**, the linked investigation; **The record**, the preload step |
| Green nights do not close an investigation while a symptom is outstanding | CITED. Dengue's critical phase begins at defervescence; Faget's sign puts relative bradycardia in typhoid, dengue, Legionella and Q fever; Radin et al. measured resting heart rate taking 79 days on average to return to baseline after COVID | **The record**, the 'Checking what you have told us' topic |
| A long run of mildly raised nights opens nothing | Tried on an archive of past wearable data and found to add nothing, at the cost of more interruptions. That is an engineering trial, not clinical evidence: `experiments/detection/` | **The record**, 'Deciding a night is worth looking at' |
| The system holds no guidance about any specific illness, including ones common where the user lives | Scope decision, made 7 September 2026 after a live test showed the agent could not name a dengue warning-sign picture. Accepted deliberately: it may say a group of symptoms is worth seeing somebody about, never which illness they point to | **Today**, in the safety note under the verdict |
| Symptom phrases are matched exactly, so unusual wording can be missed | Design of the deterministic floor. Tier C, a model second opinion, is the backstop | **The record**, "How this works", the safety rules topic |
| Only a *raised* heart rate is investigated | Scope decision, not a cited finding. Infection raises nocturnal RHR; a low rate is usually fitness | **Home** expander; **History**, beneath the chart |
| Naps are excluded | Whitehurst, Naji & Mednick 2018: heart rate is higher during daytime naps than overnight sleep at matched stages | **Home** expander; **History**, chart notes |
| Sleep apnoea cannot be detected | Design consequence: a nightly elevation is absorbed into a personal baseline | **Home** expander; **History**, chart notes |
| Only sleep heart rate is used; waking heart rate never is | Mishica et al. 2022: morning measures significantly more variable, "during sleep, individuals are no longer affected by external stimuli" | **History**, chart notes; the source passage is in **The record**, sleep-window step |
| Measured over recorded sleep, with a clock fallback | Dial et al. 2025, validation of nocturnal RHR in consumer wearables | **History**, chart caption; per-night source on the night detail |
| The starting range is a population figure | Bloomfield et al. 2024, n=525 | **History**, chart notes; the source passage is in **The record**, baseline step |
| Nights with no reading are not judged | None needed. A night the watch did not record is an absence of data, not a finding about the person | **Today**, stated separately from the quiet-night count |
| General health information comes from MedlinePlus, is about a condition in general, and is never about you | National Library of Medicine, attribution-only. Snapshot and checksum in `data/knowledge/corpus-sources.json`. See `docs/CORPUS-VERIFICATION.md` | **Today**, in the citation panel attribution and each expanded MedlinePlus passage |
| The likelihood behind every question is assumed, not measured | `probes.yaml` records every row as ASSUMED; no published study measures next-morning self-report accuracy to an app | **The record**, How it works, and the question value detail |
| **Several causes rest on a guess, and which ones is now shown** | 45 of the 57 temporal profile weights in `causes.yaml` have no source, and the profile is what tells causes apart across nights. Most between-person spreads have none either | **Today**, beside each cause and its provenance |
| **The clinical tables were generated by a language model, not written by a person** | Established 5 September 2026. Every number carries its own `provenance`: `CITED` with a source you can open, `DERIVED` with the working shown, or `ASSUMED` meaning no published value exists | `data/knowledge/README.md`; **The record**, How it works, and cause provenance on **Today** |
| **The uncited labelling is done by the AI and can miss things** | Observed in real transcripts: it wrote "that's reassuring" into a reply with no warning; another reply arrived with both citation and uncited fields empty, leaving its source status unknown | **Today**, in a caption directly under the amber panel; **Dashboard**, Agent Chat and **The record**, archived replies, mark a reply with no source metadata as unverified |
| A reply can arrive without citation or uncited-content metadata, leaving its source status unknown | A real isolated Vite chat returned empty citation and uncited fields, and the panel originally displayed no source-status warning | **Dashboard**, Agent Chat; **The record**, archived replies; review drafts show the same warning |
| **Blood oxygen thresholds come from a pathway for people already diagnosed with COVID-19** | NHS England COVID Oximetry @home: 92 percent or less means emergency care, 93 to 94 means contact a GP. British Thoracic Society target range 94 to 98. Not WHO, and not a screening rule for somebody who is well | **Today** and the episode record, whenever an oxygen band fires, in the band's own wording |
| **Pulse oximeters overestimate oxygen saturation for everybody, not only for darker skin** | Singh et al., J Med Internet Res 2024;26:e62769: overestimation "for both light and dark skin pigmentation", and its own conclusion is that this "may not be clinically relevant" | Shown every time an oxygen reading is reported, including on normal nights |
| **The Chronos forecast is not part of the current pipeline** | Its engineering evaluation is recorded in `experiments/forecasting/`; this is not clinical evidence | **The record**, How it works |
| Whether a cause is 'large enough' to explain a night is a presentation rule, not a clinical one | Unevidenced. The 0.5 and 0.25 fractions in `wha/agent/differential.py` were chosen to be legible, not derived | **The record**, How it works |
| A chest pain report is assessed by questions, not by matching the words | Marburg Heart Score: Bosner et al., CMAJ 2010;182(12):1295-1300; external validation Haasenritter et al., Br J Gen Pract 2012;62(599):e415-21. Sensitivity 87.1%, specificity 80.8% | **Today**, in the conversation, with the rule named and its source shown |
| Some presentations still escalate with no questions at all, on purpose | Marburg's own contraindication, "do not use in an emergency setting"; and no history-only rule exists for syncope, meningism, GI bleeding or new confusion | **Today**, when it escalates; **Summary for your doctor**, under Recommendation |
| The AI may say things with no source behind them, and they are labelled as such | Draelos et al. 2025, arXiv:2507.18905: 5 to 13 percent of unguarded frontier-model answers to patient questions were unsafe | **Today**, under an amber "Not from a cited source" heading |
| The labelling of uncited content is best effort, not guaranteed | Observed: the model sometimes writes clinical reasoning into the reply itself instead of the uncited list, where it is shown without the warning. The deterministic checks that always run are the red-flag floor, the never-say phrases and the urgency ratchet | **Today**, stated in the conversation caption |
| **A sentence with a source shown can still misdescribe that source** | Not a study, a measurement made here on 5 September 2026. `enforce_grounding` checks that the span the AI quoted is verbatim in a passage; it never compares the sentence built around that span. Asked why a night was flagged, the reply called the baseline an "average" (it is the median) and said a night is flagged at 3 bpm (3 is elevated; flagging needs two consecutive nights at 4), while citing the two passages that say both correctly. Pinned in `tests/unit/retrieve/test_grounding.py` | **Today**, in a caption under every quoted passage, saying the passage is the one to believe where the two differ |
| The AI can never make anything less urgent | Design property enforced in code, not asked of the model | **Today**, under the urgency banner and in the conversation caption |
| Conversation length and weekly unsolicited interruptions use configured limits | AMIE (Tu et al., Nature 2025;642:442-450): accurate differential within the first ten turns. Alarm fatigue: Front Digit Health 2022;4:843747. The active conversation and weekly limits are operating settings, not clinical thresholds | **Today**, under Conversation and notification limits |
| Blood oxygen can raise urgency but never lowers it, and cannot say what is wrong | NHS England's home oximetry pathway and the British Thoracic Society target range, corrected 5 September 2026 from an earlier attribution to WHO, which recommends using home oximetry but does not publish these levels. Documented silent hypoxia in COVID. No study relates a wearable reading to a specific cause, so it has no likelihood in the belief model | **Today**, when it fires; the rule and its source are named |
| Blood oxygen readings are biased HIGH, and by more on darker skin | Singh et al., J Med Internet Res 2024;26:e62769: pooled bias 0.70 percent light, 0.27 medium, 1.27 dark, and the review states overestimation "for both light and dark skin pigmentation". Corrected 5 September 2026: this page and the rule previously framed the bias as affecting darker skin only, which understates the warning for everybody else. Occult hypoxaemia missed about three times more often in Black patients during COVID | **Today**, on every blood oxygen result, including normal ones, which are explicitly not an all-clear |
| Blood oxygen says nothing at all unless the watch recorded a night of it | Ten readings inside the sleep window are required. A single spot check is not a night, and the real device produced an 80 percent followed by a 92 percent 66 seconds later | **Today**, stated as no opinion rather than shown as normal |
| A question that is asked and never answered leaves the episode UNRESOLVED, not benign | Handler, Bedi and Shah, arXiv:2605.15000 (2026): premature closure is "inappropriate commitment under uncertainty", measured at 55 to 81 percent false-action rates in frontier models | **History**, in the investigation outcome for that night |
| If it cannot establish enough to run the rule within three replies, it escalates anyway | UNEVIDENCED. No study says how long someone may be left without an answer. Chosen because the measured alternative was worse: a live run left a person describing chest pain with no urgency at all | **Today**, stated in the escalation itself as the cautious direction rather than a finding |

---

## The record itself

Audit entries came only from the agent's tool calls and from settings changes, so after a
full night of measuring, scoring and judging, the page that exists to show a person what
happened to their data was blank. A user could not tell that from the system having done
nothing at all.

The deterministic half now writes to the same tamper-evident chain, under
`src/wha/audit/monitor.py`, with two rules:

- **Only changes are recorded.** Ingest polls every 30 minutes and night scoring runs every
  few hours, mostly redoing identical work. A pass that finds nothing new writes nothing, so
  the record stays a history of what happened to the person rather than a list of cron ticks.
  A night's first scoring always writes, whether or not anything changed.
- **Refusals are recorded too.** A stage that declined made a decision about the person.
  "Nothing can be flagged yet: 3 of the 7 nights needed" is what turns silence into something
  a reader can understand. This bullet also quoted "The forecasting model did not run: it needs
  5 usable nights and there are 3", which no code can produce since the forecast was deleted in
  item 22. Rows written before that still carry it and are deliberately not rewritten: the audit
  chain is tamper-evident, and editing history to tidy it is the one thing it must never do.

Every entry carries two forms: the exact figures, so the arithmetic can be redone and
checked, and a **plain narrative** written for someone with no medical or technical
background, which is what the page shows first. A record nobody can read is not
transparency.

---

## The reasoning behind each

- `docs/DESIGN-BASELINE-CENTRE.md`: why a night is compared against the person's own
  median, what the population-shrunk centre cost, and why nothing is flagged below seven
  nights.
- `docs/DESIGN-SLEEP-WINDOW.md`: why the window is the recorded sleep session rather than
  a fixed clock window, why naps are excluded, and why apnoea is out of reach.
- `docs/DESIGN-DATA-CHANNELS.md`: which of the device's channels are used and which are
  captured but cannot move the belief.
- `docs/CORPUS-VERIFICATION.md`: every figure in the retrievable corpus checked against
  the paper it cites, what did not hold up, and what the consumer health layer changed.
- `docs/RESEARCH-AGENTIC-TRIAGE.md`: the evidence behind the conversation, the triage
  redesign and the clinician handover: why keyword matching was replaced, what a frontier
  model may and may not say here, and what remains unevidenced.
- `docs/DISCLOSURES.md`: the decisions deliberately left to a human, including whether the
  step at seven nights should be smoothed and whether one population mean is the right
  cold-start prior across ages and sexes.

---

## The rule this page serves

A clinical design choice must be the most accurate option under medical best practice and
backed by study or research cited next to the number it justifies. Where research does not
settle a question, the choice is still made explicitly, written down here, and **disclosed
in the dashboard** rather than left for the reader to discover. The user must be able to
see what the system can and cannot do without reading the source.
