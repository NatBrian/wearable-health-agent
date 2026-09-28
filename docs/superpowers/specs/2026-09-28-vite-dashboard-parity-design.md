# Vite Dashboard Parity and Safety Refinements Design

## Context

PR #3 replaces the Streamlit dashboard with a React, TypeScript, and Vite client of the existing FastAPI service. The migration improves the desktop presentation and adds sleep, steps, and oxygen summaries, but it removes several legacy screens and interactions. This design restores the user-visible feature set while addressing the safety, data-display, and maintenance issues found in the review.

The accepted implementation direction is to keep the Vite and API architecture, split the frontend along view boundaries, and avoid adding a router, global state library, or a second runtime dashboard. The current Vite visual system is the starting point for refinement. The Streamlit UI is the source of feature and content requirements, not a visual template.

## Goals

- Preserve every legacy screen-level capability, user action, explanation, and disclosure in an equivalent React view or component. Layout and interaction may be improved, but no feature is silently dropped.
- Treat behavior and information parity as mandatory, while deliberately improving the visual hierarchy, readability, navigation, responsiveness, and interaction feedback. Do not reproduce Streamlit's default layout, widgets, or table styling.
- Keep the dashboard as an HTTP API client. Health calculations, thresholds, policy decisions, and numeric configuration come from the backend.
- Fix the reviewed CORS, pending-workflow, conversation-context, citation-transparency, chart, responsive-layout, API-error, and stale-documentation issues.
- Give every restored or changed user-visible behavior an automated regression check and verify the real interface with demo data.

## Legacy feature inventory

The implementation will use this inventory as its parity checklist. Each row must map to a React view/component and a verification case before the migration is considered complete.

| Legacy area | Capabilities to preserve |
| --- | --- |
| Home | Resolve the configured subject consistently across all views; if multiple subjects need a choice, let the person choose rather than silently using the first API row. Preserve the no-subject state, status bar, emergency guidance, standing medical-device disclaimer, what the system can and cannot do, how a night is judged, links to the other views, and the live evidence-provenance summary. Preserve the summary's entry-count meaning and wording. Reuse archived wording and its documented source; do not author new clinical claims. |
| Today | Current status and overnight metrics, episode and urgency information, baseline-aware reassurance, symptom and structured-question flows, decline/free-text answers, measurement instructions, human review actions, current-night conversation, citations and unsupported-claim notices, per-cause evidence/provenance, contextual oxygen explanation, verdict and measurement explanations, and the doctor handover summary with prepare, preview, and copy actions. Show the date of the latest available sleep/steps observation so older samples do not look current. |
| History | Selectable historical windows; detection-level and investigated-only filters; the show-every-recorded-field toggle; chart, tabular records, conclusion explanation, empty-filter state that says no matching rows are not a health statement, and per-night detail; and the action that opens the selected night in The record. Numeric window values and labels must be supplied by the API/configuration rather than hard-coded UI copy. |
| The record | Per-night pipeline trace and explanations, hash-chain verification, audit-event filters and table, available filtered export, and a dated archive of conversations. |
| Settings | Subject profile, bridge/data-source configuration and diagnostics, notification and Telegram configuration/testing, weekly interruption budget, per-investigation question budget, policy-cost weight and their explanations, model/retrieval settings, save-all feedback, and privacy controls. Preserve the ranges accepted by the legacy UI/backend contract instead of narrowing them in frontend code. Preserve the existing data-deletion safeguards: real `me` data is never deleted; only disposable `sim` and `demo` data can be purged. |

The shared component inventory also needs an explicit React mapping: subject resolution/selection, status bar, verdict, night chart, chat, citation drawer, pipeline graph and step detail, "How it works" explanations, formatting, and visual design tokens. Components may be combined when behavior remains available and testable; their user-visible content and actions may not be omitted.

