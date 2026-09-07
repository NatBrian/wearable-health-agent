# Dashboard Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete and rewrite the five Streamlit screens so a person with no engineering and no medical background can read every number, see where it came from, and follow the night's journey step by step.

**Architecture:** One new read-only service module assembles a whole night's pipeline from data already stored, exposed through two new endpoints. The interface layer is rewritten from scratch against the HTTP client only, with all explanatory prose in one module and all CSS in another.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, Streamlit 1.62, Altair, SQLite, pytest, ruff, Playwright MCP for interface verification.

**Spec:** `docs/superpowers/specs/2026-09-06-dashboard-overhaul-design.md`

## Global Constraints

- Always `uv run`. Bare `python` resolves to an unrelated project's virtual environment.
- Never `git push`. Commit locally. No co-author line. No em-dash anywhere, in code, copy, commits or documents.
- Subject `me` holds four real nights of a real person's data. Never write to it, never delete it. All development and all verification runs against subject `sim`.
- Never invent a number. A step with no recorded timestamp shows no timestamp. A figure with no source is marked as having none.
- No module under `src/wha/ui/` may import from `wha` anything other than `wha.api`, `wha.models`, `wha.ui`. No SQL, no `sqlite3`, no `wha.service`, no `wha.constants`, no `wha.clock`.
- No string shipped by the interface may appear in the `never_say` list in `data/knowledge/red_flags.yaml`.
- `docs/CONTRACTS.md`, `history/`, `research/`, `archive/` are read-only.
- Stop `uv run wha serve` before any `uv sync`; it holds the virtual environment open.
- The dashboard is verified by driving it with the Playwright MCP tools, not by tests alone. Task 12 is not optional and is not a formality.
- The full suite runs ONCE, at the end. Individual test files run freely during work.

---

## File Structure

**Created:**

| File | Responsibility |
|---|---|
| `src/wha/service/pipeline.py` | Assemble one night's journey from stored data. No new writes |
| `tests/unit/service/test_pipeline.py` | Behaviour of that assembly, over seeded nights |
| `src/wha/ui/design.py` | CSS tokens and layout primitives. The only module with styling |
| `src/wha/ui/explain.py` | Every explanatory sentence, keyed by id. Contains no figures |
| `src/wha/ui/format.py` | API values to display strings: bpm, dates, durations, probabilities |
| `src/wha/ui/components/status_bar.py` | The top bar |
| `src/wha/ui/components/verdict.py` | The level card and the three numbers behind it |
| `src/wha/ui/components/citations.py` | Citation chip and passage drawer |
| `src/wha/ui/components/night_chart.py` | The history chart |
| `src/wha/ui/components/pipeline_graph.py` | The clickable step grid |
| `src/wha/ui/components/step_detail.py` | The detail panel for a selected step |
| `src/wha/ui/components/chat.py` | The conversation |
| `tests/ui/conftest.py` | The fake API fixture every interface test uses |
| `docs/superpowers/plans/walkthrough-2026-09-06.md` | Findings from driving the real interface |

**Rewritten in place (deleted first, then written fresh):**

`src/wha/ui/Home.py`, `src/wha/ui/pages/1_Today.py`, `2_History.py`, `3_Audit.py`, `4_Settings.py`, and the page bodies which move from `src/wha/ui/{today,history,audit,settings}.py` into `src/wha/ui/pages/`.

**Deleted outright:** `src/wha/ui/components/{disclaimer,status_strip,subject_selector,belief_chart,episode_panel,pipeline_trace,wording}.py`, `src/wha/ui/{today,history,audit,settings}.py`, `tests/ui/test_{app_shell,audit,episode,history,history_page,settings,today}.py`.

**Kept untouched:** `tests/ui/test_ui_boundary.py`, `tests/unit/ui/test_client_results_are_used_as_returned.py`. **Kept and strengthened:** `tests/unit/ui/test_wording_never_say.py`, `tests/unit/ui/test_citation_labels.py`.

**Modified:** `src/wha/models.py` (new pipeline models), `src/wha/api/app.py` (two endpoints), `src/wha/api/client.py` (two methods), `src/wha/service/__init__.py` (exports), `BLOCKERS.md` (one appended entry), `STATUS.md` (what changed).

---

### Task 1: Pipeline models

**Files:**
- Modify: `src/wha/models.py` (append after `PipelineStage`, around line 449)
- Test: `tests/unit/service/test_pipeline.py` (create)

**Interfaces:**
- Consumes: `Citation`, `DetectionLevel`, `CauseId` from `wha.models`
- Produces: `StepLayer`, `StepStatus`, `PipelineStepView`, `PipelineHeadline`, `NightPipeline`, `PipelineNightRef`, `CANONICAL_PIPELINE_STEPS`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/service/test_pipeline.py`:

```python
"""The night pipeline: every step of the journey, for every night, or an honest gap."""

from datetime import date

from wha.models import (
    CANONICAL_PIPELINE_STEPS,
    NightPipeline,
    PipelineHeadline,
    PipelineStepView,
    StepLayer,
    StepStatus,
)
from wha.models import DetectionLevel


def test_the_canonical_steps_are_ordered_and_unique() -> None:
    """The order on screen is the order the system ran, and no id appears twice."""
    ordinals = [s.ordinal for s in CANONICAL_PIPELINE_STEPS]
    ids = [s.step_id for s in CANONICAL_PIPELINE_STEPS]
    assert ordinals == sorted(ordinals)
    assert len(set(ids)) == len(ids)


def test_the_agentic_ids_match_the_stage_names_the_agent_already_uses() -> None:
    """Two vocabularies for one pipeline is how a screen comes to contradict the record."""
    from wha.service.episodes import CANONICAL_STAGES

    agent_ids = {s.step_id for s in CANONICAL_PIPELINE_STEPS if s.layer == StepLayer.AGENTIC}
    for name, _description in CANONICAL_STAGES:
        assert name in agent_ids, f"agent stage {name} has no pipeline step"


def test_a_step_view_rejects_a_field_nobody_declared() -> None:
    step = PipelineStepView(
        step_id="detect",
        ordinal=7,
        layer=StepLayer.DETERMINISTIC,
        status=StepStatus.RAN,
        reason="Compared the reading against your own band.",
    )
    assert step.occurred_utc is None
    assert step.headline_figure is None
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/unit/service/test_pipeline.py -v`
Expected: FAIL, `ImportError: cannot import name 'CANONICAL_PIPELINE_STEPS'`

- [ ] **Step 3: Add the models**

Append to `src/wha/models.py`:

```python
class StepLayer(StrEnum):
    """Which machine ran the step. The screen colours by this."""

    DETERMINISTIC = "deterministic"
    AGENTIC = "agentic"
    USER = "user"
    SAFETY = "safety"


class StepStatus(StrEnum):
    """RAN and SKIPPED are claims about the night. UNRECORDED is a claim about us.

    Reporting "we did not write this down" as "it did not run" is the defect the
    September 2026 audit found on every episode, so the two are separate values.
    """

    RAN = "ran"
    SKIPPED = "skipped"
    NOT_APPLICABLE = "not_applicable"
    UNRECORDED = "unrecorded"


class PipelineStepDef(BaseModel):
    """One step of the journey, independent of any particular night."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    step_id: str
    ordinal: int
    layer: StepLayer


class PipelineStepView(BaseModel):
    """What one step did on one night."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    step_id: str
    ordinal: int
    layer: StepLayer
    status: StepStatus
    reason: str
    headline_figure: str | None = None
    occurred_utc: datetime | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    sources: list[Citation] = Field(default_factory=list)
    detail_json: dict[str, Any] = Field(default_factory=dict)


