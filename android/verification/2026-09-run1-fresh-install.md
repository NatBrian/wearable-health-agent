# Verification run 1: fresh install against the real webhook

Date: 2026-09-12 (in progress)
APK: android-task25-rc1
Phone: owner's Samsung

Expected was written before touching the phone. Observed is filled during the
run. Per the standing rule, every finding is recorded here, fixed afterwards,
then the run restarts from a fresh install.

| Step | Expected | Observed |
|---|---|---|
| Uninstall any previous build, install the release-candidate APK | Onboarding page one shows | |
| Pages one and two | Wording matches `wording.py`; Next disabled until the disclaimer is ticked | |
| Test connection with the real port | Reports the record types the core sees; a wrong port reports unavailable in words | BLOCKED: tapping Test connection closes the app instantly, before any result shows. Same for Test model below. No result text was shown, so there is nothing to compare against the expectation yet. |
| Test provider with the rotated key | Reports success | BLOCKED: same instant close as above on tapping Test model. |
| Finish | Notification permission asked; corpus fetch starts; Today shows the provider notice absent and the corpus notice present | |
| Within one minute | Today shows the last pull time and last night with its level | |
| History | Thirty days of nights; unmeasured nights open circles; the band present once the rung allows | |
| Record | Newest night's twenty-one steps; investigation group dimmed with reasons | |
| Settings | Every constant matches the dashboard on the PC for the same constant | |
| Corpus finished | Retrieval ready; a chat turn about fever quotes MedlinePlus with the Library named | |

## Findings

1. 2026-09-12: onboarding Test connection and Test model buttons close the app instantly (rc1, owner's Samsung). Both buttons are the first touch of Python, and the onboarding view model is the only one that calls the core without a try/catch, so any throw during first Python start kills the app instead of showing words. Fixed in rc2: the buttons show the error as text.
2. 2026-09-12: with rc2 the buttons show `PyException: ModuleNotFoundError: No module named 'scipy'` instead of closing. Root cause: `wha.service.evaluation` imports `wha.eval.detection` at module top, which reaches `scipy`, which the phone never installs (pc extra only). The old import sweep missed it because scipy was not on its blocked list and the dev machine has scipy anyway. Fix: lazy import plus a phone-boot simulation test that blocks everything outside the phone requirements.