Before implementation, compare every row in `docs/DISCLOSURES.md` and every UI copy entry used by the archived `explain.py` and `how_it_works.py` against its archived screen and assign it a React destination. Preserve the full supported oxygen caveats, source/population context, evidence labels, and urgency limitations wherever they appeared. A disclosure documented in Markdown is not considered preserved until it appears in the relevant UI. Numeric clinical values must continue to originate in `data/knowledge/` and reach the UI through the API; system parameters must originate in backend constants/configuration.

## Architecture and navigation

Keep React, TypeScript, Vite, the typed API client, and FastAPI. The shell will expose five clear views: Home, Today, History, The record, and Settings. Home remains the safe landing view; Today remains the active dashboard. Navigation can continue to use the existing local view state, so no routing dependency is needed.

Split the current `App.tsx` into a small shell, view-level components, and shared UI components only where behavior is reused. Shared components should cover the disclosure/status presentation, metric/chart presentation, citations, conversation controls, and confirmation/error states. Keep feature behavior in its owning view rather than building a generalized dashboard framework.

## Visual and interaction direction

Build on the existing Vite dashboard's visual identity and refine it into a polished, readable health dashboard. Use clear page hierarchy, consistent spacing and typography, purposeful cards and charts, responsive navigation, and visible loading, unavailable, stale, pending, success, and error states. Do not aim for a pixel-for-pixel Streamlit recreation or carry over default Streamlit controls. The same information and actions must remain discoverable even when a denser legacy section is reorganized into a well-labeled tab, detail panel, or expandable section.

Keep emergency guidance and the standing disclaimer immediately visible on Home. Use text and icons as well as color to communicate status. All actions must work with keyboard and touch input, show focus clearly, and give feedback after success or failure. Preserve the full detail behind progressive disclosure; collapsing content is a layout choice, not a feature removal.

All data reads and writes go through `frontend/src/api.ts` and the FastAPI API. Add or extend only the endpoints needed to reproduce legacy behavior. Move trend, aggregation, threshold, and calendar-window calculations into the service/API. The browser formats returned values and submits user choices; it does not infer health states.

## Safety, data, and interaction behavior

- Show the standing disclaimer and emergency guidance on the Home landing view. Preserve the archived clinical wording and the existing evidence caveats. Do not invent thresholds, medical advice, or clinical copy.
- Resolve the active subject from the remembered or configured subject, falling back to the sole available subject. If configuration is ambiguous with multiple subjects, ask the person to choose. Never silently select the first API row.
- Keep the Today reassurance state conditional on backend baseline maturity. An immature baseline must explain that the system is still learning and must not imply that absence of a pending episode means health was assessed as clear.
- Render question, measurement, and human-review pending states. Questions and reviews expose the response actions supported by the current API; questions preserve optional free text and decline behavior. The legacy measurement state is informational and shows its instruction and explanation. The current policy has no measurement producer and the API has no completion endpoint, so do not invent a submit action or promise a result. Keep urgency decisions and red-flag logic on the backend.
- Scope the active conversation to the current night/episode and show older sessions in The record with date/session boundaries. Do not merge old answers into an unlabeled current chat.
- Render unsupported-claim warnings independently of whether citations exist. Show source attribution, the full inspectable passage, and the quoted evidence span; label missing spans and retain the limitation that verbatim span presence does not prove the surrounding claim is fair to the source.
- Preserve per-cause provenance and the live count/labels for unevidenced assumptions. Oxygen results must retain their archived population and source caveats, measurement limitations, and explicit no-all-clear meaning; do not reduce this to the threshold pathway alone.
- Keep Pipeline descriptions aligned with the current API and architecture. Do not describe a removed or `NOT_RUN` subsystem as active or present assumed values as literature-backed.
- Preserve missing nights and calendar gaps in charts. Use the band appropriate to each point or explicitly label a current band as current-only. Steps averages must represent the configured calendar interval, not merely the last few non-null samples.
- Use explicit approved frontend origins for CORS and retain the API's local-only binding. Do not treat CORS as user authentication or add a broad authentication subsystem as part of this dashboard parity change.
- Distinguish expected missing resources from failed API requests. Do not convert every HTTP 404 into a successful empty result.
- On chat or settings save failures, retain the user's input and show a clear retryable error. Do not silently discard edits or imply that a save succeeded.
- Ensure settings save and connection-test actions work with pointer, touch, and keyboard input. Slider bounds come from the backend contract and preserve the legacy-supported range.
- Keep the layout usable on narrow screens. Fix duplicate React keys in safety-rule lists.