class PipelineHeadline(BaseModel):
    """The five tiles above the graph. Assembled, never recalculated."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    level: DetectionLevel
    flagged: bool
    primary_cause: CauseId | None = None
    primary_probability: float | None = None
    sleep_hours: float | None = None
    coverage_minutes: int = 0
    questions_asked: int = 0
    sources_read: int = 0


class NightPipeline(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    subject_id: str
    night_date: date
    episode_id: str | None = None
    headline: PipelineHeadline
    steps: list[PipelineStepView] = Field(default_factory=list)


class PipelineNightRef(BaseModel):
    """One entry in the night stepper. Small on purpose: sixty of these load at once."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    night_date: date
    level: DetectionLevel
    has_episode: bool
    usable: bool


CANONICAL_PIPELINE_STEPS: tuple[PipelineStepDef, ...] = (
    PipelineStepDef(step_id="collect", ordinal=1, layer=StepLayer.DETERMINISTIC),
    PipelineStepDef(step_id="store", ordinal=2, layer=StepLayer.DETERMINISTIC),
    PipelineStepDef(step_id="sleep_window", ordinal=3, layer=StepLayer.DETERMINISTIC),
    PipelineStepDef(step_id="features", ordinal=4, layer=StepLayer.DETERMINISTIC),
    PipelineStepDef(step_id="baseline", ordinal=5, layer=StepLayer.DETERMINISTIC),
    PipelineStepDef(step_id="subtract_explained", ordinal=6, layer=StepLayer.DETERMINISTIC),
    PipelineStepDef(step_id="detect", ordinal=7, layer=StepLayer.DETERMINISTIC),
    PipelineStepDef(step_id="episode_open", ordinal=8, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="preload", ordinal=9, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="investigate", ordinal=10, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="believe", ordinal=11, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="decide", ordinal=12, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="ask", ordinal=13, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="answer", ordinal=14, layer=StepLayer.USER),
    PipelineStepDef(step_id="conclude", ordinal=15, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="critique", ordinal=16, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="review", ordinal=17, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="deliver", ordinal=18, layer=StepLayer.AGENTIC),
    PipelineStepDef(step_id="safety_phrase_rules", ordinal=19, layer=StepLayer.SAFETY),
    PipelineStepDef(step_id="safety_triage", ordinal=20, layer=StepLayer.SAFETY),
)
```

Note: `CANONICAL_STAGES` in `src/wha/service/episodes.py` has no `deliver` step. `deliver` is a pipeline step only, so the test in Step 1 checks stage names are a subset of step ids, not the reverse.

- [ ] **Step 4: Run and confirm green**

Run: `uv run pytest tests/unit/service/test_pipeline.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/wha/models.py tests/unit/service/test_pipeline.py
git commit -m "Add the pipeline step models, with unrecorded as a first-class status"
```

---

### Task 2: The deterministic half of the pipeline, steps 1 to 7

**Files:**
- Create: `src/wha/service/pipeline.py`
- Modify: `src/wha/service/__init__.py`
- Test: `tests/unit/service/test_pipeline.py`

**Interfaces:**
- Consumes: `wha.db.connect`, `wha.db.apply_schema`, `service.nights.get_night_detail`, models from Task 1
- Produces: `get_night_pipeline(subject_id, night_date, conn=None) -> NightPipeline`, `list_pipeline_nights(subject_id, days=60, conn=None) -> list[PipelineNightRef]`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/service/test_pipeline.py`. Use the repository's existing seeding helpers; check `tests/conftest.py` for the fixture that produces a database with nights in it, and follow the pattern used in `tests/unit/service/test_episodes.py`.

```python
def test_a_quiet_night_still_has_the_first_seven_steps(seeded_db) -> None:
    """The screen exists to explain every night, not only the alarming ones.

    Sixty-eight of seventy-two nights in the sample opened no investigation. If those
    nights render as an empty page, the page says nothing on the nights the person is
    most likely to look at it.
    """
    from wha.service.pipeline import get_night_pipeline

    pipeline = get_night_pipeline("sim", date(2026, 8, 1), conn=seeded_db)

    deterministic = [s for s in pipeline.steps if s.layer == StepLayer.DETERMINISTIC]
    assert [s.step_id for s in deterministic] == [
        "collect", "store", "sleep_window", "features",
        "baseline", "subtract_explained", "detect",
    ]
    assert all(s.status == StepStatus.RAN for s in deterministic)


def test_the_step_that_found_the_sleep_window_says_which_window_it_used(seeded_db) -> None:
    """The page must not assert "because no sleep was recorded" on a night that recorded it."""
    from wha.service.pipeline import get_night_pipeline

    pipeline = get_night_pipeline("sim", date(2026, 8, 1), conn=seeded_db)
    window = next(s for s in pipeline.steps if s.step_id == "sleep_window")
    assert window.outputs["window_source"] in {"sleep", "clock"}


def test_no_step_carries_a_timestamp_the_database_does_not_hold(seeded_db) -> None:
    """A clock time nobody recorded is an invented number, which this project does not add."""
    from wha.service.pipeline import get_night_pipeline

    pipeline = get_night_pipeline("sim", date(2026, 8, 1), conn=seeded_db)
    recorded = {
        row[0]
        for row in seeded_db.execute(
            "SELECT computed_at_utc FROM nightly_features WHERE subject_id = 'sim'"
        )
    } | {
        row[0]
        for row in seeded_db.execute(
            "SELECT timestamp_utc FROM audit_events WHERE subject_id = 'sim'"
        )
    }
    for step in pipeline.steps:
        if step.occurred_utc is not None:
            assert step.occurred_utc.isoformat() in recorded, step.step_id


def test_a_night_with_no_reading_says_so_rather_than_reporting_a_number(seeded_db) -> None:
    """A missing night is missing data, never a quiet night."""
    from wha.service.pipeline import get_night_pipeline

    pipeline = get_night_pipeline("sim", date(2026, 7, 4), conn=seeded_db)
    features = next(s for s in pipeline.steps if s.step_id == "features")
    assert features.status in {StepStatus.SKIPPED, StepStatus.UNRECORDED}
    assert features.headline_figure is None


def test_the_night_list_covers_every_calendar_night_in_the_window(seeded_db) -> None:
    from wha.service.pipeline import list_pipeline_nights

    refs = list_pipeline_nights("sim", days=30, conn=seeded_db)
    assert len(refs) == 31
    assert refs == sorted(refs, key=lambda r: r.night_date)
```

- [ ] **Step 2: Run and watch them fail**

Run: `uv run pytest tests/unit/service/test_pipeline.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'wha.service.pipeline'`

- [ ] **Step 3: Write the module**

Create `src/wha/service/pipeline.py`. The docstring states why the module exists, in the style of the rest of `service/`:

```python
"""One night's journey, assembled from what was stored rather than re-run.

The deterministic half of this system leaves its working behind in four tables:
`heart_rate_samples`, `nightly_features`, `baselines` and `detections`. Nothing before
this module put those together and told the story of a single night, so the interface
could explain an investigation and could not explain the sixty-eight nights out of
seventy-two where no investigation happened.

Nothing here recalculates. Every figure is read from the row the deterministic half
wrote, so this module cannot disagree with the detector. Where a row records when it was
computed, that time is reported. Where none was recorded, none is reported: a plausible
clock time is exactly the kind of invented figure this project refuses to add.
"""
```

Implement `get_night_pipeline` as: open a connection when none is given, load the night detail, then build the seven deterministic steps in order. Each step sets `status`, `reason`, `headline_figure`, `inputs`, `outputs`, and `occurred_utc` only where a stored timestamp exists.

Rules the implementation must follow, each of which has a test above:

