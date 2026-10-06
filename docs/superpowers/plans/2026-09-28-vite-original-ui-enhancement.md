# Original Vite Dashboard Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the original Vite dashboard's complete visual and interaction contract while integrating all approved Streamlit parity content and actions.

**Architecture:** Keep the original Dashboard/Pipeline/Settings shell, original metric overview, existing settings sections, and global chat rail. Recompose the current parity components beneath those destinations, with secondary Dashboard and Pipeline sections; continue to use the existing typed API and backend services.

**Tech Stack:** React, TypeScript, Vite, Vitest, FastAPI, Playwright MCP.

**Spec:** `docs/superpowers/specs/2026-09-28-vite-original-ui-enhancement-design.md`

## Global Constraints

- Keep the original Vite primary navigation: Dashboard, Pipeline, Settings.
- Keep the original brand, palette, typography roles, Dashboard widgets, selected-series chart, Pipeline overview, Settings sections, and global chat rail.
- Preserve every Streamlit copy item, disclosure, feature, and supported action in the current parity inventory.
- All health decisions, thresholds, aggregation, and numeric system settings come from the API. The browser formats and selects returned values.
- Preserve the informational-only measurement prompt because no active producer or completion endpoint exists.
- Do not invent clinical text, remove or weaken tests, add new routing/state libraries, or change medical constants.
- Keep the deterministic safety floor, explicit CORS origins, retryable save/chat errors, and real/demo data boundary intact.
- Use focused Vitest files for each red/green cycle. Run the complete frontend and Python suites, and Ruff, once at the end; use Playwright with demo data after those checks.

## Review Focus

- Original metric cards or selectable trend series disappear, or missing/stale values look current. Pin with Dashboard overview tests using recorded and unavailable series.
- A link from Dashboard lands in the wrong primary destination or loses the selected night. Pin with Dashboard-to-Pipeline and History-to-Pipeline tests.
- Moving pending interactions into the global chat leaves duplicate or unreachable answer controls. Pin with shell navigation tests that answer the pending interaction from each primary destination.
- The restored chat rail clips or obscures controls at narrow widths. Pin with responsive Playwright review and chat interaction tests.
- Returning Settings sections hides a legacy field, widens a range, or loses unsaved input after failure. Pin with exact field/bounds and save-failure tests.

---

### Task 1: Protect the original Vite interaction contract

**Files:**

- Create `frontend/src/test/originalViteInventory.ts`
- Extend the original shell cases in `frontend/src/__tests__/App.test.tsx`
- Read-only reference: original UI in commit `214c39b`, `frontend/src/App.tsx` and `frontend/src/index.css`

**Interfaces:**

- Inventory entries identify the original destination, control/content, and the current component expected to render it.
- Keep `frontend/src/test/legacyParityInventory.ts` as the separate Streamlit-source inventory.

- [x] Record the original brand/tagline, subject/baseline and open-session/last-closed summaries, page titles, three primary destinations, Dashboard episode/quiet-state banner, all four metric cards, per-card sparklines, selected-series chart, sleep streak, latest-night/baseline/deviation details, full cause differential and change, oxygen spot checks, Pipeline groupings/trace/provenance, four Settings sections, and global chat open/close/unread/pending/citation actions.
- [x] Add accessible-DOM regression cases for each inventory group. Assert roles, labels, and actions; do not snapshot the whole page or couple tests to incidental markup.
- [x] Retain and extend the existing Streamlit inventory tests so every legacy entry still maps to a visible view and supported action.
- [x] Define failure messages that identify the lost original Vite or Streamlit element.
- [x] First run the new focused tests against the current UI and confirm they fail because original Vite elements are missing. Keep the full test suite for Task 6.

**Done when:** the new inventory distinguishes original Vite parity from Streamlit parity, and tests fail when either contract loses an element.

**Commit intent:** explain that the two source dashboards have separate preservation checks.

### Task 2: Restore the original shell and global chat rail

**Files:**

- Modify `frontend/src/App.tsx`
- Modify `frontend/src/views/HomeView.tsx` and `frontend/src/views/TodayView.tsx` navigation callback types
- Modify `frontend/src/components/ChatPanel.tsx`, `frontend/src/components/PendingInteraction.tsx`, and `frontend/src/components/StatusBar.tsx`
- Modify `frontend/src/__tests__/App.test.tsx` and `frontend/src/__tests__/ChatPanel.test.tsx`
- Modify shell/sidebar/chat rules in `frontend/src/index.css`

**Interfaces:**

