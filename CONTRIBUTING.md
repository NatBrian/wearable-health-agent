# Contributing

**Read these two before writing any code:**

1. **[README.md](README.md)** for what the project is and where everything lives. Three
   sections are worth reading first:
   - **"I want to do X. What do I read?"**, which routes you by goal.
   - **"Working in parallel"**, the boundaries between subsystems and the shared files.
   - **"Rules enforced by tests, not by convention"**.
2. **[AGENTS.md](AGENTS.md)** for the rules that apply to every contributor. If this file
   disagrees with it, `AGENTS.md` is correct.

## Before opening a pull request

```bash
uv run pytest -n auto          # the whole suite
uv run ruff check src tests    # lint
```

Then open the dashboard and use the part you changed. Most defects found in this project
were found that way rather than by the suite.

## Two constraints specific to this project

**It has no clinical validation.** Nothing you write may imply otherwise. Every number in
user-facing text must be a published figure with its citation, an operating parameter of the
code, or absent. See [DISCLAIMER.md](DISCLAIMER.md) and `docs/DISCLOSURES.md`.

**Conventions are enforced by tests.** If a rule matters, add the check alongside it rather
than only documenting it. Never weaken or skip a test to make a change pass; if a test looks
wrong, raise it in the pull request.