1. `collect`: read the most recent `raw_payloads` row covering the night and the newest ingest audit event. No payload row and no audit event means `UNRECORDED`, not `SKIPPED`.
2. `store`: count `heart_rate_samples` and `sleep_stages` rows for the night. Zero samples is `SKIPPED` with the reason "the watch recorded nothing for this night".
3. `sleep_window`: `outputs["window_source"]` is `NightlyFeatures.rhr_window_source` verbatim. Never defaulted.
4. `features`: `occurred_utc` is `nightly_features.computed_at_utc`. `headline_figure` is the resting heart rate, or `None` when `rhr_bpm` is null.
5. `baseline`: centre, band scale, usable nights and rung, all from the `baselines` row.
6. `subtract_explained`: `NOT_APPLICABLE` with the reason "nothing to subtract: no recorded evening workout" when `explained_bpm` is zero.
7. `detect`: level, flagged, and the detector's own `reasons` list carried verbatim into `outputs`.

`list_pipeline_nights` reuses `service.nights.list_nights` and maps each `NightRow` to a `PipelineNightRef`, so the two lists cannot disagree about which nights exist.

Export both functions from `src/wha/service/__init__.py`, following the existing import and `__all__` pattern in that file.

- [ ] **Step 4: Run and confirm green**

Run: `uv run pytest tests/unit/service/test_pipeline.py -v`
Expected: all pass

- [ ] **Step 5: Check it against a real night, not only a seeded one**

Run:

```bash
uv run python -c "
from datetime import date
from wha.service.pipeline import get_night_pipeline
p = get_night_pipeline('sim', date(2026, 9, 4))
for s in p.steps:
    print(s.ordinal, s.step_id, s.status.value, s.headline_figure, s.occurred_utc)
"
```

Read the output. Every deterministic step should say something true about that night. If a step reads oddly, the reason text is wrong and this is the moment to fix it.

- [ ] **Step 6: Commit**

```bash
git add src/wha/service/pipeline.py src/wha/service/__init__.py tests/unit/service/test_pipeline.py
git commit -m "Assemble the deterministic half of a night's pipeline from what was stored"
```

---

### Task 3: The agentic half, the user step, and the safety floor

**Files:**
- Modify: `src/wha/service/pipeline.py`
- Test: `tests/unit/service/test_pipeline.py`

**Interfaces:**
- Consumes: `service.episodes.get_episode`, `service.episodes.CANONICAL_STAGES`, `EpisodeDetail`, `PipelineHeadline`
- Produces: the same two functions, now returning all twenty steps and a populated headline

- [ ] **Step 1: Write the failing tests**

```python
def test_a_quiet_night_explains_why_no_investigation_opened(seeded_db) -> None:
    """Silence has a reason, and the reason is the interesting part."""
    from wha.service.pipeline import get_night_pipeline

    pipeline = get_night_pipeline("sim", date(2026, 8, 1), conn=seeded_db)
    opened = next(s for s in pipeline.steps if s.step_id == "episode_open")
    assert opened.status == StepStatus.NOT_APPLICABLE
    assert opened.reason
    assert pipeline.episode_id is None
    later = [s for s in pipeline.steps if s.ordinal > 8 and s.layer == StepLayer.AGENTIC]
    assert all(s.status == StepStatus.NOT_APPLICABLE for s in later)


def test_an_investigated_night_carries_every_step(seeded_db_with_episode) -> None:
    from wha.service.pipeline import get_night_pipeline

    pipeline = get_night_pipeline("sim", date(2026, 9, 4), conn=seeded_db_with_episode)
    assert pipeline.episode_id is not None
    assert [s.ordinal for s in pipeline.steps] == list(range(1, 21))
    believe = next(s for s in pipeline.steps if s.step_id == "believe")
    assert believe.status == StepStatus.RAN
    assert believe.outputs["top_cause"]


def test_an_episode_with_no_stored_trace_is_unrecorded_not_skipped(
    seeded_db_with_untraced_episode,
) -> None:
    """"We did not write it down" and "it did not run" are different claims.

    Reporting the first as the second is what made every episode's trace read
    "Ask probe not selected by EVSI optimizer" directly above a chart showing the
    probability moving because a question had been answered.
    """
    from wha.service.pipeline import get_night_pipeline

    pipeline = get_night_pipeline("sim", date(2026, 9, 4), conn=seeded_db_with_untraced_episode)
    agentic = [s for s in pipeline.steps if s.layer == StepLayer.AGENTIC and s.ordinal > 8]
    assert all(s.status == StepStatus.UNRECORDED for s in agentic)


def test_the_headline_counts_what_actually_happened(seeded_db_with_episode) -> None:
    from wha.service.pipeline import get_night_pipeline

    pipeline = get_night_pipeline("sim", date(2026, 9, 4), conn=seeded_db_with_episode)
    head = pipeline.headline
    assert head.questions_asked >= 0
    assert head.sources_read == len({c.source_id for c in _all_sources(pipeline)})


def _all_sources(pipeline) -> list:
    return [c for step in pipeline.steps for c in step.sources]
```

Add the two new fixtures to `tests/unit/service/conftest.py` if that file exists, otherwise to the test module. `seeded_db_with_episode` inserts an episode, an `episode_traces` row listing the nodes that ran, interactions and an outcome. `seeded_db_with_untraced_episode` inserts the episode without the trace row.

- [ ] **Step 2: Run and watch them fail**

Run: `uv run pytest tests/unit/service/test_pipeline.py -v -k "episode or headline"`
Expected: FAIL, the agentic steps are absent

- [ ] **Step 3: Extend the module**

Add a private `_agentic_steps(detail: EpisodeDetail | None, flagged: bool) -> list[PipelineStepView]`:

- No episode and the night was not flagged: every agentic step is `NOT_APPLICABLE`, and `episode_open` carries the reason from the detection, phrased for a reader: no investigation opened because the night was not flagged.
- No episode and the night WAS flagged: `episode_open` is `UNRECORDED`. That combination means the detector flagged and no episode exists, which is a real fault and must be visible rather than smoothed over.
- Episode present, trace row present: map each `CANONICAL_STAGES` name to `RAN` or `SKIPPED` using `trace["nodes_ran"]`, exactly as `service.episodes._pipeline_stages` already does. Reuse that function rather than reimplementing the mapping.
- Episode present, no trace row: every agentic step is `UNRECORDED`.

`answer` (step 14, layer `user`) reads `interactions`: `RAN` when the person replied, `NOT_APPLICABLE` when no question was asked, `UNRECORDED` when a question was asked and no reply was stored.

`deliver` (step 18) reads `notifications` and the audit events for the episode.

The two safety steps read the safety check records and `triage_answers` for the night. Both are always present in the list with `status` reflecting whether they ran, because the safety floor runs on anything the person types, and a screen that hides it when it did not trigger teaches the wrong thing about when it applies.

`_headline(...)` assembles `PipelineHeadline` from the detection, the features, the belief and the citations already gathered. It counts distinct `Citation.source_id` values across all steps for `sources_read`, and counts `interactions` of kind question for `questions_asked`.

- [ ] **Step 4: Run and confirm green**

Run: `uv run pytest tests/unit/service/test_pipeline.py -v`
Expected: all pass

- [ ] **Step 5: Check it against the real investigated night**

Run:

```bash
uv run python -c "
from datetime import date
from wha.service.pipeline import get_night_pipeline
p = get_night_pipeline('sim', date(2026, 9, 4))
print(p.headline)
for s in p.steps:
    print(f'{s.ordinal:>2} {s.step_id:<20} {s.status.value:<15} {s.reason[:70]}')
"
```

Read every line. A reason that would confuse a non-technical reader is a defect in this task, not a polish item for later.

- [ ] **Step 6: Commit**

```bash
git add src/wha/service/pipeline.py tests/unit/service/test_pipeline.py
git commit -m "Add the agentic, user and safety steps to the night pipeline"
```

---

### Task 4: Endpoints and client

**Files:**
- Modify: `src/wha/api/app.py` (after the nights section, around line 175)
- Modify: `src/wha/api/client.py`
- Test: `tests/integration/test_api_pipeline.py` (create)

**Interfaces:**
- Consumes: `service.get_night_pipeline`, `service.list_pipeline_nights`
- Produces: `ApiClient.get_night_pipeline(subject_id, night_date) -> NightPipeline`, `ApiClient.list_pipeline_nights(subject_id, days=60) -> list[PipelineNightRef]`

