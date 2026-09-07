# Component 15. Interaction and interface

**Phase:** the Telegram notifier lands in Phase B; the dashboard is Phase C.
**Depends on:** `service/` (component 14) and the view models in `docs/CONTRACTS.md` 6.5.
**Imports nothing else.** No `sqlite3`, no `detect/`, no `belief/`, no `policy/`, no `agent/`,
no `db/`. A lint rule enforces this.

---

## 1. Principles

1. **Silent by default.** On most days there is nothing to see and nothing should be opened.
2. **The system initiates.** When the agent wants something it reaches the person on their phone.
3. **Trust comes from evidence.** Every number on screen traces to a stored row; every clinical
   claim shows its source; every pipeline stage shows whether it ran or was skipped and why.
4. **No business logic here.** Pages call `service/` and render the result.
5. **The interface does not know what a demo is.** It renders subjects. See `04-decisions.md` D-115.

---

## 2. The interaction model

```
  morning batch flags a deviation, red flags clear, episode opens
        |
  the LLM investigates (T1 tools), belief updates
        |
  policy selects a Probe by expected value of sample information, authorises ASK
        |
  the LLM writes the question text for that probe
        |
  outbound validation  ->  Telegram message with inline buttons
        |
  the person taps one option, from anywhere
        |
  belief updates, policy re-decides, the episode advances
        |
  on close, a short summary message with a link to the dashboard
```

The dashboard is where someone goes for the detail behind that summary. It is not required for the
loop to complete.

---

## 3. Telegram notifier

### 3.1 Position in the control model

Sending is a **T4** action: user-facing, and it cannot be undone. Therefore:

- The notifier is **not an agent tool**. It is absent from the tool registry and the LLM cannot call
  it. It is invoked by deterministic code in the episode state machine.
- The LLM writes the question *text*, but only for a `Probe` the arithmetic already selected. It
  cannot choose to send and it cannot invent a probe.

Full security posture and the narrowed exfiltration claim: `04-decisions.md` B-7.

### 3.2 Implementation

Raw HTTP against the Bot API via `httpx`, synchronous, in a background thread started by
`wha serve`. **Not `python-telegram-bot`**, whose async-first design from version 21 fights
Streamlit's threading model.

| Concern | Rule |
|---|---|
| Receiving | `getUpdates` long-poll, 30 second timeout. Offset persisted in `telegram_offset` so an update is never processed twice |
| Sending | `sendMessage` with `reply_markup.inline_keyboard` |
| Identity | Any update whose `chat.id` differs from `WHA_TELEGRAM_CHAT_ID` is dropped and logged with `safety_event='unauthorised_sender'`. **The message content is not logged** |
| `callback_data` | Hard limit `TELEGRAM_CALLBACK_MAX_BYTES` (64). Format `a:<interaction_id[:8]>:<option_id>`. Never JSON |
| Idempotency | Every `callback_query` is acknowledged with `answerCallbackQuery`, and the interaction moves `PENDING -> ANSWERED` in one transaction. A duplicate tap is a no-op |
| Failure | A send failure writes `notifications.status='FAILED'` plus a `system_status` row. It never raises into the episode |
| Default | `WHA_NOTIFY_CHANNEL=none` unless configured |

### 3.3 Message kinds

A closed enum, each with a fixed template. There are no others.

| Kind | Trigger | Buttons | Links |
|---|---|---|---|
| `QUESTION` | Policy returned `ASK` | The probe's answer options, plus `Not now` | `interaction_id` |
| `MEASUREMENT` | Policy returned `MEASURE` | `Done`, `Can't right now` | `measurement_id` |
| `ESCALATION` | Red-flag intercept, or policy returned `ESCALATE` | None. Text only, with explicit care guidance | `episode_id` |
| `OUTCOME` | Episode closed | `View detail`, a URL button to the dashboard | `episode_id` |
| `SYSTEM` | Bridge unreachable beyond `INGEST_STALE_REFUSE_HOURS` | None | none |

### 3.4 Outbound validation

Before any send, text passes `safety/outbound.py::validate_outbound`:

