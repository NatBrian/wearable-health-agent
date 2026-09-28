# Vite Dashboard Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore every legacy Streamlit capability, interaction, explanation, and disclosure in the Vite dashboard, while improving its visual hierarchy and responsive behavior and correcting the regressions identified in the PR review.

**Architecture:** Keep React, TypeScript, Vite, the typed HTTP client, and FastAPI. Split the current frontend monolith into five view modules and focused shared components. Keep health calculations, policy decisions, thresholds, filters over domain records, and numeric configuration in the API/service layer. Reuse existing API endpoints first; add only narrow service/API support where the reviewed Vite implementation or current API contract is insufficient. Do not add a router or global state library.

**Tech Stack:** React, TypeScript, Vite, Tailwind CSS, FastAPI, Pydantic, existing service layer, Vitest and React Testing Library for focused frontend behavior checks, and the available Playwright MCP for the final real-interface pass.

**Spec:** `docs/superpowers/specs/2026-09-28-vite-dashboard-parity-design.md`

## Implementation Scope and Sources

- Implement against PR #3's reviewed head, `214c39b` (`origin/pr/3`), after creating an isolated worktree at that revision. The current documentation branch is based on `main`; it is not the frontend implementation checkout. Carry the approved spec and this plan into the implementation worktree. Do not rewrite or force-push the existing PR branch.
- Use the legacy UI at `origin/main:src/wha/ui/` and `docs/DISCLOSURES.md` as the behavioral and wording sources. The legacy UI is the requirements source, not a styling template. Do not invent or clinically re-author copy.
- Preserve every legacy content key from `src/wha/ui/explain.py` and every explanatory section in `src/wha/ui/components/how_it_works.py`. Preserve all disclosure rows from `docs/DISCLOSURES.md` in the relevant live view. Replace embedded numbers only with values returned by the API/config; do not lose the surrounding explanation.
- The PR review found the Vite implementation incomplete in content, behavior, API boundaries, and responsive layout. Treat the review findings and the spec's feature inventory as merge gates, not optional polish.

## Legacy Source-to-React Parity Map

Every source below must have a React destination and a behavior/content check. Combining components is fine only when all original information and actions remain available.

