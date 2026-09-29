# Vite Pipeline, Settings, and Pending Chat Fix Plan

## Goal

Fix the reported Vite frontend behavior while preserving the existing Vite theme, navigation, API boundary, and dashboard layout. Make selected-night traces visibly belong to the selected night, report Settings changes accurately, and surface an agent interaction as soon as the API reports one. Keep backend code unchanged.

## Review basis

- Follow the already approved Vite parity spec and plan in `2026-09-28-vite-dashboard-parity-design.md` and `2026-09-28-vite-dashboard-parity.md`.
- The product documentation says an investigation opens only after two consecutive RED nights. It also says the agent then decides whether a question is worth asking, so two RED nights open an investigation but do not guarantee a question.
- The demo API returned different Pipeline statuses and measured values for a quiet night and an investigated night. Selecting dates did issue a new API request and update the displayed trace date.
- Vite keeps the old `pipeline` object rendered while a request for a new `nightDate` is in flight. Streamlit showed a step's local occurrence time, or said that no time was recorded; Vite currently omits that context.
- A live change to the disposable demo's weekly question limit round-tripped through `POST /settings` and `GET /settings`. The UI reported “No returned setting values changed” because it compared the submitted draft with the API response instead of comparing the response with the pre-save values.
- Pending interactions are fetched only with the initial dashboard load or an explicit refresh. The API data hook has no pending-status polling, and the chat panel opens only after the reader clicks its toggle.
- Chat sends through the conversation API. The backend retrieves passages and returns only grounded citations; the Vite chat renders returned source passages and shows an unverified warning when source metadata is absent. Keep retrieval and citation generation in the existing API.

## Constraints

- Frontend-only product changes. Do not edit Python, schemas, API routes, clinical constants, or the retrieval pipeline.
- Use the disposable `demo` record for live checks. Never write to or delete subject `me`.
- Preserve the dark sidebar, lavender canvas, existing Vite cards, status palette, navigation, and global chat affordance.
- Never infer Pipeline status, health state, or citations in the browser. Render values and source metadata returned by the API.
- Keep all existing Settings sections, chat actions, citations, and Pipeline tabs available.

## Tasks

### Pipeline date switching and event context

1. Ensure a trace is rendered only when `pipeline.night_date` matches the selected date. Clear the old detail selection while loading the new date and show the existing loading state until the matching response arrives.
2. Restore the per-step event context that Streamlit displayed. When the API provides `occurred_utc`, show its date and time in the subject's timezone. For a `ran` step without a timestamp, state that the time was not recorded. Do not synthesize an event time.
3. Label the overview's investigation context as live only when the API state is open; call a closed entry the most recent investigation.
4. Make clear that overview stage status is investigation-wide, and that a selected-night trace may include investigation events recorded on another date.
5. Add tests for changing dates with a deferred API response, for different returned status/data values, and for timestamp and missing-time rendering.

### Settings save feedback

1. Compare saved values with the pre-save API settings to list the fields that actually changed.
2. If the API returns a value different from the requested draft, make that adjustment visible instead of claiming a normal change.
3. If a write-only secret was submitted, confirm that it was saved without implying the secret can be read back.
4. Add a test where a user changes a setting and the API accepts it. Keep existing error-retention and secret-redaction coverage.

### Pending agent interaction visibility

1. Poll only the pending-interaction endpoint while the selected subject is active and the page is visible. Do not reload the rest of the dashboard on each poll.
2. When a new pending interaction is received, open the existing chat rail so its question, measurement, or review controls are visible. Track the pending interaction identity so a reader can close the rail without it reopening on an unrelated refresh.
3. Keep the chat toggle and manual open/close behavior. Render pending questions from the API response and keep the existing citation and unsupported-content UI for agent replies.
4. Add tests for an interaction arriving after page load, an interaction already pending at load, and closing the panel while the same interaction remains pending.

### Pipeline tab data audit

1. Manually inspect System overview, This night, Everything the system did, and How this works against the demo API responses.
2. Verify live episode details, safety provenance, nightly step values, audit events, conversation archive, permitted tools, runtime configuration, and settings are API-backed. Treat architecture descriptions as explanatory copy and the night trace as the selected-night API response.
3. Record any API limitation rather than fabricating a frontend value. Do not expand scope into backend changes.

### Settings boundary found during review

- The browser save path and `GET /settings` round-trip work for the disposable demo. The service currently updates process environment variables, so this is not evidence of persistence after an API restart.
- The notification destination cannot be validated as a frontend behavior: the notifier factory selects Telegram from credentials and does not inspect `notify_channel`. No Telegram message or phone delivery is sent during this review, and backend files remain out of scope.

## Verification

- Run the focused Vite tests, then the full frontend suite, TypeScript check, and production build once at the end.
- Run repository Python tests and Ruff once at the end as required by `AGENTS.md`; report pre-existing failures accurately.
- Use Playwright against the isolated demo API to switch between a quiet night and an investigated night, inspect the event context, visit every Pipeline tab, and verify Settings save plus restoration.
- Use a pending-interaction fixture to verify the chat auto-opens. Confirm existing demo conversation records contain citation metadata and that the Vite source panel renders it. Do not send a Telegram message.
- Confirm no backend source files changed and inspect the final diff.

## Completion criteria

- The selected Pipeline date and displayed trace cannot disagree, including while a new request is pending.
- Step statuses remain API-driven and steps with recorded times show them; missing times are explicit.
- A successful Settings save reports actual before/after changes.
- A newly returned pending agent interaction becomes visible in the chat rail without manual refresh, while manual close remains respected.
- Existing Vite visual identity and the API-backed content in all Pipeline tabs remain intact.
