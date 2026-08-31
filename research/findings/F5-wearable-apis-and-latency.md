# F5 — Wearable Data Access and Real-Time Feasibility

Research date: 2026-08-30
Scope: how data actually gets from a wrist to a Python process, and how long that takes.
Devices the team owns: **Samsung Galaxy Watch**, **WHOOP**.

Every claim below carries a URL. Where official documentation and developer-community
experience disagree, both are reported. Claims I could not confirm against a primary
source are marked **UNVERIFIED**.

---

## 1. Executive summary — how real-time can this actually be?

**The honest answer: the vendor cloud APIs are not real-time and cannot be made real-time.
Real-time is only achievable by bypassing the cloud entirely and reading the sensor
directly — either with a Wear OS app you write and install on the Galaxy Watch, or over
the WHOOP BLE heart-rate broadcast.**

Three tiers exist, and they are separated by orders of magnitude:

**Tier 1 — genuinely real-time (sub-second to ~15 s), requires you to write device code**
- **Galaxy Watch + your own Wear OS app.** Samsung Health Sensor SDK gives heart rate + inter-beat
 interval at 1 Hz, PPG green/IR/red raw at 25 Hz, accelerometer at 25 Hz, skin temperature at 1 Hz,
 streamed to a listener callback on the watch, batched at intervals such as ~12 s for PPG green
 ([data specs](https://developer.samsung.com/health/sensor/guide/data-specifications.html)).
 You then relay to the phone over the Wearable Data Layer and from the phone to your laptop.
 **This is the only path in this whole report that gives continuous nocturnal streaming of
 raw physiology.**
- **WHOOP BLE Heart Rate Broadcast.** WHOOP implements the standard Bluetooth Heart Rate Service
 (0x180D) so it can pair with gym equipment, Zwift and Peloton. A laptop with `bleak` can
 subscribe and receive BPM plus RR intervals in ~1 s
 ([whoop-live](https://github.com/grivera82/whoop-live)). No official API, no OAuth, but also
 no raw PPG, no temperature, no accelerometer, and only one BLE connection at a time.

**Tier 2 — minutes to hours, polling or delayed push (the "phone-mediated" tier)**
- Samsung Health Data SDK / Health Connect on the phone. Samsung Health writes to Health Connect
 "as soon as data is created or changed", but the *Galaxy Watch → phone* hop
 "follows its own policy" for battery reasons
 ([Samsung Health Connect FAQ](https://developer.samsung.com/health/health-connect-faq.html)).
 Continuous heart rate is *deliberately* delayed. Developers report Samsung Health sometimes
 taking **more than a day** to start writing to Health Connect at all.
- Fitbit: device syncs roughly every 15 minutes with all-day sync on, then server-side processing
 adds 10 minutes to an hour before third-party apps see it.

**Tier 3 — once per night, after you wake up (the "daily summary" tier)**
- **WHOOP REST API.** Recovery does not exist until the sleep cycle closes. Querying recovery
 before the user wakes returns nothing. Webhooks fire only once WHOOP has *processed* the sleep.
 Practical availability window is 6–10 AM local
 ([Open Wearables analysis](https://openwearables.io/blog/whoop-api-recovery-strain-sleep-data-for-developers)).
- **Oura.** The ring syncs to the phone every few hours and the app pushes to Oura Cloud in the
 morning after sleep analysis completes.

**What this means for a nocturnal early-warning system.** If the demo must show a physiological
anomaly at 03:00 producing an alert at 03:00, then **WHOOP's REST API, Oura, Fitbit, Garmin and
Health Connect are all disqualified** — they will surface that event somewhere between 6 AM and
the following afternoon. Only a custom Wear OS app on the Galaxy Watch (Tier 1) or the WHOOP BLE
broadcast (Tier 1) can do it. The Galaxy Watch path is the stronger one because it yields raw PPG,
IBI and skin temperature rather than just BPM.

**Effort reality check.** WHOOP REST API to first data in Python: ~2–4 hours. WHOOP BLE to first
data in Python: ~1–3 hours (plus device-dependent risk). Galaxy Watch custom Wear OS app to first
data in Python: **realistically 2–5 days** — you need Android Studio, a Wear OS module, a phone
companion module, the Wearable Data Layer, and a phone→laptop bridge. Samsung's own codelab covers
the watch→phone half and is genuinely usable
([codelab](https://developer.samsung.com/codelab/health/heart-rate-data-transfer.html)).

**The single most important structural fact.** Every consumer wearable cloud API is built around
*scored daily summaries*, not *streams*. WHOOP does not expose a heart-rate time series at all
([Terra's own writeup confirms this gap](https://tryterra.co/blog/whoop-integration-series-part-2-data-available-from-the-api-ec4337a9455b)).
Samsung Health's Data SDK has **no HRV data type and no respiratory-rate data type**
([DataType reference](https://developer.samsung.com/health/data/api-reference/-shd/com.samsung.android.sdk.health.data.request/-data-type/index.html)).
Fitbit is the only consumer platform with genuinely fine-grained intraday endpoints — and it is
being shut down in September 2026.

---

## 2. Verification verdict table

| Prior claim | Verdict | Evidence |
|---|---|---|
| "Fitbit legacy API deprecated September 2026, migrating to Google Health API" | **VERIFIED** | "In September 2026, the legacy Fitbit Web API will be turned down and will no longer sync data." Side-by-side running May–Sept 2026; OAuth tokens do not transfer, every user must re-consent. [developers.google.com/health/about](https://developers.google.com/health/about) |
| "Oura API v2 has self-serve instant Personal Access Token" | **REFUTED (stale)** | Oura's own auth docs now list the PAT page as "Personal Access Tokens **[Deprecated]**". Secondary sources state PATs were deprecated December 2025, no new ones can be created, and new integrations must use OAuth2. [cloud.ouraring.com/docs/authentication](https://cloud.ouraring.com/docs/authentication) |
| "Oura push webhooks ~30s post-mobile-sync" | **UNVERIFIED / misleading** | No Oura official latency statement found. Webhooks exist (`/v2/webhook/subscription`, create/update/delete on `sleep`, `daily_sleep`, `daily_readiness`, `daily_activity`, `daily_spo2`, `daily_stress`, `workout`, `session`, `tag`). But the binding constraint upstream is that the ring syncs to the phone only every few hours and the app pushes sleep analysis to the cloud the following morning — so "30 s after sync" is technically possible while still meaning "hours after the physiological event". [Oura API support article](https://support.ouraring.com/hc/en-us/articles/4415266939155-The-Oura-API) |
| "Oura 5000 requests per 5 minutes" | **VERIFIED (secondary sources only)** | Multiple independent client libraries and integration guides state 5000 requests / 5 minutes with 429 on exceed. Could not load Oura's own rate-limit page (JS-rendered). Treat as high-confidence but not primary-sourced. |
| "Garmin Health API is enterprise B2B only, vetted" | **VERIFIED** | "available for enterprise use" / "only for business use"; individual applications not permitted. Approval confirmation within two business days, integration 1–4 weeks. [Garmin Program FAQ](https://developer.garmin.com/gc-developer-program/program-faq/) |
| "Garmin … NDA, fee/volume minimums" | **PARTIALLY REFUTED** | Garmin's FAQ says "There are **no** licensing or maintenance fees" for program access, but "some metrics may require a license fee payment or minimum device order quantity for commercial use" — specifically Beat-To-Beat Interval data. **NDA is not documented anywhere I could find.** [Garmin Health API](https://developer.garmin.com/gc-developer-program/health-api/) |
| **New, more important Garmin finding the prior model missed** | **Garmin has PAUSED new API access requests.** As of August 2026 applicants receive "Temporarily paused the review and approval of new API access requests"; the access-request form has been removed; no waitlist, no ETA. Existing partners unaffected. **Garmin is effectively unobtainable for this project regardless of gating terms.** [Garmin Forums](https://forums.garmin.com/apps-software/mobile-apps-web/f/garmin-connect-web/436199/garmin-connect---program-on-hold), [Momentum writeup](https://www.themomentum.ai/blog/garmin-developer-program-closed-roadmap) |
| "Apple HealthKit has no native cloud REST API" | **VERIFIED** | "There is no server-side Apple Health API; your iOS app must read HealthKit data on device and upload it to your backend." [Open Wearables](https://openwearables.io/blog/getting-apple-health-data-into-your-backend) |
| "Apple HealthKit … no native real-time streaming" | **PARTIALLY REFUTED (too strong)** | There is no *cloud* streaming, correct. But on-device, `HKObserverQuery` + `enableBackgroundDelivery(for:frequency:)` with `HKUpdateFrequency.immediate` wakes your app when data lands, and on watchOS `HKLiveWorkoutBuilder`/`HKWorkoutSession` delivers live heart rate. Apple's own entitlement `com.apple.developer.healthkit.background-delivery` exists for exactly this. [HKObserverQuery](https://developer.apple.com/documentation/healthkit/hkobserverquery), [background-delivery entitlement](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.healthkit.background-delivery) |
| "Fitbit offers 1-second and 1-minute intraday heart rate, and 5-minute HRV" | **VERIFIED, with two caveats** | HR intraday detail levels are `1sec`, `1min`, `5min`, `15min`. Caveat 1: "The '1sec' detail-level may not always return data in 1 second sampling outside of a recorded exercise." Caveat 2: HRV intraday returns every 5 minutes but **only collects during sleep** and only if the Health Metrics tile is enabled. [Get HR Intraday by Date](https://dev.fitbit.com/build/reference/web-api/intraday/get-heartrate-intraday-by-date/), [Intraday index](https://dev.fitbit.com/build/reference/web-api/intraday/) |

**Additional correction the prior model did not have:** Samsung Health SDK for Android was
**deprecated 31 July 2025**; the replacement is the Samsung Health Data SDK (v1.1.0, 12 March 2026).
Any tutorial or code sample referencing `com.samsung.android.sdk.healthdata` / `HealthDataStore`
from the old SDK is dead.
[Deprecation notice](https://developer.samsung.com/sdp/news/en/2025/10/30/dev-insight-oct-2025-move-to-samsung-health-data-sdk-as-samsung-health-sdk-for-android-deprecates-and-other-latest-news),
[release notes](https://developer.samsung.com/health/data/release-note.html)

---

## 3. THE LATENCY TABLE

Sensor-to-readable = wall clock between the physiological event on the body and the moment your
Python process can read it.

| Path | Sensor→readable delay | Push or pull | Data during sleep? | Continuous streaming? | Evidence |
|---|---|---|---|---|---|
| **Galaxy Watch — your own Wear OS app (Samsung Health Sensor SDK) → Data Layer → phone → laptop** | **~1–15 s.** HR+IBI sampled 1 Hz, PPG 25 Hz; events batched (e.g. ~12 s for PPG green). Add ~0.1–1 s for BT relay to phone and a local socket/HTTP hop to the laptop. | **Push** (SDK tracker callback → `MessageClient`) | **YES** — this is the only path that works reliably overnight, provided you run a foreground service | **YES** — raw PPG green/IR/red 25 Hz, accel 25 Hz, HR+IBI 1 Hz, skin temp 1 Hz | [data specs](https://developer.samsung.com/health/sensor/guide/data-specifications.html), [codelab](https://developer.samsung.com/codelab/health/heart-rate-data-transfer.html) |
| **Galaxy Watch — plain Android `SensorManager` `TYPE_HEART_RATE` wake-up sensor + foreground service** | **~1–5 s** (BPM only) | **Push** (sensor listener) | **YES** — the wake-up sensor variant + `FOREGROUND_SERVICE_TYPE_HEALTH` explicitly prevents the watch pausing your app after 60 s of screen-off | Partial — BPM only, no IBI, no PPG | [Samsung dev blog, 23 Apr 2026](https://developer.samsung.com/galaxy-watch/blog/en/2026/04/23/continuous-heart-rate-tracking-on-galaxy-watch-even-with-the-screen-off) |
| **Galaxy Watch → Samsung Health app → Samsung Health Data SDK (phone)** | **minutes to many hours.** Watch→phone sync "follows its own policy" for battery; continuous HR is *deliberately* delayed; sync is triggered by watch reconnect, opening Samsung Health, or pull-to-refresh | **Pull** (`readData` / `readChanges`) | **Mostly NO** — sleep data is processed once the watch reconnects to the phone | No | [Samsung HC FAQ](https://developer.samsung.com/health/health-connect-faq.html), [Samsung HC blog](https://developer.samsung.com/health/blog/en/accessing-samsung-health-data-through-health-connect) |
| **Galaxy Watch → Samsung Health → Health Connect → your Android app** | Same as above plus ~0 (Samsung Health writes to HC "as soon as data is created or changed"). **But developers report Samsung Health taking >1 day to begin writing to HC, and some users get nothing at all.** | **Pull** (Changes API tokens; no push callback) | Mostly NO | No | [Samsung HC FAQ](https://developer.samsung.com/health/health-connect-faq.html); community reports in §9 |
| **WHOOP REST API v2 (recovery / sleep / cycle)** | **6–14 h for a nocturnal event.** "Recovery data is not real-time: it is only available after a sleep cycle completes." Practical window 6–10 AM local. | **Push** (webhook) — but the webhook only fires *after* WHOOP processes the sleep | **NO.** Categorically. There is no in-sleep query. | **NO** — the API exposes no heart-rate time series at all | [Webhooks](https://developer.whoop.com/docs/developing/webhooks/), [Open Wearables](https://openwearables.io/blog/whoop-api-recovery-strain-sleep-data-for-developers), [Terra](https://tryterra.co/blog/whoop-integration-series-part-2-data-available-from-the-api-ec4337a9455b) |
| **WHOOP BLE Heart Rate Broadcast → laptop (`bleak`)** | **~1 s** (standard BLE HR Service notify rate) | **Push** (GATT notify) | **Probably yes, if broadcast stays on and laptop is in range — NEEDS EMPIRICAL TEST.** Broadcast is a user-toggled mode intended for workouts; it is reported to reset after app/firmware updates. | **YES** but only BPM + RR intervals | [whoop-live](https://github.com/grivera82/whoop-live), [the5krunner](https://the5krunner.com/2023/12/28/whoop-broadcast-your-heart-rate-over-ant/) |
| **Fitbit Web API (legacy, dies Sept 2026)** | **~15 min – 1 h.** Tracker syncs every ~15 min with all-day sync; server processing adds "around ten minutes (or up to an hour)". | **Push** (subscriptions/webhooks, "near real-time" after sync) + pull | Partial — intraday HR/HRV/SpO2/breathing-rate values covering the night become readable after the first post-wake or overnight sync | No (1 s is the finest, and only reliably during recorded exercise) | [Using Subscriptions](https://dev.fitbit.com/build/reference/web-api/developer-guide/using-subscriptions/), [Intraday](https://dev.fitbit.com/build/reference/web-api/intraday/) |
| **Google Health API (Fitbit successor)** | Expected same as Fitbit (device sync bound). No published latency SLA. Webhook batches ≤99 messages sent "as they become available"; failed deliveries retried with exponential backoff up to 7 days. | **Push** (HTTPS webhooks, `UPSERT`/`DELETE`, `AUTOMATIC` subscription policy) | Partial (intraday available) | No | [Webhooks](https://developers.google.com/health/webhooks), [About](https://developers.google.com/health/about) |
| **Oura API v2** | **hours to ~next mid-morning.** Ring→phone sync every few hours; app pushes to Oura Cloud each morning after sleep analysis. Ring buffers up to ~1 week of data offline. | **Push** (webhooks) + pull | **NO** for the night in progress | No (finest is 5-min HR samples plus an IBI collection, both post-hoc) | [Oura API support article](https://support.ouraring.com/hc/en-us/articles/4415266939155-The-Oura-API) |
| **Garmin Health API** | N/A — **cannot obtain access** (new requests paused, 2026) | Ping/pull or push architectures offered | — | — | [Garmin Health API](https://developer.garmin.com/gc-developer-program/health-api/), [Forums](https://forums.garmin.com/apps-software/mobile-apps-web/f/garmin-connect-web/436199/garmin-connect---program-on-hold) |
| **Apple HealthKit → your iOS app → your backend** | **seconds to ~1 h.** `HKUpdateFrequency` offers `immediate`/`hourly`/`daily`/`weekly`; guidance is that "for most health data types, hourly or daily is appropriate". No guarantee iOS wakes you promptly. | **Push on-device** (`HKObserverQuery` + background delivery), then *you* push to your server | **YES in principle** (background delivery fires overnight), but Apple Watch wrist temperature is written once, post-hoc, for the whole sleep | On-device only, and only via workout session APIs | [HKObserverQuery](https://developer.apple.com/documentation/healthkit/hkobserverquery), [Open Wearables](https://openwearables.io/blog/getting-apple-health-data-into-your-backend) |

---

## 4. THE ACCESS TABLE

| Platform | Gating | Auth | HRV? | Skin temp? | Resp rate? | Sleep stages? | History depth | Cost | Hours to first data in Python |
|---|---|---|---|---|---|---|---|---|---|
| **WHOOP REST v2** | Self-serve, **10-member cap** until app approval | OAuth 2.0 (`offline` scope for refresh) | ✅ `hrv_rmssd_milli` (once/night) | ✅ `skin_temp_celsius` (once/night, WHOOP 4.0+) | ✅ `respiratory_rate` (once/night) | ✅ light / SWS / REM / awake totals, cycle count, disturbances — **totals only, no transitions** | Full account history via `start`/`end` + pagination (25/page) | Free API; requires **paid WHOOP membership** | **2–4 h** |
| **WHOOP BLE broadcast** | None (consumer feature) | None | Partial — RR intervals, you compute RMSSD yourself | ❌ | ❌ | ❌ | Live only | Free | **1–3 h** |
| **Samsung Health Data SDK** | **Read = developer mode, no partner request.** Write = access code via partner request. Distribution = partner approval. | On-device Android permission | ❌ **no HRV type exists** | ✅ `SkinTemperatureType` | ❌ **no type exists** | ✅ `SleepType` with `SESSIONS` (stages) + `SLEEP_SCORE` | Whatever is in the Samsung Health DB | Free | **8–16 h** (needs an Android app) |
| **Samsung Health Sensor SDK (Privileged)** | Developer mode on watch = no approval for dev/test. **Partner Program required to distribute.** | On-device; app package + SHA-256 must match once out of dev mode | ✅ derive from 1 Hz IBI | ✅ 1 Hz continuous (GW5+) | ❌ (derive from PPG yourself) | ❌ (raw signal, not staged) | Live only | Free | **16–40 h** |
| **Health Connect** | Self-serve; Play Store distribution needs a health-permissions declaration | On-device Android permission | ✅ `HeartRateVariabilityRmssdRecord` — **but Samsung Health reportedly does not write it** | ✅ `SkinTemperatureRecord` (series of deltas) — not in Samsung's published sync list | ✅ `RespiratoryRateRecord` — not in Samsung's published sync list | ✅ `SleepSessionRecord` with stages | 30 days by default; `READ_HEALTH_DATA_HISTORY` for more | Free | **6–12 h** |
| **Fitbit Web API** | **Personal app type = instant self-serve intraday for your own account.** Client/Server intraday = case-by-case approval | OAuth 2.0 | ✅ 5-min intraday (sleep only) | ⚠️ skin temp variation via Temperature endpoints (nightly, not intraday) | ✅ Breathing Rate intraday | ✅ | ~years | Free (dies Sept 2026) | **2–4 h** |
| **Google Health API** | Google Cloud project + OAuth web client; **all Health scopes are Restricted → privacy & security review** | Google OAuth 2.0 | ✅ | ✅ | ✅ | ✅ | Migrating from Fitbit | Free (no published pricing) | **4–8 h** + review wait |
| **Oura API v2** | Self-serve app registration; **PATs deprecated** | OAuth 2.0 only for new integrations | ✅ 5-min during sleep + IBI collection | ✅ temperature deviation / trend | ✅ | ✅ | Full history | Free API; requires **Oura Membership** for Gen3+ | **2–4 h** (OAuth adds ~1 h vs the old PAT) |
| **Garmin Health API** | **Enterprise only, and new access is paused** | OAuth | ✅ (BBI = paid metric) | ⚠️ | ✅ | ✅ | — | Program free; BBI needs commercial licence fee | **Blocked** |
| **Apple HealthKit** | Apple Developer Program; background-delivery entitlement | On-device permission | ✅ `heartRateVariabilitySDNN` | ✅ `appleSleepingWristTemperature` (Watch S8/Ultra, Sleep Focus on) | ✅ `respiratoryRate` | ✅ | Full device history | $99/yr Apple Developer | **16–30 h** (needs an iOS app + Mac) |

---

## 5. Deep dive — Samsung Health (all access paths)

The team owns a Galaxy Watch, so this is the most consequential section. There are **five distinct
access channels** and they have wildly different gating and latency.

### 5.1 Samsung Health SDK for Android — DEAD

Deprecated 31 July 2025. Do not use; do not trust tutorials that reference it.
[Overview](https://developer.samsung.com/health/android/overview.html) ·
[Deprecation announcement](https://developer.samsung.com/sdp/news/en/2025/10/30/dev-insight-oct-2025-move-to-samsung-health-data-sdk-as-samsung-health-sdk-for-android-deprecates-and-other-latest-news) ·
[Migration guide](https://developer.samsung.com/health/data/migration-guide/overview.html)

### 5.2 Samsung Health Data SDK — the current phone-side SDK

- **Latest: v1.1.0, 12 March 2026.** v1.0.0 GA was 31 July 2025.
 [Release notes](https://developer.samsung.com/health/data/release-note.html)
- **Requirements:** Android 10 (API 29)+, Samsung Health app **6.30.2+**, Java 17+, **no emulator support**.
 Works on non-Samsung Android phones too (Samsung Health ships there).
 [Overview](https://developer.samsung.com/health/data/overview.html)
- **Gating — this is the good news:** *reading* requires only **developer mode**, no partner request.
 Enable via Samsung Health → ⋮ → Settings → About Samsung Health → tap the version line ~10×
 → "Developer mode (Samsung Health Data SDK)" → turn on **Developer Mode for Data Read**.
 *Writing* requires an **access code**, obtained only through an approved partner request.
 [Developer mode](https://developer.samsung.com/health/data/guide/developer-mode.html) ·
 [Process](https://developer.samsung.com/health/data/process.html)
- **Operations:** read, aggregate, **readChanges** (returns `UPSERT`/`DELETE` lists — this is your
 polling primitive), readAssociatedData, insert, update, delete (own data only). Multi-data ops are
 all-or-nothing.
 [Data access](https://developer.samsung.com/health/data/guide/features/data-access.html)
- **Data types available** (from the `DataType` API reference): `SleepType`, `StepsType`,
 `HeartRateType`, `ExerciseType`, `ExerciseLocationType`, `BloodOxygenType`, **`SkinTemperatureType`**,
 `BodyTemperatureType`, `ActivitySummaryType`, `FloorsClimbedType`, `BloodGlucoseType`,
 `BloodPressureType`, `BodyCompositionType`, `EnergyScoreType`, `NutritionType`, `WaterIntakeType`,
 `UserProfileDataType`, plus goal types, and (new in v1.1.0) `SleepApneaType` and
 `IrregularHeartRhythmNotificationType`.
 [DataType reference](https://developer.samsung.com/health/data/api-reference/-shd/com.samsung.android.sdk.health.data.request/-data-type/index.html)
- **Critical gap: there is NO HRV data type and NO respiratory-rate data type.** For an early-warning
 system built on autonomic reviewers, this is the single biggest limitation of the phone-side path.
- **`HeartRateType.SERIES_DATA`** gives continuous heart rate; each `HeartRate` entry has
 `startTime`, `endTime`, `heartRate` (bpm), `min`, `max`.
 [HeartRate reference](https://developer.samsung.com/health/data/api-reference/-shd/com.samsung.android.sdk.health.data.data.entries/-heart-rate/index.html)
- **`SleepType`** gives bedtime, wake time, `DURATION`, `SESSIONS` (stage information), `SLEEP_SCORE`,
 and **associates** `BloodOxygenType` and `SkinTemperatureType` recorded during sleep — one query
 returns sleep plus SpO2 plus skin temperature.
 [SleepType reference](https://developer.samsung.com/health/data/api-reference/-shd/com.samsung.android.sdk.health.data.request/-data-type/-sleep-type/index.html)
- **Latency:** bound entirely by the Galaxy Watch → phone sync, which Samsung explicitly refuses to
 specify: "For battery life reasons, the timing and frequency of data synchronization between the
 Galaxy Watch and Samsung Health follows its own policy." Triggers are watch reconnect, opening the
 app, and pull-to-refresh. **Continuous heart rate is delayed on purpose; manual spot measurements
 sync right away.**
 [Health Connect FAQ](https://developer.samsung.com/health/health-connect-faq.html)

### 5.3 Samsung Privileged Health SDK / Health Sensor SDK — the real-time path

This is the one that matters for a live demo.

- **Devices:** Galaxy Watch4 and later running Wear OS powered by Samsung. No emulator.
 Current SDK v1.4.1.
 [Overview](https://developer.samsung.com/health/sensor/overview.html)
- **Gating:** you need the **Samsung Partner Program** to *distribute* an app. But **developer mode
 on the watch lets you run an unregistered app for testing/debugging**: Settings → Apps →
 Health Sensor Service → tap the title ~10× → Developer mode → accept the Samsung Health Partner
 Service & SDK License → toggle on. Without it, an app whose package name + SHA-256 don't match
 Samsung's registry gets `SDK_POLICY_ERROR`.
 [Developer mode](https://developer.samsung.com/health/sensor/guide/developer-mode.html) ·
 [FAQ](https://developer.samsung.com/health/sensor/faq.html)
 **For a university course project demo that is never published, developer mode is sufficient.**
- **Trackers and sampling rates** (primary source —
 [data specifications](https://developer.samsung.com/health/sensor/guide/data-specifications.html)):

 | Tracker | Raw/processed | Frequency | Payload |
 |---|---|---|---|
 | `ACCELEROMETER_CONTINUOUS` | raw | 25 Hz | x/y/z |
 | `HEART_RATE_CONTINUOUS` | processed | 1 Hz | HR + inter-beat interval (0–4 IBI values per sample) |
 | `PPG_CONTINUOUS` | raw | 25 Hz | PPG green, IR, red |
 | `SKIN_TEMPERATURE_CONTINUOUS` | processed | 1 Hz | skin + ambient temp (Galaxy Watch5+) |
 | `EDA_CONTINUOUS` | raw | 1 Hz | electrodermal activity (Galaxy Watch8+) |
 | `ECG_ON_DEMAND` | raw | 500 Hz | ECG |
 | `PPG_ON_DEMAND` | raw | 100 Hz | PPG green/IR/red |
 | `SPO2_ON_DEMAND` | processed | — | blood oxygen |
 | `BIA_ON_DEMAND` / `MF_BIA_ON_DEMAND` | processed | — | body composition |

- **Batching:** the SDK collects data in the application processor without waking the CPU and fires
 the listener periodically — e.g. **~12 s for PPG green**. This is your latency floor for raw signals.
 On-demand trackers should run in the foreground and complete within 30 seconds.
- **Screen-off / overnight operation:** the SDK is explicitly designed for all-day tracking without
 waking the CPU. If instead you use plain Android `SensorManager`, you must request the **wake-up**
 heart-rate sensor (`getDefaultSensor(Sensor.TYPE_HEART_RATE, true)`) and run a **foreground service**
 with `FOREGROUND_SERVICE_TYPE_HEALTH`, otherwise "Galaxy Watch [pauses] your application after
 60 seconds of screen-off time". Permissions needed: `BODY_SENSORS`, `BODY_SENSORS_BACKGROUND`
 (Android 12+, requested separately), `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_HEALTH`, `WAKE_LOCK`.
 [Samsung dev blog, 23 Apr 2026](https://developer.samsung.com/galaxy-watch/blog/en/2026/04/23/continuous-heart-rate-tracking-on-galaxy-watch-even-with-the-screen-off)

### 5.4 Health Connect route

Samsung Health syncs with Health Connect since app version 6.22.5 (Oct 2022). The published mapping
covers 17 types: Steps, BloodGlucose, **OxygenSaturation**, BloodPressure, ExerciseSession,
TotalCaloriesBurned, Distance, **HeartRate**, Power, Speed, Vo2Max, Nutrition, **SleepSession**,
Weight, BodyFat, BasalMetabolicRate, Height.
[Samsung blog](https://developer.samsung.com/health/blog/en/accessing-samsung-health-data-through-health-connect)

**Note what is NOT in that list: HRV, skin temperature, respiratory rate, resting heart rate.**
Community reports confirm exactly this gap
([Samsung Community thread](https://us.community.samsung.com/t5/Galaxy-Watch/HRV-breathing-rate-and-resting-HR-won-t-write-to-the-health/td-p/3351258)).

**Documentation conflict to be aware of:** Samsung's blog states "For security reasons, Health Connect
data can only be retrieved by applications running in the foreground." **This is stale.** Android now
ships `android.permission.health.READ_HEALTH_DATA_IN_BACKGROUND`, gated on
`HealthConnectFeatures.FEATURE_READ_HEALTH_DATA_IN_BACKGROUND` being available on the device.
[Health Connect read data](https://developer.android.com/health-and-fitness/health-connect/read-data)

### 5.5 Samsung Health Server / Partner REST API

A Samsung Health REST Data API exists (auth API + data API, OAuth2-style) but the documentation lives
under a `partner-only` path and is not publicly readable.
[Health Server partner-only intro](https://developer.samsung.com/health-server/server/partner-only/api-reference/intro.html)
**Treat as unobtainable for a student project.** There is no consumer-facing Samsung Health cloud REST
API — repeated developer-forum requests for one go unanswered.

### 5.6 Plain data export — "Download personal data"

Samsung Health has a user-initiated export. The output is a ZIP containing roughly **19 CSV files**
(one per attribute — sleep, sleep_stage, heart rate, activity day summary, activity level, floors
climbed, food info, water intake, height, preferences, device profile, rewards, best records, report…)
plus a **`jsonfiles` folder** of JSON blobs. Rows with fine-grained time series carry a
`binning_data` column naming a blob file; **the JSON blobs contain higher-resolution per-minute heart
rate**, while the top-level CSV has hourly summaries or individual points.
[How to extract your Samsung Health data](https://medium.com/@dimshik100/how-to-extract-your-personal-samsung-health-data-514bbe2331f7) ·
[Export without root — stress, HRV & BIA](https://bhived.ai/lessons/export-samsung-health-data-without-root) ·
[samsung-health-mcp (parser reference)](https://github.com/davidmosiah/samsung-health-mcp)

**Use for this project:** excellent for *offline model development and backtesting* (hours of work,
zero gating, real per-minute data from the team's own watch). **Useless for a live demo** — it is a
manual, user-initiated download.

### 5.7 Samsung Health Research Stack

Open-source platform for digital health research on Android + Wear OS: app SDK, backend service,
and a web portal for study design and data analysis. Version 2.0 Beta adds Sensor SDK support
(ECG, SpO2, body composition) and Data SDK integration for Galaxy Watch/Ring sleep data.
"Available for all companies and medical institutions." Already used in clinical studies.
[Samsung Health Stack](https://developer.samsung.com/health/s-healthstack) ·
[Overview](https://developer.samsung.com/health/research/overview.html) ·
[Codelab](https://developer.samsung.com/codelab/health/research-system.html)

This is worth citing in the course project report as the "how real researchers do it" reference point,
even if it is too heavy to deploy in a semester.

### 5.8 Concrete path: Galaxy Watch → Python on a laptop

Yes, there is a realistic path. Steps:

1. **Install Android Studio**, create a project with a **Wear OS module** and a **phone module**. (1–3 h)
2. **Enable developer mode** on the watch (Health Sensor Service, tap-title-10×) and on Samsung Health
 if you also want the Data SDK. (15 min)
3. **Watch module:** connect to `HealthTrackingService`, get `HealthTracker.HEART_RATE_CONTINUOUS`
 (and/or `PPG_CONTINUOUS`, `SKIN_TEMPERATURE_CONTINUOUS`), register a listener, run it inside a
 **foreground service** with `FOREGROUND_SERVICE_TYPE_HEALTH`. Samsung's codelab is a working
 starting point — it ships most of the plumbing and leaves three small functions to implement
 (IBI validity filter, capability filter, JSON encode). (4–10 h)
4. **Watch → phone:** `CapabilityClient` to find the paired node, `MessageClient` to send JSON byte
 arrays. Codelab covers this. Change it from "on tap" to "on every batch". (2–4 h)
5. **Phone → laptop:** simplest reliable option is an HTTP POST from the phone module to a
 FastAPI/Flask server on the laptop over the same Wi-Fi (or `adb reverse` over USB, which also
 solves the "phone must stay charged and connected overnight" problem). (2–4 h)
6. **Python side:** FastAPI endpoint → in-memory ring buffer → your detection logic. (1–2 h)

**Total: realistically 2–5 working days for someone who has not written Android before; 1–2 days for
someone who has.** No partner approval, no fee, no NDA required for a non-distributed demo app.

**Cheaper fallback if Android work is too expensive:** use Health Connect (~6–12 h) and accept
Tier-2/Tier-3 latency; or use the Download-personal-data export for offline development and pair it
with the WHOOP BLE broadcast for the live half of the demo.

---

## 6. Deep dive — WHOOP API

### 6.1 Getting in (genuinely easy)

- Create a Team, then an App at `developer-dashboard.whoop.com/apps/create`. Requires ≥1 scope and
 ≥1 redirect URI. You get a Client ID and Client Secret. **Up to 5 apps per account.**
 [Getting started](https://developer.whoop.com/docs/developing/getting-started/)
- **No approval needed to start: "Apps can be used for development immediately with a limit of
 10 WHOOP members."** Approval is only needed to exceed 10 users, and requires an app name, contact
 emails, a privacy policy URL, design-guideline compliance, and testing with ≥1 real member.
 No published approval SLA.
 [App approval](https://developer.whoop.com/docs/developing/app-approval/)
- **A 3-person course project team never needs approval.**

### 6.2 Auth

OAuth 2.0 authorization-code flow. Scopes include `read:profile`, `read:body_measurement`,
`read:cycles`, `read:recovery`, `read:sleep`, `read:workout`, and **`offline`** (required to get a
refresh token). There is also a `clientCredentials` "Trusted Partner" flow, not available to you.
[OAuth](https://developer.whoop.com/docs/developing/oauth/) · [API docs](https://developer.whoop.com/api/)

**Gotcha:** refresh tokens rotate — every exchange returns a new one, and concurrent refreshes
invalidate each other, forcing re-authentication.
[Open Wearables](https://openwearables.io/blog/whoop-api-recovery-strain-sleep-data-for-developers)

### 6.3 Exact data available (v2)

`GET /v2/cycle/{cycleId}/recovery` and `GET /v2/recovery` — `score` object:
- `recovery_score` (0–100)
- `resting_heart_rate` (bpm)
- **`hrv_rmssd_milli`** (ms)
- **`spo2_percentage`**
- **`skin_temp_celsius`**
- `user_calibrating` (bool)

`GET /v2/activity/sleep` — `score` object:
- `stage_summary`: `total_in_bed_time_milli`, `total_awake_time_milli`, `total_no_data_time_milli`,
 `total_light_sleep_time_milli`, `total_slow_wave_sleep_time_milli`, `total_rem_sleep_time_milli`,
 `sleep_cycle_count`, `disturbance_count`
- `sleep_needed`: baseline, sleep-debt, recent-strain, recent-nap components
- **`respiratory_rate`** (breaths/min)
- `sleep_performance_percentage`, `sleep_consistency_percentage`, `sleep_efficiency_percentage`
- `nap` (bool)

`GET /v2/cycle` — `strain`, `kilojoule`, `average_heart_rate`, `max_heart_rate`
`GET /v2/activity/workout` — `strain`, avg/max HR, `kilojoule`, `percent_recorded`, `distance_meter`,
`altitude_gain_meter`, `zone_durations` (ms in zones 0–5)
`GET /v2/user/measurement/body` — `height_meter`, `weight_kilogram`, `max_heart_rate`
[Full API reference](https://developer.whoop.com/api/)

**What is NOT there:** any heart-rate time series, sleep-stage *transitions* (only totals), GPS,
steps, blood glucose, ECG, raw PPG.
[Terra](https://tryterra.co/blog/whoop-integration-series-part-2-data-available-from-the-api-ec4337a9455b) ·
[Open Wearables](https://openwearables.io/blog/whoop-api-recovery-strain-sleep-data-for-developers)

**Granularity summary: one value per night for HRV, RHR, SpO2, skin temp and respiratory rate.**
That is five scalars per 24 hours. For an "early warning" system that is a legitimate but very thin
signal — it is exactly the WHOOP/Oura "readiness" paradigm and is defensible academically, but it is
not a live monitor.

### 6.4 History, rate limits, pagination

- **History:** full account history via `start`/`end` query params, `limit` ≤ 25 per page,
 `nextToken` cursor, sorted descending.
- **Rate limits: 100 requests/minute and 10,000 requests/day.** Headers `X-RateLimit-Limit`,
 `X-RateLimit-Remaining`, `X-RateLimit-Reset` (seconds until reset); `429` on exceed. WHOOP will
 raise limits on request.
 [Rate limiting](https://developer.whoop.com/docs/developing/rate-limiting/)

### 6.5 Webhooks

- Six event types: `recovery.updated`, `recovery.deleted`, `sleep.updated`, `sleep.deleted`,
 `workout.updated`, `workout.deleted`. **Creates are delivered as "update" events.**
- Payload: `user_id` (int64), `id` (UUID in v2), `type`, `trace_id`. HTTPS POST to a URL you configure
 in the Developer Dashboard — **you need a publicly reachable HTTPS endpoint** (ngrok / Cloudflare
 Tunnel is fine for a demo).
- Signature: HMAC-SHA256 over `X-WHOOP-Signature-Timestamp` concatenated with the raw body, keyed on
 your app secret, base64-encoded, compared against `X-WHOOP-Signature`.
- Retries: **five times over about one hour** on non-2XX or timeout.
- WHOOP explicitly warns webhooks should not be your sole source of truth — implement a reconciliation
 poll.
- **No latency SLA.** The docs only say events arrive "once this activity is processed".
 [Webhooks](https://developer.whoop.com/docs/developing/webhooks/)

### 6.6 Versioning state

v2 launched 2025-07-01. **v1 webhooks were removed 2025-11-01** and "developers must migrate to v2 to
continue getting webhook events". v1 is unsupported; new features go to v2 only. A
`GET /v1/activity-mapping/{activityV1Id}` endpoint exists for ID translation. **Build on v2 only.**
[Changelog](https://developer.whoop.com/docs/api-changelog/) ·
[Migration guide](https://developer.whoop.com/docs/developing/v1-v2-migration/)

### 6.7 Terms of use relevant to a student project

- No selling/licensing/leasing API data to third parties; no redistributing or syndicating access.
- No reverse-engineering WHOOP algorithms.
- No building an app that functions substantially the same as the APIs.
- **Cached copies must not outlive the cache header**; delete stored content on termination.
- **"Developer credentials may not be embedded in open-source projects"** — relevant if the course project
 repo is public. Use environment variables and a `.env` that is gitignored.
- WHOOP makes no HIPAA representations; no PHI without prior written consent.
- **Academic/research use is not explicitly addressed either way.** Reading your own team members'
 data with their consent, for a non-commercial class project, is not prohibited by anything in the
 terms I could find — but the terms are written for commercial apps.
 [API Terms of Use](https://developer.whoop.com/api-terms-of-use/)

### 6.8 Concrete path: WHOOP → Python

**REST path (~2–4 hours):**
1. Sign in at `developer-dashboard.whoop.com`, create a Team and an App, add scopes
 `read:recovery read:sleep read:cycles read:workout read:profile offline`, redirect URI
 `http://localhost:8000/callback`. (20 min)
2. Python: `requests-oauthlib` or hand-roll. Auth URL → browser → code → token exchange at the WHOOP
 token endpoint. Persist the rotating refresh token to disk. (1–2 h)
3. `GET https://api.prod.whoop.com/developer/v2/recovery?limit=25` etc. Done. (30 min)
4. Optional webhooks: run FastAPI locally, expose with `cloudflared tunnel` or `ngrok`, register the
 URL in the dashboard, verify the HMAC. (1–2 h)

**BLE path (~1–3 hours), for the live demo:**
1. In the WHOOP app: More → Device Settings → **Broadcast Heart Rate = On**.
2. `pip install bleak`; scan for the device advertising service `0000180d-...`; subscribe to the
 Heart Rate Measurement characteristic `00002a37-...`; parse flags byte for BPM width and RR-interval
 presence.
3. You get BPM ~1 Hz plus RR intervals — enough to compute rolling RMSSD yourself in Python.
 [whoop-live reference implementation](https://github.com/grivera82/whoop-live)

**Known BLE limitations:** WHOOP broadcasts to **one device at a time** (disconnect Peloton/Zwift/
Garmin first); broadcast mode is reported to need re-enabling after app or firmware updates; battery
drain is higher. **Whether it survives an entire night without being auto-disabled is the single
highest-value experiment the team can run this week.** I found no documentation either way — treat
as **UNVERIFIED** and test empirically.

---

## 7. Per-platform writeups (A–N)

### 7.1 Google Health Connect (Android)

- **A. Gating:** self-serve. Play Store distribution requires a health-permissions declaration under
 Google Play's user data policy; sideloading for a demo needs nothing.
- **B. Auth:** on-device Android runtime permissions per data type; no OAuth, no server.
- **C. Channels:** ~50 record types. Relevant ones: `HeartRateRecord` (series),
 `HeartRateVariabilityRmssdRecord` (instantaneous), `SkinTemperatureRecord` (series of deltas,
 behind `FEATURE_SKIN_TEMPERATURE`), `RespiratoryRateRecord`, `OxygenSaturationRecord`,
 `SleepSessionRecord` (with stages), `RestingHeartRateRecord`, `BodyTemperatureRecord`.
- **D.** HRV ✅ / skin temp ✅ / resp rate ✅ / sleep stages ✅ — *as record types*. Whether your
 wearable's app actually writes them is a separate question, and for Samsung Health the answer for
 HRV, skin temp and respiratory rate appears to be **no**.
- **E. History:** 30 days by default, measured from when the permission was granted; the window resets
 if the app is reinstalled. `READ_HEALTH_DATA_HISTORY` extends it. On Android 14+ an app can always
 read its own data without a limit.
- **F. Rate limits:** none published; it is a local content provider.
- **G. Push vs pull:** **pull only.** There is no callback. You poll `readRecords()` or use change
 tokens. Background reads need `READ_HEALTH_DATA_IN_BACKGROUND` plus
 `FEATURE_READ_HEALTH_DATA_IN_BACKGROUND` availability on the device.
- **H. Latency:** adds ~nothing itself; entirely bound by the writing app.
- **I. Platform:** Android phone app required (Android 9/SDK 28+; Health Connect is part of the OS
 from Android 14). **Health Connect does not run on Wear OS.**
- **J. Cost:** free.
- **K. Terms:** Google Play user-data policy applies to `READ_HEALTH_DATA_IN_BACKGROUND` and
 `READ_HEALTH_DATA_HISTORY`.
- **L. Effort:** 6–12 h to a Kotlin app reading records; add 2–4 h to ship them to Python.
- **M. Docs:** https://developer.android.com/health-and-fitness/health-connect
- **N. Gotchas:** page tokens can come back as `""` rather than `null` — use `isNullOrEmpty()`.
 Samsung's claim that HC is foreground-only is out of date.

### 7.2 Fitbit Web API

- **A. Gating:** register at dev.fitbit.com. **Choosing the "Personal" OAuth application type gives
 you automatic intraday access to your own data with no request form.** "Client"/"Server" types need
 case-by-case intraday approval (now routed through Google's Issue Tracker).
- **B. Auth:** OAuth 2.0.
- **C/D. Intraday endpoints** (each has by-date and by-interval variants): Active Zone Minutes,
 Activity, **Breathing Rate**, **Heart Rate**, **HRV**, **SpO2**. HR detail levels `1sec`/`1min`/
 `5min`/`15min`; HRV every 5 min; max 24-hour range per request.
- **E. History:** years, subject to the 24 h/request intraday cap.
- **F. Rate limits:** 150 requests/hour/user is the long-standing published figure
 (**UNVERIFIED against the current page — confirm before relying on it**).
- **G. Push:** subscriptions/webhooks, "near real-time" once Fitbit detects updated data.
- **H. Latency:** ~15 min device sync + 10 min–1 h server processing.
- **I. Platform:** none required beyond a server for the webhook callback; polling works from a laptop.
- **J. Cost:** free.
- **K. Terms:** intraday access for non-personal apps is explicitly discretionary.
- **L. Effort:** 2–4 h.
- **M. Docs:** https://dev.fitbit.com/build/reference/web-api/intraday/
- **N. Gotchas:** **the whole platform is turned down September 2026** — do not build a
 multi-month project on it. `1sec` HR is often not actually 1 s outside recorded exercise.
 HRV is only collected during sleep and only if the Health Metrics tile is enabled.

### 7.3 Google Health API (the Fitbit successor)

- **A. Gating:** Google Cloud project + OAuth 2.0 web client. **All Health API scopes are Restricted,
 requiring a privacy and security review** — the same regime as Gmail/Drive restricted scopes.
 Test users can be used before verification (standard Google OAuth behaviour, **UNVERIFIED for this
 specific API**).
- **B. Auth:** Google OAuth 2.0.
- **C/D:** activity/fitness, vitals, workouts, nutrition, steps, sleep, women's health, ECG.
 **Intraday data and webhooks are available for all relevant data types via a dedicated list
 endpoint.** 100+ legacy Fitbit endpoints consolidated into data bundles.
- **E. History:** inherits Fitbit history for migrated users.
- **F. Rate limits:** a rate-limits guide is referenced but I could not load it — **UNVERIFIED**.
- **G. Push:** HTTPS webhooks. Resources `v4.projects.subscribers` and
 `v4.projects.subscribers.subscriptions`. Events `UPSERT` and `DELETE`. `subscriptionCreatePolicy:
 AUTOMATIC` auto-subscribes users on consent. Endpoint must be public HTTPS TLS 1.2+, respond
 `204 No Content`, pass a verification handshake, and validate the `GOOGLE-HEALTH-API-SIGNATURE`
 header against the public keyset. Batches up to 99 messages; retries with exponential backoff up
 to 7 days.
- **H. Latency:** no SLA; expect Fitbit-like device-sync-bound behaviour.
- **I. Platform:** a public HTTPS server for webhooks; otherwise polling from anywhere.
- **J. Cost:** no published pricing.
- **K. Terms:** restricted-scope review is a real barrier for a 12-week project.
- **L. Effort:** 4–8 h of code, plus unknown review latency.
- **M. Docs:** https://developers.google.com/health/about · https://developers.google.com/health/webhooks · https://developers.google.com/health/reference/rest
- **N. Gotchas:** the API is "actively evolving" with changes expected through end of May 2026 —
 it is a moving target *right now*. Every Fitbit user must individually re-consent between
 May and September 2026.

### 7.4 Apple HealthKit

- **A. Gating:** Apple Developer Program membership. The `com.apple.developer.healthkit` entitlement
 is self-serve; `com.apple.developer.healthkit.background-delivery` is an entitlement you enable in
 your app's capabilities.
- **B. Auth:** on-device user permission, per data type, per direction.
- **C/D:** HRV ✅ (`heartRateVariabilitySDNN`), skin/wrist temp ✅
 (`appleSleepingWristTemperature`, iOS 16+, Apple Watch Series 8/Ultra and later, **only recorded
 during sleep with Sleep Focus enabled**; SE models excluded), respiratory rate ✅, SpO2 ✅ (model and
 region dependent), sleep stages ✅.
- **E. History:** whatever is on the device.
- **F. Rate limits:** none (local).
- **G. Push:** `HKObserverQuery` + `enableBackgroundDelivery(for:frequency:)` with `HKUpdateFrequency`
 `immediate`/`hourly`/`daily`/`weekly`. Practical guidance is that hourly or daily is appropriate for
 most types; immediate is reasonable for workouts.
- **H. Latency:** seconds to ~1 hour on-device, then your own upload. **No cloud REST API exists** —
 everything normally done server-side must be written in Swift on-device.
- **I. Platform:** an iOS app is mandatory, which means a Mac + Xcode + a physical iPhone. **This is
 the hardest platform requirement in this whole report.**
- **J. Cost:** $99/yr Apple Developer Program.
- **K. Terms:** standard App Store health-data rules; not relevant if you never ship.
- **L. Effort:** 16–30 h if nobody on the team has Swift experience.
- **M. Docs:** https://developer.apple.com/documentation/healthkit/reading-data-from-healthkit
- **N. Gotchas:** revoked permissions return **empty data rather than an error** — you cannot detect
 revocation. Missing entitlement makes all HealthKit calls fail *silently*. Multiple data sources
 (Watch vs third-party apps) produce duplicate/conflicting samples. Large reads cause memory
 pressure — chunk by week.
 **The team does not own an Apple Watch, so this is out of scope; documented for completeness.**

### 7.5 Oura API v2

- **A. Gating:** self-serve app registration at `developer.ouraring.com`. **Personal Access Tokens are
 deprecated** (docs nav shows "[Deprecated]"); secondary sources say no new PATs since December 2025.
 Requires an **active Oura Membership** for Gen3+ rings — without it the API returns nothing.
- **B. Auth:** OAuth 2.0. Server-side flow (auth code + refresh token) or client-side flow (tokens
 expire after 30 days, no refresh). Scopes: email, personal, daily, heartrate, workout, tag, session,
 spo2.
- **C/D:** `/v2/usercollection/sleep` (detailed sleep periods: HRV, respiratory rate, sleep stages,
 movement), `/v2/usercollection/daily_sleep`, `daily_readiness`, `daily_activity`, `daily_spo2`,
 `daily_stress`, `/v2/usercollection/heartrate` (BPM samples, 5-min interval),
 `/v2/usercollection/interbeat_interval` (raw IBI time series), `workout`, `session`, `tag`,
 `sleep_time`, `rest_mode_period`, `ring_configuration`, `daily_cycle_phases`.
 HRV ✅ 5-min during sleep / temperature ✅ (deviation + trend) / respiratory rate ✅ / sleep stages ✅.
- **E. History:** full account history.
- **F. Rate limits:** 5000 requests / 5 minutes, `429` on exceed (**secondary sources only**).
- **G. Push:** webhooks via `/v2/webhook/subscription` — create/list/renew/update/delete. Each
 subscription binds one `data_type` × one `event_type` (`create`/`update`/`delete`) to an HTTPS
 callback with a verification token and HMAC verification. Subscriptions require renewal (a
 `renew` method exists).
- **H. Latency:** **hours.** Ring→phone sync every few hours; ring buffers up to ~1 week; the app
 pushes to Oura Cloud each morning after sleep analysis completes, "generally available by
 mid-morning the following day".
- **I. Platform:** a public HTTPS endpoint if you want webhooks; otherwise polling from a laptop.
- **J. Cost:** API free; Oura Membership (~$5.99/mo) mandatory for Gen3+.
- **K. Terms:** standard developer terms; nothing specifically hostile to academic use found.
- **L. Effort:** 2–4 h.
- **M. Docs:** https://cloud.ouraring.com/docs/ (v2 at https://cloud.ouraring.com/v2/docs)
- **N. Gotchas:** the v2 docs page is a JS single-page app and does not render for scrapers/LLM
 fetchers — you must open it in a browser. V1 was removed 22 January 2024. PAT deprecation will
 break any tutorial written before 2026. **The team does not own an Oura ring.**

### 7.6 Garmin Health API / Garmin Connect

- **A. Gating:** **Enterprise only** — "available for enterprise use", "only for business use",
 individual applications not permitted. You must apply as a legal entity (company, university,
 hospital, research institution). **And as of 2026 new access requests are paused**, the request form
 has been removed, there is no waitlist, and developers who applied in April 2026 were still waiting
 in August. Existing partners are unaffected.
- **B. Auth:** OAuth.
- **C/D:** steps, heart rate, calories, sleep (with stages), **respiration**, body composition,
 **stress**, **pulse ox (SpO2)**, detailed epoch summaries. **Beat-To-Beat Interval** data (the HRV
 source) is a premium metric requiring a commercial licence fee.
- **E. History:** backfill available to partners.
- **F. Rate limits:** not published publicly.
- **G. Push:** choice of Ping/Pull or Push architecture; JSON.
- **H. Latency:** not documented. Garmin's push service is generally regarded as among the better ones,
 but I have no primary source and the point is moot given access is closed.
- **I. Platform:** a server with a public URL for the push/ping callbacks.
- **J. Cost:** "no licensing or maintenance fees" for program access; BBI and some metrics require a
 licence fee or minimum device order for commercial use. Third-party claims of a $5,000
 administrative fee for production access are **UNVERIFIED** and Garmin does not publish pricing.
- **K. Terms:** business use only — a student project would need to apply through the university as the legal
 entity, and even then the queue is closed.
- **L. Effort:** **blocked**.
- **M. Docs:** https://developer.garmin.com/gc-developer-program/health-api/
- **N. Gotchas:** developers report access requests rejected without notification. **Do not plan
 around Garmin.**

---

## 8. Aggregator comparison

| Provider | Free / academic tier | Entry price | Devices | Model | Latency added | Notes |
|---|---|---|---|---|---|---|
| **Terra** | **No free tier**; 30-day money-back guarantee | ~$399/mo billed annually (~$499 monthly), ~100k credits | 1000+ sources incl. Apple, Garmin, Fitbit, Oura, **WHOOP**, Google Fit, **Samsung Health**, Polar, COROS | Unified API + webhooks, 500+ normalised metrics | Adds a hop; **cannot beat the underlying vendor latency** | Best device coverage. Their own blog admits WHOOP continuous HR is not available. |
| **Sahha** | **Free 30-day sandbox with 25 development users, all products unlocked** | $299/mo billed annually ($399 monthly), 1,000 users | 800+ devices | Mobile SDKs + REST + webhooks, proprietary passive health scores | Same constraint | **Most generous free tier** — the only one usable for a semester project without payment, but the 30-day clock is the catch. |
| **Rook** | No free tier | $399/mo core (750 active users); **webhooks +$99/mo**, granular data +$249/mo, ROOKScore +$249/mo | Broad | Android/iOS SDKs first | Same constraint | Unbundled pricing means the real cost is well above the headline. |
| **Spike** | No free tier, **no self-serve signup** | from $450/mo | Broad | API | Same constraint | **Acquired by Raintree Systems in July 2026** — treat continuity as a risk. |
| **Junction** (formerly Vital) | No free tier | $0.50/user/month, **$300 minimum** | Broad | Developer-first connectivity layer | Same constraint | Cheapest per-user, but the $300 floor makes it $300/mo for a 3-person team. |

**Verdict for this project:** aggregators solve *breadth*, not *latency*. They sit downstream of
exactly the same vendor clouds and therefore inherit every delay in §3. For a two-device project where
the team owns both devices, paying $300–500/month to avoid writing one OAuth flow is not defensible.
**Skip aggregators entirely.** Mention them in the report as the industry-standard integration
approach and explain why direct integration was chosen.

### Open-source bridges

- **Health Auto Export (iOS, ~$$ Premium).** Exports Apple Health to a **generic REST API** endpoint
 via HTTP POST in JSON or CSV with configurable auth headers, plus MQTT, iCloud, Dropbox, Home
 Assistant. 100+ metrics including sleep phases, heart rate, ECG. Automated background exports on
 the Premium tier (7-day free trial).
 [GitHub docs](https://github.com/Lybron/health-auto-export) ·
 [REST API help](https://help.healthyapps.dev/en/health-auto-export/automations/rest-api/)
 **This is the pragmatic way to get Apple Health into Python without writing Swift.** Not relevant to
 the team's devices, but worth one line in the report.
- **Gadgetbridge.** Open-source Android companion for many wearables. Has added **export to Health
 Connect**, but **currently only steps and heart rate**.
 [Health Connect PR](https://codeberg.org/Freeyourgadget/Gadgetbridge/pulls/4481) ·
 [Auto-export issue](https://codeberg.org/Freeyourgadget/Gadgetbridge/issues/553)
 Galaxy Watch (Wear OS) support is not a Gadgetbridge strength — it targets Tizen-era and Chinese
 vendor bands. **Not a viable path for a Wear OS Galaxy Watch.**
- **whoop-live.** Python CLI reading WHOOP's official BLE Heart Rate Broadcast via `bleak`; includes a
 scan mode. Uses "no unofficial APIs or scraping, just the standard BLE profile that WHOOP explicitly
 supports". [GitHub](https://github.com/grivera82/whoop-live)
- **reverse-engineering-whoop-post.** A community reverse-engineering writeup of the WHOOP 4.0
 protocol with Python BLE tooling notes.
 [GitHub](https://github.com/bWanShiTong/reverse-engineering-whoop-post) —
 **flagged: reverse engineering is explicitly prohibited by WHOOP's API Terms of Use. Do not use this
 in course project you submit.**
- **samsung-health-mcp.** Local-first parser for Samsung Health personal-data CSV/ZIP exports — useful
 as a reference for the export schema.
 [GitHub](https://github.com/davidmosiah/samsung-health-mcp)

### What researchers actually use

- **Fitabase** — the de facto standard for Fitbit (and now Garmin) in clinical research; handles
 de-identification and minute-level export. https://www.fitabase.com/
- **Labfront** — aggregates high-resolution physiological data (sleep staging, IBI, SpO2) plus EMA
 surveys and adherence tracking; free tier historically offered to academics
 (**UNVERIFIED** — check current terms). https://www.labfront.com/
- **MyDataHelps** (CareEvolution) — digital trial platform, connects to Fitbit and anything in Apple
 Health / Google Fit. https://careevolution.com/mydatahelps/fact-sheet-wearable-data/
- **Empatica** — research-grade wearable + cloud platform, used in neurology/sleep/mental health
 studies. https://www.empatica.com/platform/research-studies/
- **Samsung Health Research Stack** — Samsung's own open-source study platform for Android + Wear OS.
 https://developer.samsung.com/health/s-healthstack
- **WHOOP Unite** — WHOOP's research/enterprise offering; a research FAQ is publicly mirrored by the
 University of Arizona Sensor Lab.
 [PDF](https://www.sensorlab.arizona.edu/sites/default/files/2023-05/WHOOP%20Unite%20Research%20FAQs_0.pdf)
- Scale context: ClinicalTrials.gov shows 1,300+ studies using wearables, dominated by ActiGraph
 (~1,024), Fitbit (~668), Garmin (~84), Apple (~52), Empatica (~47).
 [CareEvolution](https://careevolution.com/post/wearable-device-data-in-digital-clinical-research/)

**Relevance:** cite these to justify the project's design choices. The fact that research-grade
studies almost universally use ActiGraph or Fitbit rather than WHOOP/Oura is itself a finding —
it is precisely because those platforms expose raw/minute-level data and the readiness-score
platforms do not.

---

## 9. Developer-reported gotchas (documentation optimism vs reality)

**Samsung Health → Health Connect is the worst offender.**
- Developers report that after granting all permissions, "Samsung Health can sometimes take **more than
 a day** to start sending data to Health Connect, and this is very often reported by customers."
 Some users report **never** getting any data.
 [Samsung dev forum: syncing is unreliable](https://forum.developer.samsung.com/t/syncing-data-is-unreliable-between-samsung-health-and-health-connect/24850) ·
 [Samsung dev forum: Health Connect delay](https://forum.developer.samsung.com/t/health-connect-delay/35955)
 (Both threads 404 to automated fetchers — open them in a browser to cite verbatim.)
- "Samsung Health is able to read and write data to Health Connect, but it writes **far less data** than
 developers have in Samsung Health itself."
- **HRV, breathing rate and resting heart rate do not write from Samsung Health to Health Connect**,
 while other metrics sync fine.
 [Samsung Community thread](https://us.community.samsung.com/t5/Galaxy-Watch/HRV-breathing-rate-and-resting-HR-won-t-write-to-the-health/td-p/3351258)
- Samsung's own doc says data reaches HC "as soon as data is created or changed" — true, but only
 measures the *phone-to-HC* hop and quietly omits that the *watch-to-phone* hop is unbounded.
 **This is the clearest case of documentation optimism in this report.**

**Samsung Health's timestamps.** Developers report missing/odd timestamps on Health-Connect-synced
records. [Forum thread](https://forum.developer.samsung.com/t/health-connect-sync-no-timestamps/40497)

**Samsung Privileged Health SDK partnership is not for individuals.** Forum reports describe the
Partner App Program as "only for established companies that currently have Health apps", and Samsung
has at times paused accepting applications entirely.
[Partner App Program thread](https://forum.developer.samsung.com/t/partner-app-program/5983) ·
[How to get approval](https://forum.developer.samsung.com/t/how-to-get-approval-for-samsung-health-partner-app/11082) ·
[Privileged SDK partnership thread](https://forum.developer.samsung.com/t/samsung-privileged-health-sdk-partnership/23542)
**Mitigation: developer mode makes partnership unnecessary for a non-distributed demo.**

**WHOOP requires a paid membership.** "The OAuth flow will not complete for users without a current
WHOOP subscription." Reported as the most common early blocker producing empty dashboards.
[Open Wearables](https://openwearables.io/blog/whoop-api-recovery-strain-sleep-data-for-developers)

**WHOOP rotating refresh tokens.** "Every token exchange returns a new refresh token. If you store the
old one, the user loses access." Concurrent refreshes need distributed locking. Forgetting the
`offline` scope means no refresh token at all. Same source.

**WHOOP webhooks are not a source of truth.** WHOOP's own docs tell you to run a reconciliation job;
retries stop after five attempts over ~1 hour, so an hour of downtime loses events permanently.
[Webhooks](https://developer.whoop.com/docs/developing/webhooks/)

**WHOOP BLE broadcast is single-connection and resets.** "WHOOP can only broadcast to one device at a
time" — you must disconnect Peloton/Zwift first — and "the broadcast is temporary — you usually need to
re-enable it after app/firmware updates."
[whoop-live](https://github.com/grivera82/whoop-live)

**Fitbit `1sec` is a half-truth.** Fitbit's own docs concede the 1-second detail level "may not always
return data in 1 second sampling outside of a recorded exercise" and point you at the TCX endpoint
instead.
[Get HR Intraday by Date](https://dev.fitbit.com/build/reference/web-api/intraday/get-heartrate-intraday-by-date/)

**Fitbit end-to-end is slower than "near real-time" implies.** Synced data appears in the app in
10–15 seconds, but "because the data travels through Fitbit's servers, a complete daily total may
update around 10 minutes to an hour later," and third-party apps sit behind that queue.
[Pacer support](https://support.mypacer.com/hc/en-us/articles/41581758645261-Fitbit-data-delayed-partial-sync)

**HealthKit fails silently.** Missing entitlement → all calls fail silently at runtime. Revoked
permissions → empty results, not errors. Duplicate samples from multiple sources are the norm.
[Open Wearables](https://openwearables.io/blog/getting-apple-health-data-into-your-backend)

**Health Connect page tokens.** Some implementations return `""` instead of `null` at the end of
pagination — an `if (token != null)` loop will spin forever.
[Read data](https://developer.android.com/health-and-fitness/health-connect/read-data)

**Garmin: silent rejections and a closed door.** Access requests rejected without notification; the
form removed; developers waiting 4+ months with no ETA.
[Connect IQ forum](https://forums.garmin.com/developer/connect-iq/f/discussion/434542/garmin-connect-developer-program---access-request-rejected-without-notification) ·
[Access paused thread](https://forums.garmin.com/apps-software/mobile-apps-web/f/garmin-connect-mobile-andriod/441607/garmin-connect-api-access-paused-for-months-what-are-startups-supposed-to-do/2054194)

**Oura's docs don't render for tooling.** `cloud.ouraring.com/v2/docs` is a JS SPA that returns an
empty body to scrapers, and several documented sub-pages (`/docs/webhooks`,
`/docs/personal-access-tokens`) 404 on direct fetch while being linked from the nav. Budget browser
time.

---

## 10. Recommended empirical tests (cheap, high information value)

These are not recommendations about architecture — they are the measurements that would resolve the
remaining **UNVERIFIED** items, and they are all doable in under a day.

1. **WHOOP BLE overnight test.** Enable Broadcast Heart Rate, run `whoop-live` (or 30 lines of
 `bleak`) on a laptop next to the bed, log timestamps overnight. Resolves: does broadcast survive a
 full night? What is the sample interval? Does the WHOOP app disable it at sleep onset?
2. **Galaxy Watch → phone sync lag test.** Note wall-clock time, do a hard physical exertion, then poll
 Health Connect every minute from a trivial Android app and record when the heart-rate record appears.
 Repeat once with the phone untouched overnight. Resolves the single biggest unknown in §3.
3. **Samsung Health export inspection.** Run "Download personal data" today and inspect the
 `binning_data` JSON blobs. Resolves: what resolution of nocturnal heart rate does the team's actual
 watch record? Is HRV present in the export even though it is absent from the SDK?
4. **WHOOP webhook timing test.** Register a tunnel-exposed FastAPI endpoint, sleep, and log the exact
 arrival time of `sleep.updated` and `recovery.updated` relative to wake time. Resolves the missing
 WHOOP latency SLA with your own data.

---

## 11. Bibliography

**WHOOP**
- WHOOP Developer Platform — https://developer.whoop.com/docs/introduction/
- Getting started — https://developer.whoop.com/docs/developing/getting-started/
- App approval (10-member dev limit) — https://developer.whoop.com/docs/developing/app-approval/
- OAuth 2.0 — https://developer.whoop.com/docs/developing/oauth/
- API reference (all endpoints and fields) — https://developer.whoop.com/api/
- Rate limiting (100/min, 10,000/day) — https://developer.whoop.com/docs/developing/rate-limiting/
- Webhooks — https://developer.whoop.com/docs/developing/webhooks/
- API changelog — https://developer.whoop.com/docs/api-changelog/
- v1→v2 migration guide — https://developer.whoop.com/docs/developing/v1-v2-migration/
- API Terms of Use — https://developer.whoop.com/api-terms-of-use/
- Recovery data guide — https://developer.whoop.com/docs/developing/user-data/recovery/
- Support — https://developer.whoop.com/docs/developing/support/
- whoop-live (BLE, Python) — https://github.com/grivera82/whoop-live
- WHOOP HR broadcast over ANT+ (context) — https://the5krunner.com/2023/12/28/whoop-broadcast-your-heart-rate-over-ant/
- WHOOP Unite research FAQ — https://www.sensorlab.arizona.edu/sites/default/files/2023-05/WHOOP%20Unite%20Research%20FAQs_0.pdf
- Open Wearables WHOOP analysis — https://openwearables.io/blog/whoop-api-recovery-strain-sleep-data-for-developers
- Terra WHOOP data availability — https://tryterra.co/blog/whoop-integration-series-part-2-data-available-from-the-api-ec4337a9455b

**Samsung**
- Samsung Health Data SDK overview — https://developer.samsung.com/health/data/overview.html
- Data SDK release notes (v1.1.0, 12 Mar 2026) — https://developer.samsung.com/health/data/release-note.html
- Data SDK developer mode — https://developer.samsung.com/health/data/guide/developer-mode.html
- Data SDK app creation / partner process — https://developer.samsung.com/health/data/process.html
- Data access (read / aggregate / readChanges / associated) — https://developer.samsung.com/health/data/guide/features/data-access.html
- DataType reference (full type list) — https://developer.samsung.com/health/data/api-reference/-shd/com.samsung.android.sdk.health.data.request/-data-type/index.html
- SleepType reference — https://developer.samsung.com/health/data/api-reference/-shd/com.samsung.android.sdk.health.data.request/-data-type/-sleep-type/index.html
- HeartRate entry reference — https://developer.samsung.com/health/data/api-reference/-shd/com.samsung.android.sdk.health.data.data.entries/-heart-rate/index.html
- Samsung Health SDK for Android (deprecated) — https://developer.samsung.com/health/android/overview.html
- Deprecation announcement — https://developer.samsung.com/sdp/news/en/2025/10/30/dev-insight-oct-2025-move-to-samsung-health-data-sdk-as-samsung-health-sdk-for-android-deprecates-and-other-latest-news
- Migration guide — https://developer.samsung.com/health/data/migration-guide/overview.html
- Samsung Health Sensor SDK overview — https://developer.samsung.com/health/sensor/overview.html
- Sensor SDK introduction (tracker types) — https://developer.samsung.com/health/sensor/guide/introduction.html
- **Sensor SDK data specifications (sampling rates)** — https://developer.samsung.com/health/sensor/guide/data-specifications.html
- Sensor SDK developer mode — https://developer.samsung.com/health/sensor/guide/developer-mode.html
- Sensor SDK FAQ — https://developer.samsung.com/health/sensor/faq.html
- Privileged Health SDK — https://developer.samsung.com/health/privileged
- Privileged Health SDK FAQ — https://developer.samsung.com/health/privileged/faq.html
- Codelab: heart rate data transfer watch→phone — https://developer.samsung.com/codelab/health/heart-rate-data-transfer.html
- Blog: measure and transfer HR from Galaxy Watch — https://developer.samsung.com/health/blog/en/transfer-heart-rate-from-galaxy-watch-to-a-phone
- **Blog: continuous HR with screen off (23 Apr 2026)** — https://developer.samsung.com/galaxy-watch/blog/en/2026/04/23/continuous-heart-rate-tracking-on-galaxy-watch-even-with-the-screen-off
- Health Connect FAQ (sync timing) — https://developer.samsung.com/health/health-connect-faq.html
- Accessing Samsung Health data via Health Connect (type mapping) — https://developer.samsung.com/health/blog/en/accessing-samsung-health-data-through-health-connect
- Samsung Health SDK Suite / Health Server — https://developer.samsung.com/health/server
- Health Server partner-only API reference — https://developer.samsung.com/health-server/server/partner-only/api-reference/intro.html
- Samsung Health Research Stack — https://developer.samsung.com/health/s-healthstack
- Research Stack overview — https://developer.samsung.com/health/research/overview.html
- Research Stack codelab — https://developer.samsung.com/codelab/health/research-system.html
- Research portal REST export — https://developer.samsung.com/health/research/developer-guide/portal-REST-API-reference/results-analysis/export-data.html
- Export personal data walkthrough — https://medium.com/@dimshik100/how-to-extract-your-personal-samsung-health-data-514bbe2331f7
- Export without root (stress/HRV/BIA) — https://bhived.ai/lessons/export-samsung-health-data-without-root
- samsung-health-mcp export parser — https://github.com/davidmosiah/samsung-health-mcp
- Community: HRV/breathing/RHR won't write to Health Connect — https://us.community.samsung.com/t5/Galaxy-Watch/HRV-breathing-rate-and-resting-HR-won-t-write-to-the-health/td-p/3351258
- Forum: unreliable HC sync — https://forum.developer.samsung.com/t/syncing-data-is-unreliable-between-samsung-health-and-health-connect/24850
- Forum: Health Connect delay — https://forum.developer.samsung.com/t/health-connect-delay/35955
- Forum: Partner App Program — https://forum.developer.samsung.com/t/partner-app-program/5983
- Forum: Privileged SDK partnership — https://forum.developer.samsung.com/t/samsung-privileged-health-sdk-partnership/23542

**Android / Health Connect / Wear OS**
- Health Connect — https://developer.android.com/health-and-fitness/health-connect
- Data types — https://developer.android.com/health-and-fitness/health-connect/data-types
- Read raw data (background read, history, pagination) — https://developer.android.com/health-and-fitness/health-connect/read-data
- Skin temperature feature — https://developer.android.com/health-and-fitness/health-connect/features/skin-temperature
- Get started — https://developer.android.com/health-and-fitness/health-connect/get-started
- Codelab — https://developer.android.com/codelabs/health-connect
- Health Services on Wear OS — https://developer.android.com/health-and-fitness/health-services
- MeasureClient — https://developer.android.com/health-and-fitness/health-services/active-data/measure-client
- Play Console health permissions policy — https://support.google.com/googleplay/android-developer/answer/12991134

**Fitbit / Google Health API**
- Fitbit intraday index — https://dev.fitbit.com/build/reference/web-api/intraday/
- Get HR intraday by date — https://dev.fitbit.com/build/reference/web-api/intraday/get-heartrate-intraday-by-date/
- Get HR intraday by interval — https://dev.fitbit.com/build/reference/web-api/intraday/get-heartrate-intraday-by-interval/
- Get HRV intraday by date — https://dev.fitbit.com/build/reference/web-api/intraday/get-hrv-intraday-by-date/
- Using subscriptions (webhooks) — https://dev.fitbit.com/build/reference/web-api/developer-guide/using-subscriptions/
- Google Health API about + Fitbit sunset timeline — https://developers.google.com/health/about
- Google Health API webhooks — https://developers.google.com/health/webhooks
- Google Health API REST reference — https://developers.google.com/health/reference/rest
- Google Fit migration FAQ — https://developer.android.com/health-and-fitness/health-connect/migration/fit/faq
- Validic transition guide — https://help.validic.com/space/VCS/5513478151/Fitbit+to+Google+Health+API+Developer+Transition+Guide
- Fitabase migration prep — https://www.fitabase.com/blog/post/google-health-api-announcement/
- Fitbit sync delay (third-party report) — https://support.mypacer.com/hc/en-us/articles/41581758645261-Fitbit-data-delayed-partial-sync

**Apple**
- Reading data from HealthKit — https://developer.apple.com/documentation/healthkit/reading-data-from-healthkit
- HKObserverQuery — https://developer.apple.com/documentation/healthkit/hkobserverquery
- Executing observer queries — https://developer.apple.com/documentation/healthkit/executing-observer-queries
- enableBackgroundDelivery — https://developer.apple.com/documentation/healthkit/hkhealthstore/enablebackgrounddelivery(for:frequency:withcompletion:)
- background-delivery entitlement — https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.healthkit.background-delivery
- appleSleepingWristTemperature — https://developer.apple.com/documentation/healthkit/hkquantitytypeidentifier/applesleepingwristtemperature
- Getting Apple Health data into a backend — https://openwearables.io/blog/getting-apple-health-data-into-your-backend
- Health Auto Export API docs — https://github.com/Lybron/health-auto-export
- Health Auto Export REST API help — https://help.healthyapps.dev/en/health-auto-export/automations/rest-api/

**Oura**
- Oura API docs — https://cloud.ouraring.com/docs/
- Authentication (PAT deprecated) — https://cloud.ouraring.com/docs/authentication
- Error handling — https://cloud.ouraring.com/docs/error-handling
- Oura API support article (membership requirement, data download) — https://support.ouraring.com/hc/en-us/articles/4415266939155-The-Oura-API
- Python client (v2 + OAuth2) — https://github.com/hedgertronic/oura-ring
- TypeScript client (webhook subscription API) — https://github.com/Pinta365/oura_api
- Open Wearables Oura analysis — https://openwearables.io/blog/oura-api-accessing-ring-data-sleep-hrv-readiness

**Garmin**
- Health API — https://developer.garmin.com/gc-developer-program/health-api/
- Program FAQ — https://developer.garmin.com/gc-developer-program/program-faq/
- Activity API — https://developer.garmin.com/gc-developer-program/activity-api/
- Access request form — https://www.garmin.com/en-US/forms/GarminConnectDeveloperAccess/
- Forum: program on hold — https://forums.garmin.com/apps-software/mobile-apps-web/f/garmin-connect-web/436199/garmin-connect---program-on-hold
- Forum: access paused for months — https://forums.garmin.com/apps-software/mobile-apps-web/f/garmin-connect-mobile-andriod/441607/garmin-connect-api-access-paused-for-months-what-are-startups-supposed-to-do/2054194
- Forum: rejected without notification — https://forums.garmin.com/developer/connect-iq/f/discussion/434542/garmin-connect-developer-program---access-request-rejected-without-notification
- Momentum: developer program closed — https://www.themomentum.ai/blog/garmin-developer-program-closed-roadmap

**Aggregators and research platforms**
- Terra — https://tryterra.co/ · https://tryterra.co/integrations/oura
- Sahha pricing — https://sahha.ai/pricing
- Sahha Terra alternatives comparison — https://sahha.ai/compare/terra-alternatives/
- Sahha Spike alternatives comparison — https://sahha.ai/compare/spike-api-alternatives/
- Open Wearables comparison — https://www.openwearables.io/compare
- Fitabase — https://www.fitabase.com/
- Labfront — https://www.labfront.com/
- MyDataHelps wearables fact sheet — https://careevolution.com/mydatahelps/fact-sheet-wearable-data/
- CareEvolution: wearables in clinical research — https://careevolution.com/post/wearable-device-data-in-digital-clinical-research/
- Empatica research platform — https://www.empatica.com/platform/research-studies/
- Gadgetbridge Health Connect integration PR — https://codeberg.org/Freeyourgadget/Gadgetbridge/pulls/4481
- Gadgetbridge automatic export issue — https://codeberg.org/Freeyourgadget/Gadgetbridge/issues/553

---

## 12. Unverified items requiring follow-up

| Item | Why unverified | How to resolve |
|---|---|---|
| Oura rate limit 5000 req/5 min | Oura's rate-limit page is a JS SPA that returns an empty body to fetchers | Open https://cloud.ouraring.com/v2/docs in a browser |
| Oura webhook "~30 s post-sync" | No Oura statement found | Empirical test, or browser-read the webhooks page |
| Oura PAT deprecation date (Dec 2025) | Secondary sources only; Oura's own page 404s to fetchers | Browser-read https://cloud.ouraring.com/docs/personal-access-tokens |
| Fitbit 150 req/hour/user rate limit | Not confirmed against a current Fitbit page in this pass | Read https://dev.fitbit.com/build/reference/web-api/troubleshooting-guide/rate-limits/ |
| Garmin $5,000 production fee | Third-party claim; Garmin publishes no pricing | Moot — access is closed |
| Garmin NDA requirement | Not documented anywhere found | Moot |
| WHOOP BLE broadcast overnight persistence | No documentation either way | **Empirical test — highest value experiment** |
| WHOOP webhook sync-to-delivery latency | No published SLA | Empirical test |
| Galaxy Watch → phone sync interval | Samsung explicitly declines to specify | Empirical test |
| Whether the team's specific Galaxy Watch model supports `SKIN_TEMPERATURE_CONTINUOUS` / `EDA_CONTINUOUS` | Model-dependent (GW5+ and GW8+ respectively) | Call the SDK's capability-check API on the actual device |
| Labfront academic free tier | Claim seen historically, not confirmed for 2026 | Contact Labfront |
| Google Health API rate limits and test-user policy | Rate-limits page 404s to fetchers | Browser-read developers.google.com/health |