- [ ] **Step 1: Write the failing test**

Follow the existing pattern in `tests/integration/` for building a `TestClient` over `wha.api.app`.

```python
def test_the_pipeline_endpoint_returns_every_step(api_client) -> None:
    response = api_client.get("/subjects/sim/nights/2026-09-04/pipeline")
    assert response.status_code == 200
    body = response.json()
    assert [s["ordinal"] for s in body["steps"]] == list(range(1, 21))
    assert body["headline"]["level"] in {"GREEN", "YELLOW", "RED", "NA"}


def test_an_unknown_night_is_a_404_not_a_500(api_client) -> None:
    """A client has to tell "no such thing" from "the application broke"."""
    response = api_client.get("/subjects/sim/nights/1999-01-01/pipeline")
    assert response.status_code == 404


def test_the_night_list_endpoint_is_small_enough_to_load_sixty_at_once(api_client) -> None:
    response = api_client.get("/subjects/sim/pipeline/nights?days=60")
    assert response.status_code == 200
    body = response.json()
    assert set(body[0]) == {"night_date", "level", "has_episode", "usable"}
```

- [ ] **Step 2: Run and watch it fail**

Run: `uv run pytest tests/integration/test_api_pipeline.py -v`
Expected: FAIL with 404 on every route

- [ ] **Step 3: Add the endpoints**

In `src/wha/api/app.py`, matching the thin pass-through style of every other endpoint:

```python
@app.get("/subjects/{subject_id}/nights/{night_date}/pipeline")
def get_night_pipeline(subject_id: str, night_date: date) -> Any:
    """One night's journey from watch to conclusion, step by step.

    Assembled from what was stored, so it cannot disagree with the detector, and a step
    with no recorded time is returned with no time rather than a plausible one.
    """
    try:
        return service.get_night_pipeline(subject_id, night_date)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/subjects/{subject_id}/pipeline/nights")
def list_pipeline_nights(
    subject_id: str, days: int = Query(default=60, ge=1, le=400)
) -> list[Any]:
    """Just enough about each night to draw the stepper: date, level, whether investigated."""
    return service.list_pipeline_nights(subject_id, days=days)
```

Route order matters in FastAPI. `/subjects/{subject_id}/pipeline/nights` must be declared before any route that would match `/subjects/{subject_id}/nights/{night_date}`; verify by running the test rather than by reasoning about it.

In `src/wha/api/client.py`, following the existing method style:

```python
def get_night_pipeline(self, subject_id: str, night_date: date) -> NightPipeline:
    """One night's journey. Returns the typed model, not a dict."""
    payload = self._request("GET", f"/subjects/{subject_id}/nights/{night_date}/pipeline")
    return NightPipeline.model_validate(payload)


def list_pipeline_nights(self, subject_id: str, days: int = 60) -> list[PipelineNightRef]:
    payload = self._request("GET", f"/subjects/{subject_id}/pipeline/nights", params={"days": days})
    return [PipelineNightRef.model_validate(row) for row in payload]
```

- [ ] **Step 4: Run and confirm green**

Run: `uv run pytest tests/integration/test_api_pipeline.py tests/ui/test_ui_boundary.py -v`
Expected: all pass. The boundary test includes a check that the client covers everything the screens call, so it runs here too.

- [ ] **Step 5: Record the contract gap**

`docs/CONTRACTS.md` is read-only and does not describe the new models. Append one entry to `BLOCKERS.md` in the file's existing format, stating that the contract does not list `NightPipeline`, `PipelineStepView`, `PipelineHeadline`, `PipelineNightRef` or `PipelineStepDef` because the contract is read-only, and that the drift test does not catch this because it only compares models the contract declares. This is a recorded limitation, not a task.

- [ ] **Step 6: Commit**

```bash
git add src/wha/api/app.py src/wha/api/client.py tests/integration/test_api_pipeline.py BLOCKERS.md
git commit -m "Serve the night pipeline over HTTP, so any front end can draw it"
```

---

### Task 5: Delete the old interface, build the new shell

**Files:**
- Delete: `src/wha/ui/{today,history,audit,settings}.py`, `src/wha/ui/components/{disclaimer,status_strip,subject_selector,belief_chart,episode_panel,pipeline_trace,wording}.py`, `tests/ui/test_{app_shell,audit,episode,history,history_page,settings,today}.py`
- Create: `src/wha/ui/design.py`, `src/wha/ui/explain.py`, `src/wha/ui/format.py`, `src/wha/ui/components/status_bar.py`, `tests/ui/conftest.py`
- Rewrite: `src/wha/ui/Home.py`
- Modify: `tests/unit/ui/test_wording_never_say.py`
- Test: `tests/ui/test_shell.py` (create)

**Interfaces:**
- Produces: `design.page_shell(title)`, `design.card(...)`, `design.chip(label, tone)`, `design.tile(label, value, note, tone)`, `explain.text(key) -> str`, `explain.KEYS`, `format.bpm(value)`, `format.gap(value)`, `format.probability(value)`, `format.local_time(client, moment)`, `status_bar.render(client, subject_id)`

- [ ] **Step 1: Read what you are deleting**

Before deleting each file, read its module docstring and comments. Several record real defects: a UTC hour shown to a person in Singapore, a sleep-window default that made a false statement on 44 of 72 nights, a tool-call expander populated from field names nothing ever wrote, and a benign-conclusion label that used a forbidden phrase. Write each lesson into a comment in the module that replaces it. Deleting a comment that records a defect is how the defect returns.

- [ ] **Step 2: Write the fake API fixture**

Create `tests/ui/conftest.py`:

```python
"""Every interface test runs the real script against a fake application.

`AppTest` runs the Streamlit script exactly as the browser does, so a page that crashes
on import fails here. Patching `wha.api.client.get_client` means no server, no database
and no network, while the screens still go through the same HTTP client they use in
production.
"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def fake_api(monkeypatch):
    client = MagicMock()
    client.config.return_value = {
        "today": "2026-09-05",
        "configured_subject": "sim",
        "DETECT_YELLOW_BPM": 3.0,
        "DETECT_RED_BPM": 4.0,
        "DETECT_PERSISTENCE_NIGHTS": 2,
        "BASELINE_MIN_NIGHTS_PERSONAL": 7,
        "RECENT_NIGHTS_WINDOW": 7,
    }
    monkeypatch.setattr("wha.api.client.get_client", lambda *a, **k: client)
    return client
```

Populate the return values of `client.get_system_status`, `client.list_nights` and the rest per test, with real `wha.models` instances rather than dicts, so a renamed field fails the test.

- [ ] **Step 3: Write the failing shell test**

Create `tests/ui/test_shell.py`:

```python
from streamlit.testing.v1 import AppTest


def test_the_home_page_renders_without_a_backend_error(fake_api) -> None:
    app = AppTest.from_file("src/wha/ui/Home.py", default_timeout=30).run()
    assert not app.exception


def test_home_says_what_the_system_cannot_do(fake_api) -> None:
    """The disclaimer is the point of this page, so its absence is a test failure."""
    app = AppTest.from_file("src/wha/ui/Home.py", default_timeout=30).run()
    body = " ".join(m.value for m in app.markdown).lower()
    assert "cannot diagnose" in body
    assert "emergency" in body


def test_every_explain_key_is_reachable() -> None:
    """Copy nobody can see is copy nobody maintains."""
    from wha.ui import explain

    for key in explain.KEYS:
        assert explain.text(key).strip(), key
```

- [ ] **Step 4: Run and watch it fail**

Run: `uv run pytest tests/ui/test_shell.py -v`
Expected: FAIL, the module and the keys do not exist

- [ ] **Step 5: Write design.py**

