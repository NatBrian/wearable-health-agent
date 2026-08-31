# 13. Galaxy Watch 5: what data is actually available

**Status:** Correction to an earlier claim. Verified 2026-08-30.
**Why this exists:** an earlier note claimed the Galaxy Watch gives only heart rate, sleep and activity, and that HRV, respiratory rate and skin temperature were unavailable. **That was wrong.** It was true of one access path and I generalised it to all of them.

---

## The correction

`findings/F5-wearable-apis-and-latency.md` established that the **Samsung Health Data SDK** has no HRV type and no respiratory-rate type, and that Samsung Health does not write HRV, breathing rate or resting heart rate into Health Connect. Both statements remain correct.

**But those are the live, programmatic paths.** The **manual data export** is a completely different route and it is much richer. I conflated the two.

Verified by reading the source of an open-source parser (`Devasy/samsung-health-sdk`, MIT, Python), which has dedicated modules for exactly the metrics I said were missing. The export uses Samsung's internal namespaced identifiers as filenames:

| Metric | Export identifier | Granularity |
|---|---|---|
| Heart rate | `com.samsung.shealth.tracker.heart_rate` | **Per-minute**, via binning JSON (`heart_rate`, `heart_rate_min`, `heart_rate_max`) |
| **HRV** | `com.samsung.health.hrv` | Session-level CSV, with **SDNN and RMSSD in the binning JSON** |
| **Respiratory rate** | `com.samsung.health.respiratory_rate` | **Per-minute**, via binning JSON |
| **Skin temperature** | `com.samsung.health.skin_temperature` | Per reading |
| Stress | `com.samsung.shealth.stress` | Per reading |
| SpO2 | `com.samsung.shealth.tracker.oxygen_saturation` | Per reading |
| Sleep stages | `com.samsung.health.sleep_stage` | Per stage transition (codes 40001-40004 = Awake, Light, Deep, REM) |
| Sleep sessions | `com.samsung.shealth.sleep` | Per night summary |
| Sleep raw | `com.samsung.shealth.sleep_raw_data` | Accelerometer / PPG derived |
| Exercise | `com.samsung.shealth.exercise` | Per session |
| Movement | per-minute activity levels | Per-minute |

Samsung's own materials confirm the Galaxy Watch 5 records **respiratory rate, heart rate variability, skin temperature and blood oxygen as sleep vital signs**, and the Watch 5 is the first model with the infrared skin temperature sensor (enabled by firmware update, initially surfaced through cycle tracking).

---

## What this changes

**1. The biophysical triad is available after all.** Cardiac (HRV, resting HR), thermal (skin temperature) and pulmonary (respiratory rate) can all be obtained. This is the exact channel set Oura and TemPredict use, and it is the strongest published feature set for illness detection.

**2. Doc 12's central criticism of the archived flagship is partly withdrawn.** I said their "Biomarker Sentry" could not run because its triad needed channels the watch does not expose. On the **export path it can run.** Their idea was more feasible than I credited. The other criticisms (fabricated numbers, a ranking that selected the union of its own options) still stand.

**3. Doc 06 gate G11 is wrong as written and is superseded by this document.**

**4. The Stanford-cohort alignment argument weakens slightly.** I argued the watch's channel set conveniently matched the public dataset (heart rate and steps only). It now exceeds it, which is a good problem: methods can be developed on the public data and *enriched* on personal data.

---

## The distinction that actually matters: rich but slow, versus poor but live

| Path | Channels | Latency | How you get it |
|---|---|---|---|
| **Manual export** | **Everything above**, including HRV, respiratory rate, skin temperature, per-minute HR | **Historical only.** You press a button and download a ZIP | Samsung Health app, Settings, Download personal data. No developer signup, no approval, free |
| **Health Connect** | Heart rate, steps, sleep stages, exercise. **No HRV, no respiratory rate** from Samsung | Minutes to hours | Android app + permissions |
| **On-watch Sensor SDK** | 1 Hz heart rate and inter-beat intervals, 25 Hz raw PPG, 1 Hz skin temperature | 1 to 15 seconds | Wear OS app, developer mode. 16 to 40 hours of build |