| Legacy source | Required React destination | Preservation check |
| --- | --- | --- |
| `src/wha/ui/Home.py` | `frontend/src/views/HomeView.tsx` | Subject selection/empty state, status, emergency guidance, system limits, how a night is judged, navigation cards, evidence-provenance explanation and live entry count. |
| `src/wha/ui/pages/1_Today.py` | `frontend/src/views/TodayView.tsx` | Current night, verdict and explanation, baseline maturity, episodes, oxygen context, every pending interaction, conversation, citations, and handover prepare/preview/copy. |
| `src/wha/ui/pages/2_History.py` | `frontend/src/views/HistoryView.tsx` | Time window, level and investigated-only filters, show-every-field toggle, chart, table, conclusion explanation, honest empty state, night picker, and link to that night's trace. |
| `src/wha/ui/pages/3_The_record.py` | `frontend/src/views/RecordView.tsx` | Pipeline, night navigation, step detail, hash-chain state, plain-language records and exact-detail expansion, audit filters/export, conversation archive, and How it works. |
| `src/wha/ui/pages/4_Settings.py` | `frontend/src/views/SettingsView.tsx` | Profile, bridge, model, notification/Telegram, all three budgets, diagnostics, save feedback, secrets, and safe deletion behavior. |
| `src/wha/ui/components/subject.py` | `frontend/src/subject/resolveSubject.ts` and shell selector | Configured/remembered/sole subject resolution; explicit choice when multiple subjects remain; no silent first-row selection. |
| `src/wha/ui/components/status_bar.py` | `frontend/src/components/StatusBar.tsx` | All service, ingest, scheduler, baseline, and recent-data status fields, with loading/error/unavailable states. |
| `src/wha/ui/components/verdict.py` | `frontend/src/components/VerdictPanel.tsx` | Level, investigation state, maturity-aware explanation, next step, and non-diagnosis limitation. |
| `src/wha/ui/components/chat.py` | `frontend/src/components/ChatPanel.tsx` and pending controls | Current-night/episode transcript and question, measurement, review, decline, and free-text flows. |
| `src/wha/ui/components/citations.py` | `frontend/src/components/CitationPanel.tsx` | Source attribution, full passage, quote-span status, unsupported-claim warning, and the limitation of the quote check. |
| `src/wha/ui/components/night_chart.py` | `frontend/src/components/HistoryChart.tsx` | Calendar gaps, per-night bands, level markers, labels, keyboard-accessible night selection, and chart explanation. |
| `src/wha/ui/components/pipeline_graph.py`, `step_detail.py` | `frontend/src/components/PipelineTrace.tsx`, `PipelineStepDetail.tsx` | Ordered step graph, status/layer legend, selection, inputs/outputs/sources, unrecorded-step explanation, and accurate current pipeline wording. |
| `src/wha/ui/components/how_it_works.py` | `frontend/src/components/HowItWorks.tsx` | Every section and caveat, with claims matching current API behavior. |
| `src/wha/ui/explain.py` | `frontend/src/content/legacyCopy.ts` | Every copy key and its meaning preserved, no static numeric claims or forbidden reassurance phrases. |
| `src/wha/ui/format.py` | `frontend/src/lib/format.ts` | Date, time, missing-value, BPM, coverage, range, and local-time formatting only; no domain decisions. |
| `src/wha/ui/design.py` | `frontend/src/index.css` and shared primitives | Retain useful brand tokens while redesigning hierarchy and layout for the Vite interface; do not copy Streamlit widget/table styling. |
| `src/wha/ui/components/api.py` | `frontend/src/api.ts` | Typed transport, explicit expected-absence handling, surfaced failures, and no direct browser access to service/database logic. |

## Global Constraints

- Preserve all rows in the spec's feature inventory and the source-to-React map above. A feature is not preserved merely because related data exists in the API or the text remains in Markdown.
- Do not change clinical rules, model behavior, thresholds, cause weights, evidence claims, or health guidance. Source user-facing clinical text from the legacy copy/disclosure sources. Every displayed figure must come from the API or a backend operating parameter.
- Keep all calculations and domain filtering in backend/service code. Frontend calculations are limited to visual layout, formatting, input state, and selecting a user-requested view.
- Use the existing endpoints for review, conversation sessions, handover, audit, export, profile, diagnostics, settings, and provenance wherever they already meet the needed contract.
- Keep `me` data undeletable from the UI. Only disposable `sim` and `demo` data can be deleted, with the affected subject named and explicit confirmation.
- Keep secrets write-only. Failed sends/saves must retain entered text and show an actionable error; success must be explicit.
- Keep the API local-only, allow only explicit configured frontend origins through CORS, and do not describe CORS as authentication. Keep the Vite dev/preview server on loopback by default.
- Do not introduce a second Streamlit runtime, a new router, global state framework, unrelated API refactors, or a broad authentication system.
- Use `uv run` for all Python commands. Run the full backend suite and Ruff once at the end, then drive the actual demo UI and inspect the rendered artifact. Do not alter, skip, weaken, or xfail existing tests.

## Review Focus: Five High-Risk States

Each state must have a named automated check in the task list and an explicit observation in the final Playwright pass.

1. **No subject and ambiguous subjects:** no data, API failure, configured subject, sole subject, and multiple unconfigured subjects must remain distinct; all views must use the same selected subject. Cover in Tasks 1 and 3.
2. **Cold or prior-dominated baseline:** a missing pending episode must never render as a health all-clear; display the legacy maturity explanation and current measurement limitation. Cover in Tasks 1 and 4.
3. **Pending interaction variants:** question with option, free-text answer, decline, measurement instruction/result, and human-review decision must each have a reachable action and visible result/error state. Cover in Tasks 1 and 4.
4. **Evidence and failed writes:** cited response, uncited response with no citations, missing quote span, full passage attribution, and failed chat/settings save must retain warnings/input and distinguish API failure from empty data. Cover in Tasks 1, 4, and 7.
5. **Sparse history on a narrow screen:** missing calendar dates, per-date baseline bands, each History filter, trace navigation, and narrow viewport must remain understandable and operable. Cover in Tasks 1, 5, and 8.

