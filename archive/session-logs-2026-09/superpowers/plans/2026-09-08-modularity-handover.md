# Making the repository safe for parallel work

**Started 8 September 2026.** Branch `worktree-refactor-modularity-handover`, in a git
worktree, because another agent is working in the main checkout.

## Why this exists

Teammates are about to work on this repository in parallel, each using Claude Code, on
workstreams that overlap: replacing Streamlit with React, turning the single agent into
several, reshaping retrieval. The question asked was whether the repository is modular
enough for that. It mostly is. Four things are not.

**This is a refactor of a system that works.** The bar is therefore not "the tests pass".
It is **no observable behaviour changes at all**: the same steps on screen, the same prose,
the same numbers, the same LLM calls, the same rows written. If an expected value in a test
has to change, that is a blocker, not a fix. Write it to `BLOCKERS.md` and stop.

## What was found, and verified on `main` at 23fc1fb

1. **`agent/nodes.py` is 1,534 lines and holds all eight graph nodes.** Two people
   restructuring the agent conflict on every commit.
2. **The agent's node names are the pipeline's public step ids.** `service/pipeline.py`
   reads them out of `episode_traces`, and `_agent_steps_from_evidence` hardcodes both the
   node names and the five preload tool names. So renaming an agent node breaks the audit
   view and the dashboard, which is a collision between two different teams.
3. **`HybridIndex` is imported by name outside its package**, so replacing retrieval means
   matching a class name rather than implementing an interface.
4. **No dependency direction is written down or enforced,** except for the dashboard. Seven
   function-local imports hold open two cycles (`agent -> service`, `notify -> service`) and
   nothing records that they exist.

## The rule this plan follows

From `AGENTS.md`: *"Make it a rule only a test can enforce. A correction that lives only
where it was made does not survive contact with new prose. If it matters, it is a test."*

Every item below ends in a test, not a paragraph.

---

## Progress

Legend: `[ ]` not started, `[~]` in progress, `[x]` done, `[!]` blocked.

### Step 0: Baseline

- [x] 0.1 Worktree created, `.env` copied, `uv sync` clean. The worktree also needs
      `data/corpus/` copied in: it is 32 MB, gitignored, and retrieval tests fail without
      it in a way that looks like a code defect and is not one
- [x] 0.2 Full suite run on the untouched tree.
      **Baseline: 785 passed, 2 skipped, 0 failed, in 379s.**
      Note `addopts = "-q"` is already set in `pyproject.toml`, so passing `-q` again gives
      `-qq` and silently suppresses the count line. Run `pytest -n auto --tb=no`
- [x] 0.3 `uv run ruff check src tests`: all checks passed
- [x] 0.4 Nothing red before the first edit. Two failures seen on the first attempt were
      both environmental and both fixed before starting: the missing corpus above, and an
      em-dash in this very plan file, which `tests/unit/test_docs.py` correctly rejected

### Step A: Split `agent/nodes.py` into a package

Pure movement. No logic line is edited. Nothing is renamed.

- [x] A.1 Create `src/wha/agent/nodes/` with `__init__.py` re-exporting the 8 node
      functions and the 9 response schemas, so every existing
      `from wha.agent.nodes import X` keeps working
- [x] A.2 `schemas.py`: the 9 Pydantic response models
- [x] A.3 `context.py`: `_episode_context`, `_episode_numbers`,
      `_interruptions_this_week`, `_cycle_applicability`, `_compact_json`,
      `_record_stage_ran`
- [x] A.4 `evidence.py`: `_retrieved_passages`, `_passages_for_prompt`, `_citations_for`,
      `_enforce_claims`
- [x] A.5 One file per node: `preload.py`, `investigate.py`, `believe.py`, `decide.py`,
      `ask.py`, `conclude.py`, `critique.py`, `review.py`
- [x] A.6 **The eight string-path patches.** `interrupt()` is called in exactly two places:
      `node_ask` and `node_review`. `patch("wha.agent.nodes.interrupt")` becomes
      `wha.agent.nodes.ask.interrupt` in `tests/unit/agent/test_interrupt.py` and
      `wha.agent.nodes.review.interrupt` in `tests/unit/agent/test_conclude.py`.
      **Before fixing each one, run it and watch it fail.** A patch aimed at a module that
      no longer defines the name can still leave tests passing, and that is the failure
      being guarded against.
- [x] A.7 **The safety allowlist.** `tests/unit/safety/test_symptom_persistence.py` exempts
      `"agent/nodes.py"` from the rule that every free-text call into the red-flag floor
      passes the symptom history. It must become `"agent/nodes/ask.py"`.
      **Prove it:** first set it to a deliberately wrong value and confirm the test fails
      naming the real file. Getting this wrong widens a safety exemption invisibly, which is
      the single most dangerous edit in this plan.