**Consequence for the project design.** The illness decision is nightly, so the rich export path is the one that matters for the actual reasoning. Live streaming would only serve the demo, and the demo can use time-warped replay. So we should build on the export, and treat any live element as optional decoration rather than a dependency.

---

## What is still unverified, and only a real export can settle it

The export *schema* supports these metrics. Whether **a given watch has actually been populating them** depends on settings and wear habits, and cannot be determined remotely.

| Question | Why it is uncertain |
|---|---|
| Is `com.samsung.health.hrv` populated? | HRV may only be written when a stress measurement is taken, rather than continuously |
| Is `com.samsung.health.respiratory_rate` populated? | Requires sleep tracking to have been enabled and the watch worn overnight |
| Is `com.samsung.health.skin_temperature` populated? | The Watch 5 feature arrived by firmware update and was initially surfaced through cycle tracking. Whether it records for a user who does not use cycle tracking is **the single most important open question** |
| How many nights of history exist? | Determines whether a 28-day personal baseline is even computable |
| What fraction of nights have full coverage? | Non-wear and charging create gaps |

---

## Reusable open-source code found

| Repo | What it is | Licence | State |
|---|---|---|---|
| [`Devasy/samsung-health-sdk`](https://github.com/Devasy/samsung-health-sdk) | Python parser for Samsung Health exports into pandas. Modules for HRV, respiratory rate, skin temperature, stress, SpO2, heart rate, sleep, exercise, movement. Handles BOM encoding, namespaced headers, UTC offsets, lazy JSON loading | **MIT** | Created Mar 2026, last push Apr 2026, 1 star. New and unproven, but MIT and readable. Worth using as a reference for the file format even if we write our own loader |
| [`davidmosiah/samsung-health-mcp`](https://github.com/davidmosiah/samsung-health-mcp) | Local MCP server exposing Samsung Health export data as agent tools | **MIT** | Created May 2026, last push 29 Aug 2026, 11 stars. Actively maintained. **Directly relevant**: it turns the export into typed tools an agent can call, which is the interface pattern this project needs |
| [`lionheart/health-csv-importer-samsung`](https://github.com/lionheart/health-csv-importer-samsung) | Converts Samsung export to Apple Health format | - | Useful only as a second source on the CSV schema |

The MCP server is the more interesting find. It matches the "typed, enumerated, least-privilege tools" pattern that doc 10 concluded the agent should use, and it means the data-access layer may be largely solved rather than built.

---

## Immediate action

Run **Samsung Health, Settings, Download personal data**, then check which of the identifiers above are present and non-empty, how many nights they cover, and whether skin temperature has any values. That single file resolves every open question in the table above and takes a few minutes.

**Sources:**
- [Devasy/samsung-health-sdk](https://github.com/Devasy/samsung-health-sdk)
- [davidmosiah/samsung-health-mcp](https://github.com/davidmosiah/samsung-health-mcp)
- [Samsung: skin temperature on Galaxy Watch (developer codelab)](https://developer.samsung.com/codelab/health/skin-temperature.html)
- [Samsung UK: skin temperature sensor with Samsung Health](https://www.samsung.com/uk/support/apps-services/how-to-use-the-menstrual-skin-temperature-sensor-with-samsung-health/)
- [Samsung: sleep tracking on Galaxy Watch 5](https://ushl.samsung.com/ae/support/mobile-devices/sleep-tracking-on-your-samsung-galaxy-watch-5)
- [Samsung Newsroom: Galaxy Watch5 holistic health](https://news.samsung.com/global/samsung-leads-holistic-health-innovation-with-galaxy-watch5-and-galaxy-watch5-pro)