- at most `OUTBOUND_MAX_CHARS`
- no URLs except the single dashboard link on `OUTCOME`
- no markup control characters beyond the template's own
- the `probe_id` must exist in `data/knowledge/probes.yaml`
- the option slots must match `Probe.answer_space` in count and order

A failure is a hard stop, logged `safety_event='outbound_rejected'`, and the probe's
`fallback_text` is sent instead of the LLM phrasing, with `text_source='fallback'`.

### 3.5 Edge cases that must be handled

| Case | Behaviour |
|---|---|
| Tap on an expired question | Acknowledge with "this question has expired". No state change |
| Free text with no pending question | Reply pointing to the dashboard. Do **not** open an episode |
| Free text while a question is pending | Store as `free_text` on the interaction and treat as an answer |
| `Not now` | `status='DECLINED'`. **The interruption budget is still consumed.** The policy must proceed without the answer |
| Two questions pending at once | Impossible by construction: at most one `AWAITING_USER` interaction per subject. Assert it |
| Telegram unreachable | Queue the notification, retry next scheduler tick, park the episode. Never lose it |
| Answer arrives both in Telegram and in the dashboard | First writer wins; the second is a no-op on an already `ANSWERED` row |

---

## 4. Dashboard

Streamlit. **Five navigation entries plus one drill-down.**

```
src/wha/ui/
  app.py                    entry point, sidebar, subject selector
  pages/
    1_Today.py
    2_History.py
    3_Audit.py
    4_Evaluation.py
    5_Settings.py
  components/
    status_strip.py
    night_chart.py
    belief_chart.py
    pipeline_trace.py
    episode_panel.py
    citation_list.py
```

Episode detail is **not** a navigation entry. It renders inside History via `st.query_params`
(`?episode=<id>`), so a Telegram message can link straight to it.

The **subject selector** lives in the sidebar and is hidden entirely when only one subject exists.

| Surface | The one sentence that distinguishes it |
|---|---|
| **Today** | What needs you right now |
| **History** | What has happened |
| **Episode** (drill-down) | Why one specific thing happened, in full |
| **Audit** | The raw evidence trail, for scrutiny |
| **Evaluation** | How well the system actually works |
| **Settings** | Configuration |

### 4.1 Today

The only page anyone should need. Order, top to bottom:

**1. Status strip.** Rendered on every page. One row of compact indicators from
`service.status.get_system_status`, each ok, warn or error with a tooltip: watch data (time since
last successful ingest), baseline (usable nights and rung, as progress toward `MATURE`), scheduler
(last run and result), LLM provider (reachable, unreachable, or `cassette`), notifications (channel
and last send result), errors in the last 24 hours.

Refreshed inside an `st.fragment` on a 10 second interval so the rest of the page does not re-run.

**2. The inbox.** Exactly one of, from `service.episodes.get_pending_interaction`:

- A **pending question**: the LLM-written text, the options as buttons, an optional free-text box,
  and `Not now`. Submitting calls `service.episodes.submit_answer`. This is the same interaction the
  Telegram message carries, so answering in either place resolves it.
- A **pending measurement**: the instruction and a `Done` button.
- A **conclusion awaiting review**: approve, edit, reject, escalate, via
  `service.episodes.submit_human_decision`.
- **Nothing pending**, the common case, which must read as reassuring rather than empty:
  "Nothing needs your attention. Last checked <time>. <N> quiet nights in a row."

**3. Last night, in one line.** Resting heart rate, deviation against the personal band, verdict,
and a link into History.

**4. Open episodes**, if any, as one-line summaries linking to the episode panel.

### 4.2 History

**1. The night chart** from `service.nights.list_nights`. Nocturnal resting heart rate over time,
with the personal band as a shaded region that visibly **narrows as the baseline matures**. Nights
coloured by `DetectionLevel`.

> **Non-usable nights are drawn as gaps and are never interpolated.** Imputing across a coverage gap
> manufactures normality exactly where there is no evidence.

**2. Episode spans** beneath the chart, each covering the nights it spans, coloured by disposition,
clickable.

