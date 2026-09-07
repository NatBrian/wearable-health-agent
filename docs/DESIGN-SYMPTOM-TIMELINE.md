# Symptoms over time, and the silences that came from not having them

**7 September 2026.** Why this system now records symptoms as things with a duration, and
why several of its quietest behaviours were wrong.

The question that started it, in the user's words: *"my dizziness kept getting worse,
nobody asked, and on the 10th I died. Whose fault is this?"*

The answer is the design's. What follows is what was actually broken, established by
running the system rather than by reading it.

---

## 1. The persistence rule had never fired, for any symptom, ever

`check_red_flags_deterministic` accepts a `symptom_history` argument. Across the whole
repository there were three references to it: the parameter, a pass-through in
`tier_c.py`, and one unit test that supplied the dict by hand. **No production caller ever
passed it.** So `history.get(rule_id, 1)` returned 1 on every call, and 1 is never greater
than 2, 3 or 4.

Five nights of a worsening fever, through the real path:

```
night 1 'I have a fever'          -> escalate=False
night 2 'still feverish today'    -> escalate=False
night 3 'fever is worse'          -> escalate=False
night 4 'burning up, fourth day'  -> escalate=False
night 5 'still got a fever'       -> escalate=False
```

Six symptoms carry a `persist_nights` value: fever, body aches, severe fatigue, inability
to eat or keep fluids down, exertional breathlessness, repeated vomiting. **Not one of them
could escalate alone, for any duration.** Tier C could not rescue it either: it is passed
only the current message, and its own Tier B path also requires two co-occurring.

This is the shape this project keeps producing, for the fourth or fifth time: *code that
exists, is referenced, and is never reached.* Every part worked. The wire between them did
not exist. The unit test passed throughout.

It was also worse than an inert bug. Each `persist_nights` value carries a written safety
argument in `red_flags.yaml` of the form *"a SHORTER window escalates sooner, so the error
this carries is an unnecessary appointment rather than a missed one"*. Those paragraphs
described behaviour the system did not have, and the file's header stated the rule as
"two or more, **or persistence beyond a stated duration**". Half of that sentence was
fiction. `docs/CONTRACTS.md` is compared against the code by three tests; `red_flags.yaml`
was compared against nothing.

## 2. "Co-occurring" meant "in the same sentence"

`matches_symptom` runs over one message. A fever on Monday and vomiting on Tuesday
co-occur in any ordinary reading of the word, and the system scored them as two unrelated
singletons and did nothing.

The case it failed hardest on is the one that matters most: a person whose symptoms
**evolve** across nights. Dizzy, then feverish, then abdominal pain is a systemic illness
developing, and it is more concerning than one stable symptom, not less.

## 3. The value-of-asking arithmetic cannot see deterioration, and never could

Every probe in `probes.yaml` targets a **cause**. A question's value is how much the answer
moves the belief across twelve causes. Once a cause is settled, asking again is worth
nothing *by construction*:

> **The more confident the system became that somebody was ill, the less reason it had to
> speak to them.**

Every step of that is the arithmetic working exactly as specified. And even if the policy
had wanted to ask, it had nothing to ask with: `probe_symptoms` has answer slots
`none / throat / fever / aches / other`, with no severity and no trajectory, so "feverish
or chills" is the identical token on night one and night five. **There was no question in
the system that meant "are you worse than yesterday".**

## 4. Green nights closed investigations as benign, and closes were silent

`check_close_conditions` closed on two green nights regardless of what the person had said.
And neither time-based close notified anybody: `close_episode` writes a row, and the only
code that messages anyone about an outcome is the agent's conclude node, which no timeout
close reaches.

---

# What green nights actually mean

This was the decision needing evidence, and the evidence is unusually clear. Three
independent lines, all pointing the same way.

**Dengue's critical phase begins at defervescence.** WHO and CDC both teach that patients
*may appear to improve clinically at the time of defervescence*, which is exactly when
plasma leakage begins. Dengue is endemic where this system is used.

**Heart rate can be normal or low during an active infection.** Faget's sign, fever with
inappropriately slow pulse, is documented in typhoid, dengue, Legionella, Q fever, yellow
fever, brucellosis and psittacosis.

**Real recovery is far slower than two nights.** Radin et al. measured resting heart rate
taking an average of **79 days** to return to pre-infection baseline after COVID symptom
onset, against 32 for step count and 24 for sleep; 133 days in long COVID.

That third finding inverts the old logic. A heart rate returning to normal two nights after
a red run is *not* the signature of somebody recovering from an infection. It is the
signature of a transient confounder passing.

> **A green run is good evidence about the READING and close to none about the PERSON. It
> may close the detection. It may not close the symptom.**

---

# The design

## The timeline

`symptom_observations`, one row per symptom per night, rebuilt from `conversation_turns`
text that was already stored. **Nothing new is collected from anybody.**

Three definitions, each a decision rather than an implementation detail.

**When a run ends.** On an explicit retraction, or after `SYMPTOM_RUN_GAP_DAYS` of silence.
Strict night-by-night consecutiveness was rejected: somebody who says nothing on Tuesday
has not recovered on Tuesday, and resetting their fever for going quiet punishes exactly
the silence this work exists to remove.

**How long it has been going.** First mention to most recent mention within the run,
inclusive.

**What counts as gone.** The person saying so. A negated mention writes `present = 0`
rather than no row, because *"I said my fever went"* and *"I did not mention my fever"* are
different facts and only one of them is reassuring.

