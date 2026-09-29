# Vite dashboard demo film plan

## Goal

Produce and review a replacement cut of `docs/demo/wha-demo.mp4` that demonstrates the current Vite dashboard with the committed demo timeline while retaining the existing film's sourced cards, captions, disclosures, and honest data provenance.

Add a genuine live chat exchange to the cited-conversation chapter. The Vite panel must show actual user messages and completed API replies from the isolated demo clone. When an agent turn has neither citations nor an uncited-content note, the frontend must label the whole reply as unverified and keep that warning visible in the footage. The chat-status correction is frontend-only; the already accepted sleep-streak API addition remains the only backend change in this branch.

## Constraints

- Record the dashboard served from the active feature worktree and read-only demo subject `demo`; never access or modify subject `me`.
- Use the current saved timeline rather than rebuilding it. Live chat must use a disposable clone of the demo database.
- Keep chat isolated from subject `me`: use a disposable demo database, no scheduler, and `WHA_NOTIFY_CHANNEL=none`. Do not save Settings or send Telegram messages. The user separately requested a read-only Telegram bot connection check; it called `getMe` and sent no message.
- Use synthetic demo wording, not personal data. Enter the second user turn only after the first real reply appears. If the model is unavailable or returns a diagnostic claim or unsafe advice, stop and report the blocker. Do not substitute scripted bubbles or fabricated replies.
- Demonstrate other conversation and investigation capabilities from existing records only.
- Keep the existing film, Streamlit footage, cards, captions, and chapters intact while the Vite footage and review render are prepared.
- Preserve the existing Vite theme, layout, and navigation. Keep the current Dashboard notice scroll behavior, show missing citation status in the existing warning style, and label the Telegram `getMe` diagnostic as a connection check rather than a sent message.
- Do not add clinical wording, new figures, or conclusions. Reuse the existing film script and verify every captured claim against the screen and saved demo record.

## Approach

1. Inspect the available demo timeline and Vite views. Use the recorded exercise, alcohol, first raised night, investigation, cited conversations, audit trail, and recovery records already visible in the product. Keep the chest-pain rule explanation on its sourced card and in the Pipeline explanation without inventing a chest-pain interaction in this timeline.
2. Add a Vite-only fallback in `CitationPanel` for an agent reply with no citations and no uncited-content note. Use the existing warning style, and show it in live chat, archived replies, and review drafts. Record this limitation in `docs/DISCLOSURES.md`. Do not change the API or backend.
3. Add a repeatable Playwright recorder for the Vite application. Capture the real interface at a 16:9 full-HD viewport, using accessible controls and gradual scrolls. For live chat, show the conversation already created through actual UI/API turns on the isolated database clone.
4. Extend the cited-conversation chapter after its read-only archive shot by scrolling through the saved user and agent turns and their source-status labels. Keep every bubble verbatim; retain the outage chapter as a separate fallback demonstration.
5. Store new footage and an alternate render under separate review paths. Reuse the existing `script.yaml`, cards, captions, and chapter structure. Make the assembler accept explicit footage/output paths if needed so preview generation cannot overwrite the published video.
6. Review the footage and full review render visually. Verify the Dashboard notice scrolls away, Vite styling and color-coded Pipeline provenance remain visible, all chosen records match the captions, the live chat shows the actual alternating turns, and replies with no source metadata show the frontend warning. Stop if a reply contains a diagnostic claim or unsafe advice. Do not use the Today status panel to infer model reachability: it reports configured status without making a live connection check. Confirm the medical limitations/provenance ending remains intact.
7. Check the rendered file's resolution, frame rate, chapters, duration, decode, and file size. Replace `docs/demo/wha-demo.mp4` only after the Vite review render passes these checks, then update demo documentation with the reproducible Vite capture command.

## Completion evidence

- Vite live captures show the actual demo data and preserved visual theme.
- The cited-conversation chapter shows actual user/API/agent turns; empty citation and uncited metadata is visibly marked as unverified in Vite.
- The outage scene remains isolated and shows the model-unavailable fixed-rule response without contacting a phone.
- No chat capture accesses subject `me` or the committed demo timeline.
- The alternate full render has been opened and visually reviewed before it is copied to the published path.
- The final video and chapter/caption artifacts agree, and repository status contains no unrelated files.

## Source-status finding

The initial isolated chat turn returned empty citation and uncited metadata, and the Vite panel rendered no source-status warning. The frontend now labels that reply as unverified, without changing the API response or backend. The earlier capture without a warning was excluded from the film source.

## Verification results

- Captured current Vite scenes for the color-coded Pipeline, actual API chat, Settings connection check, and scrolling Dashboard notices. Reused the existing Vite footage for unchanged scenes. The reviewed render retains the original Vite sidebar and dashboard styling.
- The chat exchange used the actual `openai_compatible` provider and `deepseek-chat` configured in `.env` on an isolated `demo` database. The UI showed the missing-source warning and an unsupported-content warning. One reply repeated a question; another included unsupported text. This is visible as unverified content and is not evidence of a bug-free agent response.
- The Telegram `getMe` diagnostic succeeded, but it does not send a message. The bridge `/health` diagnostic returned a connection error from this environment. No Settings were saved and no Telegram message was sent.
- The published render is 1920 by 1080 H.264, 21:27 long, and decoded without errors. The caption and chapter sidecars were copied from the same render.
- `npm test -- --maxWorkers=2`: 77 passed. `npm run build` and `uv run ruff check src tests` passed.
- `uv run pytest -n auto`: 711 passed, 3 skipped, 2 failed. The parquet cache test lacks `pyarrow` or `fastparquet`; a separate retrieval-ranking test returned a probe passage in the top results for a fever query. Neither failing subsystem was changed for this Vite work.