## Implementation Tasks

### Task 1: Add the frontend behavior test harness and parity inventory

**Files:** `frontend/package.json`, `frontend/package-lock.json`, `frontend/vitest.config.ts`, `frontend/src/test/setup.ts`, `frontend/src/test/legacyParityInventory.ts`, `frontend/src/__tests__/`

- [ ] Add Vitest, jsdom, and React Testing Library with a `test` script. Keep the dependency set limited to component-level behavior checks; do not add a separate E2E framework.
- [ ] Convert the spec's source-to-React map and disclosure/copy inventory into test data. Include every `explain.py` key and every `DISCLOSURES.md` row, each with its required view/component destination.
- [ ] Add focused failing checks for the five high-risk states above. Assert visible user outcomes and API calls, not Streamlit-specific implementation details.
- [ ] Add a check that every legacy copy/disclosure key is represented, numeric prose is not typed into frontend copy, and no copy violates the existing forbidden-phrase rule.
- [ ] Keep tests deterministic with mocked API responses. Do not require network access or depend on mutable demo database state.
- [ ] Run the focused frontend tests while implementing each slice; reserve the full backend suite and Ruff for Task 8.

**Done when:** the harness runs in the frontend package and parity omissions produce a focused, readable failure rather than being discoverable only by manual review.

**Commit intent:** explain that regression checks protect the legacy user-facing contract.

### Task 2: Correct the API boundary, CORS, subject resolution data, and display summaries

**Files:** `frontend/src/api.ts`, `frontend/vite.config.ts`, `src/wha/api/app.py`, `src/wha/service/nights.py`, `src/wha/models.py`, `tests/unit/api/test_app.py`, `tests/unit/api/test_pipeline_endpoints.py`, new focused service/API tests as needed

- [ ] Replace the generic `404 => null` behavior with a typed API error. Add explicit optional-resource handling only to methods whose endpoint documents absence as an expected result; preserve distinct empty, unavailable, and failed states.
- [ ] Add typed client calls for existing APIs the React app does not yet expose: config, subject profile/update/delete, pipeline-night index, review, urgency/acknowledgement, handover, audit query/export, knowledge provenance, and diagnostics. Keep request and response types aligned with Pydantic models.
- [ ] Scope conversation-session requests by `since_night` for Today, while leaving the unscoped session endpoint for The record archive.
- [ ] Replace wildcard CORS with an exact allowlist from backend configuration, including the loopback Vite origin used by dev/preview. Test allowed preflight, rejected unlisted origin, and that the response never advertises `*`. Keep the API bound to loopback.
- [ ] Restrict CORS methods and headers to the methods and headers the frontend actually uses; do not leave the reviewed wildcard methods/headers in place after narrowing origins.
- [ ] Change Vite dev and preview hosts from `0.0.0.0` to loopback by default. Keep the current API base URL configurable without adding another state/configuration library.
- [ ] Add a narrow backend dashboard summary only for data the current client otherwise computes or mislabels: latest sleep observation/date, latest steps observation/date, and the calendar-window steps average plus its returned window bounds. Use a backend configuration value for the averaging interval; do not average the last N non-null samples in React.
- [ ] Add backend query support for History's level and investigated-only filters if the existing API does not provide it. Keep the unfiltered calendar series available for the chart; preserve gaps from `service.list_nights`.
- [ ] Expose History window options and setting control bounds from backend configuration/schema so labels and limits do not become frontend numeric literals. Preserve the legacy-supported ranges exactly.
- [ ] Add endpoint/service tests for summary dates, calendar averaging with missing readings, filter semantics, subject/config resolution inputs, CORS, and expected-absence versus server failure.

