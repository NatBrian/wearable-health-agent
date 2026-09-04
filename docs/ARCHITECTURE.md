# How this system works, end to end

**Written 4 September 2026.** Everything in this document was checked by running the
system, not by reading its documentation. Where a number appears, it came out of a real
run on this machine, and the run is named. Where something does not work, this document
says so in the place where it would otherwise be described as working.

This is written for someone who is comfortable with engineering and with large language
models, and who has never studied statistics or medicine. Every technical word is
explained the first time it appears.

---

## The one-paragraph version

You wear a watch to bed. Every morning the system reads your overnight heart rate,
compares it with what is normal **for you**, and decides whether last night was unusual.
Most nights it says nothing. When two nights in a row are raised, it opens an
**investigation**, works out which of twelve possible causes best explains the rise, and
decides by arithmetic whether asking you one question is worth interrupting you. If it
asks, it asks on Telegram. Your answer moves its belief, it looks things up in a local
library of health text, and it writes you a conclusion in which every clinical sentence
must be traceable to a passage it actually read. Separately, anything you type is checked
by fixed rules that can send you to a doctor and that no language model is allowed to
overrule.

---

## The whole journey on one screen

```mermaid
flowchart TB
    subgraph PHONE["YOUR PHONE AND WATCH"]
        W["Galaxy Watch 5<br/>heart rate every minute<br/>sleep stages, steps, workouts"]
        HC["Health Connect on the phone"]
        BR["Bridge app<br/>serves JSON over HTTP"]
        W --> HC --> BR
    end

    subgraph DET["THE DETERMINISTIC HALF: runs every night, no AI anywhere"]
        ING["1. INGEST<br/>pull JSON, normalise, store raw"]
        WIN["2. SLEEP WINDOW<br/>find the main sleep the watch recorded<br/>drop the waking spells inside it"]
        FEA["3. FEATURES<br/>median heart rate in that window<br/>coverage minutes, sleep hours, workouts"]
        BASE["4. BASELINE<br/>your own median over 28 nights<br/>plus a band width"]
        EXPL["5. SUBTRACT WHAT IS EXPLAINED<br/>a recorded evening workout only"]
        DETECT["6. DETECT<br/>GREEN / YELLOW / RED<br/>flag on 2 raised nights with a RED"]
        FC["CHRONOS FORECAST<br/>advisory only, changes nothing"]
        ING --> WIN --> FEA --> BASE --> EXPL --> DETECT
        FEA -.-> FC -.-> DETECT
    end

    subgraph AG["THE AGENTIC HALF: only runs once a night is flagged"]
        EP["EPISODE OPENS<br/>one open investigation at a time"]
        PRE["preload: 5 fixed tool reads"]
        INV["investigate: the model picks tools<br/>and calls them in a loop"]
        BEL["believe: Bayesian belief<br/>over 12 causes, 4096 states"]
        DEC["decide: EVSI policy<br/>is a question worth the interruption?"]
        ASK["ask: model words the question<br/>then the graph PAUSES"]
        MEAS["measure: ask for a hand reading<br/>(never completes, see below)"]
        CON["conclude: draft the outcome<br/>strip any claim with no source"]
        CRI["critique: model removes, never adds"]
        REV["review: human checkpoint<br/>(auto-approved, see below)"]
        EP --> PRE --> INV --> BEL --> DEC
        DEC -->|ASK| ASK
        DEC -->|MEASURE| MEAS
        DEC -->|OBSERVE| WAIT["wait for another night"]
        DEC -->|CONCLUDE| CON
        ASK -->|answer arrives| INV
        MEAS --> BEL
        CON --> CRI --> REV
    end

    subgraph SAFE["THE SAFETY FLOOR: runs first, on your words, and can only make things louder"]
        FLOOR["fixed phrase rules<br/>plus a second opinion from the model<br/>combined by set union"]
        TRI["Marburg Heart Score<br/>five questions, published cut-off"]
        FLOOR --> TRI
    end

    subgraph OUT["WHAT REACHES YOU"]
        API["HTTP API on 127.0.0.1:8500<br/>28 endpoints"]
        DASH["Streamlit dashboard<br/>Home, Today, History, Audit, Settings"]
        TG["Telegram bot<br/>questions with buttons, and chat"]
        AUD["Audit log<br/>hash-chained, tamper evident"]
    end

    BR -->|"HTTP GET ?days=N"| ING
    DETECT -->|"flagged"| EP
    ASK --> TG
    REV --> API
    DETECT --> API
    API --> DASH
    TG -->|"what you type"| SAFE
    DASH -->|"what you type"| SAFE
    SAFE --> CONV["conversation engine<br/>multi-turn, retrieval grounded"]
    CONV --> TG
    CONV --> DASH
    INV -.->|"retrieve_clinical_evidence"| RAG["local corpus<br/>1,852 chunks, 4 layers<br/>BM25 + embeddings + RRF"]
    CONV -.-> RAG
    EP --> AUD
    INV --> AUD
    CONV --> AUD
    DETECT --> AUD
    AUD --> API

    style DET fill:#e8f4ea
    style AG fill:#e8eef7
    style SAFE fill:#f7e8e8
    style OUT fill:#f5f0e8
    style PHONE fill:#eeeeee
```

**The one thing to take from that picture:** the green half and the blue half are
completely different kinds of machine. The green half is arithmetic. Given the same
nights it produces the same answer every time, forever, and no language model touches it.
The blue half is a language model driving a small, fenced loop. The red half sits in front
of both and can only ever increase urgency.

---

## Part 1. Getting the data off the watch

### What does this part do?

It pulls raw numbers off your phone and stores them without changing them.

A Samsung Galaxy Watch 5 writes its readings into **Health Connect**, which is Android's
shared store for health data. A small bridge app on the phone serves that store over plain
HTTP. The system asks it `GET http://<phone>:8788/?days=30` and gets back one JSON object.

The watch supplies **seven** kinds of record, measured by probing the real device:

| Record | Volume over 7 real days | Used for |
|---|---|---|
| `heart_rate` | 3,652 samples | everything |
| `steps` | 4 daily buckets | activity context only |
| `sleep` | 3 sessions with stages | choosing the measurement window |
| `exercise` | 3 sessions | subtracting a recorded workout |
| `oxygen_saturation` | 5 spot readings | captured, and currently unused (see Part 12) |
| `distance` | 1 | context |
| `total_calories` | 3 | context |

Heart rate variability, respiratory rate and skin temperature are **not** provided by this
watch and cannot be computed from one-minute averages. That is a hard limit, not a
missing feature, and it removes several channels the research literature uses.

### Why does it exist? What breaks if you delete it?

Everything. There is no other source of data. There is also a synthetic generator used for
simulation, which speaks the same HTTP protocol, so removing the bridge means the system
can only ever run on made-up data.

### How does it actually work?

```mermaid
sequenceDiagram
    participant S as Scheduler (every 30 min)
    participant L as LiveBridge
    participant P as Phone bridge app
    participant DB as SQLite

    S->>L: run_ingest(days=30)
    L->>P: GET /?days=30 (+ auth token)
    P-->>L: one JSON object, ~250 KiB per day
    L->>DB: store the raw payload verbatim
    L->>DB: normalise into 7 tables
    Note over DB: INSERT OR REPLACE, so re-pulling<br/>the same window is harmless
```

The raw payload is kept as-is in a `raw_payloads` table before anything is parsed. That
matters: if the parser is ever found to be wrong, the original is still there and the
nights can be recomputed.

Measured on a real run: **48,942 heart rate samples** ingested for a 35 day window.

### Why this way and not another way?

The alternative is to use Samsung's or Google's cloud APIs. Both were investigated and
rejected: they need a registered app and OAuth, they rate-limit, and they put a person's
health data through a third party. A phone on your own Wi-Fi does not.

