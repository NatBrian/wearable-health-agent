# What is disclosed, and where

Every clinical design decision in this system is either backed by a citation or explicitly
recorded as unevidenced, and **each one is stated on screen as well as in this repository**.
A limitation that lives only in a markdown file is not disclosed to the person using the
system.

This page is the index. It exists so the rule can be checked rather than assumed.

---

## The standing disclaimer

`DISCLAIMER.md` has been in this repository since the beginning and **nothing in the
interface ever showed it**, so a person using the dashboard was never told it is not a
medical device. It is now rendered on the Home page, where a person lands, as a red banner
plus an expandable "What this system can and cannot do".

Source: `src/wha/ui/components/disclaimer.py`.

---

## Each limitation, its evidence, and where it is shown

| Limitation | Evidence | Shown on |
|---|---|---|
| Not a medical device; cannot diagnose | `DISCLAIMER.md` | **Home**, red banner |
| Needs 7 nights before it can alert at all | Alavi et al. 2022 (NightSignal): baseline established for over 80% of participants within seven nights | **Home** expander; **Today**, a warning while below the threshold; **History**, on the chart |
| Compares against your own median, not an average adult | Alavi et al. 2022: "the streaming median of average overnight RHR" per individual | **History**, chart notes and Full references |
| Only a *raised* heart rate is investigated | Scope decision, not a cited finding. Infection raises nocturnal RHR; a low rate is usually fitness | **Home** expander; **History**, beneath the chart |
| Naps are excluded | Whitehurst, Naji & Mednick 2018: heart rate is higher during daytime naps than overnight sleep at matched stages | **Home** expander; **History**, chart notes |
| Sleep apnoea cannot be detected | Design consequence: a nightly elevation is absorbed into a personal baseline | **Home** expander; **History**, chart notes |
| Measured over recorded sleep, with a clock fallback | Dial et al. 2025, validation of nocturnal RHR in consumer wearables | **History**, chart caption; per-night source on the night detail |
| The starting range is a population figure | Bloomfield et al. 2024, n=525 | **History**, chart caption and Full references |
| Nights with no reading are not judged | — | **Today**, stated separately from the quiet-night count |

---

## The reasoning behind each

- `docs/DESIGN-BASELINE-CENTRE.md` — why a night is compared against the person's own
  median, what the population-shrunk centre cost, and why nothing is flagged below seven
  nights.
- `docs/DESIGN-SLEEP-WINDOW.md` — why the window is the recorded sleep session rather than
  a fixed clock window, why naps are excluded, and why apnoea is out of reach.
- `docs/DESIGN-DATA-CHANNELS.md` — which of the device's channels are used and which are
  captured but cannot move the belief.
- `plan/BLOCKERS.md` — the decisions deliberately left to a human, including whether the
  step at seven nights should be smoothed and whether one population mean is the right
  cold-start prior across ages and sexes.

---

## The rule this page serves

A clinical design choice must be the most accurate option under medical best practice and
backed by study or research cited next to the number it justifies. Where research does not
settle a question, the choice is still made explicitly, written down here, and **disclosed
in the dashboard** rather than left for the reader to discover. The user must be able to
see what the system can and cannot do without reading the source.
