# Android wheels

Android arm64 wheels for the packages Chaquopy's index does not carry, built on the
shared remote with `android/remote/build-wheels.sh`: cibuildwheel 3.x (`uv tool`), NDK
27.2.12479018, API level 26, CPython 3.13, Rust via rustup with the
`aarch64-linux-android` target. Versions are the ones `uv.lock` pins, read from the lock
by the script, so phone and PC agree.

Built 10 September 2026. Every wheel here was imported on the owner's phone by the smoke
app before anything depended on it (see "Verifying" below).

| Wheel | Result |
|---|---|
| pydantic_core 2.46.5 | built, first attempt, about twelve minutes of which one was the Rust compile and the rest cibuildwheel's one-time Android Python setup |
| orjson 3.12.0 | built, first attempt |
| ormsgpack 1.12.2 | built, first attempt |
| xxhash 4.0.1 | built on the second attempt. The first failed before compiling: the package's own `[tool.cibuildwheel]` table enables the group `pyodide-eol`, which cibuildwheel 3.2 rejects when parsing. `android/remote/cibw-override.toml` is now passed with `--config-file` for every build so a package's table is ignored |
| sqlite_vec 0.1.9 | not built, and not needed. PyPI ships no sdist for it, only binary wheels for desktop platforms. It is declared by `langgraph-checkpoint-sqlite` but never imported: `langgraph.checkpoint.sqlite` and all three of its submodules import and construct `SqliteSaver` with `sqlite_vec` blocked (checked on the PC, 10 September). The phone therefore installs the checkpointer with `--no-deps` and its real imports pinned explicitly (Task 11) |

## Decision

Spec section 4.2 named three outcomes. This is outcome **(a)**: pydantic-core built and
everything langgraph needs at import time built, so **langgraph stays and no Python
changes**. The one deviation from the letter of (a) is sqlite-vec, which is absent from
the phone rather than built, on the evidence above.

## Two things that went wrong, so they are not repeated

- `pip download --no-binary :all:` on a Rust package builds the package's metadata first,
  which means compiling maturin from source; it sat for minutes doing that. The script
  now fetches the sdist URL from PyPI's JSON API directly.
- `pkill -f` with a pattern that also matches the ssh command running it kills the ssh
  session. Kill by pid.

## Verifying a wheel

`sha256sum -c SHA256SUMS` in this directory. The smoke app (`android/app/src/main/python/wha_smoke.py`
in the Task 3 commit) imports every native module here on the real device and validates a
pydantic model, which is the only proof that counts.

## Rebuilding

`bash android/remote/sync.sh && bash android/remote/run.sh 'bash android/remote/build-wheels.sh'`
with no arguments rebuilds all four. Pass package names to rebuild some. Copy back with
`scp 'huawei_blue_1_ppt:/home/liangsheng/brian/android/wheels/*' android/wheels/`.
