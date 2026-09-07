# Dashboard overhaul: a screen an ordinary person can read

**Date:** 6 September 2026
**Status:** approved design, not yet implemented
**Scope:** `src/wha/ui/` is deleted and rewritten. One new read-only service module and two
new endpoints support it. No behaviour in the deterministic half, the agentic half or the
safety floor changes.

---

## 1. The problem

The dashboard is correct and nearly unreadable to the person it is for. It states results
without saying what produced them, uses the system's internal vocabulary as its labels, and
keeps its best material (the execution trace, the safety floor, the provenance of every
clinical figure) behind expanders that read like developer output.

The person using this system has no engineering and no medical background. For every number
on screen they should be able to answer, without leaving the page: what is this, where did it
come from, how was it worked out, and what should I do about it. Nothing on screen may make a
claim the system cannot support.

## 2. What is being built

A full rewrite of the five screens, with a sixth capability added: a per-night pipeline view
that shows the whole journey from watch to conclusion, step by step, for **every** night, not
only investigated ones.

The design reference is a mockup supplied by the user showing a numbered step graph with a
detail panel. Two elements of that mockup are deliberately not built: a Share button (this
system has no sharing, and adding one to a health record is a decision nobody has made) and an
Evidence Library page (a browsable clinical corpus edges this toward being a medical
reference, which it is not).

## 3. Decisions taken, with their reasons

| Decision | Choice | Why |
|---|---|---|
| Pipeline data | Reconstruct steps 1 to 7 at read time, read steps 8 to 18 from the stored episode trace | Every past night gets a pipeline, including quiet nights and everything already recorded for subject `me`. No schema change, no new writes in the nightly path |
| Timestamps | Shown only where a row actually recorded one (`computed_at_utc`, audit events) | The alternative is inventing a clock time, which this project does not do |
| Theme | Light | User decision. Read in daylight, and charts of a health record are easier to judge on white |
| Explanatory copy | Lives in the Streamlit layer, in one module | User decision. Prose is presentation. The constraint is that copy carries no figures: every number arrives from the API |
| Night labels | Keep GREEN / YELLOW / RED, add a plain sentence under each | These are the system's own labels, so the screen and the record agree. "Healthy" and "sick" are claims the system cannot make |
| Doctor summary | Copy to clipboard | User decision |
| Citations | Quoted span inline, full passage on click with the quote highlighted | Grounding that cannot be inspected is a badge, not evidence |
| Screen size | Desktop only | User decision |
| Graph rendering | Clickable HTML and CSS step cards | The value of the mockup is that a step can be clicked. A static diagram loses that |

## 4. Architecture

```
wha.service.pipeline      NEW. Assembles one night's journey from stored data
wha.api.app               NEW endpoints, thin pass-through as every other endpoint is
wha.api.client            NEW client methods
wha.ui.*                  DELETED and rewritten
```

Everything else is untouched.

### 4.1 The pipeline service

`src/wha/service/pipeline.py` exposes:

```python
def get_night_pipeline(subject_id: str, night_date: date) -> NightPipeline
def list_pipeline_nights(subject_id: str, days: int = 60) -> list[PipelineNightRef]
```

`NightPipeline` (new, in `wha/models.py`) carries:

- `night_date`, `level`, `episode_id | None`
- `headline`: the five tile values (result, primary driver and its probability, sleep hours
  and coverage, questions asked, sources read). Every one of these is already computed
  somewhere; this assembles them rather than recalculating them.
- `steps: list[PipelineStepView]`

`PipelineStepView` carries: `step_id`, `ordinal`, `layer` (`deterministic` / `agentic` /
`user` / `safety`), `status` (`ran` / `skipped` / `not_applicable` / `unrecorded`),
`headline_figure` (one short string, or none), `occurred_utc | None`, `reason`,
`inputs: dict`, `outputs: dict`, `sources: list[Citation]`, `detail_json: dict`.

**Canonical steps.** The agentic ids reuse `CANONICAL_STAGES` exactly, so the system has one
vocabulary rather than two:

| # | id | layer | Reconstructed from |
|---|---|---|---|
| 1 | `collect` | deterministic | `raw_payloads`, ingest audit events, `system_status` |
| 2 | `store` | deterministic | `heart_rate_samples` count for the night, `sleep_stages` |
| 3 | `sleep_window` | deterministic | `nightly_features.rhr_window_source`, `sleep_hours` |
| 4 | `features` | deterministic | `nightly_features`, including `computed_at_utc` |
| 5 | `baseline` | deterministic | `baselines` row: centre, scale, usable nights, rung |
| 6 | `subtract_explained` | deterministic | `NightRow.explained_bpm`, exercise session |
| 7 | `detect` | deterministic | `detections` row: level, persistence, whether flagged |
| 8 | `episode_open` | agentic | `episodes` row, or "no investigation, and why" |
| 9 | `preload` | agentic | episode trace |
| 10 | `investigate` | agentic | episode trace, tool calls |
| 11 | `believe` | agentic | `beliefs`, belief history |
| 12 | `decide` | agentic | trace, EVSI value and chosen action |
| 13 | `ask` | agentic | `interactions` |
| 14 | `answer` | user | `interactions`, `triage_answers` |
| 15 | `conclude` | agentic | `outcomes`, citations |
| 16 | `critique` | agentic | trace `stripped_claims` |
| 17 | `review` | agentic | human decision recorded on the outcome |
| 18 | `deliver` | agentic | `notifications`, audit events |
| S1 | `safety_phrase_rules` | safety | safety check records for the night |
| S2 | `safety_triage` | safety | `triage_answers`, Marburg score |

A step with no stored evidence is `unrecorded` with the reason "the system did not write this
down", never `skipped`. Those are different claims, and conflating them is what the September
2026 audit found on every episode.

### 4.2 Endpoints

```
GET /subjects/{subject_id}/nights/{night_date}/pipeline   -> NightPipeline
GET /subjects/{subject_id}/pipeline/nights?days=N         -> [PipelineNightRef]
```

The second exists so the night stepper can be populated without pulling sixty full pipelines.
Both are thin pass-throughs, matching the rule stated at the top of `api/app.py`. New client
methods mirror them in `api/client.py`.

### 4.3 The UI layer, rewritten

```
src/wha/ui/
  Home.py               entry point, shell, navigation
  pages/
    today.py            last night, chat, doctor summary
    history.py          the chart and the night table
    audit.py            pipeline, record, how it works
    settings.py         configuration
  design.py             CSS tokens and layout primitives (card, tile, chip, step)
  explain.py            ALL explanatory copy, keyed by id. No figures
  format.py             turning API values into display strings
  components/
    status_bar.py       the top bar
    verdict.py          the GREEN / YELLOW / RED card
    citations.py        citation chip and passage drawer
    night_chart.py      the history chart
    pipeline_graph.py   the step grid
    step_detail.py      the right-hand panel
    chat.py             the conversation
```

Two rules carried over from the existing tests, both kept and both strengthened:

- No module under `src/wha/ui/` may import anything from `wha` other than `wha.api`,
  `wha.models` and `wha.ui`. The rewrite does not weaken this.
- No string the interface ships may appear on the `never_say` list in
  `data/knowledge/red_flags.yaml`. Today that test checks four dictionaries. It will check
  every string constant in `explain.py`, so new copy cannot escape it.

## 5. The screens

### 5.1 Top bar

One line, five plain statements, each about what it means for the person rather than what
failed internally:

```
Watch data: arrived 07:12 today   |   Your normal: well established, 28 nights
Nightly check: ran 02:30, next about 02:30   |   AI model: reachable
Questions reach you on: Telegram
```

Amber or red when a component is degraded, with the sentence saying what stops working as a
result. The subject selector and a one-word overall state sit at the left.

### 5.2 Home

Not a README. In order:

1. What this is, in two sentences.
2. If you feel unwell right now, this block first: contact a clinician or emergency services,
   do not wait for this system.
3. What it can do. Three bullets.
4. What it cannot do. Four bullets, including: it cannot diagnose, it sees only heart rate,
   sleep and what you tell it, nobody is watching it on your behalf, and it can be wrong.