- Define `type PrimaryView = 'dashboard' | 'pipeline' | 'settings'` in the shell.
- Define `type DashboardSection = 'overview' | 'today' | 'history'` for secondary Dashboard selection.
- The shell owns `chatOpen`, `hasUnread`, `selectedNight`, and the active primary destination.
- Keep one global `ChatPanel` receiving the current subject, applicable night/episode, pending interaction, configuration, settings, safety provenance, and a refresh callback.

- [x] Replace the five-item sidebar and mobile navigation with the original three primary destinations and original labels. Restore the Vital Agent brand, health triage tagline, subject/baseline summary, and open-session/last-closed summary.
- [x] Restore the original page titles and active-navigation treatment. Keep current subject selection and retry behavior.
- [x] Mount the chat rail at shell level so it remains reachable from Dashboard, Pipeline, and Settings. Restore open/close and unread affordances without rendering duplicate chat panels.
- [x] Render pending question/decline/free-text/review controls in the global chat rail. Keep a concise pending status on the Dashboard and point its action to opening the rail. Preserve the informational measurement state and do not add a submit action.
- [x] Keep active chat scoped to the relevant current night/episode; keep archived sessions separate in Pipeline.
- [x] Preserve input on send failure, show retryable errors, and refresh dashboard state after a successful answer or message.
- [x] Add tests for all three primary destinations, persistent chat access, pending-answer reachability from each destination, unread/open/close behavior, and retained failed-send input; run the focused tests red before the shell changes and green after them.

**Done when:** navigation and chat behave like the original Vite app while current subject selection and supported parity actions remain available.

**Commit intent:** explain that keeping conversation access global preserves the original interaction model.

### Task 3: Rebuild the original Dashboard overview and add parity sections

**Files:**

- Create `frontend/src/views/DashboardView.tsx`
- Create `frontend/src/components/DashboardVitals.tsx`
- Modify `frontend/src/App.tsx`
- Modify `frontend/src/views/HomeView.tsx`, `frontend/src/views/TodayView.tsx`, and `frontend/src/views/HistoryView.tsx`
- Modify `frontend/src/useBackend.ts` only to request the API-configured trend window when needed
- If required to keep the original same-level streak without browser-side calculation: modify `src/wha/models.py`, `src/wha/service/status.py`, `frontend/src/api.ts`, `docs/CONTRACTS.md`, and the directly related status tests
- Extend original Vite Dashboard contract cases in `frontend/src/__tests__/App.test.tsx` because it already owns the shared API fixture
- Modify `frontend/src/__tests__/HistoryView.test.tsx` and `frontend/src/__tests__/TodayInteractions.test.tsx`

**Interfaces:**

- `DashboardView({ subject, config, data, section, onSectionChange, onOpenPipeline })` receives the selected subject, API configuration, shared backend state, a `DashboardSection`, and callbacks. It does not fetch or calculate clinical state itself.
- `DashboardVitals({ data })` renders the original metric cards, selected-series chart, latest-night/baseline details, and cause differential from `BackendData` API values.
- `HistoryView` receives `onOpenPipeline(nightDate)` so a selected historical trace retains its date.
- The sleep-card streak and its direction indicator use a typed backend status value; React does not derive a streak or its direction from night rows.

- [x] Make the original Dashboard overview the default visible section. Restore the original overview and order: episode context, the original Resting HR/Sleep/Steps (configured day average)/SpO₂ cards, selected-series trend, latest-night and baseline details, and the full cause differential. Keep the detailed service-health panel in the Dashboard's Today section so it does not push the original overview below the fold.
- [x] Use returned API values for all series. The chart keeps calendar gaps and per-night ranges; unavailable or stale readings remain labeled. Keep click, keyboard, and screen-reader selection equivalent.
- [x] Preserve baseline maturity, detection level, episode state, chart explanation, date context, sleep-card same-level streak, and oxygen spot-check details and source/measurement caveats. Do not turn missing readings into zero or a normal result.
- [x] Keep the legacy streak direction as a backend-provided display description of rising, steady, or falling residuals; do not describe it as a clinical course or calculate it in React.
- [x] Add clearly labeled secondary Dashboard sections for **Today** and **History** without adding top-level navigation destinations. The Today section contains the urgent state, verdict/explanations, oxygen context, handover actions, and status for pending work. The History section retains API-backed windows/filters, every legacy table field, empty-filter explanation, and selected-night action.
- [x] Place emergency guidance and standing disclaimer prominently on Dashboard while retaining all original overview widgets. Keep the legacy Home explanations, evidence count, and how-a-night-is-judged details within the Dashboard.
- [x] Place detailed service-health status in Dashboard's Today section. Keep the original compact open-session/last-closed summary in the sidebar instead of adding a status strip above the original Vite overview or every primary destination.
- [x] Map Home destination cards to Dashboard sections or the appropriate existing primary destination. Do not leave buttons pointing to removed `home`, `today`, `history`, or `record` primary routes.
- [x] Use API-configured history windows and step-average interval. Keep aggregation, baseline math, cause updates, and policy decisions out of React.
- [x] Add tests for original overview ordering/content, card sparklines and sleep streak, selectable metric series, cause differential, oxygen spot checks, stale/missing states, safety copy, secondary section navigation, History filtering, and date-retaining pipeline navigation. Run focused tests red before the view changes and green after them.
- [x] Reuse the existing `DashboardSummary` API values for configured steps-average interval and latest observations. Add the smallest typed `SystemStatus` streak value only if needed to move the existing displayed streak out of React; update its service/model/API contract tests and `docs/CONTRACTS.md`. Do not calculate either value in React.