## The numbers, and where each came from

| Constant | Value | Standing |
|---|---|---|
| `SYMPTOM_RUN_GAP_DAYS` | 7 | **CITED.** Respiratory illness surveillance separates two episodes by at least seven symptom-free days. Cross-checked against saddleback dengue, whose second peak arrives 1 to 2 days after defervescence, so a biphasic fever stays one illness |
| `EPISODE_RECURRENCE_LINK_DAYS` | 7 | **CITED**, same convention. Held separately so a later change to one does not silently move the other |
| `SYMPTOM_COOCCURRENCE_WINDOW_NIGHTS` | 2 | **DERIVED** from the shortest `persist_nights` already in `red_flags.yaml`. Not invented |
| `SYMPTOM_FOLLOWUP_MAX_PER_EPISODE` | 3 | **ASSUMED.** No source measures how often to ask an unwell person how they are. Disclosed as unevidenced |

The gap counts **symptom-free** days, not reading-normal days, because that is what the
source counts. Substituting one for the other would be reading a citation to suit the data
on hand, and sections 1 to 4 above are what that habit produces.

## The rule that overrides the arithmetic

`select_action` step 3b. An outstanding symptom forces an ASK. It is a **rule**, and it
sits beside the scoring rather than inside it: putting trajectory into the belief model
would mean writing likelihood rows for "worse than yesterday" that no literature supplies.
A rule can be read, argued with, and shown on a screen as a rule.

What it may not bypass, and why:

- **A pending question.** Two open questions is how one gets answered and the other times
  out silently.
- **Its own per-episode cap.** Alarm fatigue is a real harm.

What it may bypass, and why:

- **The weekly interruption budget.** A budget exists to stop the system pestering a
  **well** person. Letting it gag somebody who has said they feel unwell inverts its
  purpose. The follow-up is still *charged* to the budget and still shown, because it does
  arrive on somebody's phone unbidden; it simply cannot be silenced by it.
- **The rung gates.** Not knowing somebody's baseline well is a reason to be careful
  reading their heart rate. It is not a reason to stop asking them how they feel.
- **The EVSI score**, which is the entire point.

## The tracked tier

`red_flags.yaml` gains `tracked:`, holding dizziness. Recorded over time, escalates on
nothing.

This existed because dizziness had no good home. A tier assignment asserts a routing
threshold no source supports; omission means silence while somebody deteriorates. Tracking
asserts nothing clinical: *you told us, so we will remember and ask*. A tracked symptom
counts toward nothing in Tier B's arithmetic. It keeps an investigation from closing as
benign while outstanding, and gives the follow-up rule something to ask about.

## What was deliberately left out

**Severe abdominal pain**, a WHO and CDC dengue warning sign, is in no tier and not tracked.
The user reserved it as a live test of whether the agent can reason to a dengue warning sign
unaided.

**Prediction recorded before running it: it will fail.** `corpus.yaml` contains "dengue"
zero times, so `enforce_grounding`'s verbatim containment test makes a grounded dengue claim
impossible, and Tier C can only return ids from the red-flag list. Only an uncited note can
survive.

## What was measured and left alone

A long run of merely yellow nights opens nothing. That gap is real, and
`experiments/detection/cohort/yellow_persistence.py` measured what closing it would buy across 30 labelled
cases and controls in an archive of past wearable data: **nothing additional found** at every run length from
3 to 7 nights, for up to 5 percent more investigations on healthy people. Every case a long
yellow run would catch is already caught by the two-red rule. Nothing changed. That is a
finding, not a shrug, and it should not be re-argued from theory.

---

# What guards this now

The wire that did not exist for the life of the project is asserted **on the call**, by an
AST check over `src/wha`, because no unit-level behavioural test can see a missing call
site. Verified by reintroducing the original bug:

```
AssertionError: These call the safety floor on something a person typed without
their symptom history, so Tier B persistence cannot fire there:
agent/conversation.py:590
```

The persistence test is parameterised over `red_flags.yaml` itself rather than a
hand-written list, so a rule added later with a window nobody wires up fails immediately
instead of sitting dead for months, which is what happened to all six of these.

---

# Sources

- CDC, *Clinical Features of Dengue*: <https://www.cdc.gov/dengue/hcp/clinical-signs/index.html>
- CDC Yellow Book 2026, *Dengue*: <https://www.ncbi.nlm.nih.gov/books/NBK620887/>
- WHO, *Dengue: clinical management and delivery of clinical services*: <https://www.ncbi.nlm.nih.gov/books/NBK143161/>
- *The Significance of Prolonged and Saddleback Fever in Hospitalised Adult Dengue*, PLOS One: <https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0167025>
- Faget sign, LITFL eponym library: <https://litfl.com/faget-sign/>
- *Dengue and Relative Bradycardia*: <https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2725972/>
- Radin et al., prolonged physiological changes after COVID-19: <https://www.fiercehealthcare.com/digital-health/fitbit-readings-highlight-lingering-physiological-behavioral-changes-after-covid-19>
- Episode-separation interval, ILI surveillance cohort: <https://academic.oup.com/cid/article/81/3/459/8237737>
- *Assessing the Impact of Acute Respiratory Illnesses on the Risk of Subsequent Respiratory Illness*: <https://doi.org/10.1093/infdis/jiab313>