One `CSS` string and small helpers. Rules: no reliance on Streamlit's internal class names, all colours defined once as tokens, and every helper returns a string of HTML that a caller passes to `st.markdown(..., unsafe_allow_html=True)`. Tokens: level colours for GREEN, YELLOW, RED and NA, and layer colours for deterministic, agentic, user and safety, matching the spec's palette (green, blue, purple, red).

- [ ] **Step 6: Write explain.py**

A single dict `TEXT: dict[str, str]`, a tuple `KEYS`, and `text(key)`. Required keys, at minimum:

- one per canonical step id, in the form `step.<step_id>.what` and `step.<step_id>.why`
- one per `DetectionLevel` value: `level.GREEN`, `level.YELLOW`, `level.RED`, `level.NA`
- one per `BaselineRung` value
- one per metric shown on Today: `metric.rhr`, `metric.baseline`, `metric.band`, `metric.gap`, `metric.coverage`, `metric.window_source`
- `chart.how_to_read`, `home.what_it_is`, `home.can`, `home.cannot`, `home.emergency`, `home.judging`, `citation.what_this_means`

No value in this dict may contain a digit. A figure belongs to the API, not to the copy. Add a test asserting that.

- [ ] **Step 7: Write format.py, status_bar.py and Home.py**

`Home.py` renders, in the order given in the spec section 5.2, using `design` primitives and `explain` copy. It calls the client for the subject list, the status, and `/knowledge/provenance` for the honesty note. No figure is typed into the page.

`status_bar.render` produces the five statements of spec section 5.1. It keeps the fix recorded in the old `status_strip.py`: times are shown in the subject's local timezone via the client's `localise`, never as a raw UTC hour.

- [ ] **Step 8: Strengthen the never_say test**

Change `tests/unit/ui/test_wording_never_say.py` to sweep every value in `wha.ui.explain.TEXT` in addition to whatever tables remain, so new copy cannot escape the check.

- [ ] **Step 9: Run the interface tests**

Run: `uv run pytest tests/ui tests/unit/ui -v`
Expected: all pass, including the untouched boundary test

- [ ] **Step 10: Commit**

```bash
git add -A src/wha/ui tests/ui tests/unit/ui
git commit -m "Rewrite the dashboard shell: one place for styling, one for copy, one for formatting"
```

---

### Task 6: Today

**Files:**
- Create: `src/wha/ui/pages/1_Today.py`, `src/wha/ui/components/verdict.py`, `src/wha/ui/components/chat.py`
- Test: `tests/ui/test_today.py` (create fresh)

**Interfaces:**
- Consumes: `design`, `explain`, `format`, `ApiClient.get_night_detail`, `get_pending_interaction`, `get_episode`, `get_transcript`, `send_message`, `build_handover`
- Produces: `verdict.render(client, subject_id, detail)`, `chat.render(client, subject_id, episode_id)`

- [ ] **Step 1: Write the failing tests**

Create `tests/ui/test_today.py`. `_night_detail(**overrides)` is a local helper building a real
`NightDetail` with `NightRow`, `NightlyFeatures`, `Baseline` and `Detection` instances, so a
renamed field fails the test rather than passing through a dict.

```python
"""Today, as the person meets it: what happened last night, and where that came from."""

from datetime import UTC, date, datetime

from streamlit.testing.v1 import AppTest

from wha.models import (
    AnswerOption,
    Baseline,
    BaselineRung,
    Detection,
    DetectionLevel,
    Forecast,
    NightDetail,
    NightRow,
    NightlyFeatures,
    PendingInteraction,
    Probe,
    Question,
)

PAGE = "src/wha/ui/pages/1_Today.py"


def _night_detail(
    level: DetectionLevel = DetectionLevel.GREEN,
    rhr: float | None = 52.0,
    window_source: str = "sleep",
) -> NightDetail:
    night = date(2026, 9, 4)
    return NightDetail(
        row=NightRow(
            night_date=night,
            rhr_bpm=rhr,
            centre_bpm=45.0,
            band_lo=39.0,
            band_hi=51.0,
            deviation_bpm=7.0,
            explained_bpm=1.2,
            residual_bpm=5.8,
            coverage_minutes=331,
            usable=rhr is not None,
            level=level,
            rhr_window_source=window_source,
        ),
        features=NightlyFeatures(
            subject_id="sim",
            night_date=night,
            rhr_bpm=rhr,
            coverage_minutes=331,
            usable=rhr is not None,
            sleep_hours=6.9,
            rhr_window_source=window_source,
        ),
        baseline=Baseline(
            centre_bpm=45.0,
            scale_bpm=6.0,
            usable_nights=28,
            rung=BaselineRung.MATURE,
            shrink_weight=0.0,
        ),
        detection=Detection(
            subject_id="sim",
            night_date=night,
            deviation_bpm=7.0,
            level=level,
            flagged=level is DetectionLevel.RED,
            forecast=Forecast(),
        ),
    )


def _question() -> PendingInteraction:
    return PendingInteraction(
        kind="question",
        episode_id="ep_1",
        question=Question(
            probe=Probe(probe_id="fever", text="Any illness symptoms yesterday?"),
            text="Any illness symptoms yesterday?",
            options=[
                AnswerOption(option_id="yes", label="Yes"),
                AnswerOption(option_id="no", label="No"),
            ],
        ),
    )


def test_a_pending_question_comes_before_last_night(fake_api) -> None:
    """Anything needing the person outranks anything reporting to them."""
    fake_api.get_pending_interaction.return_value = _question()
    fake_api.get_night_detail.return_value = _night_detail()

    app = AppTest.from_file(PAGE, default_timeout=30).run()

    rendered = [m.value for m in app.markdown]
    question_at = next(i for i, t in enumerate(rendered) if "illness symptoms" in t)
    verdict_at = next(i for i, t in enumerate(rendered) if "Last night" in t)
    assert question_at < verdict_at


def test_the_verdict_shows_the_level_the_system_recorded(fake_api) -> None:
    """The screen and the record must use the same word for the same night."""
    fake_api.get_pending_interaction.return_value = None
    fake_api.get_night_detail.return_value = _night_detail(level=DetectionLevel.RED)

    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert not app.exception
    assert "RED" in " ".join(m.value for m in app.markdown)


def test_every_number_on_the_verdict_card_has_an_explanation(fake_api) -> None:
    """A number with no explanation is the defect this rewrite exists to fix."""
    from wha.ui import explain

    fake_api.get_pending_interaction.return_value = None
    fake_api.get_night_detail.return_value = _night_detail()

    app = AppTest.from_file(PAGE, default_timeout=30).run()
    body = " ".join(m.value for m in app.markdown)

    for key in ("metric.rhr", "metric.baseline", "metric.gap"):
        assert explain.text(key) in body, key


def test_a_night_measured_over_the_clock_fallback_says_so(fake_api) -> None:
    """Never assert "because no sleep was recorded" on a night that recorded sleep."""
    fake_api.get_pending_interaction.return_value = None
    fake_api.get_night_detail.return_value = _night_detail(window_source="sleep")

    app = AppTest.from_file(PAGE, default_timeout=30).run()
    body = " ".join(m.value for m in app.markdown).lower()

    assert "no sleep was recorded" not in body


def test_the_doctor_summary_shows_what_it_will_copy(fake_api) -> None:
    """A copy button that sends something the person never saw is not one they consented to."""
    fake_api.get_pending_interaction.return_value = None
    fake_api.get_night_detail.return_value = _night_detail()
    fake_api.build_handover.return_value = {
        "text": "SITUATION: raised resting heart rate over two nights.",
        "situation": "raised resting heart rate over two nights",
        "background": "",
        "assessment": "",
        "recommendation": "",
        "questions": [],
        "what_this_is_not": "",
    }

    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert any("SITUATION" in block.value for block in app.code)
```

If the `Question` or `PendingInteraction` field names differ from those shown, read `src/wha/models.py` and use the
real ones; the point of building real models here is that this cannot be guessed.