**Done when:** opening Dashboard shows the familiar Vite overview, and its secondary sections expose the full Streamlit Home/Today/History contract.

**Commit intent:** explain that the original overview remains the default while legacy detail is added inside Dashboard.

### Task 4: Preserve Pipeline and house the record features there

**Files:**

- Modify `frontend/src/views/RecordView.tsx` while retaining its focused child components
- Create `frontend/src/components/PipelineOverview.tsx`
- Modify `frontend/src/components/HowItWorks.tsx`, `frontend/src/components/PipelineTrace.tsx`, and `frontend/src/components/PipelineStepDetail.tsx` as required by the original composition
- Create `frontend/src/__tests__/PipelineView.test.tsx`
- Modify `frontend/src/__tests__/PipelineTrace.test.tsx` and `frontend/src/__tests__/HowItWorks.test.tsx`

**Interfaces:**

- The primary shell renders the Pipeline destination with `subject`, `config`, shared `data`, and `selectedNight`.
- Pipeline secondary sections are **System overview**, **This night, step by step**, **Everything the system did**, and **How it works**. The trace section owns date selection; changing primary destinations does not erase `selectedNight`.

- [x] Restore the original Pipeline overview grouping and active-episode context. Render safety-rule provenance and live status from API data; remove or correct original static subsystem claims contradicted by current code.
- [x] Keep selected-night trace, earlier/later controls, step selection, input/output/source details, and all per-step explanations from the Streamlit parity implementation.
- [x] Keep audit-chain empty/intact/broken states distinct; preserve all event columns, actor/operation/permission filters, filtered export, and retryable API errors.
- [x] Keep archived conversations date/session-separated with source and uncited labels. Never merge archive turns into current chat.
- [x] Keep every How it works topic, live configuration, permitted tool list, safety-rule provenance, and evidence labels.
- [x] Keep the History-to-Pipeline action and selected date working after introducing internal Pipeline sections.
- [x] Add tests for original Pipeline grouping, active-episode summary, trace/date selection, audit integrity/filter/export, conversation archive, and topic-to-step coverage. Run focused tests red before the Pipeline composition changes and green after them.

**Done when:** Pipeline still looks and works like the original destination while including the full legacy record, audit, archive, and explanation features.

**Commit intent:** explain that reviewable system processing and records remain together under the familiar Pipeline destination.

### Task 5: Restore Settings sections without losing parity controls

**Files:**

- Modify `frontend/src/views/SettingsView.tsx`
- Modify `frontend/src/__tests__/SettingsView.test.tsx`

**Interfaces:**

- Restore the original Settings section IDs: `device`, `agent`, `model`, and `privacy`.
- Keep existing API methods and typed `Settings`/`SubjectProfile` models.

- [x] Restore the original Device & Data, Agent Behavior, Model & RAG, and Privacy section navigation and labels.
- [x] Place every current legacy profile, bridge, model/retrieval, notification/Telegram, budget, diagnostic, and deletion control in its existing corresponding section, with its preserved explanation.
- [x] Preserve API-defined bounds, write-only secrets, unsaved diagnostic overrides, the single settings save action, profile save behavior, and visible success/failure states without clearing failed inputs.
- [x] Preserve the `me` deletion prohibition and explicit target confirmation for disposable `sim`/`demo` data.
- [x] Add tests asserting every original section/control is reachable, exact backend bounds remain in force, save errors retain values, and destructive controls respect the subject boundary. Run focused tests red before section navigation changes and green after them.

