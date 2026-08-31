# 14. Automatic (no-export) data access, and a competitor that just shipped

**Status:** Research finding. Two items, one architectural and one strategic.
**Date:** 2026-08-30
**Trigger:** the developer requires automatic data flow with no manual export, Galaxy Watch 5 for MVP, extensible to other watches, reusing open source where possible.

---

## Part 1: THE BIG ONE. Samsung shipped our detection layer in June 2026

**Samsung Health "Vitals"**, announced June 2026, does the following:

- Analyses **five overnight bio-signals** on waking: heart rate, heart rate variability, respiratory rate, skin temperature, blood oxygen.
- Compares each against the user's **own resting baseline**.
- Uses **machine learning to identify statistically significant deviations**.
- **Notifies only when thresholds are exceeded**, explicitly to avoid alert fatigue.
- Is marketed as helping the user *"better determine whether you are fighting an illness or just need more rest"*, and to spot *"early signs of physical fatigue or potential illness before symptoms manifest."*

That is, almost line for line, the passive half of the original project idea. Personalised baselines, multi-signal fusion, statistical deviation detection, restraint about notifications, pre-symptomatic framing.

### Two ways to read this, and both are true

**As a threat.** Building "detect deviations in overnight vitals against a personal baseline" is now building something that ships on the user's own watch. Any project whose headline is detection is dead on arrival: the reviewer can open Samsung Health and see it.

**As a gift, and this is the stronger reading.** Samsung's own marketing copy poses a question and then does not answer it:

> *"helping you better determine whether you are fighting an illness or just need more rest"*

**It does not determine that. It notifies you and leaves you to guess.** It cannot, because the two states are physiologically near-identical on those five signals, and Samsung has no mechanism for acquiring the information that would separate them. Distinguishing them requires knowing whether you trained hard, drank, slept badly, or have a sore throat, and Samsung never asks.

So the gap statement for the report writes itself, in the competitor's own words:

> In June 2026 Samsung shipped Vitals, which detects deviations across five overnight signals and tells the user it may mean illness or may mean they need rest. **It cannot tell them which. This project answers that question.**

This is a far stronger framing than anything invented, because it is not a claimed gap, it is a shipped product's admitted limitation.

### What this changes in the project

1. **Do not compete on detection.** Replicate it cheaply (NightSignal-class, under 100 lines) or read Samsung's own signal, and spend the budget on the part Samsung does not do.
2. **The "sick or just wrecked?" framing (doc 12, R2) is now validated by the market.** Samsung thinks the question is worth putting on a marketing page.
3. **Multi-signal fusion is confirmed as the right substrate**, and is now the industry-standard approach rather than a research idea.
4. **Novelty must sit in: asking, reasoning about competing causes, grounding in evidence, and explaining.** Exactly where doc 10 already placed it.

---

## Part 2: Automatic data access without a manual export

### The three Samsung routes, compared

| Route | Rich channels? | Automatic? | Gating | Fit |
|---|---|---|---|---|
| **Manual export ZIP** | **Yes**: per-minute HR, HRV (SDNN/RMSSD), respiratory rate, skin temperature, SpO2, sleep stages | **No.** User presses a button | None | Rejected as the product path. Still useful once, see below |
| **Health Connect** (Android app reads it) | Reported to include **HRV, respiratory rate, skin temperature** from Samsung Health | **Yes**, background reads | **Self-serve. No approval, no OAuth, no fee** | **The MVP route** |
| **Samsung Health Platform API** (server side, OAuth) | Rich: continuous HR, HRV, stress, SpO2, respiratory rate, sleep stages, 80+ workout types | **Yes**, cloud | Developer programme application, **5 to 15 business days approval** | Too slow for a two-week build. Correct for "later" |

**Conclusion: Health Connect is the automatic route for the MVP.** It needs a small Android component to read the data and forward it, but it requires no approval and no waiting.

### The extensibility answer: Open Wearables

