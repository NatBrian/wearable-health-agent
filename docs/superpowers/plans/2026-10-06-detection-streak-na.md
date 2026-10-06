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
- Do not merge PR #3; report its readiness for the owner.

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
- [ ] Commit the plan, tests, and backend change with a why-focused message.

**Done when:** Both new cases pass, existing same-level behavior remains covered, and the full repository checks pass.

**Verification note:** The new streak cases and focused dependency checks pass, and Ruff passes. The full suite still fails at `tests/unit/retrieve/test_knowledge_corpus.py::test_the_index_finds_the_right_passage_for_a_symptom_and_for_a_red_flag`. That test, its retrieval code and corpus, and the relevant retrieval package versions are unchanged from the base branch.

### Task 2: Preserve locally and scrub PR history

**Files:** Local-only `.env2` in the original checkout; PR branch history.

- [x] Copy the PR `.env` blob to `.env2` without reading or changing the existing `.env`.
- [x] Add `.env2` to the original checkout's local Git exclude file.
- [ ] Push the tested branch with an explicit lease against the known PR head, omitting both `.env` commits.
- [ ] Verify PR #3 has no `.env` file and no `.env`-bearing commit in its current branch history.
- [x] Confirm the local `.env` hash is unchanged and the `.env2` file is ignored.

**Done when:** The PR branch contains the backend fix and no `.env` path in its current tree or history, while the local original `.env` remains unchanged and `.env2` is safely excluded.