**Done when:** browser code has no domain aggregation/filtering, all required legacy API capabilities are typed and callable, and API tests prove local-origin behavior and correct summary/filter semantics.

**Commit intent:** explain that accurate client data and explicit local-origin boundaries protect the record and prevent misleading displays.

### Task 3: Build the shared shell, subject resolver, Home, status, and complete copy catalog

**Files:** `frontend/src/App.tsx`, `frontend/src/useBackend.ts`, `frontend/src/subject/resolveSubject.ts`, `frontend/src/views/HomeView.tsx`, `frontend/src/components/StatusBar.tsx`, `frontend/src/components/HomeDisclosure.tsx`, `frontend/src/content/legacyCopy.ts`, `frontend/src/lib/format.ts`, `frontend/src/index.css`, focused files under `frontend/src/__tests__/`

- [ ] Reduce `App.tsx` to shell/navigation, active-view state, a shared selected subject, loading/error handling, and view composition. Keep five destinations: Home, Today, History, The record, Settings.
- [ ] Resolve a subject using `/config.configured_subject`, the current in-app remembered selection, and the sole-subject fallback. If there are multiple subjects without a usable configured/remembered selection, require an explicit selection; never use `subjects[0]` silently. Distinguish no subjects from API errors.
- [ ] Use that one subject state for every view and make the selected identity visible. Preserve the empty-state explanation from Home and provide a safe route to settings/setup where appropriate.
- [ ] Create the central legacy copy catalog from the archived `explain.py` and the documented disclosures. Keep keys stable, preserve wording and context, and interpolate any operating/clinical values from typed API data. Do not paraphrase clinical meaning or delete an explanation to make the page shorter.
- [ ] During implementation, compare every catalog entry and disclosure row directly against its archived source, record its React destination in the parity inventory, and review the complete rendered copy in context. A key-presence test alone is not sufficient evidence that text was preserved.
- [ ] Map every row in `docs/DISCLOSURES.md` to a live Home, Today, Settings, or Record destination and test the destination. Keep the standing medical-device disclaimer and emergency guidance prominent on Home.
- [ ] Rebuild Home with clear hierarchy and the Vite visual system: what the system is, emergency guidance, what it can/cannot do, how a night is judged, navigation cards, and the live provenance entry count. Keep the count as entries, not figures, and keep the legacy explanatory sentence.
- [ ] Rebuild the status component from the full legacy status bar data, with explicit loading, stale, unavailable, and error presentation. Use text/icons with color.
- [ ] Remove `computeStreak` and any Home/Today statistic inferred in React; use returned backend summary/status fields or omit a metric that has no supported backend result.
- [ ] Remove the reviewed client-only direction/severity heuristics, including the `0.5 BPM` delta direction and `1.5 sigma` styling rules. Use an existing backend result when it has the same documented meaning; otherwise omit the heuristic rather than inventing a clinical interpretation.
- [ ] Preserve view-level visual clarity without copying Streamlit columns, tables, widget styling, or spacing.

**Tests:** configured/remembered/sole/ambiguous/no-subject/error cases; all disclosure and copy keys map to visible destinations; live provenance count is labeled as entries; Home contains emergency and standing disclaimer text; static copy contains no UI digits or forbidden reassurance.

**Done when:** all screens share one explicit subject choice, Home preserves every legacy section, and copy inventory coverage is complete.

**Commit intent:** explain that the landing screen and one consistent subject context are the user's safety and navigation boundary.

### Task 4: Restore Today, verdict, evidence, interaction, conversation, and handover workflows

**Files:** `frontend/src/views/TodayView.tsx`, `frontend/src/components/VerdictPanel.tsx`, `frontend/src/components/ChatPanel.tsx`, `frontend/src/components/PendingInteraction.tsx`, `frontend/src/components/CitationPanel.tsx`, `frontend/src/components/OxygenContext.tsx`, `frontend/src/api.ts`, focused files under `frontend/src/__tests__/`

