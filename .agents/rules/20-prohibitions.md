# Prohibitions

Hard rules. Breaking any of these is worse than leaving a task unfinished. Every one of them exists
because the failure it prevents is **silent**: the code runs, the tests pass, and the system is
wrong in a way nobody notices until it matters.

---

## 1. Tests

**Never modify, weaken, delete, rename, skip or `xfail` a test to make it pass.**

That includes all of these, which are the same act wearing different clothes:

- loosening an assertion (`assertAlmostEqual` where `assertEqual` was written)
- widening a tolerance
- adding `@pytest.mark.skip` or `@pytest.mark.xfail`
- changing an expected value in a fixture
- deleting a case from a parametrised list
- wrapping the assertion in a conditional
- catching the exception the test was meant to surface

If a test appears to be wrong, **it may well be**, but that is a decision for a human. Record it in
`plan/BLOCKERS.md` and move to the next independent task.

You may **add** tests freely.

---

## 2. Numbers

**Never write a numeric literal that affects behaviour.**

Every threshold, budget, window, temperature and floor lives in `src/wha/constants.py`. Every
clinical figure, base rate, effect size and likelihood lives in `data/knowledge/`.

If the value you need does not exist there, that is a blocker. **Do not estimate it, do not infer it
from a similar value, and do not take one from a docstring or a comment.**

The exceptions are obvious and few: array indices, `0`, `1`, `-1`, and format widths.

---

## 3. Read-only paths

Never create, edit, move or delete anything under:

```
data/knowledge/     the cited medical tables. Authored by a human, with sources
plan/               the design. You may only write PROGRESS.md and BLOCKERS.md
research/           evidence corpus
archive/            a superseded earlier generation. Not fact
PROPOSAL.md         the narrative artefact
HANDOFF.md          project history
```

Inside `plan/` you may write **only** `PROGRESS.md` and `BLOCKERS.md`.

---

## 4. Contracts

`plan/02-contracts.md` defines every schema, model, field name, enum value, service signature and
constant. **Never** rename a field, add one, widen a type, change an enum, alter a table, or change
a function signature.

If a task cannot be completed without changing a contract, the task or the contract is wrong. That
is a blocker, always.

---

## 5. Errors

- Never raise a bare `Exception`. Use the taxonomy in `src/wha/errors.py`.
- Never `except:` or `except Exception:` without re-raising, unless the contract names that
  behaviour explicitly.
- Never swallow an exception to keep a pipeline running.
- Never add `# type: ignore`, `# noqa`, or `Any` to silence a checker. Fix the type or record a
  blocker.

---

## 6. The model

- The LLM **never** decides whether to interrupt the human. That is `policy/`, in numpy.
- The LLM **never** produces a probability that reaches the user. Numbers come from `belief/`.
- The LLM **never** removes a red flag. It may only add one.
- The LLM **never** sends anything. `notify/` is not a tool and must not appear in any tool
  registry.
- No tool may run a shell command, execute generated code, fetch an arbitrary URL, or reach the open
  web. Live data comes only from the named endpoints in `data/knowledge/sources.yaml`.

---

## 7. Secrets

- Never log, print, format, or write to the audit log any value from a key ending `TOKEN` or `KEY`.
- Never commit `.env`.
- Never hard-code a host, bearer token, bot token or chat id, not even in a test. Tests use fixtures.
- `Settings` carries no secret fields. `SettingsPatch` uses `SecretStr` and is write-only.

---

## 8. Git

- Never `git push`, `git push --force`, `git rebase`, `git reset --hard`, or rewrite history.
- Never `--no-verify` or skip a hook.
- Never add a co-author trailer, an attribution line, or a tool name to a commit message.
- Commit only when a task says to.

---

## 9. Scope

- Do not refactor code a task did not name.
- Do not add a dependency. The list in `plan/02-contracts.md` section 1 is closed.
- Do not add a feature, a flag, a helper module or an abstraction "for later".
- Do not upgrade or pin a version differently from `uv.lock`.

If `uv lock` fails to resolve, record it. **Do not remove a dependency and do not drop the
`numpy>=2` floor.**

---

## 10. Writing style

No em-dashes anywhere: not in code comments, docstrings, commit messages, user-facing strings, or
anything you write into `PROGRESS.md` or `BLOCKERS.md`. Use a comma, a colon, or a full stop.