- [ ] **Step 2: Run and watch them fail**

Run: `uv run pytest tests/ui/test_today.py -v`

- [ ] **Step 3: Build the page**

Spec section 5.3, in that order. Specific requirements:

- The level chip uses the system's own word (GREEN, YELLOW, RED) with the plain sentence from `explain.text(f"level.{level}")` beneath it.
- Three numbers side by side: your reading, your normal with its band, the gap. Each with its `metric.*` explanation and a link that sets `st.session_state["pipeline_night"]` and switches to the Audit page via `st.switch_page`.
- Coverage and window source in words, from the night detail, never defaulted.
- The doctor summary block renders the handover text and one Copy button. Streamlit has no clipboard API: use `st.code(text)`, whose built-in copy control is a real one-click copy, and say in one line what the button copies.

- [ ] **Step 4: Run tests and confirm green**

Run: `uv run pytest tests/ui/test_today.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/wha/ui/pages/1_Today.py src/wha/ui/components/verdict.py src/wha/ui/components/chat.py tests/ui/test_today.py
git commit -m "Rewrite Today around one verdict, three numbers, and where each came from"
```

---

### Task 7: Citations that can be inspected

**Files:**
- Rewrite: `src/wha/ui/components/citations.py`
- Test: `tests/unit/ui/test_citation_labels.py` (extend)

**Interfaces:**
- Produces: `citations.chip(citation, key)`, `citations.drawer(citation)`

- [ ] **Step 1: Write the failing test**

```python
def test_the_drawer_shows_the_whole_passage_not_only_the_quote() -> None:
    """Grounding that cannot be inspected is a badge, not evidence."""


def test_the_quoted_span_is_highlighted_inside_the_passage() -> None:


def test_a_quote_absent_from_its_passage_is_reported_rather_than_highlighted() -> None:
    """The grounding check proves the span exists. If it does not, say so loudly."""
```

- [ ] **Step 2: Run and watch it fail**

Run: `uv run pytest tests/unit/ui/test_citation_labels.py -v`

- [ ] **Step 3: Implement**

`chip` renders a small clickable marker carrying the source title. `drawer` renders the full `Citation.passage` with the quoted span wrapped in a highlight span, the document title, and the provenance tag from `/knowledge/provenance` where the source has one. When the quote is not a substring of the passage, render the passage unhighlighted with a plain warning that the quote could not be located in the passage. That is the known open limitation in `BLOCKERS.md` and the screen states it rather than hiding it.

- [ ] **Step 4: Run and confirm green**

Run: `uv run pytest tests/unit/ui -v`

- [ ] **Step 5: Commit**

```bash
git add src/wha/ui/components/citations.py tests/unit/ui/test_citation_labels.py
git commit -m "Let a citation be opened and read, and say when the quote cannot be located"
```

---

### Task 8: History

**Files:**
- Create: `src/wha/ui/pages/2_History.py`, `src/wha/ui/components/night_chart.py`
- Test: `tests/ui/test_history.py` (create fresh)

**Interfaces:**
- Consumes: `ApiClient.list_nights`, `ApiClient.list_episodes`, `design`, `explain`, `format`
- Produces: `night_chart.chart_frame(rows: list[NightRow]) -> pandas.DataFrame` and
  `night_chart.render(rows: list[NightRow])`. The frame is separate from the drawing so the
  handling of a missing night can be tested without rendering a chart

- [ ] **Step 1: Write the failing tests**

```python
"""History: sixty nights that a person can actually read."""

from datetime import date

from streamlit.testing.v1 import AppTest

from wha.models import DetectionLevel, NightRow

PAGE = "src/wha/ui/pages/2_History.py"


def _rows() -> list[NightRow]:
    return [
        NightRow(
            night_date=date(2026, 9, 1),
            rhr_bpm=46.0,
            centre_bpm=45.0,
            band_lo=39.0,
            band_hi=51.0,
            deviation_bpm=1.0,
            coverage_minutes=340,
            usable=True,
            level=DetectionLevel.GREEN,
        ),
        NightRow(
            night_date=date(2026, 9, 2),
            coverage_minutes=0,
            usable=False,
            level=DetectionLevel.NA,
        ),
        NightRow(
            night_date=date(2026, 9, 3),
            rhr_bpm=52.0,
            centre_bpm=45.0,
            band_lo=39.0,
            band_hi=51.0,
            deviation_bpm=7.0,
            coverage_minutes=331,
            usable=True,
            level=DetectionLevel.RED,
            episode_id="ep_1",
        ),
    ]


def test_the_chart_has_a_caption_naming_every_element_on_it(fake_api) -> None:
    """A chart nobody can read is decoration."""
    from wha.ui import explain

    fake_api.list_nights.return_value = _rows()
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    captions = " ".join(c.value for c in app.caption)
    assert explain.text("chart.how_to_read") in captions


def test_a_night_with_no_reading_is_a_gap_not_a_zero(fake_api) -> None:
    """A missing night drawn at zero reads as a heart rate of zero."""
    from wha.ui.components.night_chart import chart_frame

    frame = chart_frame(_rows())
    missing = frame[frame["night_date"] == date(2026, 9, 2)].iloc[0]
    assert missing["rhr_bpm"] != 0
    assert missing["rhr_bpm"] is None or str(missing["rhr_bpm"]) == "nan"


def test_the_table_shows_the_investigation_outcome_in_words(fake_api) -> None:
    """The point of the column is the result, not that a row exists."""
    fake_api.list_nights.return_value = _rows()
    fake_api.list_episodes.return_value = []
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert not app.exception
    assert app.dataframe, "the night table did not render"
    assert "Investigated" in list(app.dataframe[0].value.columns)


def test_the_full_field_view_is_off_by_default(fake_api) -> None:
    """The default view is what the person needs; everything else is behind one toggle."""
    fake_api.list_nights.return_value = _rows()
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    toggles = [t for t in app.toggle]
    assert toggles, "no control for showing every recorded field"
    assert all(t.value is False for t in toggles)
```

- [ ] **Step 2: Run and watch them fail**

Run: `uv run pytest tests/ui/test_history.py -v`

- [ ] **Step 3: Build the page**

Spec section 5.4. The chart is Altair, already a dependency. Baseline band as an area mark behind a line mark, points coloured by level, missing nights as gaps rather than zeros or interpolations. The caption names the line, the band and the dot colours in one sentence each.

- [ ] **Step 4: Run and confirm green**

Run: `uv run pytest tests/ui/test_history.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/wha/ui/pages/2_History.py src/wha/ui/components/night_chart.py tests/ui/test_history.py
git commit -m "Rewrite History around one readable chart and six columns"
```

---

### Task 9: Audit, the pipeline view

**Files:**
- Create: `src/wha/ui/pages/3_Audit.py`, `src/wha/ui/components/pipeline_graph.py`, `src/wha/ui/components/step_detail.py`
- Test: `tests/ui/test_audit_pipeline.py` (create)

**Interfaces:**
- Consumes: `ApiClient.get_night_pipeline`, `ApiClient.list_pipeline_nights`
- Produces: `pipeline_graph.render(pipeline) -> str | None` returning the clicked step id, `step_detail.render(client, pipeline, step_id)`

- [ ] **Step 1: Write the failing tests**