- [ ] Preserve the current status, overnight metrics, episode/urgency, sleep/steps/oxygen summaries, baseline maturity, per-cause provenance, evidence explanations, and doctor handover. Show the actual latest sleep/steps observation dates from the API summary.
- [ ] Restore the complete legacy verdict and next-step wording for each level. For a cold/prior-dominated baseline, display the maturity explanation and do not imply that an absent episode or normal-looking result means health was assessed as clear.
- [ ] Render each pending kind explicitly. Questions must support listed options, optional free text where allowed, and decline. Measurements must show instructions and the supported submitted/result state. Reviews must show the draft outcome and the existing accept/revise/reject decision controls supported by the API. Disable repeat submission while pending and show retryable errors without losing input.
- [ ] Scope Today chat to the active night/episode using the existing `since_night` API capability. Preserve current messages, attribution, urgency/safety output, and retryable send behavior.
- [ ] Render uncited/unsupported warnings independently of citation-array presence. Show complete source attribution and the complete inspectable passage; identify whether the quoted span was found; retain the copy explaining that a matching span does not prove the surrounding claim is fair to the source. Remove the reviewed passage truncation.
- [ ] Preserve oxygen source/population caveats, measurement limitations, dates, and explicit no-all-clear meaning. Do not present oxygen as the current threshold/safety pathway unless the API says so.
- [ ] Restore handover prepare, preview, and copy actions using the current API response. Give confirmation/error feedback and keep the prepared text available if clipboard access fails.
- [ ] Fix every pending-state label/action and citation branch against the legacy copy inventory. Keep urgency logic and safety decisions in the backend.

**Tests:** cold/prior-dominated baseline; each pending kind and response path; review submit body; active-chat session boundary; uncited claim with an empty citation list; missing quote span; complete passage/source display; oxygen caveat; handover prepare/preview/copy and failure; failed chat send retains input.

**Done when:** every legacy Today capability is actionable and the five high-risk baseline, pending, and evidence states have direct regression coverage.

**Commit intent:** explain that complete, correctly scoped interactions prevent unanswered work and unsupported claims from looking resolved.

### Task 5: Restore History controls and make chart/table data accurate

**Files:** `frontend/src/views/HistoryView.tsx`, `frontend/src/components/HistoryChart.tsx`, `frontend/src/api.ts`, `src/wha/api/app.py`, `src/wha/service/nights.py`, relevant `frontend/src/__tests__/`, relevant backend service/API tests

- [ ] Restore the legacy time-window choices, level filter, investigated-only filter, show-every-recorded-field toggle, night-by-night table, conclusion explanation, empty-filter explanation, and per-night trace action.
- [ ] Obtain the time-window labels and day ranges from the API/config. Preserve the legacy windows and default selection. The show-every-field option changes visible fields only; it must expose all fields in the legacy table.
- [ ] Keep domain filtering server-side. When filters change, request the corresponding records from the API; do not reimplement episode/level semantics in React.
- [ ] Keep the chart's full calendar series and its empty dates. Render each point with its own returned band, rather than applying the last band's values to the whole date range. Do not join across missing nights. Keep all non-chart data/status distinctions visible.
- [ ] Keep calendar-axis gaps distinct from recorded but unusable nights; do not let a usability filter silently erase the fact that a night was recorded but could not be judged.
- [ ] Keep chart labels and selection operable by keyboard and touch; provide a non-visual equivalent selection/list for assistive technology.
- [ ] Ensure a filtered empty table says no rows match and makes clear this is not a health statement. Preserve API failure as a distinct error state.
- [ ] Make the History trace action open The record on the selected night and retain that date as the selected pipeline night.

**Tests:** each window/filter combination; all-fields columns; empty filter versus API failure; calendar gaps stay empty; point-specific bands; selected-night navigation; returned numeric window/config values rather than static frontend numbers.

**Done when:** History preserves every legacy control and presents sparse dates and baseline bands without implying unmeasured nights were normal.

**Commit intent:** explain that accurate history and reachable drill-down protect the meaning of past measurements.

### Task 6: Restore The record, pipeline, audit, archive, and How it works

