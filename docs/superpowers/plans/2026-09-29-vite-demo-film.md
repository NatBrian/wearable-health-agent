# Vite dashboard demo film plan

## Goal

Produce and review a replacement cut of `docs/demo/wha-demo.mp4` that demonstrates the current Vite dashboard with the committed demo timeline while retaining the existing film's sourced cards, captions, disclosures, and honest data provenance.

## Constraints

- Record the dashboard served from the active feature worktree and read-only demo subject `demo`; never access or modify subject `me`.
- Use the current saved timeline rather than rebuilding it or generating new model replies.
- Do not submit symptom reports, answer prompts, change Settings, or contact Telegram. The outage chapter may submit one existing demo prompt only to a separate database clone, with the model pointed at a closed localhost port, no scheduler, and notifications disabled. Remove that clone after capture.
- Demonstrate other conversation and investigation capabilities from existing records only.
- Keep the existing film, Streamlit footage, cards, captions, and chapters intact while the Vite footage and review render are prepared.
- Preserve the existing Vite theme, layout, and navigation. The only visual change in this cut is the already implemented Dashboard notice scroll behavior.
- Do not add clinical wording, new figures, or conclusions. Reuse the existing film script and verify every captured claim against the screen and saved demo record.

## Approach

1. Inspect the available demo timeline and Vite views. Use the recorded exercise, alcohol, first raised night, investigation, cited conversations, audit trail, and recovery records already visible in the product. Keep the chest-pain rule explanation on its sourced card and in the Pipeline explanation without inventing a chest-pain interaction in this timeline.
2. Add a repeatable Playwright recorder for the Vite application. Capture the real interface at a 16:9 full-HD viewport, using accessible controls and gradual scrolls. Record only read-only screen changes.
3. Store new footage and an alternate render under separate review paths. Reuse the existing `script.yaml`, cards, captions, and chapter structure. Make the assembler accept explicit footage/output paths if needed so preview generation cannot overwrite the published video.
4. Review the footage and full review render visually. Verify the Dashboard notice scrolls away, Vite styling and color-coded Pipeline provenance remain visible, all chosen records match the captions, and the isolated outage interaction shows the explicit model-unavailable and fixed-rule response in chat. Do not use the Today status panel to infer model reachability: it reports configured status without making a live connection check. Confirm the medical limitations/provenance ending remains intact.
5. Check the rendered file's resolution, frame rate, chapters, duration, decode, and file size. Replace `docs/demo/wha-demo.mp4` only after the Vite review render passes these checks, then update demo documentation with the reproducible Vite capture command.

## Completion evidence

- Vite live captures show the actual demo data and preserved visual theme.
- The only chat action is the existing outage prompt sent to the isolated clone; there is no external model call, phone action, or access to subject `me`.
- The alternate full render has been opened and visually reviewed before it is copied to the published path.
- The final video and chapter/caption artifacts agree, and repository status contains no unrelated files.