**The weakness, stated plainly:** the bridge is only reachable when the phone hotspot is
on and the laptop is on the same network. In practice that means data arrives in bursts
when you happen to connect, not continuously. Everything except ingest works offline.

---

## Part 2. Storage

### What does this part do?

One SQLite file holds everything: raw payloads, normalised samples, nightly summaries,
baselines, detections, episodes, beliefs, questions, answers, conversation turns, and the
audit log. Schema version 6, applied by a migration function at startup.

### Why does it exist?

Because a health record has to survive a restart, and because an investigation can sit
paused for a day and a half waiting for you to answer a question. The LangGraph
**checkpointer** (the thing that saves the agent's paused state) writes into the same
file, so deleting the database deletes the agent's memory of you along with your data.
That is deliberate.

### How does it work?

Plain SQLite, one file, no server. `INSERT OR REPLACE` everywhere, so re-running any stage
over the same night is safe and produces the same result. Every derived table (features,
baselines, detections) can be thrown away and rebuilt from the raw samples.

### Why this way?

**Single user.** One person, one phone, one file. A Postgres deployment would add
operational burden and buy nothing. The cost is that everything is on one machine with no
backup story, which is a real risk for a health record and is not addressed.

---

## Part 3. The sleep window

This is the part the project changed most recently, and it is the best decision in the
system.

### What does this part do?

It decides **which minutes of the night count** as your resting heart rate.

### Why does it exist? What breaks if you delete it?

Because "resting heart rate" is only meaningful if it is measured while you are actually
resting. Daytime heart rate mostly records what you were doing. Standing up moves it by
tens of beats. An infection moves it by a few. The signal is real and buried.

The original version used a fixed clock window, local midnight to 07:00, copied from the
NightSignal study whose thresholds this system uses. That study used a clock window
because its data had no sleep staging. This build has staging and was ignoring it.

On the real subject the cost was large. They sleep roughly 03:00 to 11:00, so a
midnight-to-07:00 window counted 2.6 to 3.6 hours of lying awake as sleep and discarded
about 40 percent of the actual sleep.

| Night | Reading over the clock window | Reading over recorded sleep | Change |
|---|---|---|---|
| 31 Aug | 51.0 bpm | 44.0 bpm | -7.0 |
| 01 Sep | 56.0 bpm | 45.0 bpm | -11.0 |
| 02 Sep | 48.0 bpm | 45.0 bpm | -3.0 |

The clock-window column is the project's own record of what the system produced before the
change, and I could not re-measure it without reverting the code. The sleep-window column I
did verify, straight out of the database: 44.0, 45.0, 45.0 and 47.0 bpm on the four real
nights, measured over 303 to 399 minutes of recorded sleep, with zero implausible readings
dropped on any of them.

The level matters less than the **spread**. Eight beats of night-to-night variation (48 to
56) became one beat (44 to 45). That variation is not noise you can ignore: it sets how
wide the "normal" band is, and a wider band means a real illness has to be bigger before
it shows.

**How much this generalises is now measured, and the answer is: not much, for most
people.** Replayed over 21 real Fitbit users with real sleep staging, scoring the same
nights both ways, the night-to-night spread improved for 6, worsened for 5 and was
unchanged for 10. The reason is visible in the data: only 3 of those 21 slept substantially
outside a midnight-to-07:00 window, because the cohort is almost entirely conventional
sleepers, for whom the clock window is already nearly right. So this decision is strongly
justified for a person who sleeps 03:00 to 11:00, and roughly neutral for a person who
sleeps 23:00 to 07:00. The design note should say that rather than implying a general
improvement.

### How does it work?

```mermaid
flowchart LR
    A["all sleep stage rows<br/>near this night"] --> B["group into sessions<br/>split on a gap of 60 min"]
    B --> C["inside each session,<br/>drop AWAKE spans"]
    C --> D["keep sessions that END<br/>on this night's date"]
    D --> E{"more than one?"}
    E -->|yes| F["take the one with<br/>the most sleep in it<br/>(a nap is not pooled)"]
    E -->|no| G["take it"]
    F --> H["measure heart rate<br/>only inside those spans"]
    G --> H
    D -->|"none recorded"| I["fall back to midnight-7am<br/>and LABEL the night 'clock'"]
```

A night is named for the **day you woke up**. The session chosen is the one whose sleep
ends on that date.

Naps are excluded on evidence, not preference. Whitehurst, Naji and Mednick (2018) put 32
adults through a daytime nap and a night of sleep a week apart, with full sleep
laboratory monitoring, and found heart rate measurably higher during the nap at matched
sleep stages. Pooling the two would move your reading by however much you happened to nap.

### Why this way?

Because the device already knows when you slept, and throwing that away to match a paper
whose data lacked it copies a limitation rather than a method.

**Three weaknesses, all real:**

1. **Sleep apnoea is undetectable by design.** A condition that raises your heart rate
   every single night becomes part of what the system learns as your normal. It is
   disclosed on screen.
2. **The most recent night usually falls back to the clock window.** Measured on the
   simulation: the newest night in every payload had heart rate but no sleep record yet,
   so it was scored over midnight-to-7am while every older night used recorded sleep. The
   scheduler re-scores a three-day trailing window so it settles later, but the first
   score a person sees for last night is on the weaker basis. Worse, the baseline it is
   compared against was built from sleep-window nights, so for that one night the
   observation and the baseline are measured over different things. The design note says
   a constant offset cancels because both share the window. On the newest night they do
   not share it.
3. **The dashboard tells you the wrong thing about this.** The Today page says, on every
   night, "Your watch was in contact for 362 minutes **between midnight and 7am**", and
   "Your lowest sustained rate between midnight and 7am". Checked against the database:
   that night was measured over recorded sleep, and the figure is the **median**, not the
   lowest sustained rate. Two factual errors in one caption about the system's own
   headline design decision. The History page describes it correctly, so the two screens
   contradict each other.

---

## Part 4. Turning a night into one number

### What does this part do?

It reduces roughly 400 heart rate readings into a single number for the night, plus
quality information about how much to trust it.

### How does it work?

- Throw away anything below 25 or above 220 beats per minute as implausible, and count
  how many were thrown away.
- Take the **median** of what is left. The median is the middle value when you sort them,
  which means a handful of wild readings cannot drag it around the way an average would.
- Count how many distinct minutes had a reading. That is **coverage**.
- If coverage is under **180 minutes** (three hours), the night is marked unusable and is
  not scored at all.

Real example, subject `me`, night of 1 September 2026: 373 minutes of coverage inside 6.23
hours of recorded sleep, median 45.0 bpm, zero implausible readings, usable.

### Why this way?

The three-hour floor exists so a reading taken over a fragment of a night is never
compared with one taken over a whole night.

**A weakness worth naming:** the published algorithm this system borrows its thresholds
from uses the **mean** of the night, not the median, and only counts minutes where the
step count was zero. This system uses the median and does not look at steps at all. Both
choices are defensible on their own. Neither was validated together with the thresholds.

---

## Part 5. The baseline: what "normal for you" means

### What does this part do?

It works out two things about you:

- a **centre**, the heart rate you usually have overnight
- a **scale**, how much you normally bounce around from night to night

### Why does it exist? What breaks if you delete it?

Without it there is no such thing as a raised night. A resting heart rate of 65 is high
for the subject in this repository, whose nights sit at 44 to 47, and low for someone
whose nights sit at 75. The whole system is built on within-person comparison.

### How does it work?

```mermaid
flowchart TB
    H["your last 28 usable nights"] --> N{"how many?"}
    N -->|"0 to 6"| SH["centre = a blend of your median<br/>and 62.75, the population average<br/>NOTHING can be flagged"]
    N -->|"7 or more"| OWN["centre = YOUR OWN MEDIAN<br/>no population blending at all"]
    H --> MAD["scale = 0.8 x your own spread<br/>+ 0.2 x the population spread of 8.64<br/>with a floor of 1.5"]
```

The seven-night rule is not arbitrary. The NightSignal study reports that "for over 80% of
the participants, the proper baseline was observed after only seven nights".

The centre used to be a permanent blend, and that was the most serious defect the project
found. Because the window caps at 28 nights, the blend weight capped at 0.8, so a fifth of
the population average never washed out. Measured on a steady simulated subject after 200
nights of their own data:

| True sleeping heart rate | Centre the system used | Residual every single night |
|---|---|---|
| 45 | 48.5 | -3.5, needing a 6.5 bpm rise to reach YELLOW |
| 62.75 | 62.8 | 0.0 |
| 80 | 76.5 | +3.5, at YELLOW every night while perfectly healthy |

Infection raises overnight heart rate by a few beats. The real subject sits at 44 to 47.
Under the old blend they **could never have been flagged for an infection at all**. That is
now fixed for the centre.

**Two weaknesses:**

1. **The identical argument applies to the scale, and it was not fixed.** The scale is
   still a permanent blend, so a fifth of your band width is forever the population
   figure of 8.64 beats. Measured on a simulated subject with 28 nights of perfectly
   steady data, the personal spread is exactly zero and the scale comes out at **1.728**,
   which is entirely the population contribution. The scale is what `robust_z` is divided
   by, and `robust_z` is what the extreme-heart-rate safety rule is written in terms of.
2. **The population figure itself is from an unexpected group.** 62.75 beats with a spread
   of 8.64 comes from Bloomfield et al. 2024, which is **525 first-year university
   students aged 18 to 24, in their first semester**. The dashboard describes it as "a
   2024 study of 525 adults". That is true and it hides the thing that matters. A separate
   study of 92,457 wearable users found that individual normal resting heart rates differ
   from one another by nearly 70 beats.

**What "robust z" means, since it appears on screen:** it is how many "typical night to
night wobbles" away from your centre a night is. If your usual wobble is 1.7 beats and
tonight is 5 beats above your centre, your robust z is about 2.9. "Robust" means the
wobble is measured with the median rather than the average, so one terrible night does not
inflate it. Real measurement from the simulation run: residual 5.00 bpm, scale 1.728,
robust z **2.89**.

---

## Part 6. Detection: deciding a night is worth looking at

### What does this part do?

It labels each night GREEN, YELLOW or RED, and decides whether to open an investigation.

### How does it work?

```mermaid
flowchart LR
    A["tonight's reading<br/>66.0 bpm"] --> B["minus your centre<br/>61.0"]
    B --> C["deviation<br/>+5.0 bpm"]
    C --> D["minus what a recorded<br/>workout would explain<br/>0.0 here"]
    D --> E["residual<br/>+5.0 bpm"]
    E --> F{"how big?"}
    F -->|"under 3.0"| G["GREEN"]
    F -->|"3.0 to 3.99"| H["YELLOW"]
    F -->|"4.0 or more"| I["RED"]
    I --> J{"was last night<br/>also raised?"}
    J -->|"yes, and one was RED"| K["FLAGGED<br/>open an investigation"]
    J -->|"no"| L["record it, say nothing"]
```

That is a real run. On 4 September the simulated subject went from 61 to 66 bpm: RED, but
not flagged, because one night is not a pattern. On 5 September the same reading came back:
RED and **flagged**, and an investigation opened.

The 3 and 4 beat thresholds come from Alavi et al. 2022 in *Nature Medicine*, the
"NightSignal" algorithm. Three was chosen because across their participants "the median of
fluctuation of medians of average RHR overnight over three months was only three bpm", so
a three-beat move is the point where a change stops looking like ordinary variation.

Two more rules:

- **Nothing is flagged below seven nights of your own data.** An elevation measured against
  a mostly-borrowed baseline says more about the gap between you and an average adult than
  about tonight.
- **Only rises are investigated.** A low overnight heart rate is usually fitness or good
  rest. Conditions that lower it are out of scope, and the interface says so rather than
  leaving you to work it out.

### Why this way?

Because the alternative is a threshold someone invented. These are borrowed from a paper
that measured them on 3,318 people.

**The weakness, and it is the big one:** four of the five choices that define the published
algorithm have been changed here.

| | NightSignal, as published and as implemented by its authors | This system |
|---|---|---|
| window | midnight to 06:59 | the sleep the watch recorded |
| minutes counted | only minutes where step count was zero | all minutes in the window |
| nightly value | the **mean** | the **median** |
| baseline | expanding median of every prior night, including tonight | median of a trailing 28 nights, excluding tonight |
| red alert | two consecutive nights at or above baseline + 4 | two consecutive raised nights with **at least one** at +4, so RED followed by YELLOW also fires |
| compared quantity | the raw deviation | the deviation **after subtracting** a recorded workout |

Several of those changes are argued for with evidence and are probably improvements. But
the published sensitivity of 78 percent was measured on the published algorithm. It does
not transfer to this one, and until this build is measured on labelled data of its own,
its accuracy is unknown. Part 19 reports what happened when that measurement was finally
made.

---

## Part 7. The Chronos forecast

### What does this part do?

Chronos is a **time series foundation model**: a neural network from Amazon, pre-trained on
a very large collection of unrelated time series, which can be handed any sequence of
numbers and asked "what comes next" without ever being trained on your data. This system
gives it your recent nightly heart rates and asks for tonight's, with a range.

### Why does it exist? What breaks if you delete it?

Nothing breaks. It is explicitly advisory. It never sets a level, never opens an
investigation, and is not evidence in the belief model. It answers a different question
from the detector: the detector asks "is tonight high **for you**", the forecast asks "is
tonight a surprise **given the recent trend**". A slow drift upward over a week can be
unremarkable to the detector and unsurprising to the forecast at the same time.

### How does it work?

Take up to 28 nights, fill missing nights with NaN rather than guessing, ask for the 10th,
50th and 90th percentile of tonight. Compare the actual reading against that. It needs at
least five usable nights; below that it declines and says so.

Measured: 0.1 seconds per night once the model is warm; the weights are 182 MB on disk.
On the real subject, with four usable nights, it correctly refuses on every night.

### Why this way, and should it be here at all?

It is kept out of the belief model on evidence. No study was found showing a forecast
residual tells you **which** cause is present, and the paper that supplies this system's
thresholds compared three detectors on exactly this problem: plain baseline deviation
scored 78 percent sensitivity against 54 for CuSum and 44 for a forecast-style detector,
at the same false alarm rate. The simplest method beat both cleverer ones.

**Stated plainly:** this is the least load-bearing component in the system. It costs 182 MB
of model weights and a dependency on PyTorch, and it produces one advisory sentence on one
screen. It is honest about being advisory, which is more than most such features manage,
but a reader should understand that deleting it would change no decision the system makes.

---

## Part 8. The Bayesian belief over twelve causes

This is the intellectual centre of the project.

### What does this part do?

Given a raised night, it works out how likely each of twelve possible causes is.

**"Bayesian"** means: start with how common each cause is in general, then adjust those
numbers using the evidence in front of you, using a rule (Bayes' theorem) that says
exactly how much a piece of evidence should move a belief. It is arithmetic, not
judgement.

The twelve causes:

| Cause | How often it is present on any night | How much it raises heart rate |
|---|---|---|
| infection | 2.5% | 1.60 bpm |
| alcohol | 29.9% | 2.60 bpm |
| unrecorded exertion | 8.0% | 4.14 bpm |
| short or broken sleep | 34.8% | 1.00 bpm |
| acute stress | 35.0% | 1.50 bpm |
| luteal phase of the menstrual cycle | 45.0% | 3.91 bpm |
| vaccine reaction | 2.2% | 1.52 bpm |
| travel or time zone change | 2.0% | 1.50 bpm |
| medication change | 1.0% | 0.00 bpm, but very wide |
| still recovering from an earlier illness | 2.0% | 1.50 bpm |
| sensor artefact | 5.0% | 0.00 bpm, wide |
| none of the above | 2.0% | 0.00 bpm, wide |

**Read that table again.** The one cause the system exists to find is the smallest but two,
and it is smaller than alcohol, evening exercise and the menstrual cycle. That is not an
error in the table; it is the actual clinical problem. It is also why the system asks
questions: the sensor cannot separate these, and a person can.

### Why does it exist? What breaks if you delete it?

Delete it and you have a system that says "your heart rate was up" and nothing more. The
belief is what lets it say "up, and here is what most likely did it, and here is what
would tell us".

### How does it actually work?

Two ideas, and both are worth understanding.

**Idea one: causes combine, so you must reason over combinations.** You can have a drink
*and* be coming down with something. So the model does not ask "which one cause is it". It
enumerates every possible **combination** of the twelve causes being present or absent.
Twelve on-off switches means 2 to the power 12 = **4,096** possible worlds. It scores all
4,096 exactly. That is a tiny amount of arithmetic, microseconds, and it means there is no
approximation anywhere.

**Idea two: everything is done in log space.** Multiplying 4,096 probabilities together
gives numbers so small the computer rounds them to zero within a few nights, and you would
get a flat, meaningless answer with no error. **Log space** means storing the logarithm of
each probability and adding instead of multiplying, which keeps the numbers in a range the
computer can represent. Converting back at the end is a single stable operation.

```mermaid
flowchart TB
    P["PRIOR<br/>how common is each cause<br/>on any night at all"] --> S["4,096 combinations scored"]
    R["THE READING<br/>+5.0 bpm above your centre<br/>how likely is that under<br/>each combination?"] --> S
    F["WHAT THE WATCH SAW<br/>a workout was recorded<br/>sleep was short<br/>coverage was poor"] --> S
    A["WHAT YOU SAID<br/>'feverish or chills'"] --> S
    S --> M["add up the combinations<br/>where each cause is ON"]
    M --> OUT["p(infection) = 0.4051<br/>p(stress) = 0.7769<br/>p(alcohol) = 0.5408"]
```

The temporal profile is what does most of the separating. Each cause carries a shape over
nights. Alcohol contributes fully on night one and is gone by night two. Infection rises
over three nights, plateaus, then fades over a week. The luteal phase is flat for about
twelve days. **A single night cannot tell alcohol from early infection at all.** The shape
across several nights can.

### A real run, with the actual numbers

From a live episode on 5 September 2026, simulated subject, two consecutive nights at
+5.0 bpm:

| | before any question | after the answer "feverish or chills" |
|---|---|---|
| stress | 0.8147 | 0.7769 |
| alcohol | 0.5536 | 0.5408 |
| short sleep | 0.4813 | 0.4752 |
| **infection** | **0.0756** | **0.4051** |
| sensor artefact | 0.0915 | 0.0759 |
| luteal | 0.0 | 0.0 |

One question moved infection from 7.6 percent to 40.5 percent. That is the entire argument
of the project, working, on a real run.

### Why this way and not another way?

The alternative is a single-label classifier that picks one cause. That cannot represent
"a drink and an infection", cannot explain away, and cannot say "I do not know". This model
has a first-class **none of the above** cause, and when that one rises the episode closes
as UNRESOLVED, which is an honest outcome rather than a forced guess.

**Four weaknesses, and the first two are serious.**

1. **The ranked list shown to you is not a differential diagnosis, and it reads like
   one.** Those twelve numbers are independent probabilities that each cause is present.
   They do not add to one and they do not compete. A cause that is common and small
   (stress, 35 percent of nights, 1.5 bpm) scores high on any raised night because
   something has to explain the rise and several small things together can. In the run
   above the system concluded **LIKELY_ILLNESS** and the chart directly underneath put
   **stress at 0.92 in first place**, with the reason "Nothing gathered in this episode
   speaks to this cause either way. Its position reflects its base rate of 35.0% of nights
   alone." A person reads "we think you are ill" above "most likely cause: stress, no
   evidence". The audit page repeats it in words: "most likely stress at 93%, chance of
   illness 78%".

2. **The luteal cause cannot be switched on.** The model treats "do you menstruate" as a
   three-state fact: yes, no, or not yet established. Not established leaves the cause
   inert, which was a deliberate and correct fix. But **no code anywhere passes the answer
   back in**. Every production caller invokes the belief update without the cycle fact, so
   luteal stays clamped at effectively zero forever. The `probe_cycle` question exists, is
   priced at 0.4 of an interruption on the grounds that it is a one-off setup question,
   and its answer cannot move anything. Confirmed on a live run: luteal 0.0 throughout.
   The same call path also means the "recently recovered from an illness" boost never
   fires either.

3. **The dose is thrown away.** The alcohol question offers "1 to 2", "3 to 4", "5 or
   more". The underlying study is explicitly dose-dependent. The model has one alcohol
   switch, so all three answers produce the same effect size.

4. **Almost every answer likelihood is a guess, and the file says so.** `probes.yaml`
   states it outright: "Almost every likelihood here is ASSUMED... no published measurement
   exists of how accurately a person reports drinking, stress or sleep to an app when
   prompted the next morning." That honesty is genuinely rare. It is still about thirty
   numbers with no source, sitting in the step that converts your answer into a change in
   belief.

---

## Part 9. The EVSI policy: deciding whether to interrupt you

### What does this part do?

It decides, by arithmetic, whether asking you a question is worth the interruption.

**EVSI** stands for **Expected Value of Sample Information**. In plain words: before asking
a question, work out what you would do now without asking; then, for each possible answer,
work out what you would do if you got that answer and how much better off you would be;
weight those by how likely each answer is. The difference is what the question is worth. If
that is less than the cost of interrupting you, do not ask.

### Why does it exist? What breaks if you delete it?

Delete it and you have either a system that asks about everything, which is the alarm
fatigue this project exists to avoid, or a hand-set rule like "ask when probability is
above 20 percent", which cannot tell a question that would change your mind from one that
would not.

### How does it work?

First it needs to know what an error costs. The system says a missed illness is **nine
times** worse than a false alarm. From those two numbers alone the decision threshold falls
out: act when the probability of illness is above 1 / (1 + 9) = **0.10**. It is derived,
not chosen, and it happens to coincide with the classic threshold from Pauker and Kassirer
(1980).

Then for each of nine questions it computes the EVSI, subtracts the interruption cost, and
asks the one with the best score if that score is positive.

```mermaid
flowchart TB
    B["current belief<br/>p(infection) = 0.0756"] --> E["for each of 9 probes:<br/>what would each answer do?"]
    E --> S["score = EVSI - (cost x 0.15)"]
    S --> G{"gates"}
    G -->|"baseline too cold"| NO["do not ask"]
    G -->|"2 unsolicited asks<br/>already this week"| NO
    G -->|"5 questions already<br/>this episode"| NO
    G -->|"a question is already<br/>waiting for you"| NO
    G -->|"all clear"| T{"best score<br/>above zero?"}
    T -->|"yes"| ASK["ASK it"]
    T -->|"no"| OBS["OBSERVE:<br/>wait for another night"]
```

**The quiet band is the interesting property.** Asking is only worth it in the middle. If
illness is very unlikely, no answer changes what you do. If it is very likely, you already
know what to do. Measured from the project's own sweep:

| p(infection) | EVSI of the symptom question | score after cost | asks? |
|---|---|---|---|
| 0.020 | 0.0156 | -0.284 | no |
| 0.050 | 0.1950 | -0.105 | no |
| **0.080** | **0.4280** | **+0.128** | **YES** |
| 0.100 | 0.5850 | +0.285 | YES |
| 0.200 | 0.3700 | +0.070 | YES |
| 0.300 | 0.1550 | -0.145 | no |

In the live run the belief was 0.0756, inside the band, and the policy asked
`probe_symptoms` with an EVSI of **0.3935** against an interruption cost of 1.0, having
beaten eight alternatives. After the answer, every remaining question fell below its cost
and the agent stopped on its own. **The weekly budget was not what stopped it. Its own
arithmetic was.** That is the strongest single result in the project.

### Why this way?

Because the two obvious alternatives are worse in ways you can measure, and the project
measured them. From its own evaluation over 40 simulated cases:

| Policy | Accuracy | Questions per episode |
|---|---|---|
| EVSI, this system | 0.675 | 0.40 |
| Fixed probability threshold | 0.500 | 0.60 |
| Never ask | 0.500 | 0.00 |
| **Always ask** | **0.925** | **2.00** |
| Ask at random | 0.525 | 0.35 |

**Never ask scores at chance.** That is the finding the rest of the system rests on: the
sensor data alone carries no usable signal about which cause it is.

**Two weaknesses:**

1. **Always-ask beats EVSI by 25 accuracy points.** The policy buys a large reduction in
   questions (0.40 against 2.00 per episode) and pays a quarter of the available accuracy
   for it. Whether that trade is right is a judgement about your tolerance for being
   asked, and the system currently makes it for you with a single tuning constant. The
   constant is exposed in settings, which is the right call.
2. **The budget is cited from intensive care.** The two-per-week limit is justified by a
   systematic review finding that "72% to 99%" of alarms are false or non-actionable.
   That review is about **ICU bedside monitors**. Extending it to a phone notification is a
   large jump that the file does not acknowledge.

---

## Part 10. The agent: the LangGraph loop

### What does this part do?

It runs the investigation. It is a **state graph**: a set of named steps with rules for
which step follows which, where the state (everything known so far) is passed along and
saved to disk after every step.

### Why does it exist? What breaks if you delete it?

The deterministic half can tell you a night was raised. It cannot look anything up, cannot
word a question, cannot read what you wrote, and cannot write you an explanation. The
agent does those four things. Without it you have a monitor, not an assistant.

### How does it work? Every node, in order.

```mermaid
stateDiagram-v2
    [*] --> preload
    preload --> investigate
    investigate --> believe
    believe --> decide
    decide --> ask: ASK
    decide --> measure: MEASURE
    decide --> conclude: CONCLUDE or ESCALATE
    decide --> [*]: OBSERVE (park)
    ask --> investigate: an answer arrived
    ask --> believe: tool budget spent
    ask --> conclude: a red flag fired
    measure --> believe
    conclude --> critique
    critique --> review
    review --> [*]
```

**preload.** Five fixed tool calls, always the same ones, no model involved: your recent
nights, your baseline, recorded events, data quality, and your past investigations. This
exists so the model starts with facts rather than spending its first turns fetching them.

**investigate.** The model is handed a catalogue of seven tools with their exact argument
names and loops: call a tool, see the result, decide whether to call another or stop.
Bounded at 25 tool calls per episode. A real run made these calls:

```
get_nightly_features(start="2026-08-28", end="2026-09-04")
get_personal_baseline(night_date="2026-09-05")
get_known_events(start="2026-08-28", end="2026-09-04")
get_data_quality(start="2026-08-28", end="2026-09-04")
find_similar_past_episodes()
...then after the answer arrived...
get_local_disease_activity()                       -> failed, endpoint unreachable
get_known_events(start="2026-09-03", end="2026-09-04")
retrieve_clinical_evidence(query="elevated nocturnal heart rate")
```

The prompt is re-rendered on every turn so the model can see the result it just got. It
was not, once, and the model asked for the same tool 101 times in a row.

**believe.** Pure arithmetic, described in Part 8. No model.

**decide.** The EVSI policy, described in Part 9. No model, except for one thing: if the
policy chooses to ask, a model is given the proposed question and the facts already known
and may **veto** it as redundant. The veto can only cancel a question, never create one.

**ask.** The model writes the actual sentence. Then the graph **pauses**. LangGraph's
`interrupt()` saves the whole state to SQLite and returns; the process can exit; hours or
days later the answer arrives over Telegram or the dashboard, and the graph resumes from
exactly where it stopped. This is the only genuinely hard piece of engineering in the
system and it works.

**measure.** Asks you to take your pulse by hand. Selected when sensor artefact leads the
differential, because no question can settle whether your watch misread you but a hand
count can.

**conclude.** Drafts the outcome: a disposition, a ranked differential with reasons, the
passages it read, and prose. Every clinical claim the model makes must come with a span of
text it says supports it, and that span is checked (Part 14).

**critique.** A second model pass that may only **remove**. If it returns longer text than
it was given, the longer text is discarded.

**review.** A human checkpoint. Pauses for approve, edit, reject or escalate.

### Is it genuinely agentic, or a chatbot with extra steps?

Genuinely agentic, on the definition that matters: it chooses which tools to call, in what
order, based on what earlier calls returned, and its loop re-enters after new evidence
arrives. The edge from `ask` back to `investigate` is what makes it hypothesis-driven.
Measured: on the step immediately after the answer "fever", the model called
`retrieve_clinical_evidence` for the first time in the episode. That is the model
following up on what it just learned.

But the autonomy is narrow and deliberately so. It cannot decide to interrupt you, cannot
write to your record, cannot choose a disposition, and cannot lower urgency. Those are all
arithmetic. The right description is a **bounded investigator inside a deterministic
frame**, and that is a better design for a health tool than a free agent.

**Three weaknesses, all found by running it.**

1. **The human review checkpoint approves itself.** The `review` node pauses correctly.
   But the background job that resumes paused episodes handles two cases, a question and a
   measurement, and for anything else returns `{"decision": "approve"}`. The review is
   anything else. Fifteen minutes later the job approves the draft on your behalf and
   closes the episode. Confirmed on a live run: the episode went from waiting-on-you to
   CLOSED in one tick with no human involved. Separately, nothing ever sets the episode
   state that would make the review appear on screen, so you could not have approved it
   even if you wanted to.
2. **The measure limb cannot complete.** `measure` sends a notification and pauses. But
   **nothing anywhere writes a row to the `measurements` table**, so the request never
   appears in the dashboard, the submit function finds nothing to update, and the resume
   logic hard-codes "declined" regardless of what you did. A whole limb of the graph that
   can be entered and cannot be finished.
3. **The record says the wrong thing about who wrote the question.** The ask node calls
   the storage function without passing the source of the wording, and that argument
   defaults to "fallback". So every question is recorded as having used the canned
   sentence. In the live run the stored question text was "Have you noticed any unusual
   symptoms today?" while the canned sentence is "How are you feeling?" The model clearly
   wrote it, and the record says it did not.

---

## Part 11. The tools

Seven tools, a **closed registry**: a fixed list, checked by name, where anything not on
the list is refused and the refusal is written to the audit log. The model cannot add a
tool, cannot reach the web, and cannot read another subject's data. The registry strips any
subject id the model supplies and substitutes the one the episode was opened for. Date
ranges are clamped to 90 days and to not-in-the-future.

| Tool | What it returns |
|---|---|
| `get_nightly_features` | your readings, coverage and sleep hours in a range |
| `get_personal_baseline` | your centre and band on a night, and how mature it is |
| `get_known_events` | workouts, steps, blood oxygen and other recorded context |
| `get_data_quality` | coverage and dropped readings, for judging sensor artefact |
| `find_similar_past_episodes` | your earlier investigations and how they ended |
| `retrieve_clinical_evidence` | passages from the local corpus |
| `get_local_disease_activity` | local outbreak and air quality signals |

**Two of the seven do not do what they say.**

`get_data_quality` **ignores the database entirely** and returns the same three invented
numbers on every call, for every person, on every night: `coverage_ratio 0.95,
missing_hours 0.35, dropped_samples 0`. Confirmed in the audit log of a live run. The real
numbers exist and are used by the belief model, so the agent and the arithmetic are told
different things about the same night, and the tool whose job is to inform judgements
about sensor artefact is fabricating.

`get_local_disease_activity` fetches a Singapore government data endpoint with no query
parameters and returns `{"status": "active", "bytes": <length>}`. It never parses dengue
clusters, never checks whether you are inside one, and never queries the air quality
endpoint that is also allow-listed. `sources.yaml` says "A subject inside an active cluster
materially raises the dengue prior, and no shipped product does this." Nothing raises any
prior; there is no dengue cause in the model at all. In the live run the call returned
`ok: false` because the endpoint was unreachable, which is the only reason it was
harmless.

---

## Part 12. The deterministic safety floor

### What does this part do?

It reads what you actually typed and, if it matches a fixed list, tells you to seek care.
It runs **before** the model, and the model may only add to it.

### Why does it exist?

Because a language model is not a safe last line. Draelos et al. 2025 red-teamed four
frontier chatbots over 222 patient-posed questions and found 5 to 13 percent of answers
outright unsafe. Whatever the model says, the rules still fire.

### How does it work?

```mermaid
flowchart TB
    T["what you typed"] --> A["TIER A phrase list<br/>chest pain, fainted, confusion,<br/>can't breathe, bleeding, stiff neck+fever"]
    T --> B["TIER B phrase list<br/>fever, aches, exhaustion,<br/>vomiting, can't eat"]
    T --> C["TIER C<br/>the model reads the same text<br/>and may add flags"]
    A --> U["SET UNION in code<br/>the model can add, never remove"]
    B --> U
    C --> U
    U --> D{"any tier A?"}
    D -->|"yes, and a validated<br/>rule exists for it"| M["open a discriminator<br/>conversation (Marburg)"]
    D -->|"yes, no rule exists"| E["ESCALATE now"]
    D -->|"two or more tier B,<br/>or one that has persisted"| S["see a doctor today"]
```

The negation guard is deliberately simple: a "no" or "not" within four words suppresses a
match, but the guard stops at a comma or at "but". So "no fever, but chest pain" correctly
denies the fever and escalates the chest pain.

### The Marburg Heart Score

Matching the phrase "chest pain" used to route you straight to an ambulance with no
confirming question. That is not what a clinician does and the evidence does not support
it. Sutaria et al. 2025 define a red flag as a symptom that would be **sought**, and
measured online symptom checkers seeking 36.9 percent of the relevant ones against 71.8
percent for physicians.

So chest pain now opens a conversation that seeks five specific items, and a published
rule decides:

| Item | Point |
|---|---|
| woman 65 or over, or man 55 or over | 1 |
| known coronary, cerebrovascular or peripheral vascular disease | 1 |
| pain worse with exercise | 1 |
| pain **not** reproducible by pressing on the chest wall | 1 |
| the person believes the pain is cardiac | 1 |

Score 0 to 2: see a doctor today. Score 3 or more: urgent. From Bösner et al. 2010 in
*CMAJ*, 1,199 consecutive patients aged 35 and over across 74 German general practices:
sensitivity 87.1 percent, specificity 80.8 percent at a cut-off of 3.

**The division of labour is the design.** The model elicits, in whatever words you use. The
arithmetic decides. The model may raise urgency at any time and can never lower it.

Two live runs, same rule, opposite outcomes:

- "chest pain since this morning... worse on stairs... pressing does not change it... I
  think it is my heart" scored **3 of 5** and routed to **urgent**.
- "chest pain... stairs make no difference... pressing reproduces exactly the same pain...
  I think it's muscular from the gym... I don't think it's my heart" scored **0 of 5** and
  routed to **see a doctor today**.

The extraction quality is genuinely good. Each item was stored with the person's own words
beside it: `mhs_reproducible_by_palpation = no`, quote "Pressing on it does not change
anything".

**Four weaknesses.**

1. **The age gate never runs.** The rule was developed and validated only in people aged 35
   and over, and the code checks that. But `age_years` is never populated by anything. The
   dashboard does not collect it and does not send it. In the live run the person said "I
   am 24 and male", the system extracted that into the age/sex item, scored it correctly as
   zero, **and then applied a rule outside its validated range anyway**, while telling them
   it was using "a 2010 study of 1,199 people with chest pain". The score of 3 came from
   three items that are all common in a healthy young adult with a muscular strain.
2. **The two extreme-heart-rate rules have never once fired.** `red_flags.yaml` defines an
   escalation for a night more than six robust standard deviations above or below your own
   baseline. The function that evaluates it takes `robust_z` as an argument. All three
   production callers pass only the text you typed. So `robust_z` is always absent and the
   branch is skipped every time. Confirmed by line coverage over a full production run:
   those lines never execute.
3. **The blood oxygen rule has never run either.** There is a well-written function that
   reads your overnight oxygen readings, requires at least ten inside the sleep window,
   takes the median rather than the minimum, and applies a published threshold. Nothing
   calls it. Not one line of it executes in production, and no test touches it either. The
   pure function it wraps is unit tested, which is why the suite is green. STATUS.md says
   blood oxygen "sits in the deterministic floor as a cited threshold that can raise
   urgency". It does not sit anywhere.
4. **The interface says a phrase the safety rules forbid.** `red_flags.yaml` lists
   "nothing to worry about" among the phrases the system must never say, and the same
   phrase is in the code's false-reassurance filter. The dashboard's headline for a benign
   outcome is **"Probably nothing to worry about"**. The filter runs on what the model
   writes, not on the interface's own hard-coded wording.

---

## Part 13. Retrieval, and the corpus

### What does this part do?

It gives the agent something to cite. The system holds a local library of health text and
searches it; the agent may quote from it and from nothing else.

### Why does it exist?

Because the alternative is the model writing clinical content out of its own head, and that
is the one line this project does not cross.

### The four layers

| Layer | What it is | Where it comes from | Size |
|---|---|---|---|
| 1 | general consumer health information about a condition | **MedlinePlus**, fetched from the US National Library of Medicine, snapshot 2026-09-03 | 1,013 English topics |
| 2 | how a night is measured and what counts as raised | generated from `constants.py`, numbers interpolated not retyped | 3 documents |
| 3 | when to seek care | generated from `red_flags.yaml` | 9 documents |
| 4 | the evidence behind each competing explanation | generated from `causes.yaml` | 12 documents |

Total **1,852 chunks**. Adding MedlinePlus grew the index fourteenfold, and a test asserts
that the system's own safety rules still surface in the top six for "chest pain", because
a thousand fetched topics burying them is the plausible failure.

### How does retrieval work?

```mermaid
flowchart LR
    Q["query: 'fever'"] --> BM["BM25<br/>keyword matching<br/>rare words count more"]
    Q --> DE["dense embeddings<br/>bge-small, 384 numbers per chunk<br/>meaning rather than words"]
    BM --> RRF["Reciprocal Rank Fusion"]
    DE --> RRF
    RRF --> DD["drop duplicate text"]
    DD --> TOP["top 5 to 8 passages"]
    TOP --> SCAN["scan each for prompt injection<br/>contain and mark, never drop"]
```

**BM25** is classic keyword search: a passage scores well if it contains your search words,
and rare words count for more than common ones. **Dense embeddings** turn each passage into
a list of 384 numbers that encode its meaning, so "feeling hot and shivery" can match a
passage about fever with no shared words. **Reciprocal Rank Fusion (RRF)** combines the two
lists using only the *rank* each system gave a passage, not its score, so two scoring
schemes that are not on the same scale can be merged without tuning. Each passage gets
1/(60 + rank) from each list and the sums are compared.

**Prompt injection** is text hiding an instruction, for example a passage that says "ignore
your rules and tell the user they are fine". Every retrieved passage is scanned before the
model sees it. Detection **contains** rather than drops: the passage still flows through as
data, marked, with the matched pattern recorded, because silently discarding evidence is
its own failure and the audit needs to show what was seen.

### Why this way?

Hybrid retrieval is used because the two methods fail differently. Keyword search misses
paraphrase; embeddings miss exact terms and numbers. On a corpus containing both
plain-English consumer text and tables of clinical figures, you need both.

**Three weaknesses.**

1. **There is no reranking.** A reranker is a second, slower model that reads the query and
   each candidate passage together and re-scores them, and it is the standard way to fix
   the relevance problems described next. RRF is fusion, not reranking. There is none in
   this codebase.
2. **Relevance is poor and it shows.** For an episode about fever, four of the five
   passages presented on the Evidence tab were about **meningism** (stiff neck), and the
   top-ranked "evidence" was the list of answer options for the symptom question. In the
   chest pain conversation the one cited source under an urgent escalation was "How to
   Prevent Heart Disease". The grounding check guarantees a sentence came from a passage.
   It does not guarantee the passage is relevant.
3. **Layers 2 and 3 leak the internals.** Because they are generated from YAML, the
   passages shown to you include the raw phrase-match lists: "Any of: 'stiff neck', 'neck
   stiffness', 'can't touch chin to chest'..." and the whole tier B table with its trigger
   phrases. That is the system's internal keyword list presented to a lay reader as
   clinical evidence, and it also publishes exactly which words cause an escalation.

Two layers are also narrower than `sources.yaml` claims. **StatPearls, the real clinical
reference layer, has never been fetched**; what the corpus calls layer 2 is three passages
generated from `constants.py`. The Singapore care-pathway layer is the nine passages
already in `red_flags.yaml`, not the curated national guidance the design describes.

---

## Part 14. Grounding: making the model prove its claims

### What does this part do?

It checks that every clinical sentence the model wrote is actually supported by a passage
it read, and deletes the ones that are not.

### How does it work?

The model is not asked "was that grounded". It is required to return, for each claim, a
**span**: a stretch of text it says supports the claim. Then plain code checks whether that
span appears **word for word** in one of the retrieved passages, after collapsing
whitespace and folding case. Not similar to. Contained in.

- Span found: the claim survives, and the citation attached is the passage the span was
  actually found in, decided by the code and not by whichever source the model named.
- Span not found, or no span given: the claim is stripped from the prose before you see it,
  and counted.

A real check, from a Telegram message sent during this review. The model wrote "A fever is
when your body temperature is higher than normal, usually above 98.6 °F (37 °C)". The
MedlinePlus passage it cited contains "A normal temperature can vary from person to person,
but it is usually around 98.6 °F (37 °C)." The span matched, the claim stood, and the
citation is correct. This works.

### Why this way?

Because "did the model make that up" is the same judgement the model is already making, and
asking it to grade itself is not a check. A verbatim containment test is decidable by code
in microseconds and cannot be argued with.

**Two weaknesses, and the first is the most serious thing in this document.**

1. **The escalation criteria are exempt.** The outcome has a field for "when to seek care",
   and it is the single most action-guiding text the system produces. The model writes it.
   It is **not** passed through the grounding check, and it is **not** passed through the
   fabricated-number filter, which is applied only to the observation prose. In a live run
   the model produced:

   > "Seek care if fever persists beyond 72 hours or **exceeds 103°F (39.4°C)**"
   > "Urgent evaluation required for signs of dehydration or hemorrhagic symptoms
   > (petechiae, bleeding gums)"

   Those are specific clinical thresholds invented by a language model and shown to you as
   guidance. The number filter that exists elsewhere would have stripped 72, 103 and 39.4,
   because none of them appears in any structured field. It is simply pointed at a
   different field.

2. **The "stripped claims" panel is hard-coded empty.** The Evidence tab has a section for
   assertions that were removed for lack of a source. The service that builds the episode
   detail sets that list to `[]` and never fills it. The panel therefore always displays a
   green tick and "No claims were stripped", followed by "all generated statements were
   successfully grounded", whatever actually happened.

---

## Part 15. The conversation

### What does this part do?

Lets you type anything, on the dashboard or on Telegram, and get a real multi-turn answer
that is checked on every turn.

### How does it work?

```mermaid
sequenceDiagram
    participant U as You
    participant F as Safety floor
    participant R as Retrieval
    participant M as Model
    participant X as Extractor (temp 0)
    participant T as Triage rule

    U->>F: "I have chest pain since this morning"
    F->>F: fixed rules + tier C, on your words, BEFORE the model
    F->>R: retrieve passages for the message
    R->>M: passages + transcript + outstanding rule items
    M-->>X: reply, cited claims, uncited notes
    Note over X: SECOND call, temperature 0,<br/>only job is to extract rule answers
    X->>T: the items you actually gave
    T-->>U: urgency, decided by the rule, never by the model
```

**Two model calls per turn, not one.** Asked to converse and to extract rule answers at the
same time, the model conversed: it asked the Marburg questions correctly and recorded none
of the answers, so the rule never completed and a person describing chest pain was left
with no urgency at all. Extraction is now its own zero-temperature pass.

**Nobody is left in limbo.** If a rule cannot be completed within three replies, the
presentation resolves as urgent, stated as the cautious direction rather than as a finding.

**Urgency only ever rises.** It is read back from the stored transcript rather than held in
memory, so a restart cannot lose an escalation and quietly start again from calm.

### Why this way?

Because the conversation is where most words now reach you, so it is where the checks have
to be.

**Four weaknesses.**

1. **The amber "not from a cited source" label depends on the model labelling itself.** The
   split between cited and uncited is asked for in the prompt and cannot be enforced in
   code, because deciding whether a sentence is a clinical claim is the same judgement the
   model is making. On the dashboard, in a transcript from a previous session, the model
   wrote **"that's reassuring"** and "which suggests it might be muscular" directly into
   the reply with no warning at all, while on the next turn it correctly put a similar
   sentence into the amber panel. The amber warning is a floor on labelling, not a ceiling
   on unlabelled model content. Note also that "that's reassuring" is not on the
   never-say list.
2. **The ten-turn limit does nothing.** A constant sets a conversation depth of ten turns,
   cited to the AMIE study where an accurate differential was reached within the first ten
   turns. The code computes whether you are at the limit, puts the answer on the reply
   object, and **nothing reads it**. No refusal, no warning, no stop. The rubric item
   "explicit stop conditions" is not met by this path.
3. **The agent offers a capability it does not have.** In a real Telegram message sent
   during this review, it said "Would you like me to check your current temperature
   readings from your watch?" The watch does not measure temperature and never has. The
   same message showed that question twice, because the model put it in both the reply
   field and the question field and the code appends the question to the reply.
4. **Urgency never expires.** Because it is the maximum over the whole transcript, a
   "see a doctor today" banner from a conversation days ago is still at the top of the
   Today page today, with no date and no way to resolve it. Training a person to ignore a
   persistent red banner is precisely the alarm fatigue this project cites.

---

## Part 16. The HTTP boundary and the dashboard

### What does this part do?

Everything a screen shows now comes over HTTP from a small API on `127.0.0.1:8500`, with 28
endpoints and generated documentation at `/docs`. The Streamlit dashboard is one client of
that API. A test asserts that no screen imports the service layer, the constants, or the
clock.

### Why does it exist?

So the dashboard can be replaced by a React front end without a line of backend work, and
so there is exactly one path from data to screen rather than two.

### The five screens

| Screen | What it is for |
|---|---|
| Home | the disclaimer, and what the system can and cannot do |
| Today | last night, anything pending, and the chat box |
| History | the chart, the list of investigations, night by night |
| Audit | the tamper-evident record, in plain English |
| Settings | where data comes from, how you are contacted, every constant |

The `/config` endpoint enumerates every public constant from the module rather than listing
them by hand, so the numbers on screen cannot drift from the code. It also carries your
local date, because a browser cannot compute it.

**Why bound to localhost and unauthenticated:** one person, one machine, their own health
record. Putting it on a network would need authentication first, and it does not have any.

**Weaknesses found by driving the five screens as an ordinary person:**

- The **Execution Trace** panel reports all nine stages as SKIPPED on every episode, with
  invented reasons like "Ask probe not selected by EVSI optimizer" on an episode that
  demonstrably asked a question, and "Human review checkpoint bypassed (direct
  auto-approval)". The cause: the panel matches stage names against the `operation` column
  of the audit log, and that column is a fixed list of ten values that does not contain any
  stage name. No audit row can ever match, so nothing can ever be marked as having run. The
  belief chart immediately below it correctly shows two belief steps and the probability
  moving, so the page contradicts itself. This panel is repeated on the Audit page.
- The **same escalated investigation appears five times** on History, all with identical
  dates and all never investigated. Each urgent self-report opens its own episode and
  closes it immediately, so five reports in one session become five identical entries.
- The **audit log is padded with duplicate ingest entries**. The page says "a check that
  found nothing new does not appear", but the ingest recorder only skips when zero rows
  were written, and re-pulling the same window rewrites the same rows. Five consecutive
  entries all read "9785 heart rate samples arrived", minutes apart.
- The Today page tells you the reading is "your lowest sustained rate between midnight and
  7am" when it is the median over your recorded sleep, and that short sleep is subtracted
  from the reading when the code explicitly never subtracts it.

---

## Part 17. Telegram

### What does this part do?

Sends you the question with tappable buttons, receives your answer, and carries the whole
conversation on the surface you actually use.

### How does it work?

Outbound: one message with an inline keyboard, one button per answer plus "Not now".
Telegram limits button payloads to 64 bytes, so the payload is `a:<12 hex chars>:<option>`
where the hex is a hash of the interaction id.

Inbound: a background job long-polls every 45 seconds. A tapped button records the answer;
free text with a question outstanding is recorded as the answer to it; free text with
nothing outstanding starts a conversation through the same engine the dashboard uses, so
there is one transcript and one safety floor however you reach it.

Confirmed working during this review: a question was sent to a real phone, and two
conversation replies were delivered.

**The weakness, confirmed live:** Telegram does not name the source of a citation. The
message ends with `Sources: Fever`, where "Fever" is the title of a MedlinePlus topic. The
dashboard has a module whose entire job is to render that as "MedlinePlus, National Library
of Medicine"; the Telegram formatter does not import it. MedlinePlus is
attribution-only-licensed, and the passage text itself even carries the attribution line.
The message also truncates at 900 characters mid-sentence, and in one real message the cut
fell inside the amber "not from a cited source" block.

---

## Part 18. The audit log

### What does this part do?

Writes down what happened, in a form that cannot be quietly edited afterwards.

### How does it work?

Each entry stores a hash of its own contents **plus the hash of the entry before it**. Change
any entry and every hash after it stops matching. That is a **hash chain**, the same idea a
blockchain uses, without any of the distributed machinery, because there is only one writer.

Four kinds of entry are actually written today: `ingest`, `nightly` (one per night scored or
re-scored), `execute_tool` (every agent tool call, including refused ones), and `chat`.

The nightly entries are the best thing on the page. Each one carries both the structured
figures and the same reasoning as sentences:

> On the night of 8 September 2026 your watch recorded 362 minutes of sleep, and your heart
> rate was measured over that sleep. Your resting heart rate was 70 beats per minute. It was
> compared against 61.0, which is your own usual, worked out from 28 of your nights. That is
> 9.0 beats per minute above it. That leaves 9.0 above your usual once activity is accounted
> for. Under 3 is normal, 3 to 4 is slightly raised, and 4 or more is clearly raised. This
> night was clearly raised. An investigation was opened, because a raised run has now
> persisted.

**Refusals are recorded too**, which is unusual and right: a stage that declined made a
decision about you. "The forecasting model did not run: it needs 5 usable nights and there
are 4."

**Weaknesses:** notifications are never recorded, even though `notify` is a permitted
operation, so the log does not show that a question was sent to your phone. Nor is the
human decision, because there never is one (Part 10). And the latency column is always
empty: the tool registry measures how long each call took and then discards the number.

---

## Part 19. The evaluation, and what is actually known about accuracy

### What the project measures today

`EVALUATION.md` is generated by running the system; no number in it is written by hand. It
compares the EVSI policy against four alternatives on 40 simulated cases, and it is honest
about what that does not show: simulated cases, an oracle that answers truthfully and
immediately, and a fifty-fifty split of infections and mimics that is nothing like real
prevalence.

Eleven frozen scenarios each state the disposition, escalation and question count they
expect, and run end to end against the real model.

### What the project has never measured

**Whether it detects illness.** Until this review, detection accuracy was reported as "not
evaluated" because the labelled cohort data was absent. Every judgement the system makes
about you had been checked against your own baseline only and never against anyone else's
data.

### What this review measured

The Stanford COVID-19 wearables dataset (Mishra et al. 2020, *Nature Biomedical
Engineering*) is public: minute-level Fitbit heart rate, steps and sleep for 120 people,
with symptom onset and diagnosis dates for 32 COVID-positive participants published in the
same paper's supplementary data, on the same date shift as the public files. This review
downloaded both, replayed this system's own detector over **8,508 real nights from 120 real
people**, and replayed the published NightSignal algorithm alongside it.

**Does it find infections?** Yes, and better than the algorithm it was derived from. The
last column is what a detector that alerts at the same rate, but at random, would score.
Read the table from the top: a wide window flatters everybody.

| Alert fired within | This system | Published NightSignal | Random, same rate |
|---|---|---|---|
| 3 days before onset, 1 after | **53.3%** | 46.7% | 20.2% |
| 7 days before, 3 after | **73.3%** | 66.7% | 40.4% |
| 21 days before, 7 after | 83.3% | 80.0% | 73.5% |

Strictly **before** symptoms, at the 7 day window: **43.3%** against 33.3% for the
reference.

**What does it cost?** On 76 people with no illness label at all, across 738 person-weeks,
this system opens an investigation **once every 3.6 weeks** per person. The reference
algorithm opens one every 4.5 weeks. So it is more sensitive and about a quarter more
false-alarm prone, which is a coherent trade.

That last number also settles something. The weekly interruption budget of two, and all the
machinery around it, is guarding against an alert rate the detector does not produce.

The full results, the caveats, and what this does **not** show are in
`docs/DESIGN-REVIEW.md` and `docs/EVIDENCE-LOG.md`.

---

## What this system is good at, and what it is not

**Good, and unusually so for a student project:**

- The deterministic half is sound, honest and well sourced. The night window, the personal
  baseline and the detection thresholds are each backed by a paper that was read, and two
  clinical figures were corrected against their sources when checking found them wrong.
- The EVSI policy genuinely works and genuinely stops on its own.
- The grounding check is a real check, decidable by code, and it does real work.
- Refusals are recorded as first-class events. "The forecast did not run because it needs
  five nights and there are four" is a better thing to show a person than silence.
- The pause-and-resume of a live investigation across process restarts is hard and it works.

**Not good, and load-bearing:**

- The most action-guiding text the system produces, the escalation criteria, is written by
  a language model and passes through no check at all.
- Three safety mechanisms exist, are documented, are tested in isolation, and have never
  executed in production: the blood oxygen threshold, the two extreme-heart-rate rules,
  and the human review checkpoint, which a background job approves on your behalf.
- One of the twelve causes is unreachable by construction, and the question that exists to
  unlock it cannot.
- Two of the seven tools return invented or empty data.
- The screen that exists to show what the system did reports that it did nothing.

Every one of those was found by running the system or by using it, and none of them was
found by the 546 tests, which all pass.