**Files:** `frontend/src/views/RecordView.tsx`, `frontend/src/components/PipelineTrace.tsx`, `frontend/src/components/PipelineStepDetail.tsx`, `frontend/src/components/AuditTable.tsx`, `frontend/src/components/ConversationArchive.tsx`, `frontend/src/components/HowItWorks.tsx`, `frontend/src/api.ts`, focused files under `frontend/src/__tests__/`

- [ ] Restore the three legacy Record areas: selected night step-by-step, everything recorded/audit, and How it works. Use clear Vite tabs/sections while keeping every detail discoverable.
- [ ] Restore the pipeline-night selector, Earlier/Later controls, selected-night retention, latest usable-night default, step selection, and step detail with recorded inputs/outputs/sources. Distinguish an empty record, unrecorded step, skipped step, and failed fetch.
- [ ] Preserve the pipeline legend and explanation. Remove false static claims that a Chronos-Bolt zero-shot forecast is active or that clinical priors are literature-backed; represent `NOT_RUN`, `ASSUMED`, and other provenance/status values from API data accurately. Explain that a missing trace is a record gap, not proof that a step was skipped.
- [ ] Preserve hash-chain outcomes for empty, intact nonempty, and broken chains; plain-language events; recorded timestamp; expandable exact details; and actor/operation/episode filters with filtered export.
- [ ] Preserve the filtered audit table's fields and explain actor/permission labels. Keep exported content based on active filters and provide a usable download action.
- [ ] Restore conversation archive with explicit date/session boundaries, turn counts, urgency, source titles, uncited labeling, and per-session expansion. Never flatten archived sessions into Today's active chat.
- [ ] Move every `how_it_works.py` explanation into its React section, retaining citations/caveats and avoiding claims inconsistent with current API status. Fix duplicate React keys in safety-rule lists.

**Tests:** no pipeline nights versus pipeline fetch failure; usable-night default and earlier/later; click/keyboard step details; empty/intact/broken audit chain; each audit filter and filtered export; empty/nonempty session archive with dates; every How-it-works copy key; `NOT_RUN`/`ASSUMED` pipeline states; stable list keys.

**Done when:** The record contains every legacy tab capability, and no pipeline or audit empty/error state is ambiguous.

**Commit intent:** explain that inspectable processing and a verifiable record make the system's actions reviewable.

### Task 7: Restore Settings/profile/diagnostics with safe saves and deletion

**Files:** `frontend/src/views/SettingsView.tsx`, focused shared form/confirmation components under `frontend/src/components/`, `frontend/src/api.ts`, `src/wha/api/app.py` only if an existing endpoint is insufficient, focused frontend/API tests

- [ ] Restore the profile fields and explanations: age, sex, known vascular disease, menstruation, rate-lowering medicine disclosure, and notes for a clinician. Keep clinician notes out of AI prompts as the backend currently specifies.
- [ ] Restore bridge host/token, model provider/name/base URL/key, notification channel, Telegram token, and all three live diagnostic/test actions. Secret fields remain write-only and are never echoed after save.
- [ ] Restore all three budgets and their explanations. Preserve the legacy control ranges exactly: weekly interruption budget `0–20`, per-investigation question budget `0–10`, and policy-cost weight `0–1` with `0.01` step. Preserve the legacy profile age range `0–120`. Source displayed bounds from backend configuration/schema; do not narrow them in React.
- [ ] Save profile and settings with explicit pending/success/failure state. Preserve unsaved values after errors and ensure pointer, touch, keyboard, and assistive-technology input all commit changes. Do not depend only on `onMouseUp`.
- [ ] Run bridge/model/Telegram diagnostics against the unsaved values when the legacy action does so. Display both success and failure details from the API.
- [ ] Preserve deletion controls only for disposable `sim` and `demo` subjects. Never offer deletion for `me`. For an allowed deletion, name the target, require explicit confirmation, and report the result; do not quietly fall back to another subject.
- [ ] Keep all fields from the backend settings contract represented. If the contract gains fields, tests must fail until the UI has a control or a documented reason the field is not user-editable.

