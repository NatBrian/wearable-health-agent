# Original Vite Dashboard UX Refinement Plan

> **For agentic workers:** Implement task by task with `superpowers:executing-plans`; use test-first changes and verify the running dashboard with Playwright.

**Goal:** Recover the original Vite dashboard's compact visual hierarchy while keeping every added safety disclosure and Streamlit parity feature available.

**Architecture:** Keep the current React shell, routes, API boundary, and dashboard component composition. Refine only the Dashboard presentation: keep the complete emergency instruction and medical disclaimer visible on first render in compact, readable cards, tighten vertical spacing, restore the neutral status surface and metric-specific selection treatment, and show the sleep value with the precision returned by the API.

**Tech Stack:** React, TypeScript, Vite, Vitest, React Testing Library, CSS, Playwright MCP.

**Spec:** `docs/superpowers/specs/2026-09-28-vite-original-ui-enhancement-design.md`, plus the user's instruction to preserve the original PR Vite theme and hierarchy while retaining all Streamlit copy and features.

## Global Constraints

- Keep the original Vite Dashboard/Pipeline/Settings navigation, dark sidebar, lavender canvas, typography, metric cards, selectable chart, and global chat.
- Preserve all Streamlit features and explanatory copy, including the full emergency guidance and medical disclaimer.
- Keep dashboard values and statuses sourced from the HTTP API; the browser may format returned values but must not derive health state.
- Do not add clinical copy or change backend behavior, schemas, or medical constants.
- Keep the original-pr branch untouched; commit this refinement on `feat/vite-original-ui-enhancements`.

## Review Focus

- The complete medical disclaimer and emergency instruction must remain visible on Dashboard at first render. Neither may be collapsed behind a disclosure.
- The emergency guidance must remain visible and readable at narrow widths.
- Selected metric emphasis must track the selected series color, not use one fixed accent.
- Missing or fractional sleep values must remain legible and retain their available precision.
- Added safety content must not push the main trend chart below the desktop first viewport.

---

### Task 1: Restore Dashboard hierarchy without hiding safety content

**Files:**

- Modify `frontend/src/App.tsx`
- Modify `frontend/src/views/DashboardView.tsx` only if needed for tab placement
- Modify `frontend/src/index.css`
- Test: `frontend/src/__tests__/App.test.tsx`

**Interfaces:**

- Keep the existing `home.emergency` and `home.cannot` copy keys and text unchanged.
- Keep `DashboardView`'s existing section state and `DashboardVitals` data flow unchanged.

- [x] **Step 1: Add the regression test.** In `App.test.tsx`, add `keeps complete safety guidance visible in the Dashboard context`. Assert the named Dashboard safety region contains the emergency region and exact emergency copy, plus a labeled disclaimer region with the exact existing disclaimer copy visible immediately.
- [x] **Step 2: Verify RED.** From `frontend/`, run `npm test -- src/__tests__/App.test.tsx -t "keeps complete safety guidance visible in the Dashboard context"`. Expected: fail because the current safety blocks have no enclosing named region. Observed: the test failed at the missing `Dashboard safety guidance` region, as expected.
- [x] **Step 3: Implement the hierarchy fix.** In `App.tsx`, give the safety context a named region, keep all existing emergency/disclaimer copy visible on first render, place the emergency heading and instruction on one compact row when space allows, and lay the disclaimer title and full text in a compact information card. Remove the duplicate topbar brand kicker and compact Dashboard tabs. In `index.css`, tighten dashboard-only notice spacing and metric-card padding/sparkline height while preserving every note and data detail; restore the quiet-state banner's white surface and soft green marker.
- [x] **Step 4: Verify GREEN.** Re-ran the focused App test and `npm test -- src/__tests__/App.test.tsx`; the focused test and all 23 App tests passed with the full safety copy visible in the named region.

**Done when:** the complete emergency guidance and disclaimer are both visible at first render, and the top-level dashboard content uses materially less vertical space.

**Commit intent:** explain that safety copy remains available while Dashboard regains its original scan-friendly hierarchy.

### Task 2: Restore metric-card emphasis and numeric fidelity

**Files:**

- Modify `frontend/src/components/DashboardVitals.tsx`
- Modify `frontend/src/index.css`
- Modify `frontend/src/__tests__/App.test.tsx`

**Interfaces:**

- Keep the existing `VitalSeries.color`, `aria-pressed` selection, chart selection, and `measuredValue` behavior for other metrics.
- The card's `--vital-accent` custom property is the selected series' existing API-independent display color.

- [x] **Step 1: Add the regression test.** In `App.test.tsx`, add `keeps metric selection accents and sleep value precision`. Supply a latest measured sleep value of `10.25`, assert the Sleep card shows `10.25 h`, and assert the selected Resting HR card has its orange `--vital-accent` and `aria-pressed="true"`.
- [x] **Step 2: Verify RED.** Ran the focused test before implementation. It failed because the selected Resting HR card had no `--vital-accent`; the sleep precision assertion follows that check and was not reached in the RED run.
- [x] **Step 3: Implement the card fix.** In `DashboardVitals.tsx`, pass each series' existing color as `--vital-accent` on its card and format only sleep-card values to at most two fractional digits. In `index.css`, use the selected series accent for its border and subtle card tint.
- [x] **Step 4: Verify GREEN.** Re-ran the focused App test and `npm test -- src/__tests__/App.test.tsx`; the focused regression and all 24 App tests passed. Other metric formatting remains unchanged.

