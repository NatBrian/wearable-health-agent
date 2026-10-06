# Detection Streak and Credential Scrub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Make the backend detection streak stop at unmeasured nights, matching the existing quiet-night rule, then remove the exposed `.env` commits from PR #3 while retaining its configuration locally as `.env2`.

**Architecture:** Keep streak calculation in `get_system_status`. Include `NA` rows in the descending detection query and stop the run at the first unmeasured or different-level row. Prove this with in-memory SQLite-backed service tests. After code verification, preserve the PR `.env` content as an ignored local `.env2`, then update the PR branch to the tested commit based on the parent of the two `.env`-only commits.

**Tech Stack:** Python 3.12, SQLite, `uv`, pytest, Git and PowerShell.

**Spec:** User instruction in the current conversation; repository constraints in `AGENTS.md`; streak presentation requirement in `docs/superpowers/plans/2026-09-29-dashboard-ux-refinement.md`.

## Global Constraints

- Never weaken or remove tests.
- A night with no reading is missing data and must break the streak.
- Always run Python through `uv`.
- Do not touch or replace the existing local `.env` or any real-subject database.
- Verify the `.env2` copy is excluded from Git and absent from the PR tree/history.
- Merge PR #3 only after the full Python suite passes, the `.env` scrub is verified, and every exposed credential has been revoked or rotated. The user's latest instruction authorizes merging once those blockers are clear, superseding the earlier confirmation gate.

## Review Focus

- A newest `NA` row yields no detection streak.
- A middle `NA` row breaks two matching measured levels into separate runs.
- A different measured level continues to break the run.
- Consecutive equal levels retain their residual direction.
- The cohort parquet cache has its required direct runtime dependency after Streamlit is removed.
- The dependency contract matches the runtime declarations.
- The local `.env2` has the PR `.env` values, remains untracked, and the existing `.env` remains unchanged.

The frontend audit also found a high-severity advisory in the development dependency tree. The lockfile now uses the compatible `source-map-js` patch release that clears the advisory; `npm audit` reports zero vulnerabilities. Removing Streamlit also removed `pyarrow`, which the cohort cache imports through pandas, so it is now declared directly. The runtime dependency contract records the new `pyarrow` and `pip-system-certs` requirements.

---

### Task 1: Break the backend detection streak at `NA`

**Files:**
- Modify `tests/unit/service/test_honest_reporting.py`.
- Modify `src/wha/service/status.py`.
- Update `pyproject.toml`, `uv.lock`, and `docs/CONTRACTS.md` for the dependencies this PR now requires.
- Update `frontend/package-lock.json` to clear the audited development dependency advisory.
- Create this plan file.

**Interfaces:** Consumes `DetectionStreak` and `get_system_status`; keeps the existing API model and React consumer unchanged.

- [x] Add SQLite-backed regression cases for an `NA` gap and a newest `NA` row.
- [x] Run the two cases and confirm they fail because the current query skips `NA`.
- [x] Include `NA` rows in the query and stop at the first row that differs from the newest measured level.
- [x] Declare `pyarrow` directly after Streamlit removal and reconcile the runtime dependency contract.
- [x] Rerun the cases, then run the repository test suite and Ruff once at the end.
- [x] Commit the plan, tests, and backend change with a why-focused message.

**Done when:** Both new cases pass, existing same-level behavior remains covered, and the full repository checks pass.

**Verification note:** The streak cases, focused dependency checks, full suite (`716 passed, 3 skipped`), and Ruff pass. The suite initially exposed that dense retrieval could surface assumed probe evidence for a general symptom report when the optional MedlinePlus snapshot was absent; Task 3 records the fix.

### Task 2: Preserve locally and scrub PR history

**Files:** Local-only `.env2` in the original checkout; PR branch history.

- [x] Copy the PR `.env` configuration to `.env2` without displaying its values or changing the existing `.env`.
- [x] Add `.env2` to the original checkout's local Git exclude file.
- [x] Push the tested branch with an explicit lease against the known PR head, omitting both `.env` commits.
- [x] Verify PR #3 has no `.env` file and no `.env`-bearing commit in its current branch history.
- [x] Confirm the local `.env` hash is unchanged and the `.env2` file is ignored.

**Done when:** The PR branch contains the backend fix and no `.env` path in its current tree or history, while the local original `.env` remains unchanged and `.env2` is safely excluded.

**Credential gate:** The preserved `.env2` contains exposed credentials named `WHA_LLM_API_KEY` (OpenRouter endpoint), `WHA_TELEGRAM_TOKEN`, and `WHA_BRIDGE_TOKEN`. The local `.env` hash matches its pre-task value, and `.env2` is excluded by `.git/info/exclude`. All three exposed credentials must be revoked or rotated before merge; the user must complete credential changes themselves.

### Task 3: Keep internal probe evidence out of general symptom searches

**Files:** `src/wha/retrieve/index.py`, `src/wha/retrieve/knowledge_docs.py`, and retrieval tests.

- [x] Reproduce the failing symptom query against the authored-only corpus.
- [x] Require an explicit authored probe question or a distinctive multiword answer phrase before probe-evidence chunks can enter hybrid ranking; one-word labels require question context.
- [x] Preserve direct retrieval for the probe question and fixed answer labels.
- [x] Address final review's Important finding: generic labels such as `No`, `Yes`, and `Normal` could match general symptom searches. Add regression cases for `No fever` and `yes, I feel unwell` while retaining prompt and distinctive-label retrieval.
- [x] Run the final `uv run pytest -n auto` (716 passed, 3 skipped) and `uv run ruff check src tests` (all checks passed) after the review fix.
- [x] Run `uv run ruff check src tests`: all checks passed.

**Done when:** General symptom searches do not retrieve assumed probe likelihoods, and deliberate probe-evidence searches continue to work.

**PR state:** The `.env` path and its old tip commit are absent from the current PR file list/history. GitHub previously reported the branch mergeable but blocked, without status checks or a review decision. Credential rotation remains the security blocker; recheck GitHub state after pushing Task 3.