**Tests:** complete field inventory; exact legacy bounds; secret redaction; diagnostics using unsaved overrides; save success/failure and retained form state; keyboard/touch save behavior; `me` deletion unavailable; disposable-subject target confirmation.

**Done when:** every legacy setting remains available with its explanation, supported range, diagnostics, and safe save/delete behavior.

**Commit intent:** explain that complete settings and visible save outcomes keep user-controlled behavior understandable and safe.

### Task 8: Refine the Vite visual system, update docs, and verify the complete product

**Files:** `frontend/src/index.css`, shared frontend components and views, `README.md`, `docs/demo/README.md`, `docs/CONTRACTS.md` only if an API/schema change requires it, all new frontend tests

- [ ] Apply a cohesive Vite visual system with clear page hierarchy, readable type, consistent spacing, purposeful cards/charts, responsive navigation, and visible loading/empty/stale/pending/success/error states. Keep emergency guidance and the standing disclaimer immediately visible on Home.
- [ ] Verify each view on desktop and a narrow mobile viewport, including navigation, metric cards, charts, filters, pipeline controls, tables, disclosures, dialogs, forms, focus, and touch targets. Fix clipping, horizontal overflow, obscured controls, and keyboard traps. Do not make density improvements by removing content.
- [ ] Use text and icons as well as color. Confirm progressive disclosure preserves the full detail and has clear labels.
- [ ] Update `README.md` and `docs/demo/README.md` to describe API plus Vite startup, actual ports/commands, all five screens, and demo-data viewing. Remove stale Streamlit-dashboard instructions and claims. Update `docs/CONTRACTS.md` if changed model/API shapes require it.
- [ ] Run the frontend tests and production build. Run the full backend suite once with `uv run pytest -n auto`, then run `uv run ruff check src tests` and `uv run ruff format --check src tests` once. Address failures without modifying or weakening tests.
- [ ] Before driving the demo, write down expected visible outcomes from the demo fixture/film setup. Start the API and `uv run python tools/demo_film/serve_demo.py` as instructed, then use Playwright MCP as an ordinary person across all five screens. Inspect rendered text and exercise filters, pending flows available in demo data, error/empty states where injectable, and the five high-risk states. Inspect desktop and mobile; record concrete defects and fix them before completing.
- [ ] Confirm the browser console has no duplicate-key warnings, API errors are visible and distinct from empty results, there are no frontend health/data calculations, and every legacy inventory row has both a React destination and a passing verification case.

**Done when:** automated checks pass, all five views have been used against demo data, the narrow-screen interface is usable, docs match the product, and the parity map has no unchecked item.

**Commit intent:** explain that the completed migration preserves the full interaction contract while making it easier to read and use.

## Acceptance Checklist

- [ ] Every legacy screen, shared component, copy key, disclosure row, feature, and user action maps to a React destination and a verification case.
- [ ] Home/Today/History/The record/Settings all use the same explicit subject selection and render clear no-data, loading, and failure states.
- [ ] The cold/prior-dominated baseline cannot present an unconditional all-clear.
- [ ] Question, free text, decline, measurement, review, chat, and handover actions are complete and retryable.
- [ ] Citation warnings do not depend on citations being present; full source passages and quote-span status are inspectable.
- [ ] Conversation context is scoped on Today and date/session-separated in The record.
- [ ] History controls, all recorded fields, calendar gaps, per-night bands, and trace navigation work.
- [ ] Pipeline descriptions match actual API provenance/status; audit integrity, filters, records, and filtered export work.
- [ ] Settings fields and ranges match the legacy/backend contract, saves/tests provide feedback, and `me` cannot be deleted.
- [ ] CORS is allowlisted; expected absence differs from API failure; no browser-side health/data calculations remain.
- [ ] The Vite design is cohesive and responsive, with all preserved detail discoverable and no Streamlit default styling copied.
- [ ] README/demo instructions, frontend checks, backend checks, and the final real-interface pass agree with the implementation.
