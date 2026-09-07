# Environment

Windows. Python 3.12 managed by **uv**. There is no other supported way to run anything here.

---

## The one that will bite you first

On this machine, `python` on `PATH` resolves to an **unrelated project's virtual environment**:

```
C:\Users\Admin\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe
```

If you run `python -m pytest`, it will use that interpreter, your imports will fail, and the error
will look like a code problem. It is not.

**Every command goes through `uv run`.** No exceptions.

```bash
uv run pytest              # yes
python -m pytest           # no
uv run python -c "..."     # yes, if you must
pip install anything       # never
```

---

## First-time setup

```bash
uv python install 3.12
uv sync
uv run wha doctor
```

`uv sync` reads `pyproject.toml` and `uv.lock`. If `uv.lock` does not exist yet, the first task
creates it with `uv lock`. If resolution fails, record it in `BLOCKERS.md`. **Do not remove a
dependency and do not drop the `numpy>=2` floor.**

---

## Everyday commands

```bash
uv run pytest                          # whole suite
uv run pytest tests/unit -q            # fast loop while working
uv run pytest tests/unit/test_x.py::test_y -x   # one test, stop on first failure
uv run pytest -k "belief and not slow" # by keyword

uv run ruff check src tests            # lint
uv run ruff check --fix src tests      # autofix what is safe
uv run ruff format src tests           # format

uv run wha doctor                      # database, knowledge, bridge, LLM, Telegram, cohort, baseline
uv run wha nightly --subject me        # one deterministic batch
uv run wha demo run illness-onset      # a scenario end to end
uv run wha serve                       # dashboard plus scheduler
```

---

## Test environment

Tests run **offline**. No network, no phone, no live model, no dataset download.

- `WHA_LLM_PROVIDER=cassette` is set by the test fixtures. Never override it in a test.
- Time is frozen with `freezegun`. Never call `datetime.now()` inside an assertion.
- Every generator takes an explicit seed.
- Dataset-dependent tests use `pytest.mark.skipif` and name the fetch command in the skip message.

**If a test needs the network to pass, the test is wrong.** That is a blocker.

---

## Paths

`pathlib.Path` everywhere. Never string concatenation, never a hard-coded `/` or `\`.

```python
from pathlib import Path
p = Path(settings.data_dir) / "datasets" / "stanford"   # yes
p = settings.data_dir + "/datasets/stanford"            # no
```

Paths that must exist are created with `mkdir(parents=True, exist_ok=True)`, never assumed.

---

## Disk

**About 33 GB free on C:, and no second drive.** Nothing else is available.

- Mishra et al. 2020 COVID-19-Wearables: 378 MB zipped, 3.64 GB extracted
- PMData: 1.4 GB, and nothing in this repository reads it

So: keep archives compressed, extract selectively, convert to parquet, delete intermediates. The
cohort lives under `data/cohort/`, fetched by `experiments/detection/cohort/fetch.py`, and all of `data/` is
gitignored. **Never commit a dataset, a database, a parquet file or a model weight.**

The 182 MB of Chronos weights that used to live in `data/model_cache/` are no longer needed: the
forecast was deleted on 5 September 2026 after it separated illness worse than the plain residual
the detector already computes.

---

## Shell

The repository has already lost file content to heredoc mangling: backticks became command
substitution and apostrophes broke quoting, and one incident silently emptied a table in a markdown
file.

**Write files with a file-writing tool.** Never pipe content containing backticks, quotes or dollar
signs through a shell heredoc.

---

## Encoding

UTF-8 everywhere, explicitly:

```python
path.read_text(encoding="utf-8")
path.write_text(content, encoding="utf-8")
```

Windows defaults to the system codepage otherwise, and it will corrupt anything non-ASCII without
raising.