**3. The night table.** One row per night: date, resting heart rate, deviation, explained, residual,
coverage, level, and whether an episode opened. Sortable and filterable. Expanding a row shows the
full computation from `service.nights.get_night_detail`: every input and every intermediate value.

### 4.3 Episode panel (drill-down)

Four tabs, all from `service.episodes.get_episode`.

**Tab 1, Summary.** The `EpisodeOutcome` as a card: disposition, observation, the ranked
differential as a horizontal bar chart with supporting and contradicting evidence per row, the
action, the explicit escalation criteria, the confidence, the baseline rung at the time, and the
budgets consumed. `unsupported_claims` is shown as a number, because a zero there is a claim about
the system's honesty.

**Tab 2, Trace.** `EpisodeDetail.stages` rendered as an ordered list, each with an icon for `RAN`,
`SKIPPED`, `FAILED` or `PENDING`, a duration, a one-line reason, and an expander holding inputs and
outputs.

Canonical stage order:

```
nightly batch:  INGEST -> QUALITY_GATE -> FEATURES -> BASELINE -> DETECT -> EXPLAIN -> FORECAST
episode:        RED_FLAG -> INVESTIGATE -> BELIEF -> POLICY -> ACT -> NOTIFY
                -> CRITIQUE -> CONCLUDE -> HUMAN_REVIEW
```

`INVESTIGATE` expands to the **individual T1 tool calls the model chose**, in order, each with its
arguments, its source identifier, its timestamp and its freshness verdict. This is the single most
convincing thing in the interface, because it shows the path was decided at run time rather than
scripted.

> **Skipped stages are as informative as run ones and must be shown, not hidden.** Two examples that
> demonstrate the system is deciding rather than executing a fixed pipeline:
> "NOTIFY skipped: policy returned OBSERVE, no probe cleared the interruption cost" and, inside
> `INVESTIGATE`, "retrieve_clinical_evidence not called: deviation fully explained by a recorded
> workout, no clinical evidence needed".

Below the stage list, **belief evolution** from `EpisodeDetail.belief_history`: the per-cause
marginals at each `seq`, annotated with the trigger that caused each update, plus `p_illness` drawn
as a separate line against the derived 0.10 decision threshold.

> The marginals are **probabilities that each cause is contributing** and **do not sum to 1**. Label
> the axis accordingly. Presenting them as a partition would misstate the model.

**Tab 3, Conversation.** The transcript using `st.chat_message`, from `InteractionView`. For each
question it shows the text, **which probe it served**, its `evsi` and `interruption_cost`, and
**the alternatives that were rejected with their scores**. Then the answer and how the belief moved.

Below the transcript, a free-text box answered by `service.episodes.ask_about_episode`, which is
bounded to that episode's own stored evidence and citations and has no tool access. Every answer
renders its citations; a `GroundedAnswer` with `refused=True` says so rather than guessing.

**Tab 4, Evidence.** Retrieved passages with source, title, score and text, plus
`EpisodeDetail.stripped_claims`, the claims removed for having no source. **The stripped list is
deliberately visible.**

### 4.4 Audit

`service.audit.query_audit` rendered as a filterable, paginated table: episode, actor, operation,
control tier, tool, permission decision, safety event, date range. CSV and JSON export via
`export_audit`.

A separate panel calls `service.audit.verify_hash_chain` and shows a single pass or fail with the
first bad row if any. That is the tamper-evidence demonstration.

Distinct from the episode trace: the trace is the story of one investigation, the audit log is the
cross-cutting record for scrutiny.

### 4.5 Evaluation

Static, rendered from `EvaluationResult`, never computed on page load.

- **Detection** on the cohort: episode-level recall with Clopper-Pearson exact intervals, lead-time
  distribution, false alert events per user-week, number needed to evaluate. Both mandatory
  baselines shown alongside: a random detector matched on alert rate, and a trivial fixed-threshold
  rule.
- **The baseline-age curve**: recall and false-alert rate against nights of history, with the
  statistical baseline and Chronos drawn on the same axes. **If Chronos does not extend usable
  detection to earlier nights, the page says so plainly. A reported negative result is a finding.**
