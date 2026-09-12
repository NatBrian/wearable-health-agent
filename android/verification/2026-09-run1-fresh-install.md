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
| Test connection with the real port | Reports the record types the core sees; a wrong port reports unavailable in words | rc3: `Bridge connection error to http://127.0.0.1:Connect Error` despite the webhook running on 8787 with the right token. Finding 3: the Test override sends the host but not the port, so the check probes port 80. |
| Test provider with the rotated key | Reports success | rc3: `LLM connectivity error for provider 'openai_compatible': Cassette miss for prompt_id='ping'`. Finding 4: the Test override sends only provider and model; the check builds its client from ambient settings, which pre-Finish is cassette, so it never touches the entered address. |
| Finish | Notification permission asked; corpus fetch starts; Today shows the provider notice absent and the corpus notice present | |
| Within one minute | Today shows the last pull time and last night with its level | |
| History | Thirty days of nights; unmeasured nights open circles; the band present once the rung allows | |
| Record | Newest night's twenty-one steps; investigation group dimmed with reasons | |
| Settings | Every constant matches the dashboard on the PC for the same constant | |
| Corpus finished | Retrieval ready; a chat turn about fever quotes MedlinePlus with the Library named | |

## Findings

1. 2026-09-12: onboarding Test connection and Test model buttons close the app instantly (rc1, owner's Samsung). Both buttons are the first touch of Python, and the onboarding view model is the only one that calls the core without a try/catch, so any throw during first Python start kills the app instead of showing words. Fixed in rc2: the buttons show the error as text.
2. 2026-09-12: with rc2 the buttons show `PyException: ModuleNotFoundError: No module named 'scipy'` instead of closing. Root cause: `wha.service.evaluation` imports `wha.eval.detection` at module top, which reaches `scipy`, which the phone never installs (pc extra only). The old import sweep missed it because scipy was not on its blocked list and the dev machine has scipy anyway. Fix: lazy import plus a phone-boot simulation test that blocks everything outside the phone requirements.
3. 2026-09-12: with rc3, Test connection reports `Bridge connection error to http://127.0.0.1` while the webhook runs on 8787. Root cause: the Test override carries the host but not the port, so the check probes port 80. Fix: send the port through and apply it when the URL carries none.
4. 2026-09-12: with rc3, Test model reports a cassette miss pre-Finish. Root cause: the override carries provider and model labels only; the check builds its client from ambient settings, which is cassette until Finish plus restart. Fix: forward base URL and key and build the checked client from the overrides.