5. How a night gets judged, in five sentences, ending with a link into the pipeline.
6. Four navigation cards, each phrased as the question that page answers.
7. An honesty note: how many clinical figures in the knowledge base carry no published source,
   read live from `/knowledge/provenance` rather than typed into the page.

### 5.3 Today

Order is deliberate: anything needing the person comes before anything reporting to them.

1. **Pending**: a question, a measurement request or a review checkpoint, if one is waiting.
2. **Last night verdict**: the level chip, one plain sentence, then three numbers side by
   side (your reading, your normal and its band, the gap), each with a one-line explanation
   and a "where this came from" link that opens that night in the pipeline view. Coverage and
   which sleep window was used are stated in words.
3. **Open investigation**, if any: its state in plain words, the leading cause as a labelled
   bar with the probability written out, and what it is waiting for.
4. **Chat**: grounded answers with a citation chip per sentence that carries one. Clicking a
   chip opens the passage with the quoted span highlighted, its document title, and its
   provenance tag. A refusal to answer says why in plain words.
5. **Summary for your doctor**: the SBAR handover rendered readably, with one Copy button.

### 5.4 History

One chart: resting heart rate per night over a selectable window, the baseline band shaded
behind it, dots coloured by level, and a caption naming every element on it. One table, six
columns: night, level, your reading, gap versus normal, sleep, investigated. The investigated
column carries the outcome in a few words and a button that opens that night's pipeline.
Filters: level, investigated only, date range. One toggle reveals every recorded field for a
night, for the person who wants everything.

### 5.5 Audit

Three tabs.

**This night.** A night stepper at the top, five headline tiles, then the step grid: numbered
cards in a CSS grid, coloured by layer, each showing its one key figure and its timestamp
where one was recorded. Cards are buttons. The selected card fills a detail panel: what
happened, why, what drove it, the numbers with the arithmetic stated in plain English, the
sources read with their passages, and a raw JSON expander. Steps that did not run are greyed
with their real reason. The safety floor sits to the side, marked always on, with whether it
triggered.

**Everything the system did.** The existing hash-chained record: filters by actor, operation,
episode and date, the integrity check, and the export.

**How this works.** The eight explainer sections that exist today, kept as a permanent
reference and rewritten to match the new vocabulary.

### 5.6 Settings

Audited field by field against `ServiceSettings` and the subject profile so that everything
configurable is present, then grouped: About you, Where readings come from, The AI model, How
you get asked, How often, Delete everything. Every field carries one line saying what it
changes about the system's behaviour. Connection test buttons stay.

## 6. Testing

Unit, on the new service:

- an investigated night, asserting all eighteen steps plus safety are present and ordered
- a quiet night, asserting steps 1 to 7 ran and step 8 reports no investigation with a reason
- a night with no usable reading, asserting the sleep window and feature steps say so
- an episode predating the trace, asserting `unrecorded` rather than `skipped`
- no step carries a timestamp that is not present in the database

API, per new endpoint: shape, 404 on an unknown night, and no field the models do not declare.

Interface, rewritten alongside the pages, keeping the three structural tests that matter: the
import boundary, the `never_say` sweep now covering all copy, and "the client's result is used
as returned". Plus one new test: every canonical step id has copy in `explain.py`, so a step
cannot ship unexplained.

Then the part that actually finds defects: drive all five screens with Playwright as an
ordinary person, write down what is wrong, fix it, and drive them again from a fresh start.
The suite runs once at the end.

## 7. Risks

- **A rewrite loses hard-won detail.** The current screens encode fixes for real defects: a
  UTC hour shown to a person in Singapore, a fallback that asserted the wrong sleep window on
  44 of 72 nights, a tool-call expander that was never populated. Before a file is deleted its
  comments are read, and anything recording a defect is carried into the replacement.
- **Reconstruction can quietly misreport.** A step assembled at read time can claim something
  the night did not do. Mitigated by tests over real stored nights, and by `unrecorded` being
  a first-class status rather than a fallback.
- **CSS in Streamlit is fragile.** Kept in one module, with no reliance on Streamlit's
  internal class names.