```python
"""The pipeline view: every step of one night, and an honest gap where nothing was recorded."""

from datetime import date

from streamlit.testing.v1 import AppTest

from wha.models import (
    CANONICAL_PIPELINE_STEPS,
    DetectionLevel,
    NightPipeline,
    PipelineHeadline,
    PipelineNightRef,
    PipelineStepView,
    StepStatus,
)

PAGE = "src/wha/ui/pages/3_Audit.py"


def _pipeline(status_overrides: dict[str, StepStatus] | None = None) -> NightPipeline:
    overrides = status_overrides or {}
    return NightPipeline(
        subject_id="sim",
        night_date=date(2026, 9, 4),
        episode_id="ep_1",
        headline=PipelineHeadline(
            level=DetectionLevel.RED,
            flagged=True,
            sleep_hours=6.9,
            coverage_minutes=331,
            questions_asked=1,
            sources_read=14,
        ),
        steps=[
            PipelineStepView(
                step_id=definition.step_id,
                ordinal=definition.ordinal,
                layer=definition.layer,
                status=overrides.get(definition.step_id, StepStatus.RAN),
                reason=f"reason for {definition.step_id}",
            )
            for definition in CANONICAL_PIPELINE_STEPS
        ],
    )


def _nights() -> list[PipelineNightRef]:
    return [
        PipelineNightRef(
            night_date=date(2026, 9, 4),
            level=DetectionLevel.RED,
            has_episode=True,
            usable=True,
        )
    ]


def test_every_step_the_service_returns_is_drawn(fake_api) -> None:
    """A step the page silently drops is a step nobody can audit."""
    fake_api.list_pipeline_nights.return_value = _nights()
    fake_api.get_night_pipeline.return_value = _pipeline()

    app = AppTest.from_file(PAGE, default_timeout=30).run()

    labels = " ".join(b.label for b in app.button)
    for definition in CANONICAL_PIPELINE_STEPS:
        assert definition.step_id in labels or str(definition.ordinal) in labels


def test_a_step_that_did_not_run_shows_its_real_reason(fake_api) -> None:
    fake_api.list_pipeline_nights.return_value = _nights()
    fake_api.get_night_pipeline.return_value = _pipeline({"ask": StepStatus.SKIPPED})

    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert "reason for ask" in " ".join(m.value for m in app.markdown)


def test_an_unrecorded_step_does_not_claim_it_was_skipped(fake_api) -> None:
    """"We did not write it down" and "it did not run" are different claims."""
    fake_api.list_pipeline_nights.return_value = _nights()
    fake_api.get_night_pipeline.return_value = _pipeline({"believe": StepStatus.UNRECORDED})

    app = AppTest.from_file(PAGE, default_timeout=30).run()
    body = " ".join(m.value for m in app.markdown)

    unrecorded_block = body[body.index("reason for believe") - 200 : body.index("reason for believe")]
    assert "skipped" not in unrecorded_block.lower()
    assert "not recorded" in unrecorded_block.lower()


def test_clicking_a_step_opens_its_detail(fake_api) -> None:
    fake_api.list_pipeline_nights.return_value = _nights()
    fake_api.get_night_pipeline.return_value = _pipeline()

    app = AppTest.from_file(PAGE, default_timeout=30).run()
    believe_button = next(b for b in app.button if "believe" in b.label or "11" in b.label)
    believe_button.click().run()

    assert app.session_state["pipeline_step"] == "believe"


def test_no_step_card_shows_a_time_the_pipeline_did_not_carry(fake_api) -> None:
    """Every step in this fixture has occurred_utc unset, so no clock time may appear."""
    import re

    fake_api.list_pipeline_nights.return_value = _nights()
    fake_api.get_night_pipeline.return_value = _pipeline()

    app = AppTest.from_file(PAGE, default_timeout=30).run()
    body = " ".join(m.value for m in app.markdown)

    assert not re.search(r"\b\d{2}:\d{2}\b", body)


def test_every_step_id_has_copy() -> None:
    """A step cannot ship unexplained."""
    from wha.models import CANONICAL_PIPELINE_STEPS
    from wha.ui import explain

    for step in CANONICAL_PIPELINE_STEPS:
        assert explain.text(f"step.{step.step_id}.what")
        assert explain.text(f"step.{step.step_id}.why")
```

- [ ] **Step 2: Run and watch them fail**

Run: `uv run pytest tests/ui/test_audit_pipeline.py -v`

- [ ] **Step 3: Build the graph**

Layout: four rows of five `st.columns`, each cell a step card. A card is one `st.button` with a label carrying the number and the name, immediately followed by a styled `st.markdown` block carrying the layer colour, the key figure and the timestamp where one exists. Clicking sets `st.session_state["pipeline_step"]`. The two safety steps render in a separate bordered block to the right of the grid, labelled always on. Steps whose status is not `RAN` are dimmed by the layer token's muted variant and carry their reason under the name.

The night stepper is previous and next buttons plus a selectbox populated from `list_pipeline_nights`, defaulting to `st.session_state["pipeline_night"]` when Today linked here, otherwise the most recent night.

- [ ] **Step 4: Build the detail panel**

Sections in this order: What happened, Why, What drove this, The numbers, Sources read, Raw record. "The numbers" states the arithmetic in words, taking the values from the step's `inputs` and `outputs`. "Sources read" uses the citation drawer from Task 7. "Raw record" is an expander over `detail_json`, collapsed.

- [ ] **Step 5: Run and confirm green**

Run: `uv run pytest tests/ui/test_audit_pipeline.py -v`

- [ ] **Step 6: Commit**

```bash
git add src/wha/ui/pages/3_Audit.py src/wha/ui/components/pipeline_graph.py src/wha/ui/components/step_detail.py tests/ui/test_audit_pipeline.py
git commit -m "Draw the whole night as clickable steps, including the nights nothing happened"
```

---

### Task 10: Audit, the record and the explainer

**Files:**
- Modify: `src/wha/ui/pages/3_Audit.py`
- Test: `tests/ui/test_audit_record.py` (create)

- [ ] **Step 1: Write the failing tests**

```python
"""The record tab: what the system did, and whether the record can still be trusted."""

from datetime import UTC, datetime

from streamlit.testing.v1 import AppTest

from wha.models import AuditEventView

PAGE = "src/wha/ui/pages/3_Audit.py"


def _event(operation: str = "ingest", actor: str = "system") -> AuditEventView:
    return AuditEventView(
        event_id="evt_1",
        timestamp_utc=datetime(2026, 9, 4, 7, 12, tzinfo=UTC),
        actor=actor,
        operation=operation,
        hash_ok=True,
    )


def test_an_empty_record_is_distinguished_from_a_broken_one(fake_api) -> None:
    """An empty page and a failed query must never look the same in a health system."""
    fake_api.query_audit.return_value = []
    fake_api.count_audit_events.return_value = 0
    fake_api.verify_hash_chain.return_value = (True, None)

    app = AppTest.from_file(PAGE, default_timeout=30).run()
    body = " ".join(m.value for m in app.markdown) + " ".join(i.value for i in app.info)

    assert "nothing has been recorded" in body.lower()


def test_a_broken_hash_chain_is_stated_at_the_top(fake_api) -> None:
    """If the record may have been altered, that outranks everything else on the page."""
    fake_api.query_audit.return_value = [_event()]
    fake_api.count_audit_events.return_value = 1
    fake_api.verify_hash_chain.return_value = (False, "evt_1")

    app = AppTest.from_file(PAGE, default_timeout=30).run()

    assert app.error, "a broken chain rendered without an error"
    assert "evt_1" in " ".join(e.value for e in app.error)


def test_the_filters_narrow_the_events_the_page_asked_for(fake_api) -> None:
    """The filter must reach the application, not be applied to an already-truncated page."""
    fake_api.query_audit.return_value = [_event(operation="nightly")]
    fake_api.count_audit_events.return_value = 1
    fake_api.verify_hash_chain.return_value = (True, None)

    app = AppTest.from_file(PAGE, default_timeout=30).run()
    operation = next(s for s in app.selectbox if "operation" in s.label.lower())
    operation.select("nightly").run()

    sent = fake_api.query_audit.call_args.args[0]
    assert sent.operation == "nightly"
```

- [ ] **Step 2: Run and watch them fail**

Run: `uv run pytest tests/ui/test_audit_record.py -v`

- [ ] **Step 3: Build both tabs**