**Done when:** Settings retains its original section organization and every Streamlit setting/diagnostic/privacy capability remains usable.

**Commit intent:** explain that the original settings organization remains familiar while parity controls are restored.

### Task 6: Restore the Vite visual system, update docs, and verify the product

**Files:**

- Modify `frontend/src/index.css`
- Modify `README.md`, `docs/demo/README.md`, and `docs/ARCHITECTURE.md` only where they still describe the five-view shell
- Modify existing frontend tests only to add coverage; do not remove or weaken assertions

- [x] Restore original Vite design tokens and roles: navy sidebar, gray-lavender canvas, lime/purple/urgency accents, Fraunces/DM Sans/JetBrains Mono, metric-card selection, chart presentation, and right chat rail. Improve spacing, readable detail, focus, touch targets, and responsive layout within this system.
- [x] Preserve all content at desktop and narrow widths. Keep the original three destinations and chat reachable; make tables scroll within their own regions; ensure no clipped settings or chat controls.
- [x] Update README/demo/architecture instructions to show Dashboard/Pipeline/Settings, their secondary sections, the local API/Vite commands, actual ports, and the demo data flow. Do not change backend contracts unless implementation proves an existing endpoint insufficient.
- [x] Record the expected demo observations from the committed film/fixture before starting the UI. Use the demo copy with subject `demo` and the shifted demo clock; do not browse or mutate subject `me`.
- [x] Run once at the end: `npm test`, `npx tsc --noEmit`, `npm run build`, `uv run pytest -n auto`, `uv run ruff check src tests`, and `uv run ruff format --check src tests`. Do not change tests to satisfy failures. Report any previously observed retrieval-ranking failure if it persists.
- [x] Use Playwright MCP at desktop and narrow widths to open Dashboard, select every metric, switch Dashboard sections, navigate to a selected Pipeline night, inspect audit/archive/How it works, open and close global chat from all three destinations, and inspect each Settings section. Compare desktop rendering with the original Vite at commit `214c39b`.
- [x] Confirm console/API behavior, responsive reachability, no duplicate keys, no browser-side health/data calculations, and complete original-Vite plus Streamlit inventory coverage. Fix observed defects before finalizing.

**Done when:** the original Vite UI contract and all Streamlit parity rows pass their checks, the dashboard has been used with demo data, and docs/tests match the shipped three-destination product.

**Commit intent:** explain that parity is complete inside the original product experience and is verified in the running interface.

## Acceptance Checklist

- [x] Original Vite Dashboard/Pipeline/Settings identity, layout, content, controls, and global chat are preserved.
- [x] Original Dashboard metric cards remain selectable and drive a chart with accurate gaps/ranges; baseline details and cause differential remain visible.
- [x] All Streamlit Home/Today/History content and actions are available within Dashboard sections.
- [x] All Streamlit pipeline, audit, archive, and How it works content is available within Pipeline sections.
- [x] All Streamlit Settings/profile/diagnostics/privacy content is available within the original Settings sections.
- [x] Chat and pending actions remain globally accessible, scoped, source-aware, and retryable.
- [x] Safety, disclaimer, provenance, oxygen, unsupported-claim, no-data, stale-data, and API-error distinctions remain explicit.
- [x] Frontend and backend data boundaries remain intact; no unsupported measurement submit action exists.
- [x] Original Vite and Streamlit inventories, final checks, and Playwright demo review all pass or have precisely documented existing unrelated failures.

## Final Verification Record

- `npm test`: 13 files and 68 tests passed.
- `npx tsc --noEmit`: passed after completing the `PipelineStage` test fixture.
- `npm run build`: passed.
- `uv run pytest -n auto`: 710 passed, 3 failed. The existing cohort-cache test could not find `pyarrow` or `fastparquet`; the existing retrieval-ranking assertion failed in untouched retrieval code; and the retrieval-model worker hit a Windows access violation while loading the sentence-transformer.
- `uv run ruff check src tests`: passed. The full `ruff format --check src tests` run reported 10 files needing formatting, including untouched files. The four changed Python files were formatted and their targeted format check passed.
- Playwright MCP: reviewed the original Vite tab on port `8444` beside the refined dashboard on port `8443`, using subject `demo`. Checked the four metric selectors, Dashboard sections, a historical-night to Pipeline trace transition, integrity status, archived conversations, audit filters/export affordance, How it works topics, all Settings sections, and chat open/close from each primary destination. At `390px`, the dashboard, Pipeline and Settings had no page-level horizontal overflow, and Settings save controls remained reachable. The current dashboard had zero console errors; observed API requests returned `200`.
