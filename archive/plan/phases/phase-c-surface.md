# Phase C. Surface

The dashboard, the scheduler, and the documentation that makes the repository legible to someone who
did not build it.

**Done when** `uv run wha serve` renders every scenario correctly and the interface test suite is
green.

Built **last, against a core that already passes its tests**, so every number on screen has a
passing test behind it before it is displayed.

---

## Tasks

| ID | Title | Depends on | Component |
|---|---|---|---|
| C-01 | App shell, sidebar, subject selector, status strip fragment | B-21 | 15 |
| C-02 | Today: the inbox, last night, open episodes | C-01, B-22 | 15 |
| C-03 | History: night chart with the maturing band, episode spans, night table | C-01 | 15 |
| C-04 | Episode panel: Summary and Trace tabs | C-03, B-22 | 15 |
| C-05 | Episode panel: Conversation and Evidence tabs | C-04 | 15 |
| C-06 | Audit page, with hash-chain verification and export | C-01, B-23 | 15 |
| C-07 | Evaluation page | C-01, B-23 | 15 |
| C-08 | Settings page, with connection tests and delete-all | C-01, B-23 | 15 |
| C-09 | `wha serve`, the scheduler thread, Task Scheduler documentation | C-01, B-20 | 17 |
| C-10 | README rewrite, screenshots, quickstart | C-09 | - |
| C-11 | Documentation pass: strip course and team framing from the public documents | C-10 | - |
| C-12 | Full scenario sweep and the release checklist | C-09 | - |

---

## Order notes

**C-01 before every other page**, because the status strip renders on all of them and the subject
selector governs what they read.

**The status strip lives in an `st.fragment` on a 10 second interval.** Without that, every page
re-runs entirely every ten seconds and the interface feels broken.

**C-03 before C-04.** The episode panel is reached through History via `?episode=<id>`, not from the
navigation, so the route must exist before the panel does.

**C-04's Trace tab is the most important screen in the project.** It is where `INVESTIGATE` expands
into the individual tool calls the model chose, with provenance and freshness per call, and where
skipped stages appear with their reasons. That is what shows the path was decided at run time rather
than scripted.

**C-09 last among the code tasks.** The scheduler makes notifications fire when the dashboard is
closed, and `episode_tick` is what drives every timeout, so it needs everything else working first.

**C-11 is human work, not agent work.** `history/PROPOSAL.md`, `README.md` and `history/HANDOFF.md` currently refer
to a course, a marker, a module and a team, and the system is solo and the repository will be public.
That rewrite involves narrative judgement and is done by a person. The coding agent must not touch
those files.

---

## Interface tests

`streamlit.testing.v1.AppTest` against a database seeded from the scenario fixtures. The interface is
test-gated like everything else; it is not the one unverified part of the build.

The tests that matter most:

- `test_today_nothing_pending` renders reassurance rather than emptiness. **This is the state a user
  is in on almost every day**, so it is the most-seen screen in the product.
- `test_history_gaps_not_interpolated` proves the chart draws a gap where there is no evidence.
- `test_history_band_narrows_with_maturity` proves the ladder is visible.
- `test_episode_trace_shows_skipped` and `test_episode_trace_expands_tool_calls` prove the agentic
  claim on screen.
- `test_episode_conversation_shows_rejected_probes` proves the decision was a decision.
- `test_settings_secrets_not_echoed` proves the secret handling.

---

## The release checklist, C-12

1. `uv run pytest -q` green in full.
2. `uv run ruff check src tests` clean.
3. `uv run wha doctor` with no fail rows.
4. Every scenario in `tests/fixtures/scenarios/` runs through `uv run wha demo run` and reaches its
   expected disposition.
5. Every page renders on a fresh database with **zero** data, and on the seeded demo database.
6. `verify_hash_chain` passes on the demo database.
7. No secret appears anywhere in the repository, in a log, in an audit export or in a screenshot.
8. `.gitignore` still excludes `data/`, `.env` and every dataset, database and model artefact.
9. `PROGRESS.md` complete, `BLOCKERS.md` reviewed.
10. README quickstart followed from scratch on a clean checkout.

---

## Exit condition

```bash
uv run pytest -q
uv run wha serve
```

Every page renders. Today shows the correct state for a subject with two nights and for one with
thirty. An episode panel shows its trace with skipped stages and expanded tool calls. The audit page
verifies its chain.

---

## Phase D, and whether it happens

`components/` has no document for Phase D because it is **speculative**. A FastAPI wrapper over the
service layer plus a Next dashboard would look better in a portfolio, and D-116's service boundary
makes it a wrapper rather than a rewrite.

**Plan as though Streamlit is the final surface.** Start Phase D only if Phase C is signed off and
green, and abandon it without regret if it goes badly, because Phase C is a complete product on its
own.
