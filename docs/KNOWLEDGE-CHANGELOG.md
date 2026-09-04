# Changes to the read-only knowledge files

`data/knowledge/` and the clinical constants in `src/wha/constants.py` are authored by a
human and are not the agent's to rewrite. That rule exists because a wrong number in them
becomes a retrievable, citable passage, and the citation makes it look more trustworthy
rather than less.

One narrow exception is now allowed, granted explicitly on 4 September 2026: **a figure may
be corrected when the published source can be quoted contradicting it.** No new clinical
content may be added, no figure may be changed on judgement, and every edit is recorded
here with the source, the old value, the new value and what it changed downstream.

If an entry below cannot be checked against its paper in a couple of minutes, it should not
have been made.

---

## 2026-09-04 — `causes.yaml`, luteal citation string

**Changed:** wrist skin temperature `+0.44 C` to `+0.45 C`, respiratory rate `+0.60/min` to
`+0.47/min`.

**Source:** Goodale BM, Shilaih M, Falco L, Dammeier F, Hamvas G, Leeners B. Wearable
sensors reveal menses-driven changes in physiology and enable prediction of the fertile
window. *J Med Internet Res.* 2019;21(4):e13404.

**Working:** the paper reports phase means. Late luteal wrist skin temperature 34.32 C
against follicular 33.87 C, a difference of **0.45**. Late luteal respiratory rate 17.04
breaths/min against follicular 16.57, a difference of **0.47**.

**Downstream effect: none.** Neither wrist skin temperature nor respiratory rate is
ingested by this build; the Galaxy Watch 5 does not provide either at a usable sampling
rate. The heart rate figure in the same string, +3.91 bpm, is the only one the belief model
computes with, and it was already exactly right (60.47 - 56.56).

**Why it mattered anyway:** that string is rendered into the retrievable corpus as a
citable passage. A reader checking the agent's evidence would have found two figures that
do not match the paper, which undermines every figure beside them.

---

## 2026-09-04 — `constants.py`, `EXERCISE_EFFECT_BPM`

**Changed:** `{"0-2h": 4.14, "2-4h": 2.91, "4-6h": 1.58}` to
`{"0-2h": 2.91, "2-4h": 1.87, "4-6h": 1.58}`.

**Source:** Leota J, et al. Dose-response relationship between evening exercise and sleep.
*Nat Commun.* 2025;16:3297. Kept at `research/papers/leota-2025-nat-commun-16-3297.pdf`
(open access, CC BY), because the publisher blocks automated fetching and a figure that
cannot be re-checked is not really verified.

**Working:** the paper's table gives incremental contrasts between adjacent strain levels.
High strain against no exercise is their sum: 1.58 bpm at -6h, 1.87 at -4h, 2.91 at -2h,
5.59 at sleep onset. Of the three stored values, 2.91 and 1.58 are exactly the paper's
figures at -2h and -6h, and 4.14 appears nowhere in the table. The two traceable values
were also assigned to bands one step apart from each other, so there was no single
convention. Full derivation in `docs/CORPUS-VERIFICATION.md`.

**Rule applied:** each band takes the paper's value at the edge furthest from sleep onset,
which is the smallest figure the paper supports for that band.

**Downstream effect, measured.** This quantity is subtracted from the observed elevation,
so lowering it raises the residual and makes the system slightly more likely to
investigate. That is the direction this system's own utilities prefer, weighing a missed
illness nine times a false alarm. All eleven frozen scenarios still pass, including
`workout-explained`, which is the one that depends on a workout explaining a night away.
Two unit tests asserted the literal 4.14; both were corrected to the sourced value with the
reason recorded, and neither assertion was weakened.