[`the-momentum/open-wearables`](https://github.com/the-momentum/open-wearables)

| Property | Value |
|---|---|
| Licence | **MIT** |
| Stars / forks | **2,426 / 461** |
| Language | Python (FastAPI), React frontend |
| Stack | FastAPI, PostgreSQL, Redis, Celery, self-contained auth |
| Setup | `docker compose up -d` |
| Created / last push | Oct 2025 / **29 Aug 2026** (yesterday) |
| Status warning | *"early-stage project under active development. APIs may change before version 1.0."* Pin a version |

**Providers, and how each connects:**

| Connection type | Providers |
|---|---|
| **Cloud / OAuth** | Garmin, Oura, Whoop, Suunto, Polar, Ultrahuman, Strava, Fitbit, Google Health API |
| **SDK on device** | **Samsung Health**, Apple HealthKit, Google Health Connect |

Their own explanation of the split: *"On-device platforms like Apple HealthKit, Samsung Health, and Google Health Connect require shipping a mobile SDK, because that data is only readable on the phone, but need no OAuth or program approval."*

They ship an **Android SDK in Kotlin** covering Samsung Health and Health Connect, with Flutter and React Native wrappers. Data is normalised into a consistent schema across every provider, so application code does not need per-vendor logic.

**This is a direct answer to the requirement.** It gives automatic ingestion, it is MIT, it is actively maintained at real scale, it already supports Garmin, Oura, Whoop, Fitbit, Polar, Suunto, Ultrahuman and Apple alongside Samsung, and the normalisation layer means expanding beyond the Galaxy Watch 5 later is a configuration change rather than a rewrite.

### Recommended data architecture

```
 Galaxy Watch 5
 | (automatic, Samsung's own sync)
 v
 Samsung Health on phone
 | (automatic)
 v
 Health Connect <-- small Android reader component
 | (automatic push)
 v
 Open Wearables (self-hosted, Docker, normalised schema)
 | REST
 v
 Our agent + detector (local Python)
```

**One pragmatic exception to "no manual export".** A personal baseline needs 2 to 4 weeks of history, and on day one a live feed has none. So a **single optional export at onboarding** to backfill history is worth keeping, not as an ongoing chore but as a one-time bootstrap. After that, everything is automatic. If Health Connect turns out to carry enough history, even that step disappears.

This also solves a development problem: the export gives us months of real data to build and test against immediately, while the live path is being wired up.

---

## Part 3: A correction and a new uncertainty

**Skin temperature on Galaxy Watch 5 is now in doubt.** Samsung's developer-facing documentation states skin temperature is *"available on Galaxy Watch 6 and newer"*. The Watch 5 has the infrared sensor and Samsung enabled it for consumers through the cycle tracking feature, but **developer access may begin at Watch 6.**

So doc 13's channel table needs one qualification: HRV, respiratory rate, heart rate, SpO2 and sleep stages look available on the Watch 5. **Skin temperature is uncertain and may be consumer-visible but developer-invisible.**

This matters less than it would have, because the other four of Samsung's five Vitals signals are still available, and detection built on HR, HRV and respiratory rate is well supported by the literature.

**Only a real device export or a Health Connect read can settle it.**

---

## Sources

- [the-momentum/open-wearables](https://github.com/the-momentum/open-wearables)
- [Open Wearables integrations](https://openwearables.io/integrations)
- [Open Wearables: Samsung Health API for developers](https://openwearables.io/blog/samsung-health-api-galaxy-watch-data-for-developers)
- [Samsung Developer: accessing Samsung Health data through Health Connect](https://developer.samsung.com/health/blog/en/accessing-samsung-health-data-through-health-connect)
- [Samsung Newsroom: next-gen Galaxy Watch AI health features](https://news.samsung.com/global/samsung-introduces-next-gen-galaxy-watch-features-for-ai-powered-everyday-health-companion)
- [GSMArena on the Samsung Health update](https://www.gsmarena.com/samsung_health_app_update_new_galaxy_watch_features-news-73127.php)
- [Android Authority on Samsung Health Vitals](https://www.androidauthority.com/what-i-hope-samsung-health-update-fixes-vitals-3674569/)