**Done when:** selection emphasis follows each metric's color and fractional sleep values retain the precision shown by the original dashboard.

**Commit intent:** explain that metric selection and displayed sleep precision match the original Vite behavior.

### Task 3: Preserve the original sleep-card streak treatment

**Discovery:** The original Vite baseline at `214c39b` displayed a level-colored sleep-card streak with lower-case level names and the labels `worsening`, `resolving`, and `holding steady`. The current component consumes the API's `detection_streak`, but the screenshot's running API on port `8500` returned the older status shape without that field. The current branch already computes and returns this value in `get_system_status`; do not reimplement that calculation in the frontend or change the backend for this presentation fix.

**Files:**

- Modify `frontend/src/components/DashboardVitals.tsx`
- Modify `frontend/src/index.css`
- Modify `frontend/src/__tests__/App.test.tsx`
- Modify `frontend/src/test/originalViteInventory.ts` to keep the preservation contract aligned with the verified `214c39b` source.

- [x] **Step 1: Add the regression test.** Provide an API status streak of three GREEN nights with a falling residual direction. Assert the Sleep card displays `3 green nights`, says `resolving`, and uses the green streak treatment.
- [x] **Step 2: Verify RED.** The focused regression failed as expected: the card showed `3 GREEN nights` and `Residuals falling`, instead of the original Vite wording.
- [x] **Step 3: Restore the presentation.** Map API direction names to the existing Vite wording, lowercase the level label, and use a status-specific badge class. Keep the API as the sole source of the streak and its direction. Corrected the preservation inventory after checking the original source at `214c39b`.
- [x] **Step 4: Verify GREEN.** The focused regression and all 25 App tests pass.

**Done when:** the API-provided streak is visible with the original Vite wording and severity color, while no streak calculation is added to the browser.

### Task 4: Verify the refinement in the running product

**Files:**

- No product files; use the demo dashboard at `http://127.0.0.1:8443/` and original comparison at `http://127.0.0.1:8444/`.

- [x] Run `npm test`, `npx tsc --noEmit`, and `npm run build` from `frontend/`: all 71 tests passed across 13 files, TypeScript passed, and the production build passed.
- [x] Run `uv run pytest -n auto`, `uv run ruff check src tests`, and `uv run ruff format --check src tests` once at the end. Final pytest: 710 passed, 3 skipped, 3 failed (missing optional parquet engine; retrieval model load hit Windows paging-file limit; retrieval tool returned no passages). Ruff check passed. Ruff format check reports six Python files would be reformatted; this frontend-only change does not touch them.
- [x] Capture same-size 1440×900 screenshots of both Dashboard Overview pages. Confirm the original sidebar, colors, typography, card grid, chart, and chat affordance remain recognizable; confirm the full emergency and disclaimer copy remains visible and the trend chart is visible above the fold.
- [x] At 390px, confirm the complete emergency guidance and disclaimer fit without horizontal overflow; at desktop, the metric cards should begin above y=330 and the trend panel above y=520. Measured document width was 390px; desktop cards began at y=301 and the trend panel at y=487.
- [x] Confirm each metric remains selectable, selected colors follow the series, all safety copy remains visible, and browser/API errors are absent. The regression test covers series selection; the browser showed no console errors and all observed API requests returned HTTP 200. The port `8500` status response was an older shape without `detection_streak`; the branch's current API source supplies it, so the live screenshot cannot show the streak until that service is restarted from this branch.
- [x] Commit and push the final verified plan and UI changes on `feat/vite-original-ui-enhancements` only.

**Done when:** focused tests, frontend checks, final repository checks, and Playwright comparison support the requested style and parity constraints, with repository failures reported accurately.

### Follow-up: restore Pipeline provenance status colors

**Discovery:** A same-size Playwright comparison showed the original Vite Pipeline used cyan for `CITED`, amber for `ASSUMED`, and purple for `DERIVED` safety-rule provenance. The current Pipeline table rendered the same statuses as plain text, removing that visual distinction.

**Files:**

- Modify `frontend/src/components/PipelineOverview.tsx` to render a small status badge in the existing provenance column.
- Modify `frontend/src/index.css` with the three original status colors and a neutral fallback for unrecognized API values.
- Modify `frontend/src/__tests__/PipelineView.test.tsx` to assert all three status classes.

- [x] Add and run the regression test first; confirmed all three statuses failed because the table rendered plain text without the expected color class.
- [x] Add the minimal badge markup and status color rules without changing layout, copy, or the shell theme.
- [x] Run focused Pipeline tests, the full frontend suite, type check, and production build. The focused Pipeline file passed 8 tests; the frontend suite passed 74 tests across 13 files; TypeScript and Vite production build passed.
- [x] Re-capture both Pipeline screenshots in Playwright at 1440×900 and confirm cyan `CITED`, amber `ASSUMED`, and purple `DERIVED` in the current table, matching the original status colors. Computed browser colors also matched the original Vite values.

**Repository checks:** `uv run ruff check src tests` passed. `uv run ruff format --check src tests` still reports six untouched Python files that would be reformatted. `uv run pytest -n auto` completed with 709 passed, 3 skipped, and 4 failures: the parquet test lacks `pyarrow`/`fastparquet`; two retrieval tests fail because the local passages are unavailable and the embedding-model load exceeds the Windows paging file; the conversation test's xdist worker crashed with a Windows access violation during the same model load. No Python files were changed for this UI fix.

**Done when:** the statuses remain readable text and regain the same meaning and colors as the original Vite Pipeline, with the expanded current Pipeline content unchanged.
