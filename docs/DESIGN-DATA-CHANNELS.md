# Which data this system uses, and why not more

**Status:** decided, 3 September 2026, on measurements taken from the live device and from
the simulation in `experiments/policy-simulation/`.

A reasonable question when you first see this project: Health Connect defines around sixty
kinds of health data, so why does this use seven of them? This is the answer, with the
evidence, so the reasoning can be checked rather than taken on trust.

---

## The short version

Nothing is being filtered out. The watch sends seven kinds of data and all seven are
stored. Four of them can change a conclusion.

Supporting the rest is not planned, because most of them have no bearing on whether
someone is getting ill, and the three that do are not recorded by this device and would
not fix the problem this system exists to solve.

---

## What arrives, and how far it gets

| Channel | Stored | Changes the conclusion |
|---|---|---|
| Heart rate | yes | **yes**, the overnight resting rate is what the whole system watches |
| Steps | yes | **yes**, how active the previous day was |
| Sleep stages | yes | **yes**, short sleep raises heart rate and is subtracted first |
| Workouts | yes | **yes**, a late workout raises it too, and is subtracted first |
| Blood oxygen | yes | no, see "captured but not used" below |
| Distance | yes | no, activity context; steps already carry the signal |
| Energy burned | yes | no, activity context |

Run `uv run wha data capability` to see this for whichever device is connected, including
any channel a richer device sends that this build does not parse.

**Nothing is discarded even so.** `store_raw` writes the entire payload verbatim with a
SHA-256 before anything is parsed, so a channel added later can be backfilled from data
already collected.

---

## Why the other channels are not supported

### Most of them are irrelevant

Health Connect covers weight, blood pressure, nutrition, hydration, floors climbed, VO2
max, cycle tracking and more. None of it bears on "is an overnight heart rate rise
explained by an infection". Supporting them would be work for no gain.

### Three of them would genuinely help, and this device does not record them

Heart rate variability, respiratory rate and skin temperature are the channels
`archive/prior-research/13-galaxy-watch5-data-reality.md` identifies as the strongest published feature
set for illness detection. All three are absent here:

- **Skin temperature.** Samsung exposes it from **Galaxy Watch 6 onward**
  (`archive/PROPOSAL.md` section 4.7). The device in use is a Watch 5. It will never arrive.
- **Heart rate variability and respiratory rate.** Not recorded by this watch, either
  because the feature is switched off or because it needs a manual reading that is not
  being taken.

Writing parsers for data that never arrives is how this repository previously acquired
five vitals streams, two of which did not exist and none of which were ever written to the
database. That mistake is not worth repeating.

### They also cannot be computed from what we have

Both need beat-level detail that the bridge does not deliver. Measured on the live device:
**one heart rate value every 60 seconds**, with minimum, average and maximum all equal, so
there is no within-minute variation reported at all.

- **Heart rate variability** is the variation between consecutive beats, in milliseconds.
  A one-minute average has already combined roughly sixty beats into a single integer. The
  quantity being measured is gone before the data leaves the watch.
- **Respiratory rate** can be recovered from heart rate through respiratory sinus
  arrhythmia, but that oscillation completes every four seconds or so. Detecting it needs
  sampling at least every two seconds. At one sample per minute the signal is not weak, it
  is absent.

The only route to either is an application running on the watch itself using the Wear OS
Sensor SDK, which can read inter-beat intervals directly. `research/13` estimates 16 to 40
hours of work for that.

---

## Would they have helped anyway? Modestly, and not with the hard part

Two measurements bound the answer.

**Heart rate alone already does most of the work.** NightSignal reaches **80 percent
sensitivity** using overnight heart rate only, in a prospective deployment
(`research/findings/F1`). It is also where this system's 3.0 and 4.0 bpm thresholds come
from.

**The best available figure for adding a thermal channel is about five points.** Mason
2022 improved ROC AUC from **0.770 to 0.819** by including dermal temperature, on its own
73-participant training set, using a finger sensor rather than a wrist. `research/findings/F1`
explicitly records that the widely repeated "5 to 8 percent boost" claim is
**unsubstantiated** and should not be cited.

**And none of it addresses the actual problem.** Infection, stress, poor sleep, alcohol and
the luteal phase all move these channels in the same direction. Goodale et al. 2019
(J Med Internet Res 21(4):e13404, n=193) found the luteal phase **lowers heart rate
variability while raising heart rate and respiratory rate**, the same signature as an
infection. Adding those sensors would tell you more precisely that something changed. It
would not tell you what changed.

A simulation of this, in `experiments/policy-simulation/`, behaves the way the argument
predicts: deciding on sensor readings alone does no better than chance at naming the cause,
and asking one well-chosen question does better. That simulation is self-scored and proves
nothing about a real person, but the design argument stands on its own: more sensors tell
you more precisely that something changed, and none of them tell you what changed it.

---

## Captured but not used: blood oxygen

Blood oxygen is the one arriving channel with real diagnostic relevance that does not reach
the decision. It is stored and shown to the agent, and deliberately cannot move the belief,
because `data/knowledge/causes.yaml` carries no likelihood relating a reading to any of the
twelve causes. Writing one is a clinical judgement, not a coding one.

Two things a human should weigh before that changes, both observed in the real data:

1. The readings are **spot measurements, not a stream**: five across seven days.
2. They are **noisy**. The observed set contains an 80 percent reading sixty-six seconds
   before a 92 percent one. A likelihood that does not model that noise will manufacture
   alarm.

Recorded in `docs/DISCLOSURES.md`.

---

## What would actually improve accuracy here

Not more channels. More nights.

The baseline needs roughly fourteen nights before it is judging a reading against the
person rather than against the population average, and twenty-eight before it is using
their history alone. At three nights the system is still mostly comparing against a
stranger. Consistent overnight wear moves accuracy considerably further than any sensor
that could be added.

---

## Sources

- Alavi et al. 2022, *Nature Medicine* 28:175-184 (NightSignal): 80 percent sensitivity,
  and the origin of the detection thresholds
- Mason et al. 2022, *Scientific Reports*: AUC 0.770 to 0.819 with dermal temperature
- Goodale et al. 2019, *J Med Internet Res* 21(4):e13404, n=193: luteal phase moves heart
  rate, respiratory rate and heart rate variability in the infection direction
- `archive/prior-research/13-galaxy-watch5-data-reality.md`: access paths and what each one exposes
- `archive/prior-research/findings/F1-clinical-infection-studies.md`: the corrected figures, including
  which commonly cited claims are unsupported
- `experiments/policy-simulation/`: the sensor-only versus asking comparison, self-scored