Tab two is the hash-chained record: integrity statement first, then filters for actor, operation, episode and date, then the events, then the export. Keep the existing behaviour where an empty record says so explicitly rather than rendering nothing.

Tab three carries the eight explainer sections that exist in the current `ui/audit.py` today. Read them before deleting that file, keep their content, and rewrite them into `explain.py` keys so they sit with the rest of the copy.

- [ ] **Step 4: Run and confirm green**

Run: `uv run pytest tests/ui/test_audit_record.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/wha/ui/pages/3_Audit.py src/wha/ui/explain.py tests/ui/test_audit_record.py
git commit -m "Keep the tamper-evident record and the system explainer alongside the pipeline"
```

---

### Task 11: Settings

**Files:**
- Create: `src/wha/ui/pages/4_Settings.py`
- Test: `tests/ui/test_settings.py` (create fresh)

- [ ] **Step 1: Write the failing tests**

```python
"""Settings: everything configurable, present and explained."""

from streamlit.testing.v1 import AppTest

PAGE = "src/wha/ui/pages/4_Settings.py"

# Fields the application holds that a person has no business editing from a screen.
# Each one needs a reason, and the reason is checked by a reader, not by the test.
NOT_USER_EDITABLE = {
    "db_path",  # changing where the record lives is an installation decision
    "data_dir",
}


def test_every_settings_field_the_application_accepts_has_a_control(fake_api) -> None:
    """A setting with no control is a setting nobody can change.

    Enumerated from the model rather than listed by hand, so a field added to the
    application fails this test until the screen grows a control for it.
    """
    from wha.models import Settings

    fake_api.get_service_settings.return_value = Settings()

    app = AppTest.from_file(PAGE, default_timeout=30).run()
    labels = " ".join(
        [w.label for w in app.text_input]
        + [w.label for w in app.number_input]
        + [w.label for w in app.selectbox]
        + [w.label for w in app.toggle]
    ).lower()

    missing = [
        field
        for field in Settings.model_fields
        if field not in NOT_USER_EDITABLE and field.replace("_", " ") not in labels
    ]
    assert not missing, f"settings with no control: {missing}"


def test_every_control_says_what_it_changes(fake_api) -> None:
    """A field with no consequence stated is a field a person cannot decide about."""
    from wha.models import Settings

    fake_api.get_service_settings.return_value = Settings()

    app = AppTest.from_file(PAGE, default_timeout=30).run()

    controls = list(app.text_input) + list(app.number_input) + list(app.selectbox)
    assert controls
    assert all(getattr(control, "help", None) for control in controls)


def test_delete_everything_names_what_it_deletes_before_it_runs(fake_api) -> None:
    """This function once reported success and deleted nothing.

    It is the highest-stakes control on the screen. The confirmation states what goes,
    and the call only happens after the confirmation.
    """
    app = AppTest.from_file(PAGE, default_timeout=30).run()

    delete = next(b for b in app.button if "delete" in b.label.lower())
    delete.click().run()

    assert fake_api.delete_all_subject_data.call_count == 0
    body = " ".join(m.value for m in app.markdown) + " ".join(w.value for w in app.warning)
    assert "heart rate" in body.lower()
```

If `Settings` does not expose the field names this test assumes, read `src/wha/models.py` and
use the real ones. Guessing the field list is the failure this test exists to prevent.

- [ ] **Step 2: Run and watch them fail**

Run: `uv run pytest tests/ui/test_settings.py -v`

- [ ] **Step 3: Build the page**

Spec section 5.6. Groups in order: About you, Where readings come from, The AI model, How you get asked, How often, Delete everything. Each control carries one line naming what it changes about the system's behaviour. Connection test buttons keep their existing behaviour, including testing typed but unsaved values through `/diagnostics/{component}`.

- [ ] **Step 4: Run and confirm green**

Run: `uv run pytest tests/ui/test_settings.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/wha/ui/pages/4_Settings.py tests/ui/test_settings.py
git commit -m "Rewrite Settings so every configurable field is present and explained"
```

---

### Task 12: Drive the real interface with Playwright MCP

A green suite proves almost nothing here. Every serious defect in this project's history was found by opening the dashboard and using it. This task is where the work is actually verified.

**Files:**
- Create: `docs/superpowers/plans/walkthrough-2026-09-06.md`

- [ ] **Step 1: Start the application against the disposable subject**

```bash
uv run wha serve
```

Confirm `.env` points at subject `sim` before starting. Never run this walkthrough against subject `me`.

- [ ] **Step 2: Drive every screen with the Playwright MCP tools**

Use `mcp__playwright__browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type` and `browser_take_screenshot`. Snapshot before each interaction, since refs are invalidated by navigation. Take a screenshot of each screen and LOOK at it. A blank frame is a failure, not a slow render.

The walkthrough, as an ordinary person would do it:

1. Home. Read it start to finish. Can someone with no background say what this does and what it cannot do?
2. Top bar. Does every statement mean something without internal vocabulary?
3. Today. Read the verdict. Click each "where this came from" link and confirm it lands on the right night in the pipeline.
4. Today. Ask the chat two questions, one it can ground and one it cannot. Open a citation. Confirm the passage opens and the quote is highlighted.
5. Today. Click the doctor summary copy control. Confirm what it copies is what is shown.
6. History. Read the chart caption, then the chart. Change the window. Filter to investigated nights. Open one from the table.
7. Audit, pipeline. Step through at least three nights: an investigated one, a quiet one, and one with no reading. Click every step on the investigated night and read all twenty panels.
8. Audit, record. Filter by actor and by operation. Export.
9. Audit, explainer. Read all eight sections.
10. Settings. Change one harmless value, save, reload, confirm it stuck. Run each connection test. Do NOT use Delete everything.

- [ ] **Step 3: Write down every finding before fixing anything**

Create `docs/superpowers/plans/walkthrough-2026-09-06.md` with one entry per finding: what you did, what you expected, what happened, and the screenshot filename. Findings first, fixes second. Fixing while walking is how a walkthrough ends with three findings instead of twelve.

- [ ] **Step 4: Fix the findings**

Each fix gets a test that fails before it and passes after, unless the finding is purely cosmetic, in which case say so in the log.

- [ ] **Step 5: Walk it again from a fresh start**

Stop the server, restart it, clear the browser state, and repeat step 2 in full. A fix verified only in the session that made it is not verified. Record the second pass in the same document.

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/plans/walkthrough-2026-09-06.md src tests
git commit -m "Fix what using the dashboard found, and record both walkthroughs"
```

---

### Task 13: Full verification and documentation

- [ ] **Step 1: Run everything**

```bash
uv run pytest
uv run ruff check src tests
uv run ruff format --check src tests
uv run wha doctor
```

Expected: no failures, no fail rows. Put the actual counts in the commit message, not remembered ones.

- [ ] **Step 2: Confirm the boundary still holds**

Run: `uv run pytest tests/ui/test_ui_boundary.py -v`

This is the test that keeps a React port possible. If the rewrite weakened it, that is a defect in the rewrite, not in the test.

- [ ] **Step 3: Update STATUS.md**

Append what changed, what was verified, and the date. Keep the file's existing shape: a table of checks with their results, all re-run rather than remembered.

- [ ] **Step 4: Commit**

```bash
git add STATUS.md
git commit -m "Record the dashboard overhaul and what was verified"
```

---

## Self-review against the spec

| Spec section | Task |
|---|---|
| 4.1 pipeline service | 1, 2, 3 |
| 4.2 endpoints | 4 |
| 4.3 UI layer structure | 5 |
| 5.1 top bar | 5 |
| 5.2 Home | 5 |
| 5.3 Today | 6, 7 |
| 5.4 History | 8 |
| 5.5 Audit | 9, 10 |
| 5.6 Settings | 11 |
| 6 testing | every task, and 12 |
| 7 risks | 5 step 1 (lost detail), 2 and 3 (misreporting), 5 step 5 (CSS) |