- **The policy benchmark** against never-ask, always-ask, fixed-threshold and silent concordance,
  with the accuracy-versus-interruption frontier as `POLICY_COST_PER_INTERRUPT` and the
  miss-to-false-alarm utility ratio are swept.
- **Ablations**, each with a paired bootstrap interval.
- **The adversarial suite**: attack success rate, with the injection-contained demonstration shown
  as a side-by-side of clean and poisoned corpus runs.

Every panel prints `sample_size` and renders `caveats`, so underpowered claims are stated rather
than implied.

### 4.6 Settings

From `service.settings.get_settings` and `update_settings`.

- **Connection**: bridge host, port, token, a **Test connection** button, and written setup
  instructions for the Health Connect Webhook app.
- **LLM**: provider, base URL, key, model, and a **Test** button.
- **Notifications**: channel, bot token, chat id, a **Send test message** button, and a short guide
  to creating a bot.
- **Policy**: interruption budget, depth budget, cost weight, thresholds. Changes are written and
  **logged as audit events**, because changing a threshold changes behaviour.
- **Data**: retention, export everything, and **delete all my data** behind a typed confirmation,
  calling `service.settings.delete_all_subject_data`.

Secrets are `SecretStr` on `SettingsPatch`, rendered as password fields, **never echoed back after
saving**, and never written to the audit log. `Settings` carries no secret fields at all.

---

## 5. Prohibited in this component

- Business logic of any kind.
- Direct database access. No `sqlite3` import anywhere under `ui/`.
- Network calls except through `service/`.
- Writing to `data/knowledge/`.
- Demo-specific branches.

---

## 6. Testing

`streamlit.testing.v1.AppTest`, against a database seeded from the scenario fixtures.

| Test | Asserts |
|---|---|
| `test_today_nothing_pending` | Reassurance text renders, no answer button appears |
| `test_today_pending_question` | Question text and every option render; clicking one calls `submit_answer` once |
| `test_today_status_strip_degraded` | With a stale ingest, the watch indicator is error and names the staleness |
| `test_history_gaps_not_interpolated` | A night below `MIN_NOCTURNAL_MINUTES` produces a gap, not a value |
| `test_history_band_narrows_with_maturity` | Band width at 5 nights exceeds band width at 28 |
| `test_episode_trace_shows_skipped` | A `SKIPPED` stage renders with its reason, not hidden |
| `test_episode_trace_expands_tool_calls` | `INVESTIGATE` lists each tool call with source and freshness |
| `test_episode_conversation_shows_rejected_probes` | Each question shows its `evsi` and the rejected alternatives with scores |
| `test_ask_about_episode_refuses_ungrounded` | A `GroundedAnswer` with `refused=True` renders as a refusal, not a guess |
| `test_audit_hash_chain_verifies` | Pass on a clean fixture, fail with a row number on a tampered one |
| `test_settings_secrets_not_echoed` | After saving, the token field does not contain the token |
| `test_subject_selector_hidden_when_single` | With one subject, no selector renders |
| `test_evaluation_renders_caveats` | Every panel shows `sample_size` and any `caveats` |

Telegram is tested separately against recorded Bot API responses, with no network:

| Test | Asserts |
|---|---|
| `test_callback_data_within_limit` | For every probe in the bank, every option yields `callback_data` at or under `TELEGRAM_CALLBACK_MAX_BYTES` |
| `test_unauthorised_chat_id_dropped` | An update from another chat changes no state and logs the safety event without content |
| `test_duplicate_tap_is_noop` | The same `callback_query` twice produces one state change |
| `test_not_now_consumes_budget` | Declining still decrements the interruption budget |
| `test_outbound_rejects_url` | LLM phrasing containing a URL falls back to `probe.fallback_text` with `text_source='fallback'` |
| `test_outbound_rejects_slot_mismatch` | Options differing in count from `Probe.answer_space` are rejected |
| `test_send_failure_does_not_raise` | A 500 leaves the episode intact and queues a retry |
| `test_offset_persisted` | A restart does not reprocess an already-handled update |