- [x] A.8 Targeted: `uv run pytest tests/unit/agent tests/unit/safety tests/integration -n auto`
- [x] A.9 Commit

### Step B: The agent owns its own step vocabulary

No copy moves. `STEP_NAMES`, `explain.TEXT` and `TOPIC_STEPS` stay exactly where they are;
they get copy-pasted into React later. `CANONICAL_PIPELINE_STEPS` in `models.py` is
untouched, because it is the public contract the dashboard is keyed to.

- [x] B.1 New `src/wha/agent/steps.py` holding three things and nothing else:
      `AGENT_NODES`, `NODE_TO_PIPELINE_STEP` (identity today), `PRELOAD_TOOLS`
- [x] B.2 `service/pipeline.py` reads all three instead of hardcoding them. The SQL stays
      in the service; only the vocabulary moves to the agent
- [x] B.3 Test: every value in `NODE_TO_PIPELINE_STEP` is a real `step_id` in
      `CANONICAL_PIPELINE_STEPS`
- [x] B.4 Test: every node registered in `build_agent_graph` appears in `AGENT_NODES` and in
      the map, so adding a node without mapping it fails the build
- [x] B.5 Update the "Add a pipeline step" row in `README.md`
- [x] B.6 Targeted: `uv run pytest tests/unit/service tests/unit/api tests/ui -n auto`
- [x] B.7 Commit

### Step C: `Retriever` protocol

- [x] C.1 `@runtime_checkable` `Retriever` protocol in `retrieve/index.py`, one method:
      `query(query_str, top_k, layer, metadata_filter) -> list[RetrievalResult]`
- [x] C.2 `agent/tools/impl.py` imports `Retriever` instead of `HybridIndex`.
      Note: line 275 is a real `isinstance` check. `EpisodeRepository` has no `query`
      method, so the protocol check cannot misfire on the db object it discriminates
      against. Confirm that again after the change
- [x] C.3 `EpisodeRepository.retrieval_index` typed `Retriever | None` instead of `Any`
- [x] C.4 Test: `HybridIndex` satisfies `Retriever`
- [x] C.5 Targeted: `uv run pytest tests/unit/retrieve tests/unit/agent -n auto`
- [x] C.6 Commit

### Step D: Write down and enforce the boundaries

Most of what was planned here already exists. `README.md` gained "Where things live",
"Rules enforced by tests, not by convention", "How to make common changes" and "Testing";
`AGENTS.md` gained "How this project fails". Only the parallel-work gaps remain.

- [x] D.1 `tests/unit/test_layering.py`: an AST import-direction check over all packages,
      in the shape of `tests/ui/test_ui_boundary.py`. The seven existing cycle imports are
      allowlisted **by path with a written reason each**, the way `_ALLOWED_HISTORYLESS`
      already does. This does not break the cycles. It makes them a named list of seven and
      fails the build on the eighth
- [x] D.2 `README.md`: the layer order, and the shared hot spots (`models.py` with 71
      importers, `constants.py` with 54, and `data/schema.sql`) with the instruction to
      announce changes to them
- [x] D.3 `README.md`: correct "The project is finished... nothing is waiting on anybody",
      which is about to be false
- [x] D.4 `README.md`: a "Change the retrieval" row in "How to make common changes"
- [x] D.5 Commit

### Step E: Verify

- [x] E.1 Full suite: **803 passed, 2 skipped, 0 failed** against a baseline of 785 passed,
      2 skipped. The difference is exactly the 18 tests added here: 7 in `test_steps.py`,
      5 in `test_retriever_protocol.py`, 6 in `test_layering.py`. Every test that passed
      before this branch still passes, and the arithmetic accounts for every new one
- [x] E.2 `uv run ruff check src tests`: all checks passed
- [x] E.3 Whole diff read. Twenty files under `src/`, of which twelve are the split. The
      only edits that are not movement are the four intended ones: the `PRELOAD_TOOLS` and
      trace-translation calls in `pipeline.py`, the descriptions split in `episodes.py`, the
      protocol swap in `tools/impl.py`, and three type annotations in `repository.py`
- [x] E.4 **Drove the real dashboard**, on the committed seventeen day demo timeline
      (`tools/demo_film/serve_demo.py`), which contains three linked investigations.
      - All eleven agentic and user step labels render on the pipeline view, read off the
        page rather than inferred: "Open an investigation" through "Send and save"
      - All ten nights with an episode were read back through the API. Two episodes report
        every agentic step as `ran`; the third reports `ask=skipped`,
        `answer=not_applicable`, `deliver=skipped`, which is a real difference correctly
        reported and proves the translation is not passing everything through blindly
      - The Trace tab stages return all eight names with their original descriptions
      - Today, History and The record were opened and read. No error markers on any page.
        The two console entries are Streamlit's own `_stcore/health` and `host-config`
        probes 404ing because the page was deep-linked rather than clicked into, and they
        appear on an unmodified checkout too
