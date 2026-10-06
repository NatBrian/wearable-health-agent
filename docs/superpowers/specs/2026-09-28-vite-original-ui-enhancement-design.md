# Preserve and Enhance the Original Vite Dashboard

## Status

This design replaces the five-view navigation and new green/teal visual shell in the earlier parity design. It keeps the accepted Streamlit parity, safety, data, and backend requirements while using the original Vite dashboard at commit `214c39b` as the visual and interaction baseline.

## Goal

Carry every Streamlit screen, explanation, disclosure, and action into the Vite dashboard while preserving the existing Vite product's identity, top-level navigation, dashboard content, pipeline access, settings sections, and global chat interaction. Improve readability, responsive behavior, and feedback inside that product rather than replacing its layout and interaction model.

## Protected original Vite experience

The following existing behaviors and elements remain available and recognizable:

- The three primary destinations: **Dashboard**, **Pipeline**, and **Settings**.
- The **Vital Agent** brand and **health triage** tagline, subject identity/usable-night/baseline summary, and sidebar open-session/last-closed summary.
- The original page titles and context: **Health Overview**, **System Pipeline**, and **Settings**, with the Dashboard's last-scored/open-investigation context.
- The Dashboard's original overview composition: status/episode summary; resting-heart-rate, sleep, steps, and oxygen cards when data is available; the multi-night heart-rate chart; the latest-night and baseline details; and the cause differential.
- Clickable metric cards that select the corresponding trend series, the empty/unavailable metric treatment, and the selected-series chart detail.
- The Pipeline destination's grouped system overview, safety-rule provenance, active-episode summary, and selected-night trace. Preserve the overview's visual organization while correcting static claims that do not match the running system.
- The Settings destination's existing Device, Agent, Model & RAG, and Privacy sections and their controls.
- The global Agent Chat rail and its open/close control, unread indicator, pending-question controls, transcript, text entry, and citation inspection. Chat remains reachable from every primary destination.
- The original Vite visual language: near-black navy sidebar, pale gray-lavender canvas, white cards, lime/purple and existing urgency accents, Fraunces/DM Sans/JetBrains Mono typography, and the existing chart/card treatment.

The existing Dashboard cards, chart, baseline details, cause differential, Pipeline overview and trace, Settings controls, subject/session summaries, and global chat may be refined for legibility, keyboard/touch use, and narrow screens. They must not be silently removed, replaced with unrelated components, or moved behind a new primary destination. New sections may follow them or use clearly labeled secondary tabs/disclosures within the same destination.

## Streamlit parity inside the existing Vite structure

### Dashboard

Keep the current Vite Dashboard as the landing page and retain its overview composition. Add the legacy Home and Today material to this destination: the emergency instruction and standing disclaimer, what the system can and cannot do, how a night is judged, evidence/provenance explanations, current-night status and safety state, baseline-aware explanations, oxygen caveats, measurement instruction, question/review response controls, citations and unsupported-claim warnings, and clinician handover prepare/preview/copy actions. Add the legacy History controls and records as a labeled lower Dashboard section or secondary panel. Preserve the chart, date gaps, data cards, latest-night details, and cause differential already present in Vite.

The safety instruction is prominent on the Dashboard without replacing the original overview. History windows, filters, full-field table, no-match explanation, and selected-night trace action remain discoverable inside Dashboard. Do not add Home, Today, or History as replacement top-level destinations.

### Pipeline

Keep Pipeline as the destination for the existing grouped system overview, active-episode context, selected-night step trace, and safety-rule provenance. Add the legacy record features as clearly labeled secondary sections within Pipeline: night selection and previous/next navigation, detailed step explanations, audit-chain status and event table, actor/operation/permission filters, filtered export, archived conversations with date/session boundaries, and every How it works topic. Keep trace selection and audit detail inspectable without converting the page into a new top-level Record destination.

### Settings

Keep Settings as the existing destination and retain its current section organization. Fill out the legacy profile, bridge, model/retrieval, notification/Telegram, budget, diagnostic, and privacy controls with their explanations and safe save feedback. Keep backend-supported ranges, write-only secrets, and the disposable-subject deletion safeguards.

### Global chat

Keep the original chat rail available across Dashboard, Pipeline, and Settings. Add the legacy conversation scope, safety explanation, pending interaction states, source attribution, citation details, and unsupported-claim notices to that rail. Keep prior sessions in the Pipeline archive with explicit session/date boundaries. Do not make the chat available only on Dashboard or move it into an inline Today card.

## Visual and responsive direction

Use the original Vite visual system as the design system. Refine its hierarchy, spacing, type scale, card density, chart labels, status readability, focus states, and touch targets while retaining the existing dark sidebar, accent palette, typography roles, and dashboard composition. Preserve familiar control placement where possible. Use progressive disclosure only for additional legacy detail; keep the original chart, cards, pipeline access, settings sections, and chat one-step reachable.

At narrow widths, adapt the existing shell and chat rail to the viewport while keeping all three destinations, the chat control, emergency copy, chart data, table fields, and settings controls reachable. Do not hide or discard features to avoid overflow. Status meaning uses text/icons as well as color.

## Architecture and data boundary

Keep React, TypeScript, Vite, the typed API client, and FastAPI. The app shell exposes only the original three primary destinations. Existing component extraction may remain; the composition must preserve the original user-facing destinations and interaction contract. Do not add a router or global state library for this work.

All reads, writes, calculations, thresholds, and health-policy decisions remain behind the HTTP API. Reuse the current parity components and API work where it serves the spec. Do not duplicate data logic in the browser or create a second dashboard runtime.

## Safety and state behavior

- Preserve every mapped Streamlit explanation, disclosure, label, and supported action from the parity inventory. Documentation alone does not count as visible UI parity.
- Preserve the existing non-diagnosis, emergency, source-population, uncertainty, oxygen, and evidence limitations verbatim or through the approved archived wording. Do not add clinical claims or figures.
- Keep subject resolution, backend urgency, the deterministic safety floor, evidence provenance, and API-sourced values as already specified in the parity design.
- Keep question, review, chat, handover, filter, audit, and settings actions retryable and honest about success/failure. The measurement instruction remains informational because there is no active producer or completion endpoint.
- Distinguish empty records from failed requests, stale observations from current ones, and missing nights from normal readings.

## Verification and acceptance

- Compare the new Dashboard, Pipeline, and Settings against the original Vite screenshot and source at `214c39b`. The original brand, sidebar summaries, palette, typography roles, three-destination shell, Dashboard widgets and metric selection, Pipeline overview, settings organization, and global chat access remain recognizable and functional.
- Keep a baseline inventory for original Vite controls/actions as well as the existing Streamlit parity inventory. Tests fail if an original Vite destination, chart/card, settings section, or global chat affordance disappears.
- Preserve all existing Streamlit parity assertions and verify every inventory row has a visible destination and working supported action.
- Verify the responsive layout and the original chat rail on desktop and narrow viewports with Playwright MCP and demo data.
- Keep backend/API, citation, chart, history, audit, safety, and settings assertions from the accepted parity plan. Do not weaken or remove tests.

## Out of scope

- Replacing the original Vite visual identity or three-destination navigation.
- Removing original Vite dashboard widgets or changing global chat into a page-specific chat panel.
- Recreating Streamlit's default look and controls.
- Adding unsupported measurement submission/results or new clinical behavior.
- Adding new libraries, routing, or state-management frameworks without a demonstrated need.
