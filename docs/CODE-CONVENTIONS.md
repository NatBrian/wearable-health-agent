# Python conventions

Python 3.12. Ruff for lint and format, default line length 100. Full type hints on every public
function.

---

## Module boundaries

These are enforced by `tests/unit/test_layering.py`. Breaking one is a blocker, not a
judgement call.

```
api/      the boundary. Everything a client reads passes through it
service/  application logic. May import from anything except a client
agent/    the graph, its nodes and its tools
db/       owns connections, schema and migrations
config, constants, errors, models    depend on nothing, and everything depends on them
```

**Nothing under `src/` imports a dashboard.** The system runs headless. This used to be
enforced by a `ui/` package that could import only from `api/` and `models.py`, reaching
the application over HTTP; that Streamlit dashboard was archived to
`archive/streamlit-ui-2026-09-27/` on 27 September 2026. The client that replaced it,
`frontend/`, is a separate React/TypeScript project outside `src/wha`, talking to the same
`api/` boundary over HTTP by construction rather than by a Python-level rule. No business
logic belongs in a client: if a screen needs a computation it belongs in `service/` and
reaches the screen through `api/`.

**A dependency between two packages is a design decision.** Every one that exists is listed
in `DECLARED_EDGES` in `tests/unit/test_layering.py`, and creating a new one fails that test
until it is added there. The friction is intentional: coupling two subsystems should be a
choice somebody made, and visible to anyone working in the other one.

**Two import cycles exist:** `agent` with `service`, and `notify` with `service`. Both are
held open by function-local imports, listed with their reasons in `ALLOWED_UPWARD_IMPORTS`.
A new one fails the test. Each cycle marks a boundary in the wrong place and is a candidate
for removal, not a pattern to copy.

**`sqlite3` is not confined to `db/`.** `db/` owns connection handling, schema and
migrations; query text lives with the code that needs it.

---

## Types

```python
def compute_baseline(nights: Sequence[NightlyFeatures]) -> Baseline: ...   # yes
def compute_baseline(nights): ...                                          # no
def compute_baseline(nights: list) -> dict: ...                            # no
```

- `X | None`, never `Optional[X]`.
- `list[X]`, `dict[K, V]`, never `List`, `Dict`.
- Never `Any`. If you reach for it, the contract is missing something. Record a blocker.
- Pydantic v2 models at every boundary: storage, service, LLM output, tool arguments and returns.
- Enums are `StrEnum` and are defined once, in `models.py`.

---

## Pydantic

```python
class Thing(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
```

`extra="forbid"` is not optional. A model that silently accepts unknown keys will swallow a renamed
field and produce wrong behaviour without an error.

Validate **at the boundary**, once, then pass typed objects inward. Do not re-validate in every
function and do not pass raw dicts around.

---

## Functions

- One job each. If you cannot describe it in one sentence without "and", split it.
- Pure where possible: take arguments, return a value, no hidden state.
- Side effects live in `db/`, `notify/` and `llm/`. Everything else is computation.
- No default arguments that are mutable, and no defaults that hide a decision. Pass the constant.

---

## Naming

- `snake_case` functions and variables, `PascalCase` classes, `UPPER_SNAKE` constants.
- Units in the name when there is any doubt: `rhr_bpm`, `latency_ms`, `window_hours`,
  `effect_mean_bpm`. This convention has already prevented one class of bug in the schema; keep it.
- Timestamps end `_utc` and are always UTC. Local dates are `night_date` and are never times.
- Booleans read as assertions: `usable`, `flagged`, `declined`. Not `is_usable_flag`.

---

## Errors

```python
raise SourceUnavailable(f"bridge unreachable at {host}:{port}")   # yes
raise Exception("failed")                                         # no
raise ValueError("bad")                                           # no, use the taxonomy
```

Every error is from `src/wha/errors.py`. Messages name **what** and **where**, never a secret value.

Never catch and continue. If you must catch, re-raise or convert to a taxonomy error that a caller
knows how to handle.

---

## Docstrings

Explain **why**, and any non-obvious invariant. Do not restate the signature.

```python
def nocturnal_rhr(samples: Sequence[HeartRateSample]) -> float | None:
    """Median heart rate in the local 00:00 to 07:00 window.

    Median rather than mean because a single motion artefact shifts a mean by
    several bpm and the whole detector works on a 3 to 4 bpm threshold.
    Returns None when coverage is below MIN_NOCTURNAL_MINUTES, which is a
    refusal and not an error.
    """
```

Where a value comes from a paper, cite it in the docstring next to the code that uses it.

---

## Comments

Sparse. Comment the surprising, never the obvious. If a line needs a comment to be understood,
consider whether a named intermediate variable would do the job instead.

**No em-dashes anywhere**, including comments and docstrings.

---

## Tests

Mirror the source tree: `src/wha/detect/baseline.py` is tested by
`tests/unit/detect/test_baseline.py`.

```python
def test_mad_floor_applies_when_window_is_constant():
    """MAD is exactly 0 on quantised data, which would divide by zero."""
```

- One behaviour per test. The name says the behaviour, not the function.
- Arrange, act, assert, with a blank line between.
- No mocking of code you own. Mock only at the true boundary: HTTP, the clock, the filesystem.
- Fixtures live in `conftest.py` at the narrowest scope that works.
- Assert on values, not on call counts, except where the contract is about a call.

---

## Logging

`structlog`-style key-value through the project logger, never `print`. Never log a secret, never log
raw health values above debug level, never log message content from an unauthorised sender.

The audit log is not the application log. Audit rows go through `audit/`, are append-only, and are
hash-chained. Do not write to `audit_events` directly.

---

## Imports

Standard library, then third party, then local, each block alphabetised. Ruff enforces it. No
wildcard imports. No imports inside functions except to break a genuine cycle, and a cycle is
usually a sign the boundary is wrong.