- [x] E.5 PR opened: https://github.com/NatBrian/wearable-health-agent/pull/2

---

## Findings made during the work

### 1. `docs/CODE-CONVENTIONS.md` describes boundaries that do not exist

Found at Step 0, before any edit. The "Module boundaries" section opens with *"These are
enforced by a lint rule, not by good intentions. Breaking one is a blocker, not a judgement
call."* All three of its rules are false, and so is the claim of enforcement:

| It says | Actually |
|---|---|
| `ui/` may import ONLY from `service/` and `models.py` | The reverse. `tests/ui/test_ui_boundary.py` **forbids** the UI importing `wha.service`. Screens go through `wha.api` |
| `db/` is the ONLY module that imports `sqlite3` | 22 files outside `db/` import it, across `service/`, `agent/`, `detect/`, `features/`, `ingest/` and `audit/` |
| Enforced by a lint rule | There is no such rule. `ruff.toml` sets `line-length`, `target-version` and two `per-file-ignores`, nothing else |

This is the exact shape `AGENTS.md` warns about: a rule that lives only in a document. It
is worse than a missing rule for a handover, because an incoming agent reads it and does the
opposite of what the tests require.

**This does not widen the scope.** Step D was already "write down and enforce the
boundaries". It is now aimed at `docs/CODE-CONVENTIONS.md` rather than at `README.md`:
correct the three rules to what is true, and make the enforcement claim true by writing
`tests/unit/test_layering.py`.

### 2. The node names were written out four times, not three

Found while wiring Step B. Besides `CANONICAL_PIPELINE_STEPS` and the hardcoded set in
`_agent_steps_from_evidence`, `service/episodes.py` held `CANONICAL_STAGES`: a second
complete copy of all eight node names, driving the Trace tab.

Its own comment records the defect this causes. `node_measure` was deleted, that list was
not updated, and the Trace tab went on advertising a stage of the reader's own investigation
as permanently pending. It was found by opening the tab on 5 September 2026, not by a test.

The names now come from `AGENT_NODES`; only the descriptions stay in `episodes.py`, because
they are prose and prose stays where it is. A node with no description raises `ConfigError`
at import rather than rendering a blank row.

**One thing is deliberately left alone.** `_agent_steps_from_evidence` still writes node
names as string literals, because each is tied to a specific piece of stored evidence
("a stored belief means believe and decide both ran") and turning that into a table would
obscure the reasoning. They are covered indirectly: `test_steps.py` fails if the graph gains
or renames a node, which is exactly when those literals would go stale.

### 3. The new tests were proved by breaking the code, not by watching them pass

A phantom `measure` node was added to `AGENT_NODES`, described in `_STAGE_DESCRIPTIONS` so
the import would succeed, and the suite re-run. Four tests failed, including
`test_the_graph_registers_exactly_the_nodes_declared_here`. The injection was then reverted.
A test that passes and cannot fail is worth nothing, and this is a repository where "the
failure reported success" is the documented recurring defect shape.

### 4. Running the suite in a fresh worktree needs two things a clone does not have

Neither is a defect, and both cost time to work out from a failure that looks like one.
`data/corpus/` is 32 MB and gitignored, and without it `test_knowledge_corpus.py` fails in a
way that reads like a retrieval bug. `.env` is gitignored too. Copy both from the main
checkout, or run `uv run wha data fetch corpus`.

## What was deliberately not done

Named here so the next person does not have to work out whether these were missed or
decided.

- **The two import cycles are not broken.** `agent` with `service` and `notify` with
  `service`. Breaking them means moving `symptoms`, `settings` and `episode_lifecycle` into
  a lower layer, which is code four people are about to work in. They are named with their
  reasons in `tests/unit/test_layering.py` instead, and an eighth upward import fails.
- **No user-facing copy moved.** `STEP_NAMES`, `explain.TEXT` and `TOPIC_STEPS` stay in the
  dashboard. Whoever builds the React client copies them across. Moving 63 strings behind
  the API would have been a larger change than the whole of this branch, for a benefit that
  only arrives when that client is written.
- **`_agent_steps_from_evidence` keeps its node names as literals.** Explained under
  finding 2.
- **`models.py` and `constants.py` were not split**, though they are the files parallel work
  will actually collide in. Splitting them would touch 71 and 54 importers respectively, and
  the collision is a merge problem rather than an architectural one. It is documented in the
  README instead, under "Working on this at the same time as somebody else".

## Blockers found

_None. Nothing in this branch required a decision that was not already made._