## Settings and privacy boundary

Restore legacy controls by calling the existing API endpoints where available. Any missing persistence or diagnostics capability belongs behind a narrowly scoped API endpoint. The frontend must not expose destructive actions for `me`, and every destructive action for disposable subjects must state which subject will be affected and require confirmation.

## Documentation and verification

Update setup and demo instructions to describe the API and Vite frontend processes, correct ports and commands, current routes, and the restored screens. Remove obsolete claims that Streamlit still serves the dashboard.

Use the archived Streamlit UI and UI-unit tests as the behavioral source, translating their assertions rather than their Streamlit-specific mechanics. Port behavior-focused coverage into a lightweight frontend test harness. At minimum, cover: configured/ambiguous subject selection; every disclosure row and Home provenance summary; immature-baseline reassurance; question/free-text/decline and review flows; the informational measurement prompt; citation and uncited warnings; conversation session boundaries; History's window, level, investigated-only, and all-fields controls plus date gaps and trace navigation; Record integrity, audit filters/export, and conversation archive; all Settings fields, legacy bounds, save/test feedback, and deletion safeguards; latest metric observation dates; API failures; stable safety-rule rendering without duplicate-key warnings; no literal digits in UI copy; no health/data calculations in frontend components; and narrow-screen layout. Keep backend tests for service/API contracts. Finally, run the actual Vite UI against demo data at desktop and mobile sizes and inspect the rendered text and interactions.

## Constraints and non-goals

- Do not keep Streamlit as a second supported runtime; the archived code is a parity reference.
- Do not change clinical rules, thresholds, cause weights, or evidence claims as part of this UI migration.
- Do not add multi-user support, a new global state library, or a general-purpose routing framework.
- Do not hard-code numeric UI copy or health calculations. Source numeric values from the API/configuration.
- Preserve archived wording and meaning, but interpolate numeric values from API/configuration instead of copying digits into frontend strings.
- Do not add unrelated backend refactors. Keep backend changes limited to API behavior required for parity and correct client data presentation.

## Acceptance criteria

1. Every legacy feature-inventory row maps to a React view/component and a verification case; no capability is silently removed.
2. All five user-facing areas render and their required actions complete through the API.
3. A cold or prior-dominated baseline cannot render an unconditional all-clear message.
4. Question, review, decline, and free-text paths supported by the API are actionable and preserve their backend state transitions. The legacy measurement prompt remains informational because the current backend has no request producer or completion endpoint.
5. Current chat is session-scoped; the record archive makes older conversations and dates distinct.
6. Unsupported claims remain visibly labeled even with no citations; source passages and attribution are inspectable.
7. Charts retain calendar gaps and represent baseline bands and averages accurately.
8. CORS rejects unapproved origins; expected absence and API failure have distinct UI states.
9. Home, Today, History, The record, and Settings remain usable on narrow screens, with no clipped navigation, cards, chart controls, tables, dialogs, or actions.
10. Every archived disclosure and shared UI component has a verified React destination; no visible row is treated as present merely because it remains in documentation.
11. A visual review confirms a cohesive Vite design with clearer hierarchy and responsive interaction, rather than a Streamlit-style restyling; all preserved details remain discoverable.
12. README instructions, automated frontend checks, backend checks, and a demo-data visual pass agree with the migrated UI.
