# Android App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task, inline in the main session (the owner's standing rule is never to spawn subagents). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a standalone Android app that runs the whole Wearable Health Agent on the owner's Samsung phone, with a Compose interface designed against the HCI sources in the spec, while the PC stays the main codebase.

**Architecture:** The existing Python core is embedded unchanged with Chaquopy; a thin facade returns the same Pydantic models the HTTP API returns as JSON; Kotlin owns scheduling, notifications, secure storage, the ONNX embedder and the screens. Native wheels that Chaquopy does not provide are built once with cibuildwheel on the shared remote machine, which also builds the APK.

**Tech Stack:** Python 3.13 under Chaquopy 17, pydantic 2.13.5 with pydantic-core 2.46.5, langgraph 1.2.11 (kept if its wheels build), numpy, scipy, pandas; Kotlin 2.x, Jetpack Compose with Material 3, WorkManager, kotlinx.serialization, ONNX Runtime for Android; Gradle 8 with AGP 8; cibuildwheel 3.x for Android wheels; Temurin JDK 17.

**Spec:** `docs/superpowers/specs/2026-09-10-android-app-design.md`. Read it first. Every task below argues from a numbered section of it.

## Global Constraints

Copied from the spec and `AGENTS.md`. They apply to every task without being repeated.

- Never modify, weaken, delete, skip or `xfail` a test to make it pass (`AGENTS.md` rule 1).
- Never invent a number. Every threshold comes from `src/wha/constants.py`; UI copy contains no digits; screen numbers come from `config()` or stored data (spec section 2, section 6.2).
- No number this project measured about itself appears in any string the app shows (`AGENTS.md` rule 3).
- No clinical rule, threshold, notification rule or policy changes (spec section 2). The notification rules are the system's existing rules, delivered natively (spec section 1).
- Always `uv run` on the PC. Never bare `python` (`AGENTS.md` rule 5).
- Tests run with `uv run pytest -n auto`; run only what changed while working, the whole suite once at the end.
- No em-dash in any prose or commit message. A test sweeps every tracked `.md` file.
- Commit messages say why, not what. No co-author line, no tool name.
- Work on `feat/android-app` in the worktree `Documents/Github/wha-android`. Never force-push. Open a PR at the end; merging is the owner's call.
- On the remote machine only `/home/liangsheng/brian/android` is ours. No sudo, no `kill` of anything not ours, no shell profile edits, no listening ports, builds under `nice`, Gradle workers capped, Gradle daemon stopped after each session (spec section 11).
- No secret, database, corpus or demo film ever goes to the remote. The exclude list `android/sync-exclude.txt` is tested (spec section 11).
- The remote never talks to GitHub for this repository. Source travels by tar over SSH from the PC (spec section 11).
- Chaquopy `minSdk` is 26; the phone is the only test device; there is no emulator.
- `docs/CONTRACTS.md` is compared against the code by four tests on every run. Every schema, model, constant, dependency group or service signature change updates it in the same commit.
- `docs/DISCLOSURES.md` gains an entry, naming the screen that shows it, for every limitation this work creates.

## Remote layout and the two scripts every task uses

```
/home/liangsheng/brian/android/
  env.sh            exports JAVA_HOME, ANDROID_HOME, GRADLE_USER_HOME, CARGO_HOME,
                    RUSTUP_HOME, UV_CACHE_DIR, PATH. Sourced explicitly, never from a profile
  tools/            jdk/, sdk/, rustup/, cargo/, uv/, gradle-home/, uv-cache/
  wha/              the working copy, refreshed by android/remote/sync.sh
  wheels/           output of the wheel builds, copied back into android/wheels/
```

`android/remote/sync.sh` (Task 1) pushes the worktree to `wha/`. `android/remote/run.sh`
(Task 1) runs one command there with `env.sh` sourced. Every "Run on the remote" step in
this plan means `android/remote/run.sh '<command>'`.

## Task map

| Phase | Tasks | Produces |
|---|---|---|
| 0. Remote toolchain and the wheel spike | 1 to 3 | Working toolchain, the wheel decision, a smoke APK that imports the core on the phone |
| 1. Core seams on the PC | 4 to 10 | Dependency split, embedder injection, android notifier, facade, lineage table, shared wording, and the langgraph loop only if the spike says so |
| 2. The app | 11 to 23 | Gradle project, bridge, onboarding, jobs, notifications, embedder, corpus fetch, and the six screens |
| 3. Documents and verification | 24 to 25 | Contracts, disclosures, guides, research note, the two on-phone runs, the PR |

---
## Phase 0. Remote toolchain and the wheel spike

### Task 1: The remote workspace, the sync script, and the toolchain

Spec section 11. Everything in user space under one directory, sourced from one file.

**Files:**
- Create: `android/sync-exclude.txt`
- Create: `android/remote/sync.sh`
- Create: `android/remote/run.sh`
- Create: `android/remote/env.sh` (copied to the remote as `env.sh`)
- Create: `android/remote/install-toolchain.sh`
- Create: `android/README.md` (started here, finished in Task 24)
- Test: `tests/unit/android/test_sync_exclude.py`

**Interfaces:**
- Produces: `android/remote/run.sh '<command>'` runs a command on the remote inside `/home/liangsheng/brian/android/wha` with `env.sh` sourced; `android/remote/sync.sh` refreshes that working copy.

- [x] **Step 1: Write the failing test for the exclude list**

```python
# tests/unit/android/test_sync_exclude.py
"""Nothing private may travel to the shared build machine.

The exclude list is the only thing standing between the owner's health record and a
machine other people use. A test, because a list nobody checks drifts.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXCLUDE = ROOT / "android" / "sync-exclude.txt"

# Every one of these is either a secret, personal health data, or a large artefact the
# remote has no use for. Add to this set when a new private path appears in the repo.
MUST_EXCLUDE = {
    ".env",
    ".env.*",
    "data/wha.sqlite",
    "data/corpus",
    "data/demo_film.sqlite",
    "data/demo_film_live.sqlite",
    "data/demo-snapshots",
    "data/datasets",
    "data/cohort",
    "docs/demo/wha-demo.mp4",
    ".git",
    ".venv",
    "android/app/build",
    "android/.gradle",
}


def test_exclude_list_names_every_private_path() -> None:
    lines = {
        line.strip()
        for line in EXCLUDE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    missing = MUST_EXCLUDE - lines
    assert not missing, f"android/sync-exclude.txt does not exclude: {sorted(missing)}"


def test_exclude_list_covers_every_gitignored_data_pattern() -> None:
    """If .gitignore keeps it out of git, the sync must keep it off the remote."""
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    data_patterns = {
        line.strip()
        for line in ignore
        if line.strip().startswith("data/") and not line.strip().startswith("!")
    }
    exclude = EXCLUDE.read_text(encoding="utf-8")
    uncovered = [p for p in data_patterns if p.rstrip("/").split("/")[0] not in exclude]
    assert not uncovered, f"gitignored data patterns the sync does not exclude: {uncovered}"
```

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/android/test_sync_exclude.py -v`
Expected: FAIL, `FileNotFoundError` on `android/sync-exclude.txt`. Also create
`tests/unit/android/__init__.py` (empty) so pytest collects the package.

- [x] **Step 3: Write the exclude list**

```
# android/sync-exclude.txt
# Paths never sent to the shared build machine. Read by android/remote/sync.sh as
# tar --exclude-from. Tested by tests/unit/android/test_sync_exclude.py.
.env
.env.*
.git
.venv
.pytest_cache
.ruff_cache
.playwright-mcp
__pycache__
data/wha.sqlite
data/corpus
data/demo_film.sqlite
data/demo_film_live.sqlite
data/demo-snapshots
data/datasets
data/cohort
data/sim_state.json
data/*.sqlite
docs/demo/wha-demo.mp4
docs/demo/work
docs/demo/footage-raw
android/app/build
android/.gradle
android/local.properties
serve.log
mockwatch.log
```

- [x] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/unit/android/test_sync_exclude.py -v`
Expected: PASS, two tests.

- [x] **Step 5: Write the sync and run scripts**

```bash
#!/usr/bin/env bash
# android/remote/sync.sh
# Push this worktree to the shared build machine. tar over ssh, because the PC has no rsync
# and the remote must never clone the private repository with its own GitHub key.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/../.." && pwd)"
HOST="${WHA_REMOTE_HOST:-huawei_blue_1_ppt}"
DEST="/home/liangsheng/brian/android/wha"
cd "$HERE"
ssh -o BatchMode=yes "$HOST" "mkdir -p '$DEST'"
tar --exclude-from=android/sync-exclude.txt -czf - . \
  | ssh -o BatchMode=yes "$HOST" "tar -xzf - -C '$DEST'"
echo "synced $(git rev-parse --short HEAD) to $HOST:$DEST"
```

```bash
#!/usr/bin/env bash
# android/remote/run.sh '<command>'
# Run one command on the shared build machine inside the working copy with the toolchain
# on PATH. Always nice, because other people are using that machine.
set -euo pipefail
HOST="${WHA_REMOTE_HOST:-huawei_blue_1_ppt}"
BASE="/home/liangsheng/brian/android"
ssh -o BatchMode=yes "$HOST" "source '$BASE/env.sh' && cd '$BASE/wha' && nice -n 10 bash -lc $(printf '%q' "$*")"
```

```bash
# android/remote/env.sh
# Sourced explicitly by run.sh. Never appended to a shell profile: other users share this
# machine and the profile is not ours.
export WHA_ANDROID_BASE=/home/liangsheng/brian/android
export JAVA_HOME=$WHA_ANDROID_BASE/tools/jdk
export ANDROID_HOME=$WHA_ANDROID_BASE/tools/sdk
export ANDROID_SDK_ROOT=$ANDROID_HOME
export ANDROID_NDK_HOME=$ANDROID_HOME/ndk/27.2.12479018
export GRADLE_USER_HOME=$WHA_ANDROID_BASE/tools/gradle-home
export CARGO_HOME=$WHA_ANDROID_BASE/tools/cargo
export RUSTUP_HOME=$WHA_ANDROID_BASE/tools/rustup
export UV_CACHE_DIR=$WHA_ANDROID_BASE/tools/uv-cache
export UV_PYTHON_INSTALL_DIR=$WHA_ANDROID_BASE/tools/uv-pythons
export PATH=$JAVA_HOME/bin:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$CARGO_HOME/bin:$WHA_ANDROID_BASE/tools/uv:$PATH
# Gradle must not saturate a shared box.
export GRADLE_OPTS="-Dorg.gradle.workers.max=8 -Dorg.gradle.daemon=true -Xmx6g"
```

- [x] **Step 6: Write the toolchain installer**

Every download goes under `tools/`. Versions are pinned so the build is reproducible;
record any change in `android/README.md`.

```bash
#!/usr/bin/env bash
# android/remote/install-toolchain.sh
# Run ONCE on the remote: bash install-toolchain.sh. Idempotent: skips what exists.
set -euo pipefail
BASE=/home/liangsheng/brian/android
T=$BASE/tools
mkdir -p "$T"
cp "$BASE/wha/android/remote/env.sh" "$BASE/env.sh"
source "$BASE/env.sh"

# JDK 17 (Temurin, Linux x64)
if [ ! -x "$T/jdk/bin/java" ]; then
  curl -fsSL -o /tmp/jdk.tgz "https://api.adoptium.net/v3/binary/latest/17/ga/linux/x64/jdk/hotspot/normal/eclipse"
  mkdir -p "$T/jdk" && tar -xzf /tmp/jdk.tgz -C "$T/jdk" --strip-components=1 && rm /tmp/jdk.tgz
fi
java -version

# Android command-line tools, one platform, one build-tools, one NDK
if [ ! -x "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" ]; then
  mkdir -p "$ANDROID_HOME/cmdline-tools"
  curl -fsSL -o /tmp/clt.zip "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
  unzip -q /tmp/clt.zip -d /tmp/clt && rm /tmp/clt.zip
  mv /tmp/clt/cmdline-tools "$ANDROID_HOME/cmdline-tools/latest"
fi
yes | sdkmanager --licenses > /dev/null
sdkmanager "platform-tools" "platforms;android-35" "build-tools;35.0.0" "ndk;27.2.12479018"

# Rust with the Android target, in our own homes
if [ ! -x "$CARGO_HOME/bin/rustup" ]; then
  curl -fsSL https://sh.rustup.rs | sh -s -- -y --no-modify-path --profile minimal
fi
rustup target add aarch64-linux-android

# uv and a Python 3.13 for cibuildwheel and for building pure wheels
if [ ! -x "$T/uv/uv" ]; then
  mkdir -p "$T/uv"
  curl -fsSL https://astral.sh/uv/install.sh | UV_INSTALL_DIR="$T/uv" UV_NO_MODIFY_PATH=1 sh
fi
uv python install 3.13
uv tool install --python 3.13 "cibuildwheel>=3.2,<4"
echo "toolchain ready"
```

- [x] **Step 7: Sync and install**

Run on the PC: `bash android/remote/sync.sh`
Then: `ssh huawei_blue_1_ppt 'bash /home/liangsheng/brian/android/wha/android/remote/install-toolchain.sh'`
Expected: ends with `toolchain ready`. Then `bash android/remote/run.sh 'java -version && sdkmanager --list_installed && rustup target list --installed && uv --version'` lists the JDK, the four SDK packages, `aarch64-linux-android`, and uv.

- [x] **Step 8: Start `android/README.md`**

```markdown
# The Android app

Built on the shared remote machine, installed on the owner's phone. The design is
`docs/superpowers/specs/2026-09-10-android-app-design.md`; the build steps are here.

## Remote machine rules

Only `/home/liangsheng/brian/android` is ours. No sudo, nothing outside it, nothing
killed that is not ours, no shell profile edits, builds under `nice`, Gradle daemon stopped
after a session (`android/remote/run.sh './gradlew --stop'`).

## Scripts

| Script | Does |
|---|---|
| `android/remote/sync.sh` | Pushes this worktree to the remote with `android/sync-exclude.txt` applied |
| `android/remote/run.sh '<cmd>'` | Runs a command on the remote with the toolchain on PATH |
| `android/remote/install-toolchain.sh` | One-time toolchain install, pinned versions |

## Pinned versions

JDK 17 (Temurin latest GA), command-line tools 11076708, platform 35, build-tools 35.0.0,
NDK 27.2.12479018, Python 3.13 via uv, cibuildwheel 3.x.
```

- [x] **Step 9: Commit**

```bash
git add android/ tests/unit/android/
git commit -m "Give the app a shared build machine and a fence around what may reach it

The laptop cannot hold an Android toolchain. The remote can, but other people use it and
the repository is private, so the sync excludes every secret and every health record, and
a test keeps the exclude list honest."
```

---

### Task 2: The wheel spike

Spec section 4.2. The outcomes are decided in advance; this task discovers which one holds.

**Files:**
- Create: `android/remote/build-wheels.sh`
- Create: `android/wheels/BUILD.md`
- Create: `android/wheels/*.whl` (build outputs, committed)
- Create: `android/wheels/SHA256SUMS`

**Interfaces:**
- Produces: `android/wheels/` containing `pydantic_core-2.46.5-*android*_arm64_v8a.whl` and, if they build, `orjson`, `ormsgpack`, `xxhash`, `sqlite_vec` wheels; and a written decision in `BUILD.md` selecting one of the three spec outcomes.

- [x] **Step 1: Write the build script**

cibuildwheel builds from a source tree, so each package is fetched as an sdist at the
version `uv.lock` pins. Versions come from the lock, never typed twice.

```bash
#!/usr/bin/env bash
# android/remote/build-wheels.sh [package ...]
# Build Android arm64 wheels for the packages Chaquopy does not provide, at the exact
# versions uv.lock pins, with cibuildwheel. Output: /home/liangsheng/brian/android/wheels.
set -euo pipefail
source /home/liangsheng/brian/android/env.sh
OUT=$WHA_ANDROID_BASE/wheels
WORK=$WHA_ANDROID_BASE/wheel-work
mkdir -p "$OUT" "$WORK"
cd "$WHA_ANDROID_BASE/wha"

locked_version() {
  # The version uv.lock pins for a package, read with Python's tomllib.
  uv run --python 3.13 --no-project python - "$1" <<'PY'
import sys, tomllib
name = sys.argv[1]
lock = tomllib.load(open("uv.lock", "rb"))
for pkg in lock["package"]:
    if pkg["name"] == name:
        print(pkg["version"]); break
else:
    sys.exit(f"{name} not in uv.lock")
PY
}

export ANDROID_API_LEVEL=26
export CIBW_PLATFORM=android
export CIBW_ARCHS=arm64_v8a
export CIBW_BUILD="cp313-*"
export CIBW_BUILD_FRONTEND="build[uv]"
export CIBW_TEST_SKIP="*"          # no emulator here; import is tested on the phone
export CIBW_ENVIRONMENT="PYO3_CROSS=1 PYO3_CROSS_PYTHON_VERSION=3.13 CARGO_BUILD_TARGET=aarch64-linux-android"
export CIBW_BEFORE_BUILD="rustup target add aarch64-linux-android"

for name in "${@:-pydantic-core orjson ormsgpack xxhash sqlite-vec}"; do
  ver=$(locked_version "$name")
  echo "== $name $ver"
  rm -rf "$WORK/$name" && mkdir -p "$WORK/$name"
  (cd "$WORK/$name" && uv run --python 3.13 --no-project pip download --no-deps --no-binary :all: "$name==$ver" -d . )
  sdist=$(ls "$WORK/$name"/*.tar.gz)
  tar -xzf "$sdist" -C "$WORK/$name"
  src=$(find "$WORK/$name" -mindepth 1 -maxdepth 1 -type d | head -1)
  ( cd "$src" && uvx cibuildwheel --platform android --output-dir "$OUT" ) \
    || echo "FAILED: $name $ver" | tee -a "$OUT/FAILED.txt"
done
ls -la "$OUT"
( cd "$OUT" && sha256sum *.whl > SHA256SUMS )
```

- [x] **Step 2: Sync, then build pydantic-core alone first**

Run: `bash android/remote/sync.sh && bash android/remote/run.sh 'bash android/remote/build-wheels.sh pydantic-core'`
Expected outcome written before running: a file named like
`pydantic_core-2.46.5-cp313-cp313-android_26_arm64_v8a.whl` in the remote `wheels/`
directory, and no `FAILED.txt`. If the Rust cross-compile fails on PyO3's `sysconfig`
lookup, set `PYO3_CROSS_LIB_DIR` to the Android Python lib directory cibuildwheel unpacks
(printed in its log under "Installing Python") and retry once. Record every error and every
retry in `BUILD.md`.

- [x] **Step 3: Decide, per the spec**

If pydantic-core did not build after the one documented retry: **stop.** Write what was
tried in `android/wheels/BUILD.md`, commit it, and return to the owner. Do not proceed to
Task 3 and do not begin any pydantic migration.

If it built: `bash android/remote/run.sh 'bash android/remote/build-wheels.sh orjson ormsgpack xxhash sqlite-vec'`.
Expected: four more wheels, or names in `FAILED.txt`.

- [x] **Step 4: Copy the wheels back and write the decision**

Run: `mkdir -p android/wheels && scp 'huawei_blue_1_ppt:/home/liangsheng/brian/android/wheels/*' android/wheels/`

```markdown
# android/wheels/BUILD.md

Android arm64 wheels for packages Chaquopy's index does not carry, built with
`android/remote/build-wheels.sh` on the shared remote, cibuildwheel 3.x, NDK 27.2,
API level 26, CPython 3.13. Versions are the ones `uv.lock` pins so phone and PC agree.

| Wheel | Built on | Result |
|---|---|---|
| pydantic_core 2.46.5 | <date> | built / failed: <reason> |
| orjson <ver> | <date> | built / failed: <reason> |
| ormsgpack <ver> | <date> | built / failed: <reason> |
| xxhash <ver> | <date> | built / failed: <reason> |
| sqlite_vec <ver> | <date> | built / failed: <reason> |

## Decision

One of the three outcomes in spec section 4.2, stated here with the evidence above:

- (a) all five built: langgraph stays, no Python changes.
- (b) pydantic-core built, the others did not: Task 10 replaces the LangGraph graph with
  the bounded loop.
- (c) pydantic-core did not build: stopped, owner consulted.

Chosen: <letter>, because <the rows above>.

## Verifying a wheel

`sha256sum -c SHA256SUMS`. Every wheel is also imported on the phone by the smoke app in
Task 3 before anything depends on it.
```

Fill the table from the actual run. `<date>` and `<reason>` are placeholders only in
this plan; the committed file must have real values.

- [x] **Step 5: Commit**

```bash
git add android/remote/build-wheels.sh android/wheels/
git commit -m "Build the native wheels Android needs, and record which outcome we are in

pydantic v2 has no Android wheel anywhere usable, and the spec settled in advance what
happens in each case. The wheels are committed because building them needs a machine the
laptop is not, and the decision is written beside them so nobody re-derives it."
```

---

### Task 3: The smoke app

Prove the toolchain end to end before any real work: a minimal Chaquopy app that imports
the core's heaviest dependencies on the phone.

**Files:**
- Create: `android/settings.gradle.kts`
- Create: `android/build.gradle.kts`
- Create: `android/gradle.properties`
- Create: `android/gradle/wrapper/gradle-wrapper.properties`
- Create: `android/app/build.gradle.kts`
- Create: `android/app/src/main/AndroidManifest.xml`
- Create: `android/app/src/main/java/dev/wha/app/MainActivity.kt`
- Create: `android/app/src/main/python/wha_smoke.py`
- Create: `android/remote/build-apk.sh`

**Interfaces:**
- Produces: the Gradle project every later task extends; `android/remote/build-apk.sh` producing `android/app/build/outputs/apk/debug/app-debug.apk` on the remote and copying it to `android/out/app-debug.apk` on the PC (gitignored).

- [x] **Step 1: Write the Gradle project**

```kotlin
// android/settings.gradle.kts
pluginManagement {
    repositories { google(); mavenCentral(); gradlePluginPortal() }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories { google(); mavenCentral() }
}
rootProject.name = "wha"
include(":app")
```

```kotlin
// android/build.gradle.kts
plugins {
    id("com.android.application") version "8.7.3" apply false
    id("org.jetbrains.kotlin.android") version "2.1.0" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.1.0" apply false
    id("org.jetbrains.kotlin.plugin.serialization") version "2.1.0" apply false
    id("com.chaquo.python") version "17.0.0" apply false
}
```

```properties
# android/gradle.properties
org.gradle.jvmargs=-Xmx6g
org.gradle.workers.max=8
org.gradle.parallel=false
android.useAndroidX=true
kotlin.code.style=official
```

```properties
# android/gradle/wrapper/gradle-wrapper.properties
distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\://services.gradle.org/distributions/gradle-8.11.1-bin.zip
networkTimeout=10000
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
```

The wrapper jar and `gradlew` script: generate them once on the remote with a throwaway
Gradle (`uvx --from gradle ...` is not a thing; instead download
`https://services.gradle.org/distributions/gradle-8.11.1-bin.zip` to `tools/gradle-boot`,
run `tools/gradle-boot/bin/gradle wrapper --gradle-version 8.11.1` inside `wha/android`,
and copy `gradlew`, `gradlew.bat` and `gradle/wrapper/gradle-wrapper.jar` back with scp).
Commit those three files.

```kotlin
// android/app/build.gradle.kts
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.kotlin.plugin.serialization")
    id("com.chaquo.python")
}

android {
    namespace = "dev.wha.app"
    compileSdk = 35
    defaultConfig {
        applicationId = "dev.wha.app"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
        ndk { abiFilters += listOf("arm64-v8a") }
    }
    buildFeatures { compose = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }
}

chaquopy {
    defaultConfig {
        version = "3.13"
        pip {
            // Our own Android wheels first (Task 2), then Chaquopy's index and PyPI.
            options("--find-links", file("../wheels").absolutePath)
            // Smoke only: the real requirement list arrives in Task 11.
            install("numpy", "scipy", "pandas", "pydantic==2.13.5", "lxml", "pyyaml")
        }
    }
    sourceSets { getByName("main") { srcDir("src/main/python") } }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.12.01")
    implementation(composeBom)
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.core:core-ktx:1.15.0")
}
```

```xml
<!-- android/app/src/main/AndroidManifest.xml -->
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application
        android:label="WHA"
        android:allowBackup="false"
        android:theme="@android:style/Theme.Material.Light.NoActionBar">
        <activity android:name=".MainActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
```

```python
# android/app/src/main/python/wha_smoke.py
"""Imports the heaviest dependencies and reports versions. Deleted in Task 11."""

import json


def report() -> str:
    out: dict[str, str] = {}
    import numpy, pandas, scipy, pydantic, lxml, yaml  # noqa: E401

    out["numpy"] = numpy.__version__
    out["pandas"] = pandas.__version__
    out["scipy"] = scipy.__version__
    out["pydantic"] = pydantic.__version__
    out["lxml"] = lxml.__version__
    out["pyyaml"] = yaml.__version__
    # pydantic-core is the one that was in doubt: prove it validates, not just imports.
    from pydantic import BaseModel

    class Probe(BaseModel):
        x: int

    out["pydantic_core_validates"] = str(Probe(x="3").x == 3)
    return json.dumps(out, indent=1)
```

```kotlin
// android/app/src/main/java/dev/wha/app/MainActivity.kt
package dev.wha.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.Text
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (!Python.isStarted()) Python.start(AndroidPlatform(this))
        val report = Python.getInstance().getModule("wha_smoke").callAttr("report").toString()
        setContent { Text(report) }
    }
}
```

- [x] **Step 2: Write the APK build script**

```bash
#!/usr/bin/env bash
# android/remote/build-apk.sh [assembleDebug|assembleRelease]
# Syncs, builds on the remote under nice with capped workers, copies the APK back to
# android/out/, and stops the Gradle daemon so nothing of ours lingers on a shared box.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/../.." && pwd)"
TASK="${1:-assembleDebug}"
bash "$HERE/android/remote/sync.sh"
bash "$HERE/android/remote/run.sh" "cd android && ./gradlew --no-daemon --max-workers=8 $TASK && ./gradlew --stop"
mkdir -p "$HERE/android/out"
scp "huawei_blue_1_ppt:/home/liangsheng/brian/android/wha/android/app/build/outputs/apk/debug/app-debug.apk" "$HERE/android/out/" 2>/dev/null \
  || scp "huawei_blue_1_ppt:/home/liangsheng/brian/android/wha/android/app/build/outputs/apk/release/app-release.apk" "$HERE/android/out/"
ls -la "$HERE/android/out/"
```

Add `android/out/` to `.gitignore` (the APK is a build artefact, and it is large).

- [x] **Step 3: Build**

Run: `bash android/remote/build-apk.sh`
Expected, written first: Gradle ends with `BUILD SUCCESSFUL`; Chaquopy's pip step lists
`pydantic_core` installed from `../wheels`; `android/out/app-debug.apk` exists.

- [x] **Step 4: Install on the phone and read the screen**

Copy `android/out/app-debug.apk` to the phone (USB file transfer, or adb if the owner
enabled debugging: `adb install -r android/out/app-debug.apk`). Open WHA.
Expected: a JSON block with six versions and `"pydantic_core_validates": "True"`. If the
app crashes, `adb logcat -s python.stderr AndroidRuntime` (with adb) or the crash dialog's
text is the evidence; record it in `android/wheels/BUILD.md` under the wheel concerned.

Add `--find-links` wheels for the langgraph four to the smoke `install(...)` list only if
Task 2 built them, and re-run this step so every committed wheel has been imported on the
real device once.

- [x] **Step 5: Commit**

```bash
git add android/ .gitignore
git commit -m "Stand up the Gradle project and prove the core's dependencies import on the phone

A smoke screen, because a toolchain that builds is not a toolchain that runs: the wheels
from the spike are only trusted after a real phone has imported and validated with them."
```

---
## Phase 1. Core seams on the PC

All Python. Run only the tests named in each task while working; the whole suite once in
Task 25.

### Task 4: The dependency split and the import isolation test

Spec section 4.1.

**Files:**
- Modify: `pyproject.toml`
- Modify: `docs/CONTRACTS.md` (section 1 dependency table)
- Modify: `tests/unit/test_contracts.py:379-418` (the dependency test reads a third group)
- Create: `tests/unit/android/test_core_imports_without_pc_extras.py`

**Interfaces:**
- Produces: `uv sync --extra pc` installs everything the PC uses; `uv sync` alone installs the core the phone needs. The module set `wha.ui`, `wha.api`, `wha.cli`, `wha.service.scheduler`, `wha.service.demo`, `wha.eval` is the "PC only" set and is named in the new test.

- [x] **Step 1: Write the failing isolation test**

```python
# tests/unit/android/test_core_imports_without_pc_extras.py
"""The phone installs the core without the PC-only packages. Every core module must
import with those packages absent, or the app crashes on first use of that module.

Blocks the PC-only packages in sys.modules for the duration of one import sweep, in a
subprocess so nothing already imported in this test session hides a failure.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

PC_ONLY_PACKAGES = (
    "streamlit",
    "altair",
    "fastapi",
    "uvicorn",
    "sentence_transformers",
    "torch",
    "apscheduler",
    "playwright",
)

# Modules that legitimately need a PC-only package. Everything else under wha must load
# without them.
PC_ONLY_MODULES = (
    "wha.ui",
    "wha.api",
    "wha.cli",
    "wha.service.scheduler",
    "wha.service.demo",
    "wha.eval",
)

SWEEP = r'''
import importlib, pkgutil, sys, traceback
blocked = %r
pc_only = %r
class Blocker:
    def find_spec(self, name, path=None, target=None):
        root = name.split(".")[0]
        if root in blocked:
            raise ImportError(f"{name} is PC-only and must not be imported by the core")
        return None
sys.meta_path.insert(0, Blocker())
import wha
failures = []
for info in pkgutil.walk_packages(wha.__path__, "wha."):
    if info.name.startswith(pc_only):
        continue
    try:
        importlib.import_module(info.name)
    except Exception:
        failures.append(info.name + ": " + traceback.format_exc().splitlines()[-1])
print("\n".join(failures))
sys.exit(1 if failures else 0)
'''


def test_every_core_module_imports_with_pc_packages_blocked() -> None:
    code = SWEEP % (PC_ONLY_PACKAGES, PC_ONLY_MODULES)
    proc = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True
    )
    assert proc.returncode == 0, "core modules that reach a PC-only package:\n" + proc.stdout


def test_pyproject_declares_the_pc_extra() -> None:
    import tomllib

    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    extras = pyproject["project"].get("optional-dependencies", {})
    assert "pc" in extras, "pyproject.toml has no [project.optional-dependencies] pc"
    names = {dep.split(">")[0].split("<")[0].split("=")[0].strip() for dep in extras["pc"]}
    for required in ("streamlit", "altair", "fastapi", "uvicorn", "sentence-transformers", "apscheduler"):
        assert required in names, f"{required} must be in the pc extra, not in core"
    core = {d.split(">")[0].split("<")[0].split("=")[0].strip() for d in pyproject["project"]["dependencies"]}
    assert not (core & names), f"declared in both core and pc: {core & names}"
```

- [x] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/android/test_core_imports_without_pc_extras.py -v`
Expected: `test_pyproject_declares_the_pc_extra` FAILS (no extra). The sweep test may
already pass or may name modules; either way, record the output before changing anything.

- [x] **Step 3: Split `pyproject.toml`**

Replace the `dependencies` list and add the extra. Keep every version specifier exactly as
it is today.

```toml
dependencies = [
    "pydantic>=2.9,<3",
    "pandas>=2.2,<3",
    "numpy>=2.0,<3",
    "scipy>=1.14,<2",
    "httpx>=0.27,<1",
    "typer>=0.12,<1",
    "python-dotenv>=1,<2",
    "langgraph>=1.2,<2",
    "langgraph-checkpoint-sqlite>=3.1,<4",
    "rank-bm25>=0.2,<1",
    "lxml>=5,<7",
    "pyyaml>=6,<7",
]

[project.optional-dependencies]
# Everything the PC uses that the phone does not. `uv sync --extra pc` on the PC.
# Enforced by tests/unit/android/test_core_imports_without_pc_extras.py.
pc = [
    "apscheduler>=3.10,<4",
    "sentence-transformers>=3,<5",
    "streamlit>=1.40,<2",
    "altair>=5,<7",
    "fastapi>=0.115,<1",
    "uvicorn>=0.30,<1",
]
```

`pyyaml` was previously transitive; the core imports it directly (five modules), so it is
declared. Then: `uv lock && uv sync --extra pc`.

- [x] **Step 4: Fix any module the sweep names**

Typical fix: an import of `apscheduler` or `streamlit` at module top in a core module
becomes a function-local import in the one function that uses it, with a one-line comment
saying why. Do not move logic. Re-run the sweep until it passes.

- [x] **Step 5: Extend the contracts test and the contract**

In `tests/unit/test_contracts.py`, `test_the_contract_lists_the_dependencies_pyproject_actually_declares`
builds a dict of two groups at lines 396 to 397. Add a third:

```python
        "pc": set(pyproject["project"]["optional-dependencies"]["pc"]),
```

and in `docs/CONTRACTS.md` section 1, replace the two-row table with three rows, quoting the
specifiers exactly as in `pyproject.toml`:

```markdown
| Group | Contents |
|---|---|
| runtime | `pydantic>=2.9,<3`, `pandas>=2.2,<3`, `numpy>=2.0,<3`, `scipy>=1.14,<2`, `httpx>=0.27,<1`, `typer>=0.12,<1`, `python-dotenv>=1,<2`, `langgraph>=1.2,<2`, `langgraph-checkpoint-sqlite>=3.1,<4`, `rank-bm25>=0.2,<1`, `lxml>=5,<7`, `pyyaml>=6,<7` |
| pc (optional extra) | `apscheduler>=3.10,<4`, `sentence-transformers>=3,<5`, `streamlit>=1.40,<2`, `altair>=5,<7`, `fastapi>=0.115,<1`, `uvicorn>=0.30,<1` |
| dev | `pytest>=8,<9`, `pytest-xdist`, `ruff`, `playwright>=1.62.0`, `pillow>=11,<14` |
```

and add one sentence above it: "The phone installs `runtime` only. The `pc` extra is what
the dashboard, the API, the scheduler and the film tooling need; install it with
`uv sync --extra pc`." Update the README's setup block to `uv sync --extra pc`.

- [x] **Step 6: Run the affected tests**

Run: `uv run pytest tests/unit/android tests/unit/test_contracts.py tests/unit/test_docs.py -n auto -q`
Expected: all pass.

- [x] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock docs/CONTRACTS.md README.md tests/unit/test_contracts.py tests/unit/android/ src/
git commit -m "Split the dependencies the phone needs from the ones only the PC uses

The app installs the core without Streamlit, FastAPI, the scheduler or torch, so a core
module that reaches any of them would crash on the phone the first time it loads. A
subprocess sweep with those packages blocked makes that a test failure on the PC instead."
```

---

### Task 5: The embedder seam and the ONNX model

Spec section 4.3. `HybridIndex` already takes an `Embedder`; `build_index` does not let a
caller supply one.

**Files:**
- Modify: `src/wha/retrieve/knowledge_docs.py:693-729` (`build_index`, `get_default_index`)
- Create: `src/wha/retrieve/embedder_registry.py`
- Create: `tools/export_embedder_onnx.py`
- Create: `android/app/src/main/assets/embedder/` (model.onnx, tokenizer.json, EXPORT.md)
- Test: `tests/unit/retrieve/test_embedder_registry.py`
- Test: `tests/unit/retrieve/test_onnx_agreement.py`

**Interfaces:**
- Produces: `wha.retrieve.embedder_registry.set_default_embedder(embedder: Embedder | None) -> None` and `get_default_embedder() -> Embedder | None`; `build_index(docs=None, embedder=None)` uses, in order, the argument, the registry, then the sentence-transformers default.
- Consumed by: Task 16 (Kotlin sets the registry from an ONNX-backed embedder).

- [x] **Step 1: Write the failing registry test**

```python
# tests/unit/retrieve/test_embedder_registry.py
"""The phone cannot run sentence-transformers, so it must be able to hand the index an
embedder of its own before the index is built. The registry is that hand-off."""

import numpy as np

from wha.retrieve import embedder_registry
from wha.retrieve.knowledge_docs import _INDEX_CACHE, build_index
from wha.retrieve.models import CorpusDocument


class CountingEmbedder:
    def __init__(self) -> None:
        self.calls = 0

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        self.calls += 1
        vectors = np.zeros((len(texts), 384), dtype=np.float32)
        vectors[:, 0] = 1.0
        return vectors


def _tiny_corpus() -> list[CorpusDocument]:
    return [
        CorpusDocument(
            doc_id="t1", title="Fever", text="A fever is a body temperature above normal.",
            layer=1, source_url="test", metadata={},
        )
    ]


def test_build_index_uses_the_registered_embedder(monkeypatch) -> None:
    embedder = CountingEmbedder()
    embedder_registry.set_default_embedder(embedder)
    try:
        monkeypatch.setattr("wha.retrieve.knowledge_docs._load_cached_embeddings", lambda chunks: None)
        monkeypatch.setattr("wha.retrieve.knowledge_docs._save_cached_embeddings", lambda c, e: None)
        index = build_index(_tiny_corpus())
        assert embedder.calls == 1
        assert index.embedder is embedder
    finally:
        embedder_registry.set_default_embedder(None)


def test_explicit_argument_beats_the_registry(monkeypatch) -> None:
    registered, explicit = CountingEmbedder(), CountingEmbedder()
    embedder_registry.set_default_embedder(registered)
    try:
        monkeypatch.setattr("wha.retrieve.knowledge_docs._load_cached_embeddings", lambda chunks: None)
        monkeypatch.setattr("wha.retrieve.knowledge_docs._save_cached_embeddings", lambda c, e: None)
        index = build_index(_tiny_corpus(), embedder=explicit)
        assert explicit.calls == 1 and registered.calls == 0
        assert index.embedder is explicit
    finally:
        embedder_registry.set_default_embedder(None)


def test_registry_starts_empty_and_clears() -> None:
    _INDEX_CACHE.clear()
    assert embedder_registry.get_default_embedder() is None
    embedder_registry.set_default_embedder(CountingEmbedder())
    embedder_registry.set_default_embedder(None)
    assert embedder_registry.get_default_embedder() is None
```

Check `CorpusDocument`'s real fields in `src/wha/retrieve/models.py` before running and
adjust the constructor call to them; the test must build a real document.

- [x] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/retrieve/test_embedder_registry.py -v`
Expected: FAIL, `ModuleNotFoundError: wha.retrieve.embedder_registry`.

- [x] **Step 3: Write the registry and thread it through `build_index`**

```python
# src/wha/retrieve/embedder_registry.py
"""Where a host process hands the index an embedder it cannot construct itself.

The phone has no sentence-transformers and no torch. It has the same bge-small model as
ONNX, run from Kotlin, and this is how that reaches ``build_index`` without the index
knowing anything about Android. Empty on the PC, where the default embedder is built as
before.
"""

from wha.retrieve.index import Embedder

_DEFAULT: Embedder | None = None


def set_default_embedder(embedder: Embedder | None) -> None:
    """Register the embedder every subsequently built index will use, or clear it."""
    global _DEFAULT
    _DEFAULT = embedder


def get_default_embedder() -> Embedder | None:
    return _DEFAULT
```

In `knowledge_docs.py`, change `build_index`:

```python
def build_index(docs: list[CorpusDocument] | None = None, embedder: Any = None) -> Any:
    """Chunk the corpus and build the hybrid index over it.

    The embedder is, in order: the argument, the one registered in
    ``embedder_registry`` (how the phone supplies its ONNX model), then the
    sentence-transformers default. A host that registers nothing gets the PC behaviour.
    """
    from wha.retrieve import embedder_registry
    from wha.retrieve.chunking import chunk_document
    from wha.retrieve.index import DefaultSentenceTransformerEmbedder, HybridIndex

    corpus = docs if docs is not None else build_default_corpus()
    chunks = [chunk for doc in corpus for chunk in chunk_document(doc)]

    cached = _load_cached_embeddings(chunks)

    chosen = embedder if embedder is not None else embedder_registry.get_default_embedder()
    try:
        chosen = chosen if chosen is not None else DefaultSentenceTransformerEmbedder()
        index = HybridIndex(chunks, embedder=chosen, embeddings=cached)
    except Exception:  # noqa: BLE001
        # Deliberately broad. sentence-transformers surfaces network, filesystem and
        # torch errors of several unrelated types, and none of them is a reason to leave
        # the agent with no corpus at all.
        return HybridIndex(chunks, embedder=_BM25OnlyEmbedder())

    if cached is None:
        _save_cached_embeddings(chunks, index.embeddings)
    return index
```

`test_layering.py` declares allowed edges between packages; `retrieve` importing
`retrieve` is same-package and needs no new edge.

- [x] **Step 4: Run the registry tests**

Run: `uv run pytest tests/unit/retrieve -n auto -q`
Expected: all pass, including the existing index and corpus tests.

- [x] **Step 5: Write the ONNX export tool**

Exports the exact model the PC uses. Runs on the PC once; the outputs are committed as app
assets because they are what the phone ships.

```python
# tools/export_embedder_onnx.py
"""Export BAAI/bge-small-en-v1.5 to ONNX for the phone, with its tokenizer.

Runs on the PC (`uv run python tools/export_embedder_onnx.py`). Produces
android/app/src/main/assets/embedder/{model.onnx,tokenizer.json,EXPORT.md}. The agreement
test in tests/unit/retrieve/test_onnx_agreement.py proves the export matches the
sentence-transformers model on the PC; Task 16 proves the same on the phone.

Needs `optimum[exporters]` and `onnxruntime`, installed ad hoc:
    uv run --with "optimum[exporters]>=1.23" --with onnxruntime python tools/export_embedder_onnx.py
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

MODEL = "BAAI/bge-small-en-v1.5"
OUT = Path("android/app/src/main/assets/embedder")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    work = Path("data/embedder-export")
    work.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "optimum.exporters.onnx", "--model", MODEL, "--task",
         "feature-extraction", "--opset", "17", str(work)],
        check=True,
    )
    (OUT / "model.onnx").write_bytes((work / "model.onnx").read_bytes())
    (OUT / "tokenizer.json").write_bytes((work / "tokenizer.json").read_bytes())
    digest = hashlib.sha256((OUT / "model.onnx").read_bytes()).hexdigest()
    (OUT / "EXPORT.md").write_text(
        f"# Embedder export\n\nModel: {MODEL}\nExported: {datetime.now(UTC).isoformat()}\n"
        f"Opset: 17\nmodel.onnx sha256: {digest}\n\nPooling: CLS token, then L2 normalise, "
        "which is what sentence-transformers does for this model.\n",
        encoding="utf-8",
    )
    print(OUT / "model.onnx", digest)


if __name__ == "__main__":
    main()
```

Run it. Expected: `model.onnx` around one hundred and thirty megabytes for the fp32 export;
if so, re-export with `--dtype fp16` is not supported by this exporter path, so instead run
`onnxruntime.quantization.quantize_dynamic` on it to int8 and commit the quantised file as
`model.onnx`, recording that in `EXPORT.md`. The agreement test below sets the tolerance;
int8 must still pass it. If the fp32 export is already under forty megabytes, keep it.

- [x] **Step 6: Write the agreement test**

```python
# tests/unit/retrieve/test_onnx_agreement.py
"""The phone embeds with ONNX; the PC with sentence-transformers. If they disagree, phone
retrieval silently ranks different passages. This pins them together.

Skipped when onnxruntime is not installed, which is the normal PC state; run it with
    uv run --with onnxruntime --with tokenizers pytest tests/unit/retrieve/test_onnx_agreement.py
whenever the export changes.
"""

from pathlib import Path

import numpy as np
import pytest

onnxruntime = pytest.importorskip("onnxruntime")
tokenizers = pytest.importorskip("tokenizers")

ASSETS = Path("android/app/src/main/assets/embedder")
SENTENCES = [
    "A fever is a body temperature above normal.",
    "Resting heart rate rises during infection.",
    "Alcohol in the evening can raise overnight heart rate.",
]
# Cosine agreement floor. int8 quantisation of a small BERT costs a little; below this
# the phone would rank passages differently from the PC. Recorded with the export.
MIN_COSINE = 0.98


def _onnx_embed(texts: list[str]) -> np.ndarray:
    tok = tokenizers.Tokenizer.from_file(str(ASSETS / "tokenizer.json"))
    tok.enable_padding()
    tok.enable_truncation(max_length=512)
    enc = tok.encode_batch(texts)
    ids = np.array([e.ids for e in enc], dtype=np.int64)
    mask = np.array([e.attention_mask for e in enc], dtype=np.int64)
    types = np.zeros_like(ids)
    sess = onnxruntime.InferenceSession(str(ASSETS / "model.onnx"))
    names = {i.name for i in sess.get_inputs()}
    feed = {"input_ids": ids, "attention_mask": mask}
    if "token_type_ids" in names:
        feed["token_type_ids"] = types
    out = sess.run(None, feed)[0]           # (N, T, 384) last hidden state
    cls = out[:, 0, :]
    return cls / np.linalg.norm(cls, axis=1, keepdims=True)


def test_onnx_matches_sentence_transformers() -> None:
    from wha.retrieve.index import DefaultSentenceTransformerEmbedder

    reference = DefaultSentenceTransformerEmbedder().embed_texts(SENTENCES)
    candidate = _onnx_embed(SENTENCES)
    cosines = np.sum(reference * candidate, axis=1)
    assert cosines.min() >= MIN_COSINE, f"cosine agreement per sentence: {cosines}"
```

- [x] **Step 7: Run it**

Run: `uv run --with onnxruntime --with tokenizers pytest tests/unit/retrieve/test_onnx_agreement.py -v`
Expected: PASS with the cosines printed on failure only. If the floor fails on the int8
model, commit the fp32 model instead and say so in `EXPORT.md`; never lower the floor to
fit.

- [x] **Step 8: Commit**

```bash
git add src/wha/retrieve/embedder_registry.py src/wha/retrieve/knowledge_docs.py tools/export_embedder_onnx.py android/app/src/main/assets/embedder/ tests/unit/retrieve/
git commit -m "Let a host hand the index its own embedder, and export the model the phone will use

The phone cannot run torch. The index already accepted an embedder; nothing let a caller
supply one. The ONNX export is committed with an agreement test so phone and PC retrieve
the same passages for the same question."
```

---

### Task 6: The `android` notification channel

Spec section 4.6. Python decides; Kotlin posts.

**Files:**
- Create: `src/wha/notify/android.py`
- Modify: `src/wha/notify/factory.py`
- Modify: `src/wha/config.py` (read `WHA_NOTIFY_CHANNEL` into settings if not already a field; check line 24 of `service/settings.py` which reads it from the environment directly)
- Modify: `docs/CONTRACTS.md` section 2 (`WHA_NOTIFY_CHANNEL` accepts `android`)
- Test: `tests/unit/notify/test_android_notifier.py`

**Interfaces:**
- Produces: `wha.notify.android.AndroidNotifier(sink: Callable[[dict], bool])` with `channel = "android"`, and `wha.notify.android.set_sink(sink)` used by Kotlin at start-up. The dict handed to the sink has keys `recipient_id`, `kind`, `text`, `interaction_id`, `probe_id`, `options` (list of `{"option_id", "label"}`), `url`.
- `get_notifier()` returns `AndroidNotifier` when `WHA_NOTIFY_CHANNEL=android` and a sink is set; `NullNotifier` when the channel is android and no sink is set (and logs a warning once).

- [x] **Step 1: Write the failing test**

```python
# tests/unit/notify/test_android_notifier.py
"""Python decides to notify; the phone delivers. The notifier hands the phone a dict and
never raises, because a delivery failure inside an episode must degrade to "not
delivered", exactly as Telegram does."""

import logging

from wha.models import AnswerOption
from wha.notify import android
from wha.notify.protocol import MessageKind


def test_send_hands_a_flat_dict_to_the_sink() -> None:
    received: list[dict] = []
    notifier = android.AndroidNotifier(sink=lambda payload: received.append(payload) or True)
    ok = notifier.send(
        recipient_id="me",
        kind=MessageKind.QUESTION,
        text="Did you drink alcohol last night?",
        interaction_id="int-1",
        probe_id="alcohol",
        options=[AnswerOption(option_id="yes", label="Yes"), AnswerOption(option_id="no", label="No")],
    )
    assert ok is True
    assert received == [
        {
            "recipient_id": "me",
            "kind": "QUESTION",
            "text": "Did you drink alcohol last night?",
            "interaction_id": "int-1",
            "probe_id": "alcohol",
            "options": [{"option_id": "yes", "label": "Yes"}, {"option_id": "no", "label": "No"}],
            "url": None,
        }
    ]


def test_a_sink_that_raises_is_reported_as_not_delivered(caplog) -> None:
    def broken(payload: dict) -> bool:
        raise RuntimeError("no notification permission")

    notifier = android.AndroidNotifier(sink=broken)
    with caplog.at_level(logging.WARNING):
        ok = notifier.send("me", MessageKind.ESCALATION, "See a clinician today.")
    assert ok is False
    assert "no notification permission" in caplog.text


def test_factory_picks_android_when_configured_and_a_sink_exists(monkeypatch) -> None:
    from wha.notify import factory

    monkeypatch.setenv("WHA_NOTIFY_CHANNEL", "android")
    android.set_sink(lambda payload: True)
    try:
        assert factory.get_notifier().channel == "android"
    finally:
        android.set_sink(None)


def test_factory_falls_back_to_null_when_android_has_no_sink(monkeypatch) -> None:
    from wha.notify import factory

    monkeypatch.setenv("WHA_NOTIFY_CHANNEL", "android")
    android.set_sink(None)
    assert factory.get_notifier().channel == "none"
```

Note `tests/conftest.py` patches `wha.notify.factory.get_notifier` for the whole session
to return `NullNotifier`. The two factory tests must call the real function: import
`factory` and call `factory.get_notifier.__wrapped__` if you wrap it, or, simpler, read the
original at import time in the test module before conftest's autouse fixture runs is not
possible; so instead write the factory logic in a pure function `select_notifier(channel,
sink, telegram_token, telegram_chat_id)` and test that directly, with `get_notifier`
reduced to reading configuration and calling it. Adjust the last two tests to call
`factory.select_notifier("android", sink=..., telegram_token=None, telegram_chat_id=None)`.

- [x] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/notify/test_android_notifier.py -v`
Expected: FAIL, `ImportError: cannot import name 'android'`.

- [x] **Step 3: Write the notifier and refactor the factory**

```python
# src/wha/notify/android.py
"""The phone as a notification transport.

Python decides when and what to send, exactly as for Telegram. This class hands the message
to a sink the Kotlin side registers at start-up and reports whether delivery succeeded. It
never raises: a delivery failure inside an episode must degrade to "not delivered".
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from typing import Any

from wha.models import AnswerOption
from wha.notify.protocol import MessageKind, Notifier

logger = logging.getLogger(__name__)

Sink = Callable[[dict[str, Any]], bool]

_SINK: Sink | None = None


def set_sink(sink: Sink | None) -> None:
    """Register the phone's delivery function, or clear it."""
    global _SINK
    _SINK = sink


def get_sink() -> Sink | None:
    return _SINK


class AndroidNotifier(Notifier):
    """Delivers through a sink the host process supplied."""

    channel = "android"

    def __init__(self, sink: Sink) -> None:
        self._sink = sink

    def send(
        self,
        recipient_id: str,
        kind: MessageKind,
        text: str,
        interaction_id: str | None = None,
        probe_id: str | None = None,
        options: Sequence[AnswerOption] = (),
        url: str | None = None,
    ) -> bool:
        payload: dict[str, Any] = {
            "recipient_id": recipient_id,
            "kind": str(kind),
            "text": text,
            "interaction_id": interaction_id,
            "probe_id": probe_id,
            "options": [{"option_id": o.option_id, "label": o.label} for o in options],
            "url": url,
        }
        try:
            return bool(self._sink(payload))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Android notification not delivered: %s", exc)
            return False
```

```python
# src/wha/notify/factory.py
"""Notifier selection.

Nothing in the system constructed a notifier, so even a correct ``send`` call had no
transport behind it. This picks one from configuration and falls back to the no-op
transport whenever the configured channel is not fully available, because a missing
token or an unregistered phone sink must degrade to "not delivered" rather than raise
inside an episode.
"""

import logging
import os
from typing import Any

from wha.config import get_settings
from wha.notify.android import AndroidNotifier, Sink, get_sink
from wha.notify.null import NullNotifier
from wha.notify.protocol import Notifier
from wha.notify.telegram import TelegramNotifier

logger = logging.getLogger(__name__)


def select_notifier(
    channel: str,
    sink: Sink | None,
    telegram_token: Any,
    telegram_chat_id: str | None,
) -> Notifier:
    """Pure selection, so it can be tested without the session-wide factory patch."""
    if channel == "android":
        if sink is None:
            logger.warning("WHA_NOTIFY_CHANNEL is android but the phone registered no sink")
            return NullNotifier()
        return AndroidNotifier(sink)

    if telegram_token is None or not telegram_chat_id:
        return NullNotifier()
    secret = (
        telegram_token.get_secret_value()
        if hasattr(telegram_token, "get_secret_value")
        else str(telegram_token)
    )
    if not secret:
        return NullNotifier()
    return TelegramNotifier(token=secret, chat_id=telegram_chat_id)


def get_notifier() -> Notifier:
    """Return the configured outbound transport, or NullNotifier when unavailable."""
    settings = get_settings()
    channel = os.environ.get("WHA_NOTIFY_CHANNEL", "none")
    return select_notifier(
        channel, get_sink(), settings.telegram_bot_token, settings.telegram_chat_id
    )
```

The previous factory ignored `WHA_NOTIFY_CHANNEL` entirely and chose Telegram whenever a
token existed. Keep that behaviour for every channel value other than `android` so the PC
is unchanged; the `if channel == "android"` branch is the only new path.

- [x] **Step 4: Run the notify tests**

Run: `uv run pytest tests/unit/notify -n auto -q`
Expected: all pass.

- [x] **Step 5: Contract and settings**

In `docs/CONTRACTS.md` section 2 change the `WHA_NOTIFY_CHANNEL` row to
"`none` (default), `telegram`, or `android` (the phone; requires the app to have registered
a sink)". In section 7 (service layer) add `wha.notify.android.set_sink` and
`AndroidNotifier` under the notify entries with their signatures above.

- [x] **Step 6: Commit**

```bash
git add src/wha/notify/ docs/CONTRACTS.md tests/unit/notify/test_android_notifier.py
git commit -m "Add the phone as a notification transport beside Telegram

The rules that decide when to speak do not change. The phone registers a delivery
function and the notifier hands it the same message Telegram would get, reporting
failure instead of raising so an episode never dies on a missing permission."
```

---
### Task 7: The facade

Spec section 5. One module Kotlin calls. JSON in, JSON out, never raises.

**Files:**
- Create: `src/wha_android/__init__.py`
- Create: `src/wha_android/facade.py`
- Create: `src/wha_android/envelope.py`
- Modify: `pyproject.toml` (hatch wheel packages)
- Modify: `tests/unit/android/test_core_imports_without_pc_extras.py` (sweep `wha_android` too)
- Modify: `docs/CONTRACTS.md` (new section 12, "The phone facade")
- Test: `tests/unit/android/test_facade.py`
- Test: `tests/unit/android/test_facade_parity.py`

**Interfaces:**
- Produces: every function in `wha_android.facade` listed in the table below. Each returns a `str` of JSON: on success the payload; on failure `{"error": {"kind": "unavailable" | "invalid" | "internal", "message": "..."}}`. Kotlin (Task 12) parses exactly this.
- `wha_android.envelope.guarded(fn)` is the decorator that produces the envelope; `wha_android.envelope.ok(payload) -> str`.

| Facade function | Calls |
|---|---|
| `status(subject_id)` | `service.get_system_status` |
| `config()` | the same enumeration `api.app.get_config` performs, moved to `service.config_export()` so both share it |
| `localise(utc_iso)` | `clock.to_local` |
| `nights(subject_id, days)` | `service.list_nights` with the same end-date rule as the API |
| `night(subject_id, night_date)` | `service.get_night_detail` |
| `pipeline_nights(subject_id, days)` | `service.list_pipeline_nights` |
| `night_pipeline(subject_id, night_date)` | `service.get_night_pipeline` |
| `episodes(subject_id)` | `service.list_episodes` |
| `episode(episode_id)` | `service.get_episode` |
| `pending(subject_id)` | `service.get_pending_interaction` |
| `answer(episode_id, probe_id, option_id, free_text, declined)` | `service.submit_answer` |
| `review(episode_id, decision, edited_prose, rationale)` | `service.submit_human_decision` |
| `conversation(subject_id, limit)` | `service.get_transcript` |
| `conversation_sessions(subject_id, limit_turns)` | `service.get_conversation_sessions` |
| `say(subject_id, text, episode_id)` | `service.send_message` |
| `urgency(subject_id)` | `service.urgency_banner` plus `latest_urgency_reason`, same shape as the API |
| `acknowledge_urgency(subject_id)` | `service.acknowledge_urgency` |
| `handover(subject_id, episode_id)` | `service.build_handover`, same dict as the API |
| `audit(subject_id, limit, offset)` | the same dict the API's `query_audit` builds |
| `audit_export(subject_id)` | `service.export_audit` to a temp file, returns content |
| `settings()` | `service.get_service_settings` |
| `update_settings(patch_json)` | `service.update_settings(**patch)` |
| `profile(subject_id)` and `update_profile(subject_id, patch_json)` | `service.get_subject_profile`, `service.update_subject_profile` |
| `knowledge_provenance()` and `safety_provenance()` | the two provenance functions |
| `diagnose(component, overrides_json)` | `service.test_bridge_connection` or `test_llm_connection` |
| `doctor()` | `service.run_doctor`, rows as dicts |
| `run_ingest()`, `run_nightly()`, `run_episode_tick()`, `run_startup_catchup()` | the scheduler job functions, wrapped by `safe_job_wrapper`'s lock semantics (see Step 3) |
| `fetch_corpus()` | `service.fetch_data("corpus")` |
| `retrieval_ready()` | whether `data/corpus` holds the release named in `corpus-sources.json` with a matching hash |

- [x] **Step 1: Write the failing facade tests**

```python
# tests/unit/android/test_facade.py
"""The phone calls these and parses the JSON. They never raise across the boundary."""

import json

import pytest

from wha_android import envelope, facade


def test_ok_wraps_a_model_as_json() -> None:
    from wha.models import Answer

    out = json.loads(envelope.ok(Answer(probe_id="p", option_id="yes")))
    assert out == {"probe_id": "p", "option_id": "yes", "free_text": None, "declined": False}


def test_guarded_turns_a_service_error_into_an_envelope() -> None:
    from wha.errors import SourceUnavailable

    @envelope.guarded
    def boom() -> str:
        raise SourceUnavailable("bridge is not reachable")

    out = json.loads(boom())
    assert out["error"]["kind"] == "unavailable"
    assert "bridge" in out["error"]["message"]


def test_guarded_marks_bad_input_as_invalid() -> None:
    @envelope.guarded
    def bad() -> str:
        raise ValueError("no such episode")

    assert json.loads(bad())["error"]["kind"] == "invalid"


def test_guarded_marks_everything_else_internal_and_keeps_the_type() -> None:
    @envelope.guarded
    def crash() -> str:
        raise RuntimeError("unexpected")

    out = json.loads(crash())
    assert out["error"]["kind"] == "internal"
    assert "RuntimeError" in out["error"]["message"]


def test_status_on_an_empty_database_is_a_payload_not_an_error(tmp_db_path, monkeypatch) -> None:
    monkeypatch.setenv("WHA_DB_PATH", str(tmp_db_path))
    from wha.config import get_settings

    get_settings(reload=True)
    out = json.loads(facade.status("me"))
    assert "error" not in out
    assert "subject_id" in out


def test_answer_returns_recorded_and_pending_reads_it_back(seeded_pending_episode) -> None:
    """Round trip through the same functions Telegram uses."""
    episode_id, probe_id = seeded_pending_episode
    out = json.loads(facade.answer(episode_id, probe_id, "yes", None, False))
    assert out == {"status": "recorded"}
```

`seeded_pending_episode` is a fixture to add in `tests/unit/android/conftest.py`; copy the
seeding approach from `tests/unit/service/test_episodes.py` (it builds an episode with a
pending interaction against `tmp_db_path`). Check `get_settings` accepts `reload=True`
(`src/wha/llm/client.py:50` calls it that way).

```python
# tests/unit/android/test_facade_parity.py
"""The API and the facade are two clients of one service layer. If one gains an
endpoint the other must too, or the phone and the dashboard drift apart."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _service_calls(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "service":
                names.add(node.attr)
    return names


def test_facade_calls_every_service_function_the_api_calls() -> None:
    api = _service_calls(ROOT / "src/wha/api/app.py")
    facade = _service_calls(ROOT / "src/wha_android/facade.py")
    # The API can delete a subject and probe Telegram; the phone does neither, on purpose.
    phone_never = {"delete_all_subject_data", "test_telegram_connection", "list_subjects"}
    missing = api - facade - phone_never
    assert not missing, f"the API reaches these service functions and the facade does not: {sorted(missing)}"


def test_every_facade_function_is_guarded() -> None:
    source = (ROOT / "src/wha_android/facade.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    unguarded = [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and not node.name.startswith("_")
        and not any(
            (isinstance(d, ast.Attribute) and d.attr == "guarded")
            or (isinstance(d, ast.Name) and d.id == "guarded")
            for d in node.decorator_list
        )
    ]
    assert not unguarded, f"facade functions that can raise across the boundary: {unguarded}"


def test_contract_lists_every_facade_function() -> None:
    contract = (ROOT / "docs/CONTRACTS.md").read_text(encoding="utf-8")
    tree = ast.parse((ROOT / "src/wha_android/facade.py").read_text(encoding="utf-8"))
    public = [n.name for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]
    missing = [name for name in public if not re.search(rf"`{name}\(", contract)]
    assert not missing, f"docs/CONTRACTS.md does not list: {missing}"
```

- [x] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/unit/android/test_facade.py tests/unit/android/test_facade_parity.py -v`
Expected: FAIL, `ModuleNotFoundError: wha_android`.

- [x] **Step 3: Write the envelope and the facade**

```python
# src/wha_android/__init__.py
"""The phone's entry points into the core. Nothing else on the phone imports wha directly."""
```

```python
# src/wha_android/envelope.py
"""Every facade call returns JSON and never raises across the Kotlin boundary.

Three kinds, enumerated in docs/CONTRACTS.md section 12. A screen shows each in words with
the action available: `unavailable` offers retry or Settings, `invalid` shows the message,
`internal` shows the message and keeps the rest of the screen usable.
"""

from __future__ import annotations

import functools
import json
import logging
import traceback
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from wha.errors import WhaError

logger = logging.getLogger(__name__)

# Service errors that mean "something outside the phone is not there right now".
_UNAVAILABLE_NAMES = {"SourceUnavailable", "ConfigError", "LLMUnavailable", "ProviderError"}


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        return {k: _to_jsonable(getattr(value, k)) for k in value.__dataclass_fields__}
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def ok(payload: Any) -> str:
    return json.dumps(_to_jsonable(payload), ensure_ascii=False)


def error(kind: str, message: str) -> str:
    return json.dumps({"error": {"kind": kind, "message": message}}, ensure_ascii=False)


def guarded(fn: Callable[..., Any]) -> Callable[..., str]:
    """Wrap a facade function so it always returns a JSON string."""

    @functools.wraps(fn)
    def inner(*args: Any, **kwargs: Any) -> str:
        try:
            result = fn(*args, **kwargs)
            return result if isinstance(result, str) else ok(result)
        except WhaError as exc:
            kind = "unavailable" if type(exc).__name__ in _UNAVAILABLE_NAMES else "invalid"
            logger.warning("%s: %s", type(exc).__name__, exc)
            return error(kind, str(exc))
        except (ValueError, KeyError, TypeError) as exc:
            logger.warning("%s: %s", type(exc).__name__, exc)
            return error("invalid", str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.error("facade %s failed:\n%s", fn.__name__, traceback.format_exc())
            return error("internal", f"{type(exc).__name__}: {exc}")

    return inner
```

Check `src/wha/errors.py` for the real subclass names and put every "outside the phone"
error into `_UNAVAILABLE_NAMES`; the names above are a starting guess and the test in
Step 1 asserts `SourceUnavailable` maps to `unavailable`.

```python
# src/wha_android/facade.py
"""What Kotlin calls. Every function is @guarded and returns JSON.

A second client of the same service layer the HTTP API exposes; see the parity test in
tests/unit/android/test_facade_parity.py. Reads of the record use the same end-date rule
as the API: the newest recorded night, so "the last sixty nights" means the last sixty
the watch produced, not sixty calendar days ending today.
"""

from __future__ import annotations

import json
import tempfile
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from wha import service
from wha.clock import to_local
from wha.models import Answer, AuditFilter, SubjectProfilePatch
from wha_android.envelope import error, guarded, ok

# One job at a time, like safe_job_wrapper's lock on the PC. WorkManager may overlap an
# ingest with a tick; the second waits rather than racing the first for the database.
_JOB_LOCK = threading.Lock()


def _record_end(subject_id: str) -> date:
    newest = service.latest_recorded_night(subject_id)
    return newest if newest is not None else date.today()


# ----------------------------------------------------------------- configuration


@guarded
def config() -> str:
    return ok(service.config_export())


@guarded
def localise(utc_iso: str) -> str:
    return ok({"local": to_local(datetime.fromisoformat(utc_iso)).isoformat()})


@guarded
def settings() -> str:
    return ok(service.get_service_settings())


@guarded
def update_settings(patch_json: str) -> str:
    return ok(service.update_settings(**json.loads(patch_json)))


@guarded
def profile(subject_id: str) -> str:
    return ok(service.get_subject_profile(subject_id))


@guarded
def update_profile(subject_id: str, patch_json: str) -> str:
    patch = SubjectProfilePatch.model_validate(json.loads(patch_json))
    return ok(service.update_subject_profile(patch, subject_id=subject_id))


# ------------------------------------------------------------------------ status


@guarded
def status(subject_id: str) -> str:
    return ok(service.get_system_status(subject_id))


@guarded
def urgency(subject_id: str) -> str:
    state = service.urgency_banner(subject_id)
    return ok(
        {
            "urgency": state["urgency"],
            "reason": service.latest_urgency_reason(subject_id),
            "set_on": state["set_on"],
            "days_ago": state["days_ago"],
            "stale": state["stale"],
            "cleared": state["cleared"],
        }
    )


@guarded
def acknowledge_urgency(subject_id: str) -> str:
    return ok(service.acknowledge_urgency(subject_id))


# ------------------------------------------------------------------------ nights


@guarded
def nights(subject_id: str, days: int = 60) -> str:
    end = _record_end(subject_id)
    return ok(service.list_nights(subject_id, start=end - timedelta(days=days), end=end))


@guarded
def night(subject_id: str, night_date: str) -> str:
    return ok(service.get_night_detail(subject_id, date.fromisoformat(night_date)))


@guarded
def pipeline_nights(subject_id: str, days: int = 60) -> str:
    return ok(service.list_pipeline_nights(subject_id, days=days, end=_record_end(subject_id)))


@guarded
def night_pipeline(subject_id: str, night_date: str) -> str:
    return ok(service.get_night_pipeline(subject_id, date.fromisoformat(night_date)))


# ---------------------------------------------------------------------- episodes


@guarded
def episodes(subject_id: str) -> str:
    return ok(service.list_episodes(subject_id))


@guarded
def episode(episode_id: str) -> str:
    return ok(service.get_episode(episode_id))


@guarded
def pending(subject_id: str) -> str:
    return ok(service.get_pending_interaction(subject_id))


@guarded
def answer(
    episode_id: str,
    probe_id: str,
    option_id: str | None,
    free_text: str | None,
    declined: bool,
) -> str:
    service.submit_answer(
        episode_id,
        Answer(probe_id=probe_id, option_id=option_id, free_text=free_text, declined=declined),
    )
    return ok({"status": "recorded"})


@guarded
def review(
    episode_id: str, decision: str, edited_prose: str | None, rationale: str | None
) -> str:
    service.submit_human_decision(
        episode_id=episode_id, decision=decision, edited_prose=edited_prose, rationale=rationale
    )
    return ok({"status": "recorded"})


@guarded
def handover(subject_id: str, episode_id: str | None = None) -> str:
    h = service.build_handover(subject_id, episode_id=episode_id)
    return ok(
        {
            "text": h.as_text(),
            "situation": h.situation,
            "background": h.background,
            "assessment": h.assessment,
            "recommendation": h.recommendation,
            "questions": h.questions,
            "what_this_is_not": h.what_this_is_not,
        }
    )


# ------------------------------------------------------------------ conversation


@guarded
def conversation(subject_id: str, limit: int = 40) -> str:
    return ok(service.get_transcript(subject_id, limit=limit))


@guarded
def conversation_sessions(subject_id: str, limit_turns: int = 400) -> str:
    return ok(service.get_conversation_sessions(subject_id, limit_turns=limit_turns))


@guarded
def say(subject_id: str, text: str, episode_id: str | None = None) -> str:
    return ok(service.send_message(subject_id=subject_id, text=text, episode_id=episode_id))


# ------------------------------------------------------------------------- audit


@guarded
def audit(subject_id: str, limit: int = 100, offset: int = 0) -> str:
    audit_filter = AuditFilter(subject_id=subject_id)
    intact, bad_event = service.verify_hash_chain(subject_id)
    return ok(
        {
            "events": service.query_audit(audit_filter, limit=limit, offset=offset),
            "plain": service.list_plain_records(subject_id, limit=limit),
            "count": service.count_audit_events(subject_id),
            "intact": intact,
            "first_bad_event": bad_event,
            "permitted_tools": sorted(service.get_permitted_tool_names()),
        }
    )


@guarded
def audit_export(subject_id: str) -> str:
    target = Path(tempfile.mkdtemp()) / f"audit-{subject_id}.jsonl"
    service.export_audit(AuditFilter(subject_id=subject_id), target)
    return ok({"content": target.read_text(encoding="utf-8")})


# --------------------------------------------------------------------- knowledge


@guarded
def knowledge_provenance() -> str:
    return ok(service.get_knowledge_provenance())


@guarded
def safety_provenance() -> str:
    return ok(service.get_safety_rule_provenance())


# ------------------------------------------------------------------- diagnostics


@guarded
def diagnose(component: str, overrides_json: str = "{}") -> str:
    checks = {"bridge": service.test_bridge_connection, "llm": service.test_llm_connection}
    if component not in checks:
        return error("invalid", f"No such component: {component}")
    return ok(checks[component](**json.loads(overrides_json)))


@guarded
def doctor() -> str:
    return ok([{"name": i.name, "status": str(i.status), "detail": i.detail} for i in service.run_doctor()])


@guarded
def retrieval_ready() -> str:
    return ok({"ready": service.corpus_present()})


@guarded
def fetch_corpus() -> str:
    return ok({"message": service.fetch_data("corpus")})


# -------------------------------------------------------------------------- jobs


def _job(name: str, fn: Any) -> str:
    with _JOB_LOCK:
        started = datetime.now().isoformat()
        result = fn()
        service.record_component_status(name, "ok", "ran from the phone")
        return ok({"job": name, "started": started, "result": result})


@guarded
def run_ingest() -> str:
    return _job("ingest", lambda: service.run_ingest())


@guarded
def run_nightly() -> str:
    from wha.service.scheduler import _rescore_recent

    return _job("nightly", lambda: [d.model_dump(mode="json") for d in _rescore_recent()])


@guarded
def run_episode_tick() -> str:
    return _job("episode_tick", lambda: service.run_episode_tick())


@guarded
def run_startup_catchup() -> str:
    from wha.service.scheduler import run_startup_catchup

    return _job("startup_catchup", lambda: run_startup_catchup())
```

Two service additions this needs, both small and both PC-neutral:

1. `service.config_export()`: move the body of `api.app.get_config` into
   `src/wha/service/config_export.py` and have the API call it. Same behaviour, one place.
2. `service.corpus_present()`: in `src/wha/service/corpus.py`, returns True when
   `data/corpus/` contains the release file named by `corpus-sources.json` and its SHA-256
   matches. Read how `wha doctor` already checks the corpus (`service/doctor.py`) and reuse
   that check rather than writing a second.

Check `record_component_status`'s real signature in `service/status.py` and match it.

`wha.service.scheduler` imports `apscheduler` at module top, which the isolation sweep in
Task 4 lists as PC-only; `run_nightly` and `run_startup_catchup` above import it inside
the function. Move `_rescore_recent` and `run_startup_catchup` into
`src/wha/service/jobs.py` (no apscheduler import) and have `scheduler.py` import them from
there, so the facade imports `wha.service.jobs` at top instead. Add `jobs` to
`service/__init__.py` exports and to `DECLARED_EDGES` if a new package edge appears (it
does not; `jobs` is inside `service`).

- [x] **Step 4: Hatch packages and the isolation sweep**

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/wha", "src/wha_android"]
```

In `tests/unit/android/test_core_imports_without_pc_extras.py`, after the `wha` walk add
`import wha_android` and walk it the same way. Add `"facade"`-style edges: `wha_android` is
outside `src/wha`, so `test_layering.py` does not see it; nothing to declare there.

- [x] **Step 5: Contract section 12**

Append to `docs/CONTRACTS.md`:

```markdown
## 12. The phone facade

`src/wha_android/facade.py` is what the Android app calls, through Chaquopy. Every
function is decorated with `guarded` and returns a JSON string: the payload on success,
or `{"error": {"kind": K, "message": M}}` where K is one of `unavailable` (the webhook,
the provider or the corpus is not there), `invalid` (bad input or no such record), or
`internal` (anything else, with the exception type in M). A test asserts every public
function is guarded and that this table names every one of them.

| Function | Returns the JSON of |
|---|---|
| `config()` | the same dict as `GET /config` |
| `localise(utc_iso)` | `{"local": iso}` |
| `settings()` and `update_settings(patch_json)` | `Settings` and the change report |
| `profile(subject_id)` and `update_profile(subject_id, patch_json)` | `SubjectProfile` |
| `status(subject_id)` | `SystemStatus` |
| `urgency(subject_id)` and `acknowledge_urgency(subject_id)` | the same dicts as the API |
| `nights(subject_id, days)`, `night(subject_id, night_date)` | `list[NightSummary]`, `NightDetail` |
| `pipeline_nights(subject_id, days)`, `night_pipeline(subject_id, night_date)` | `list[PipelineNightRef]`, `NightPipeline` |
| `episodes(subject_id)`, `episode(episode_id)`, `pending(subject_id)` | `list[EpisodeSummary]`, `EpisodeDetail`, `PendingInteraction | null` |
| `answer(episode_id, probe_id, option_id, free_text, declined)` | `{"status": "recorded"}` |
| `review(episode_id, decision, edited_prose, rationale)` | `{"status": "recorded"}` |
| `handover(subject_id, episode_id)` | the same dict as the API |
| `conversation(subject_id, limit)`, `conversation_sessions(subject_id, limit_turns)`, `say(subject_id, text, episode_id)` | as the API |
| `audit(subject_id, limit, offset)`, `audit_export(subject_id)` | as the API |
| `knowledge_provenance()`, `safety_provenance()` | as the API |
| `diagnose(component, overrides_json)`, `doctor()` | check result; `[{name, status, detail}]` |
| `retrieval_ready()`, `fetch_corpus()` | `{"ready": bool}`; `{"message": str}` |
| `run_ingest()`, `run_nightly()`, `run_episode_tick()`, `run_startup_catchup()` | `{"job", "started", "result"}`; serialised by one lock |
```

Adjust the model names in the table to the ones `service` really returns (read the return
annotations); the parity test only checks function names, so the table's right-hand column
is on you.

- [x] **Step 6: Run the tests**

Run: `uv run pytest tests/unit/android tests/unit/api tests/unit/test_layering.py tests/unit/test_contracts.py -n auto -q`
Expected: all pass.

- [x] **Step 7: Commit**

```bash
git add src/wha_android/ src/wha/service/ src/wha/api/app.py pyproject.toml docs/CONTRACTS.md tests/unit/android/
git commit -m "Give the phone one door into the core, and keep it level with the API

Kotlin calls a facade that returns the same models the HTTP API returns, as JSON, and
never raises. A parity test keeps the two clients calling the same service functions so
the dashboard and the phone cannot quietly diverge."
```

---

### Task 8: The lineage table

Spec section 7.5. Which step's outputs each step consumes, declared once.

**Files:**
- Modify: `src/wha/models.py` (after `CANONICAL_PIPELINE_STEPS`, around line 588)
- Modify: `docs/CONTRACTS.md` section 6.2
- Modify: `src/wha_android/facade.py` (add `lineage()`)
- Test: `tests/unit/test_lineage.py`

**Interfaces:**
- Produces: `wha.models.PIPELINE_LINEAGE: tuple[LineageEdge, ...]` where `LineageEdge(from_step: str, output: str, to_step: str)`; `facade.lineage()` returns it as a list of dicts.

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_lineage.py
"""The Record tab highlights where a result came from. The edges are declared in one
place and must describe steps that exist, in an order that is possible."""

from wha.models import CANONICAL_PIPELINE_STEPS, PIPELINE_LINEAGE

ORDINAL = {s.step_id: s.ordinal for s in CANONICAL_PIPELINE_STEPS}


def test_every_edge_names_real_steps() -> None:
    for edge in PIPELINE_LINEAGE:
        assert edge.from_step in ORDINAL, edge
        assert edge.to_step in ORDINAL, edge


def test_no_edge_runs_backwards_except_the_answer_loop() -> None:
    """Data flows forward through the numbered steps. The one declared exception is an
    answer (step 15) feeding investigate (step 11), which is the hypothesis loop."""
    allowed_backward = {("answer", "investigate"), ("answer", "believe")}
    for edge in PIPELINE_LINEAGE:
        if (edge.from_step, edge.to_step) in allowed_backward:
            continue
        assert ORDINAL[edge.from_step] < ORDINAL[edge.to_step], edge


def test_every_step_after_the_first_consumes_something() -> None:
    consumers = {e.to_step for e in PIPELINE_LINEAGE}
    orphans = [s.step_id for s in CANONICAL_PIPELINE_STEPS if s.ordinal > 1 and s.step_id not in consumers]
    assert not orphans, f"steps with no declared input: {orphans}"


def test_edges_are_unique() -> None:
    seen = [(e.from_step, e.output, e.to_step) for e in PIPELINE_LINEAGE]
    assert len(seen) == len(set(seen))
```

- [x] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_lineage.py -v`
Expected: FAIL, `ImportError: PIPELINE_LINEAGE`.

- [x] **Step 3: Declare the edges**

Every `output` name below must be a key that `service/pipeline.py` writes into that
step's `outputs` dict. Read `_collect_step`, `_store_step`, `_sleep_window_step`,
`_features_step`, `_baseline_step`, `_subtract_step`, `_detect_step`,
`_safety_floor_step`, `_episode_open_step`, `_agent_steps`, `_answer_step`,
`_deliver_step` and `_safety_steps` and use their actual key names; the names here are
the ones to look for and rename if the code differs.

```python
class LineageEdge(BaseModel):
    """One named output of one step, read by a later step. Drawn on the Record tab."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    from_step: str
    output: str
    to_step: str


PIPELINE_LINEAGE: tuple[LineageEdge, ...] = (
    LineageEdge(from_step="collect", output="samples", to_step="store"),
    LineageEdge(from_step="store", output="heart_rate_rows", to_step="sleep_window"),
    LineageEdge(from_step="store", output="sleep_rows", to_step="sleep_window"),
    LineageEdge(from_step="sleep_window", output="window", to_step="features"),
    LineageEdge(from_step="store", output="heart_rate_rows", to_step="features"),
    LineageEdge(from_step="features", output="resting_hr_bpm", to_step="baseline"),
    LineageEdge(from_step="features", output="resting_hr_bpm", to_step="subtract_explained"),
    LineageEdge(from_step="baseline", output="centre_bpm", to_step="subtract_explained"),
    LineageEdge(from_step="store", output="exercise_rows", to_step="subtract_explained"),
    LineageEdge(from_step="subtract_explained", output="residual_bpm", to_step="detect"),
    LineageEdge(from_step="baseline", output="rung", to_step="detect"),
    LineageEdge(from_step="detect", output="level", to_step="safety_floor"),
    LineageEdge(from_step="store", output="oxygen_rows", to_step="safety_floor"),
    LineageEdge(from_step="detect", output="flagged", to_step="episode_open"),
    LineageEdge(from_step="safety_floor", output="events", to_step="episode_open"),
    LineageEdge(from_step="episode_open", output="episode_id", to_step="preload"),
    LineageEdge(from_step="preload", output="facts", to_step="investigate"),
    LineageEdge(from_step="investigate", output="evidence", to_step="believe"),
    LineageEdge(from_step="believe", output="belief", to_step="decide"),
    LineageEdge(from_step="decide", output="action", to_step="ask"),
    LineageEdge(from_step="decide", output="action", to_step="conclude"),
    LineageEdge(from_step="ask", output="question", to_step="answer"),
    LineageEdge(from_step="answer", output="answer", to_step="investigate"),
    LineageEdge(from_step="answer", output="answer", to_step="believe"),
    LineageEdge(from_step="believe", output="belief", to_step="conclude"),
    LineageEdge(from_step="conclude", output="draft", to_step="critique"),
    LineageEdge(from_step="critique", output="draft", to_step="review"),
    LineageEdge(from_step="review", output="decision", to_step="deliver"),
    LineageEdge(from_step="answer", output="free_text", to_step="safety_phrase_rules"),
    LineageEdge(from_step="safety_phrase_rules", output="events", to_step="safety_triage"),
    LineageEdge(from_step="safety_triage", output="urgency", to_step="deliver"),
)
```

Add a fifth lineage test once the names are settled:

```python
def test_every_output_named_is_one_the_pipeline_writes() -> None:
    """Read from the source rather than a fixture: the keys appear as string literals
    in the outputs= dicts of service/pipeline.py."""
    from pathlib import Path

    source = Path("src/wha/service/pipeline.py").read_text(encoding="utf-8")
    missing = [e for e in PIPELINE_LINEAGE if f'"{e.output}"' not in source]
    assert not missing, f"lineage names outputs the pipeline never writes: {missing}"
```

- [x] **Step 4: Facade and contract**

In `facade.py`:

```python
@guarded
def lineage() -> str:
    from wha.models import PIPELINE_LINEAGE

    return ok(list(PIPELINE_LINEAGE))
```

In `docs/CONTRACTS.md` section 6.2 add `LineageEdge` with its three fields and the
sentence "`PIPELINE_LINEAGE` declares which named output of which step each later step
reads; tests/unit/test_lineage.py checks every edge against the step list and the
pipeline's output keys." Add `lineage()` to the section 12 table.

- [x] **Step 5: Run**

Run: `uv run pytest tests/unit/test_lineage.py tests/unit/test_contracts.py tests/unit/android -n auto -q`
Expected: pass.

- [x] **Step 6: Commit**

```bash
git add src/wha/models.py src/wha_android/facade.py docs/CONTRACTS.md tests/unit/test_lineage.py
git commit -m "Declare which step reads which result, so a screen can show where a number came from

The Record tab traces lineage on tap. The edges live beside the step list, checked against
it and against the output keys the pipeline actually writes, so the picture cannot claim a
flow the code does not have."
```

---

### Task 9: Shared wording

Spec section 7.4. The sentences the dashboard says, available to the facade without the
facade importing `wha.ui`.

**Files:**
- Create: `src/wha/wording.py` (the `TEXT` dict and the `text`, `level`, `rung`, `step` helpers, moved verbatim from `src/wha/ui/explain.py`)
- Modify: `src/wha/ui/explain.py` (becomes `from wha.wording import TEXT, text, level, rung, step` plus `__all__`)
- Modify: `tests/unit/test_layering.py` (`DECLARED_EDGES`: `wording` depends on nothing; `ui` may import `wording`; add `"wording"` to `ALLOWED_PREFIXES` in `tests/ui/test_ui_boundary.py`)
- Modify: `src/wha_android/facade.py` (add `wording()`)
- Test: `tests/unit/test_wording_shared.py`

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_wording_shared.py
"""One set of sentences for both surfaces. The dashboard's module is a re-export."""


def test_dashboard_and_core_wording_are_the_same_object() -> None:
    from wha import wording
    from wha.ui import explain

    assert explain.TEXT is wording.TEXT
    assert explain.text is wording.text
    assert explain.level is wording.level


def test_facade_returns_every_key() -> None:
    import json

    from wha import wording
    from wha_android import facade

    out = json.loads(facade.wording())
    assert set(out) == set(wording.TEXT)


def test_core_wording_contains_no_digit() -> None:
    from wha import wording

    offenders = [k for k, v in wording.TEXT.items() if any(c.isdigit() for c in v)]
    assert not offenders, f"wording with a figure in it: {offenders}"
```

- [x] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_wording_shared.py -v`
Expected: FAIL, `ModuleNotFoundError: wha.wording`.

- [x] **Step 3: Move the module**

`git mv src/wha/ui/explain.py src/wha/wording.py`, then fix the docstring's path reference
(`Add it to wha/ui/explain.py` becomes `wha/wording.py`) and recreate
`src/wha/ui/explain.py`:

```python
"""The dashboard's view of the shared wording. Every sentence lives in wha.wording so
the phone can say the same thing; this module exists so no screen import changes."""

from wha.wording import TEXT, level, rung, step, text

__all__ = ["TEXT", "level", "rung", "step", "text"]
```

Facade:

```python
@guarded
def wording() -> str:
    from wha.wording import TEXT

    return ok(dict(TEXT))
```

Layering: add `"wording": set()` to `DECLARED_EDGES` and `"wording"` to `ui`'s set;
`ALLOWED_PREFIXES` in `tests/ui/test_ui_boundary.py` gains `"wha.wording"`. The
never-say test in `tests/unit/ui/test_wording_never_say.py` imports the dashboard module;
it keeps working through the re-export, and it now also covers the phone.

- [x] **Step 4: Run**

Run: `uv run pytest tests/unit/test_wording_shared.py tests/unit/ui tests/ui/test_ui_boundary.py tests/unit/test_layering.py tests/unit/android -n auto -q`
Expected: pass.

- [x] **Step 5: Commit**

```bash
git add src/wha/wording.py src/wha/ui/explain.py src/wha_android/facade.py tests/
git commit -m "Move the screen wording where both the dashboard and the phone can read it

Two surfaces saying different things about the same step is the drift the explain module
was written to prevent. The dashboard keeps its import path through a re-export."
```

---

### Task 10: The bounded loop, only if Task 2 chose outcome (b)

Spec section 4.2. Skip this task entirely under outcome (a). Under (c) the plan has
already stopped.

**Files:**
- Create: `src/wha/agent/pause.py` (the interrupt replacement)
- Create: `src/wha/agent/loop.py` (the runner)
- Modify: `src/wha/agent/nodes/ask.py:172` and `src/wha/agent/nodes/review.py:47` (`from wha.agent.pause import interrupt`)
- Modify: `src/wha/agent/graph.py` (keep `route_after_ask`, `route_after_decide`, the public names `get_agent_graph`, `build_agent_graph`, `get_sqlite_checkpointer`, `get_pending_interrupt`, `run_episode_step`; their bodies delegate to `loop.py`)
- Modify: `src/wha/db/schema.sql` and `docs/CONTRACTS.md` section 5 (one table `agent_checkpoints`)
- Modify: `pyproject.toml`, `docs/CONTRACTS.md` section 1 (drop `langgraph`, `langgraph-checkpoint-sqlite`)
- Test: `tests/unit/agent/test_loop.py`; the existing `tests/unit/agent/` and `tests/integration/test_human_review.py`, `tests/integration/test_production_loop.py` must pass unchanged.

**Interfaces:**
- Consumes: the eight node functions, `EpisodeState`, the two route functions, `AGENT_NODES`.
- Produces: the same public functions in `wha.agent.graph` with the same signatures, so `service/episodes.py:928-982` and `service/demo.py:351-380` do not change. `build_agent_graph(...)` returns a `Loop` whose `.nodes` is a dict keyed by node name (the steps test reads `graph.nodes`; check what attribute it reads at `tests/unit/agent/test_steps.py:44-47` and match it).

- [ ] **Step 1: Write the failing loop test**

```python
# tests/unit/agent/test_loop.py
"""The loop must behave like the graph it replaces on the three things that matter:
it pauses at ask and review, it resumes with the value supplied, and it survives a
process restart through the database."""

from pathlib import Path

from wha.agent import pause
from wha.agent.loop import Loop, LoopState


def _node_a(state):
    return {"step": state.get("step", 0) + 1, "trail": state.get("trail", []) + ["a"]}


def _node_pause(state):
    answer = pause.interrupt({"kind": "question", "text": "why?"})
    return {"step": state.get("step", 0) + 1, "trail": state.get("trail", []) + [f"paused:{answer}"]}


def _node_end(state):
    return {"step": state.get("step", 0) + 1, "trail": state.get("trail", []) + ["end"]}


def _route(state):
    return "pause" if "a" in state.get("trail", []) and not any(t.startswith("paused") for t in state["trail"]) else "end"


def _build(db: Path) -> Loop:
    loop = Loop(db_path=db)
    loop.add_node("a", _node_a)
    loop.add_node("pause", _node_pause)
    loop.add_node("end", _node_end)
    loop.add_edge(Loop.START, "a")
    loop.add_conditional_edges("a", _route, {"pause": "pause", "end": "end"})
    loop.add_edge("pause", "end")
    loop.add_edge("end", Loop.END)
    return loop


def test_pauses_at_interrupt_and_reports_the_payload(tmp_path) -> None:
    loop = _build(tmp_path / "t.sqlite")
    result = loop.invoke({"episode_id": "e1"}, thread_id="e1", recursion_limit=10)
    assert result["status"] == "parked"
    assert loop.pending("e1") == {"kind": "question", "text": "why?"}


def test_resume_reruns_the_paused_node_with_the_value(tmp_path) -> None:
    db = tmp_path / "t.sqlite"
    loop = _build(db)
    loop.invoke({"episode_id": "e1"}, thread_id="e1", recursion_limit=10)
    reopened = _build(db)  # a new process
    result = reopened.invoke(None, thread_id="e1", recursion_limit=10, resume="yes")
    assert result["trail"] == ["a", "paused:yes", "end"]
    assert reopened.pending("e1") is None


def test_recursion_limit_marks_unresolved(tmp_path) -> None:
    loop = Loop(db_path=tmp_path / "t.sqlite")
    loop.add_node("spin", lambda s: {"step": s.get("step", 0) + 1})
    loop.add_edge(Loop.START, "spin")
    loop.add_edge("spin", "spin")
    result = loop.invoke({"episode_id": "e2"}, thread_id="e2", recursion_limit=5)
    assert result["status"] == "unresolved"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/agent/test_loop.py -v`
Expected: FAIL, `ModuleNotFoundError: wha.agent.pause`.

- [ ] **Step 3: Write `pause.py` and `loop.py`**

```python
# src/wha/agent/pause.py
"""The one thing LangGraph did that the loop has to reproduce exactly.

``interrupt(payload)`` stops the current node and parks the episode with the payload
visible to the interface. On resume the node runs again from the top and this call
returns the supplied value. So everything before it in a node must be idempotent, which
was already the contract (CONTRACTS.md section 1.1) and is unchanged.
"""

from __future__ import annotations

import threading
from typing import Any

_LOCAL = threading.local()


class Paused(Exception):
    """Raised by interrupt() when no resume value is available."""

    def __init__(self, payload: Any) -> None:
        super().__init__("paused")
        self.payload = payload


def _slot() -> dict[str, Any]:
    if not hasattr(_LOCAL, "slot"):
        _LOCAL.slot = {}
    return _LOCAL.slot


def begin_node(resume: Any) -> None:
    """Called by the loop before running a node. ``resume`` is the value waiting, or a
    sentinel meaning none."""
    _slot()["resume"] = resume


def interrupt(payload: Any) -> Any:
    slot = _slot()
    resume = slot.get("resume", NO_VALUE)
    if resume is NO_VALUE:
        raise Paused(payload)
    slot["resume"] = NO_VALUE  # consumed; a second interrupt in the same node pauses again
    return resume


NO_VALUE = object()
```

```python
# src/wha/agent/loop.py
"""A bounded loop over named nodes, with pause and resume through SQLite.

Replaces LangGraph's StateGraph for this project: the graph here has eight nodes, two
conditional edges and one kind of pause, and it needed four native packages the phone
cannot build. The semantics kept: nodes receive the whole state and return a partial
update; list fields declared with a reducer in EpisodeState are appended, everything else
replaced; a pause parks the episode with a payload; resume re-runs the paused node with the
value; a recursion limit closes the episode as unresolved; state survives the process.
"""

from __future__ import annotations

import json
import sqlite3
import typing
from collections.abc import Callable
from pathlib import Path
from typing import Any

from wha.agent import pause
from wha.agent.state import EpisodeState
from wha.db.connection import connect

LoopState = dict[str, Any]

_APPEND_FIELDS: frozenset[str] = frozenset(
    name
    for name, hint in typing.get_type_hints(EpisodeState, include_extras=True).items()
    if typing.get_origin(hint) is typing.Annotated
)


def _merge(state: LoopState, update: LoopState) -> LoopState:
    merged = dict(state)
    for key, value in (update or {}).items():
        if key in _APPEND_FIELDS and isinstance(value, list):
            merged[key] = list(merged.get(key, [])) + value
        else:
            merged[key] = value
    return merged


class Loop:
    START = "__start__"
    END = "__end__"

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path
        self.nodes: dict[str, Callable[[LoopState], LoopState]] = {}
        self._edges: dict[str, str] = {}
        self._conditional: dict[str, tuple[Callable[[LoopState], str], dict[str, str]]] = {}
        self._memory: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------ construction

    def add_node(self, name: str, fn: Callable[[LoopState], LoopState]) -> None:
        self.nodes[name] = fn

    def add_edge(self, src: str, dst: str) -> None:
        self._edges[src] = dst

    def add_conditional_edges(
        self, src: str, router: Callable[[LoopState], str], mapping: dict[str, str]
    ) -> None:
        self._conditional[src] = (router, mapping)

    def _next(self, current: str, state: LoopState) -> str:
        if current in self._conditional:
            router, mapping = self._conditional[current]
            return mapping[router(state)]
        return self._edges[current]

    # ------------------------------------------------------------- persistence

    def _conn(self) -> sqlite3.Connection | None:
        if self.db_path is None:
            return None
        conn = connect(self.db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS agent_checkpoints ("
            "thread_id TEXT PRIMARY KEY, state_json TEXT NOT NULL, "
            "node TEXT, pending_json TEXT, updated_utc TEXT NOT NULL)"
        )
        return conn

    def _load(self, thread_id: str) -> dict[str, Any] | None:
        conn = self._conn()
        if conn is None:
            return self._memory.get(thread_id)
        try:
            row = conn.execute(
                "SELECT state_json, node, pending_json FROM agent_checkpoints WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return {
            "state": json.loads(row[0]),
            "node": row[1],
            "pending": json.loads(row[2]) if row[2] else None,
        }

    def _save(self, thread_id: str, state: LoopState, node: str | None, pending: Any) -> None:
        record = {"state": _jsonable(state), "node": node, "pending": pending}
        conn = self._conn()
        if conn is None:
            self._memory[thread_id] = record
            return
        from datetime import UTC, datetime

        try:
            conn.execute(
                "INSERT OR REPLACE INTO agent_checkpoints VALUES (?, ?, ?, ?, ?)",
                (
                    thread_id,
                    json.dumps(record["state"]),
                    node,
                    json.dumps(pending) if pending is not None else None,
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def has_checkpoint(self, thread_id: str) -> bool:
        return self._load(thread_id) is not None

    def pending(self, thread_id: str) -> Any | None:
        saved = self._load(thread_id)
        return saved["pending"] if saved else None

    # --------------------------------------------------------------- execution

    def invoke(
        self,
        payload: LoopState | None,
        thread_id: str,
        recursion_limit: int,
        resume: Any = pause.NO_VALUE,
        restart: bool = False,
    ) -> LoopState:
        saved = None if restart else self._load(thread_id)
        if saved is not None and payload is None:
            state, current = _rehydrate(saved["state"]), saved["node"] or self.START
        else:
            state, current = dict(payload or {}), self.START
        if current == self.START:
            current = self._next(self.START, state)

        steps = 0
        pending_resume = resume
        while current != self.END:
            if steps >= recursion_limit:
                state["status"] = "unresolved"
                self._save(thread_id, state, None, None)
                return state
            pause.begin_node(pending_resume)
            pending_resume = pause.NO_VALUE
            try:
                update = self.nodes[current](state)
            except pause.Paused as parked:
                state["status"] = "parked"
                self._save(thread_id, state, current, parked.payload)
                return state
            state = _merge(state, update)
            steps += 1
            current = self._next(current, state)

        state.setdefault("status", "closed")
        self._save(thread_id, state, None, None)
        return state


def _jsonable(state: LoopState) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in state.items():
        if hasattr(value, "model_dump"):
            out[key] = {"__model__": type(value).__name__, "data": value.model_dump(mode="json")}
        elif isinstance(value, list) and value and hasattr(value[0], "model_dump"):
            out[key] = [{"__model__": type(v).__name__, "data": v.model_dump(mode="json")} for v in value]
        else:
            out[key] = value
    return out


def _rehydrate(raw: dict[str, Any]) -> LoopState:
    """Models back from JSON, by name, from the modules that define them."""
    import wha.models as models

    def one(item: Any) -> Any:
        if isinstance(item, dict) and "__model__" in item:
            cls = getattr(models, item["__model__"])
            return cls.model_validate(item["data"])
        return item

    return {
        k: [one(v) for v in val] if isinstance(val, list) else one(val) for k, val in raw.items()
    }
```

Check: the state carries models from `wha.models` only (`Detection`, `NightlyFeatures`,
`ExtractedFact`, `Answer`, `MeasurementResult`, `BeliefState`, `Action`,
`EpisodeOutcome`). If any lives elsewhere, extend `_rehydrate`'s lookup to that module.
Check `wha.db.connection.connect` is the real name of the connection helper used by
`run_ingest` (`connect(target_db)` in `service/ingest.py`).

- [ ] **Step 4: Rewire `graph.py`**

Keep the module's public names. Replace the LangGraph imports and bodies:

```python
def get_sqlite_checkpointer(db_path: Path | None = None) -> Path:
    """Kept for callers; the loop persists to the database at this path."""
    return db_path if db_path is not None else get_db_path()


def build_agent_graph(checkpointer: Path | None = None, db: Any = None, notifier: Any = None) -> Loop:
    loop = Loop(db_path=checkpointer)
    def bind(node):  # unchanged from before
        ...
    for name, fn in (("preload", node_preload), ("investigate", node_investigate), ("believe", node_believe),
                     ("decide", node_decide), ("ask", node_ask), ("conclude", node_conclude),
                     ("critique", node_critique), ("review", node_review)):
        loop.add_node(name, bind(fn))
    loop.add_edge(Loop.START, "preload")
    loop.add_edge("preload", "investigate")
    loop.add_edge("investigate", "believe")
    loop.add_edge("believe", "decide")
    loop.add_conditional_edges("decide", route_after_decide, {"ask": "ask", "conclude": "conclude", END: Loop.END})
    loop.add_conditional_edges("ask", route_after_ask, {"conclude": "conclude", "believe": "believe", "investigate": "investigate"})
    loop.add_edge("conclude", "critique")
    loop.add_edge("critique", "review")
    loop.add_edge("review", Loop.END)
    return loop
```

`END` stays a module constant equal to `Loop.END` so `route_after_decide` is untouched.
`get_pending_interrupt(graph, episode_id)` becomes `graph.pending(episode_id)`.
`run_episode_step` maps its arguments onto `loop.invoke(...)`: `resume` passes through,
`restart` passes through, and when neither is set and `graph.has_checkpoint(episode_id)`
the payload is `None`. The `GraphRecursionError` branch becomes reading
`result["status"] == "unresolved"`, returning the same dict shape as before. `_GRAPH_CACHE`
and `get_agent_graph` are unchanged.

`tests/unit/agent/test_steps.py:44-47` reads the registered node names from the compiled
graph; make `Loop.nodes` the dict it reads, or adapt the one line in that test that
accesses LangGraph internals, which is permitted because the test encodes a LangGraph
attribute name rather than a behaviour (rule 1's narrow exception, measured first: run it,
see the `AttributeError`, then change the accessor and nothing else).

- [ ] **Step 5: Schema, contract, dependencies**

Add to `src/wha/db/schema.sql` the `agent_checkpoints` table exactly as created in
`_conn()`, and its row to `docs/CONTRACTS.md` section 5. Remove `langgraph` and
`langgraph-checkpoint-sqlite` from `pyproject.toml` and the contract's dependency table;
`uv lock && uv sync --extra pc`. Delete the LangGraph rows from the "known traps" table in
section 1.1 and replace them with one row: "`interrupt()` re-runs the whole node on
resume: everything before it must be idempotent (unchanged from LangGraph)".

- [ ] **Step 6: Run the agent and integration tests**

Run: `uv run pytest tests/unit/agent tests/unit/service/test_episodes.py tests/unit/service/test_resume_value.py tests/integration/test_human_review.py tests/integration/test_production_loop.py tests/scenario -n auto -q`
Expected: all pass with no test changed except the one accessor line above. If a scenario
test fails, the loop differs from the graph in a way the tests caught: fix the loop, never
the test.

- [ ] **Step 7: Commit**

```bash
git add src/wha/agent/ src/wha/db/schema.sql pyproject.toml uv.lock docs/CONTRACTS.md tests/unit/agent/test_loop.py tests/unit/agent/test_steps.py
git commit -m "Run the agent's eight nodes in a plain loop, because langgraph's wheels do not build for Android

Same nodes, same routes, same pause at ask and review, same resume, same recursion cap,
same persistence across restarts, now through one small table. The existing agent and
scenario tests are the proof it behaves the same."
```

---
## Phase 2. The app

Kotlin. Package `dev.wha.app`. Each task builds on the remote with
`bash android/remote/build-apk.sh` and is checked on the phone. Kotlin unit tests run on
the remote with `bash android/remote/run.sh 'cd android && ./gradlew --no-daemon --max-workers=8 :app:testDebugUnitTest && ./gradlew --stop'`.

Conventions for every Kotlin file:

- One screen, one `ViewModel`, one `UiState` data class. Screens are `@Composable`
  functions that take state and callbacks, never a view model, so they can be previewed
  and tested with fake state.
- Every string the person sees lives in `res/values/strings.xml` and contains no digit. A
  Gradle check (Task 11) fails the build if one does. Numbers are formatted from data at
  the call site.
- Colours: `ui/theme/Color.kt` defines the one accent and the three pinned status colours;
  no other colour literal anywhere. A status is always colour plus icon plus word.

### Task 11: The real Gradle project, assets and the Python source set

Spec sections 3, 4.4. Replace the smoke app's Python wiring with the core.

**Files:**
- Modify: `android/app/build.gradle.kts`
- Delete: `android/app/src/main/python/wha_smoke.py`
- Create: `android/app/src/main/python/wha_boot.py`
- Create: `android/app/src/main/java/dev/wha/app/core/PythonBoot.kt`
- Create: `android/app/src/main/java/dev/wha/app/WhaApp.kt`
- Create: `android/app/src/main/res/values/strings.xml`
- Create: `android/app/src/main/java/dev/wha/app/ui/theme/{Color.kt,Theme.kt,Type.kt}`
- Create: `android/no-digits-check.gradle.kts`
- Modify: `android/app/src/main/AndroidManifest.xml`
- Test: `android/app/src/test/java/dev/wha/app/StringsHaveNoDigitsTest.kt`

**Interfaces:**
- Produces: `PythonBoot.ensureStarted(context)`: idempotent; extracts `knowledge/` assets to `filesDir/wha/data/knowledge`, sets the environment from `AppSettings` (Task 13), sets the working directory, starts Python, and calls `wha_boot.boot(...)` which registers the notifier sink and the embedder. Returns the `wha_android.facade` `PyObject`.

- [x] **Step 1: Point Chaquopy at the core**

```kotlin
// android/app/build.gradle.kts, chaquopy block replaces the smoke one
chaquopy {
    defaultConfig {
        version = "3.13"
        pip {
            options("--find-links", file("../wheels").absolutePath)
            // The core's runtime dependencies, exactly the pins in uv.lock. Regenerated by
            // tools/android_requirements.py (below) so this list cannot drift from the lock.
            install("-r", file("requirements-android.txt").absolutePath)
        }
        // The core and the facade, straight from the repository. No copy to drift.
        extractPackages("wha", "wha_android")
    }
    sourceSets {
        getByName("main") {
            srcDir("src/main/python")
            srcDir("../../src")
        }
    }
}
```

`extractPackages` is needed because the knowledge loaders and `db/migrations.py` read
files relative to package paths (`Path(__file__).parent / "schema.sql"`); Chaquopy keeps
packages zipped unless told to extract.

Write `tools/android_requirements.py`:

```python
"""Write android/app/requirements-android.txt from uv.lock: the runtime dependency
closure at its pinned versions, minus packages the phone gets from Chaquopy's own index
(numpy, scipy, pandas, lxml, pyyaml) which must stay unpinned so the index resolves them,
and minus everything only the pc extra needs."""

import subprocess
import sys
import tomllib
from pathlib import Path

FROM_CHAQUOPY_INDEX = {"numpy", "scipy", "pandas", "lxml", "pyyaml", "tokenizers"}


def main() -> None:
    lock = tomllib.loads(Path("uv.lock").read_text(encoding="utf-8"))
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    by_name = {p["name"]: p for p in lock["package"]}
    roots = [d.split(">")[0].split("<")[0].split("=")[0].strip() for d in pyproject["project"]["dependencies"]]
    closure: set[str] = set()
    stack = list(roots)
    while stack:
        name = stack.pop()
        if name in closure or name not in by_name:
            continue
        closure.add(name)
        for dep in by_name[name].get("dependencies", []):
            stack.append(dep["name"])
    lines = []
    for name in sorted(closure):
        if name == "wha":
            continue
        if name in FROM_CHAQUOPY_INDEX:
            lines.append(name)
        else:
            lines.append(f"{name}=={by_name[name]['version']}")
    out = Path("android/app/requirements-android.txt")
    out.write_text("# Generated by tools/android_requirements.py from uv.lock. Do not edit.\n" + "\n".join(lines) + "\n", encoding="utf-8")
    print(out, len(lines), "packages")


if __name__ == "__main__":
    main()
```

Run `uv run python tools/android_requirements.py` and commit the output. Add a test
`tests/unit/android/test_android_requirements.py` that regenerates to a temp path and
asserts it equals the committed file, so a lock change without a regeneration fails.

- [x] **Step 2: Assets and boot**

Copy `data/knowledge/` into the APK at build time rather than committing a second copy:

```kotlin
// android/app/build.gradle.kts, inside android { }
sourceSets["main"].assets.srcDir(layout.buildDirectory.dir("generated/wha-assets"))

tasks.register<Copy>("copyKnowledgeAssets") {
    from("../../data/knowledge") { into("knowledge") }
    from("../../data/knowledge/corpus-sources.json") { into("knowledge") }
    into(layout.buildDirectory.dir("generated/wha-assets"))
}
tasks.named("preBuild") { dependsOn("copyKnowledgeAssets") }
```

```python
# android/app/src/main/python/wha_boot.py
"""What Kotlin calls once, after Python starts and before anything else.

Registers the phone's notification sink and embedder, then returns the facade module.
Everything else on the phone goes through wha_android.facade.
"""

from __future__ import annotations

import os
from typing import Any


def boot(notify_sink: Any, embedder: Any) -> Any:
    from wha.notify import android as android_notify
    from wha.retrieve import embedder_registry

    # Kotlin objects arrive as PyObject proxies with the methods below.
    android_notify.set_sink(lambda payload: bool(notify_sink.deliver(_to_java_map(payload))))
    embedder_registry.set_default_embedder(_KotlinEmbedder(embedder))

    from wha_android import facade

    return facade


def _to_java_map(payload: dict) -> dict:
    # Chaquopy converts a dict to java.util.Map at the boundary; nested lists of dicts
    # convert too. Options carry only strings, so nothing needs special handling.
    return payload


class _KotlinEmbedder:
    """Adapts the Kotlin ONNX embedder to the Embedder protocol."""

    def __init__(self, kotlin_embedder: Any) -> None:
        self._k = kotlin_embedder

    def embed_texts(self, texts: list[str]) -> Any:
        import numpy as np

        if not texts:
            return np.empty((0, 384), dtype=np.float32)
        flat = self._k.embed(list(texts))          # FloatArray, row-major N x 384
        arr = np.asarray(list(flat), dtype=np.float32).reshape(len(texts), 384)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        return arr / np.where(norms == 0, 1.0, norms)
```

```kotlin
// android/app/src/main/java/dev/wha/app/core/PythonBoot.kt
package dev.wha.app.core

import android.content.Context
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import dev.wha.app.embed.OnnxEmbedder
import dev.wha.app.notify.NotificationSink
import dev.wha.app.settings.AppSettings
import java.io.File

/** Starts Python once per process, with the working directory and environment the core expects. */
object PythonBoot {
    @Volatile private var facade: PyObject? = null

    fun ensureStarted(context: Context): PyObject {
        facade?.let { return it }
        synchronized(this) {
            facade?.let { return it }
            val root = File(context.filesDir, "wha").apply { mkdirs() }
            extractKnowledge(context, root)
            val settings = AppSettings(context)
            val env = settings.pythonEnvironment(root)
            val platform = AndroidPlatform(context)
            if (!Python.isStarted()) Python.start(platform)
            val py = Python.getInstance()
            val os = py.getModule("os")
            env.forEach { (k, v) -> os.callAttr("putenv", k, v); os.get("environ")!!.callAttr("__setitem__", k, v) }
            os.callAttr("chdir", root.absolutePath)
            val boot = py.getModule("wha_boot")
            val started = boot.callAttr("boot", NotificationSink(context), OnnxEmbedder(context))
            facade = started
            return started
        }
    }

    /** data/knowledge from the APK to disk, once per app version. */
    private fun extractKnowledge(context: Context, root: File) {
        val marker = File(root, "knowledge.version")
        val version = context.packageManager.getPackageInfo(context.packageName, 0).longVersionCode.toString()
        if (marker.exists() && marker.readText() == version) return
        val target = File(root, "data/knowledge").apply { mkdirs() }
        context.assets.list("knowledge")!!.forEach { name ->
            context.assets.open("knowledge/$name").use { input ->
                File(target, name).outputStream().use { input.copyTo(it) }
            }
        }
        marker.writeText(version)
    }
}
```

`AppSettings.pythonEnvironment(root)` (Task 13) returns the map: `WHA_DB_PATH`
(`root/data/wha.sqlite`), `WHA_SUBJECT`, `WHA_TIMEZONE`, `WHA_BRIDGE_URL`,
`WHA_BRIDGE_HOST`, `WHA_BRIDGE_PORT`, `WHA_BRIDGE_TOKEN`, `WHA_LLM_PROVIDER`,
`WHA_LLM_BASE_URL`, `WHA_LLM_API_KEY`, `WHA_LLM_MODEL`, `WHA_NOTIFY_CHANNEL=android`,
`WHA_CASSETTE_DIR` (unused on the phone but read at import), `WHA_DATA_DIR`. Until Task 13
lands, stub `AppSettings` with those defaults and `WHA_LLM_PROVIDER=cassette` so the app
boots.

- [x] **Step 3: Theme, strings, and the no-digits rule**

```kotlin
// ui/theme/Color.kt
package dev.wha.app.ui.theme
import androidx.compose.ui.graphics.Color
val Accent = Color(0xFF2F6F73)          // one accent: a muted teal, the only brand colour
val Surface = Color(0xFFFAFAF8)
val OnSurface = Color(0xFF1F2933)
val Muted = Color(0xFF6B7480)
val Outline = Color(0xFFD9DEE3)
// Status colours are pinned to meaning and never used decoratively. Each is always paired
// with a word and an icon on screen (spec section 6.2). These are the dataviz skill's
// reference status steps (good, warning, critical); the skill's validator is for
// categorical palettes, and status colours are permitted to be close to each other
// precisely because they never carry meaning alone.
val StatusGreen = Color(0xFF0CA30C)
val StatusAmber = Color(0xFFFAB219)
val StatusRed = Color(0xFFD03B3B)
// Which machine ran a step (spec section 7.1). A categorical palette of four, validated on
// 10 September 2026 with the dataviz skill's validate_palette.js in light mode: all five
// checks pass (worst adjacent CVD separation 16.1, normal-vision 26.5, all above 3:1).
// Re-run the validator before changing any of these.
val LayerArithmetic = Color(0xFF2F6FB8)
val LayerRule = Color(0xFFD9731F)
val LayerModel = Color(0xFF8C4FCF)
val LayerPerson = Color(0xFF0F8F7C)
```

`Theme.kt` builds a `lightColorScheme(primary = Accent, surface = Surface, onSurface =
OnSurface, outline = Outline)` and applies `Type.kt`, which uses the system font at
Material 3 defaults with `bodyLarge` line height raised for reading.

`strings.xml` starts with the app name and the bottom-bar labels: `today`, `history`,
`record`, `settings`. Every later task adds its strings here.

```kotlin
// android/app/src/test/java/dev/wha/app/StringsHaveNoDigitsTest.kt
package dev.wha.app

import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class StringsHaveNoDigitsTest {
    @Test
    fun noUiStringContainsADigit() {
        val xml = File("src/main/res/values/strings.xml").readText()
        val offenders = Regex("<string name=\"([^\"]+)\">([^<]*)</string>").findAll(xml)
            .filter { it.groupValues[2].any(Char::isDigit) }
            .map { it.groupValues[1] }.toList()
        assertTrue("UI strings with a figure in them: $offenders", offenders.isEmpty())
    }
}
```

Add `testImplementation("junit:junit:4.13.2")` to dependencies.

- [x] **Step 4: Manifest and application class**

```kotlin
// WhaApp.kt
package dev.wha.app
import android.app.Application
import dev.wha.app.notify.NotificationChannels
class WhaApp : Application() {
    override fun onCreate() {
        super.onCreate()
        NotificationChannels.ensure(this)
    }
}
```

Manifest gains `android:name=".WhaApp"`, `INTERNET`, `POST_NOTIFICATIONS`,
`FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_DATA_SYNC`, `RECEIVE_BOOT_COMPLETED`, and
`android:usesCleartextTraffic="true"` restricted through
`res/xml/network_security_config.xml` to `127.0.0.1`, `localhost` and private ranges
(the webhook is plain HTTP on the phone; the provider is HTTPS).

- [ ] **Step 5: Build, install, verify** (build done 11 Sep, APK assembled; install and verify deferred to Task 25 per owner)

`MainActivity` for now calls `PythonBoot.ensureStarted(this)` and shows
`facade.callAttr("config").toString()` in a scrolling `Text`.
Run: `bash android/remote/build-apk.sh`, install, open.
Expected, written first: the config JSON with `"configured_subject": "me"` and every
upper-case constant name from `constants.py`. Time from tap to text is noted in
`android/README.md` under "Measured start-up" as a plain observation (this is an
engineering timing, not a claim about health, so it may be recorded).

- [x] **Step 6: Commit**

```bash
git add android/ tools/android_requirements.py tests/unit/android/test_android_requirements.py
git commit -m "Load the real core on the phone from the repository's own source tree

No copied Python. Chaquopy reads src/ directly, installs the lock's pinned versions from a
generated requirements file, and unpacks the knowledge tables where the loaders expect
them. The boot registers the phone's notifier and embedder before the first facade call."
```

---

### Task 12: The Kotlin bridge and its models

Spec sections 5 and 9. One class between Compose and Python.

**Files:**
- Create: `core/WhaCore.kt`, `core/WhaResult.kt`, `core/Models.kt`, `core/FakeCore.kt` (test source set)
- Test: `core/WhaResultTest.kt`

**Interfaces:**
- Produces: `interface WhaCore` with one suspend function per facade function, each returning `WhaResult<T>`; `sealed class WhaResult<T> { data class Ok(val value: T); data class Err(val kind: ErrorKind, val message: String) }`; `enum class ErrorKind { UNAVAILABLE, INVALID, INTERNAL }`; `PythonWhaCore(context)` the real one; `FakeWhaCore` for tests holding canned JSON. `Models.kt` holds `@Serializable` data classes mirroring the Pydantic models the facade returns, with `ignoreUnknownKeys = true` so a field added on the PC does not crash the phone.

- [x] **Step 1: Write the failing result test**

```kotlin
// android/app/src/test/java/dev/wha/app/core/WhaResultTest.kt
package dev.wha.app.core

import kotlinx.serialization.Serializable
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

@Serializable data class Probe(val x: Int)

class WhaResultTest {
    @Test fun payloadParsesToOk() {
        val r = WhaResult.parse<Probe>("""{"x": 3, "later_added": true}""")
        assertTrue(r is WhaResult.Ok)
        assertEquals(3, (r as WhaResult.Ok).value.x)
    }
    @Test fun envelopeParsesToErr() {
        val r = WhaResult.parse<Probe>("""{"error": {"kind": "unavailable", "message": "no webhook"}}""")
        assertTrue(r is WhaResult.Err)
        assertEquals(ErrorKind.UNAVAILABLE, (r as WhaResult.Err).kind)
        assertEquals("no webhook", r.message)
    }
    @Test fun garbageIsInternalNotACrash() {
        val r = WhaResult.parse<Probe>("not json")
        assertTrue(r is WhaResult.Err && r.kind == ErrorKind.INTERNAL)
    }
    @Test fun nullPayloadParsesToOkNull() {
        val r = WhaResult.parse<Probe?>("null")
        assertTrue(r is WhaResult.Ok && r.value == null)
    }
}
```

- [x] **Step 2: Run to verify it fails**

Run on the remote: `./gradlew :app:testDebugUnitTest --tests '*WhaResultTest*'`
Expected: compilation failure, `WhaResult` unresolved.

- [x] **Step 3: Write the result type and the core**

```kotlin
// core/WhaResult.kt
package dev.wha.app.core

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject

enum class ErrorKind { UNAVAILABLE, INVALID, INTERNAL }

@Serializable private data class Envelope(val error: EnvelopeError)
@Serializable private data class EnvelopeError(val kind: String, val message: String)

sealed class WhaResult<out T> {
    data class Ok<T>(val value: T) : WhaResult<T>()
    data class Err(val kind: ErrorKind, val message: String) : WhaResult<Nothing>()

    companion object {
        val json = Json { ignoreUnknownKeys = true; coerceInputValues = true; explicitNulls = false }

        inline fun <reified T> parse(raw: String): WhaResult<T> = try {
            val element = json.parseToJsonElement(raw)
            if (element is kotlinx.serialization.json.JsonObject && "error" in element.jsonObject) {
                val env = json.decodeFromJsonElement(Envelope.serializer(), element)
                Err(runCatching { ErrorKind.valueOf(env.error.kind.uppercase()) }.getOrDefault(ErrorKind.INTERNAL), env.error.message)
            } else Ok(json.decodeFromJsonElement(kotlinx.serialization.serializer<T>(), element))
        } catch (e: Exception) {
            Err(ErrorKind.INTERNAL, "${e::class.simpleName}: ${e.message}")
        }
    }
}
```

```kotlin
// core/WhaCore.kt
package dev.wha.app.core

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

interface WhaCore {
    suspend fun config(): WhaResult<Map<String, kotlinx.serialization.json.JsonElement>>
    suspend fun wording(): WhaResult<Map<String, String>>
    suspend fun lineage(): WhaResult<List<LineageEdge>>
    suspend fun status(subject: String): WhaResult<SystemStatus>
    suspend fun urgency(subject: String): WhaResult<Urgency>
    suspend fun acknowledgeUrgency(subject: String): WhaResult<Map<String, kotlinx.serialization.json.JsonElement>>
    suspend fun nights(subject: String, days: Int): WhaResult<List<NightSummary>>
    suspend fun night(subject: String, date: String): WhaResult<NightDetail?>
    suspend fun pipelineNights(subject: String, days: Int): WhaResult<List<PipelineNightRef>>
    suspend fun nightPipeline(subject: String, date: String): WhaResult<NightPipeline>
    suspend fun episodes(subject: String): WhaResult<List<EpisodeSummary>>
    suspend fun episode(id: String): WhaResult<EpisodeDetail>
    suspend fun pending(subject: String): WhaResult<PendingInteraction?>
    suspend fun answer(episodeId: String, probeId: String, optionId: String?, freeText: String?, declined: Boolean): WhaResult<Recorded>
    suspend fun review(episodeId: String, decision: String, editedProse: String?, rationale: String?): WhaResult<Recorded>
    suspend fun handover(subject: String, episodeId: String?): WhaResult<Handover>
    suspend fun conversation(subject: String, limit: Int): WhaResult<List<Turn>>
    suspend fun say(subject: String, text: String, episodeId: String?): WhaResult<SayResult>
    suspend fun audit(subject: String, limit: Int, offset: Int): WhaResult<AuditPage>
    suspend fun auditExport(subject: String): WhaResult<Exported>
    suspend fun settings(): WhaResult<ServiceSettings>
    suspend fun updateSettings(patchJson: String): WhaResult<kotlinx.serialization.json.JsonElement>
    suspend fun knowledgeProvenance(): WhaResult<Map<String, Map<String, String>>>
    suspend fun safetyProvenance(): WhaResult<List<Map<String, String>>>
    suspend fun diagnose(component: String, overridesJson: String): WhaResult<kotlinx.serialization.json.JsonElement>
    suspend fun doctor(): WhaResult<List<DoctorRow>>
    suspend fun retrievalReady(): WhaResult<Ready>
    suspend fun fetchCorpus(): WhaResult<Message>
    suspend fun runIngest(): WhaResult<JobResult>
    suspend fun runNightly(): WhaResult<JobResult>
    suspend fun runEpisodeTick(): WhaResult<JobResult>
    suspend fun runStartupCatchup(): WhaResult<JobResult>
}

class PythonWhaCore(private val context: Context) : WhaCore {
    private val facade by lazy { PythonBoot.ensureStarted(context) }
    private suspend inline fun <reified T> call(name: String, vararg args: Any?): WhaResult<T> =
        withContext(Dispatchers.IO) { WhaResult.parse(facade.callAttr(name, *args).toString()) }

    override suspend fun config() = call<Map<String, kotlinx.serialization.json.JsonElement>>("config")
    override suspend fun wording() = call<Map<String, String>>("wording")
    override suspend fun lineage() = call<List<LineageEdge>>("lineage")
    override suspend fun status(subject: String) = call<SystemStatus>("status", subject)
    override suspend fun urgency(subject: String) = call<Urgency>("urgency", subject)
    override suspend fun acknowledgeUrgency(subject: String) = call<Map<String, kotlinx.serialization.json.JsonElement>>("acknowledge_urgency", subject)
    override suspend fun nights(subject: String, days: Int) = call<List<NightSummary>>("nights", subject, days)
    override suspend fun night(subject: String, date: String) = call<NightDetail?>("night", subject, date)
    override suspend fun pipelineNights(subject: String, days: Int) = call<List<PipelineNightRef>>("pipeline_nights", subject, days)
    override suspend fun nightPipeline(subject: String, date: String) = call<NightPipeline>("night_pipeline", subject, date)
    override suspend fun episodes(subject: String) = call<List<EpisodeSummary>>("episodes", subject)
    override suspend fun episode(id: String) = call<EpisodeDetail>("episode", id)
    override suspend fun pending(subject: String) = call<PendingInteraction?>("pending", subject)
    override suspend fun answer(episodeId: String, probeId: String, optionId: String?, freeText: String?, declined: Boolean) =
        call<Recorded>("answer", episodeId, probeId, optionId, freeText, declined)
    override suspend fun review(episodeId: String, decision: String, editedProse: String?, rationale: String?) =
        call<Recorded>("review", episodeId, decision, editedProse, rationale)
    override suspend fun handover(subject: String, episodeId: String?) = call<Handover>("handover", subject, episodeId)
    override suspend fun conversation(subject: String, limit: Int) = call<List<Turn>>("conversation", subject, limit)
    override suspend fun say(subject: String, text: String, episodeId: String?) = call<SayResult>("say", subject, text, episodeId)
    override suspend fun audit(subject: String, limit: Int, offset: Int) = call<AuditPage>("audit", subject, limit, offset)
    override suspend fun auditExport(subject: String) = call<Exported>("audit_export", subject)
    override suspend fun settings() = call<ServiceSettings>("settings")
    override suspend fun updateSettings(patchJson: String) = call<kotlinx.serialization.json.JsonElement>("update_settings", patchJson)
    override suspend fun knowledgeProvenance() = call<Map<String, Map<String, String>>>("knowledge_provenance")
    override suspend fun safetyProvenance() = call<List<Map<String, String>>>("safety_provenance")
    override suspend fun diagnose(component: String, overridesJson: String) = call<kotlinx.serialization.json.JsonElement>("diagnose", component, overridesJson)
    override suspend fun doctor() = call<List<DoctorRow>>("doctor")
    override suspend fun retrievalReady() = call<Ready>("retrieval_ready")
    override suspend fun fetchCorpus() = call<Message>("fetch_corpus")
    override suspend fun runIngest() = call<JobResult>("run_ingest")
    override suspend fun runNightly() = call<JobResult>("run_nightly")
    override suspend fun runEpisodeTick() = call<JobResult>("run_episode_tick")
    override suspend fun runStartupCatchup() = call<JobResult>("run_startup_catchup")
}
```

`Models.kt`: one `@Serializable data class` per model named above. Derive each field list
from `docs/CONTRACTS.md` sections 6.2 and 6.5 (`SystemStatus`, `NightSummary`,
`NightDetail`, `PipelineNightRef`, `NightPipeline`, `PipelineHeadline`,
`PipelineStepView`, `Citation`, `EpisodeSummary`, `EpisodeDetail`, `PendingInteraction`,
`AnswerOption`) and section 12 for the dict shapes (`Urgency`, `Handover`, `AuditPage`,
`Recorded`, `Exported`, `Ready`, `Message`, `JobResult`, `DoctorRow`, `LineageEdge`,
`Turn`, `SayResult`, `ServiceSettings`). Every optional Pydantic field is a nullable
Kotlin field with default `null`; every `dict[str, Any]` is `JsonObject`; every enum is a
`String` (the screens map strings to words through `wording`), which is what keeps a new
enum member on the PC from crashing the phone.

Add to dependencies: `implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")`,
`implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")`.

`FakeWhaCore` (in `src/test`) implements `WhaCore` with a `MutableMap<String, String>`
of canned JSON per method name and records calls; every view model test uses it.

- [x] **Step 4: Run the unit tests**

Run on the remote: `./gradlew :app:testDebugUnitTest`
Expected: `WhaResultTest` four tests pass; `StringsHaveNoDigitsTest` passes.

- [x] **Step 5: Model parity check against the contract**

Add `tests/unit/android/test_kotlin_models_match_contract.py`: parse
`android/app/src/main/java/dev/wha/app/core/Models.kt` with a regex for
`data class Name(` and field names, parse the model field tables in `docs/CONTRACTS.md`
section 6 (the same tables `test_the_contract_lists_the_fields_the_models_actually_have`
reads; reuse its parser), and assert every Pydantic field of each mirrored model has a
Kotlin field of the same name in snake case. Fields may be missing on the Kotlin side only
if listed in an `IGNORED` dict in the test with a reason.

- [x] **Step 6: Commit**

```bash
git add android/app/src/main/java/dev/wha/app/core android/app/src/test tests/unit/android/test_kotlin_models_match_contract.py android/app/build.gradle.kts
git commit -m "Put one typed bridge between the screens and the core

Every facade call returns either a value or an error kind, never an exception, and the
Kotlin models are checked against the contract so a field renamed on the PC fails a test
rather than a screen."
```

---

### Task 13: Settings storage, environment injection, and onboarding

Spec sections 4.7, 6.3.

**Files:**
- Create: `settings/AppSettings.kt`, `settings/SecretStore.kt`
- Create: `ui/onboarding/{OnboardingScreen.kt,OnboardingViewModel.kt}`
- Modify: `MainActivity.kt` (routes to onboarding until complete)
- Test: `settings/AppSettingsTest.kt`, `ui/onboarding/OnboardingViewModelTest.kt`

**Interfaces:**
- Produces: `AppSettings(context)` with typed properties `webhookHost`, `webhookPort`, `webhookToken`, `providerBaseUrl`, `providerModel`, `providerKey`, `subject`, `timezone`, `onboarded: Boolean`, and `pythonEnvironment(root: File): Map<String, String>`. Secrets (`webhookToken`, `providerKey`) live in `SecretStore` (EncryptedSharedPreferences with a Keystore master key); everything else in plain `SharedPreferences`.

- [x] **Step 1: Failing tests**

```kotlin
// settings/AppSettingsTest.kt (Robolectric)
@RunWith(RobolectricTestRunner::class)
class AppSettingsTest {
    private val context = ApplicationProvider.getApplicationContext<Context>()

    @Test fun environmentUsesLocalhostWebhookByDefault() {
        val env = AppSettings(context).pythonEnvironment(File("/tmp/wha"))
        assertEquals("http://127.0.0.1:8787", env["WHA_BRIDGE_URL"])
        assertEquals("127.0.0.1", env["WHA_BRIDGE_HOST"])
        assertEquals("8787", env["WHA_BRIDGE_PORT"])
        assertEquals("android", env["WHA_NOTIFY_CHANNEL"])
        assertEquals("/tmp/wha/data/wha.sqlite", env["WHA_DB_PATH"])
        assertEquals("cassette", env["WHA_LLM_PROVIDER"])  // until a key is entered
    }
    @Test fun aProviderKeySwitchesTheProviderOn() {
        val s = AppSettings(context)
        s.providerKey = "sk-test"; s.providerBaseUrl = "https://api.example/v1"; s.providerModel = "m"
        val env = s.pythonEnvironment(File("/tmp/wha"))
        assertEquals("openai_compatible", env["WHA_LLM_PROVIDER"])
        assertEquals("sk-test", env["WHA_LLM_API_KEY"])
    }
    @Test fun portChangesTheUrl() {
        val s = AppSettings(context); s.webhookPort = 9000
        assertEquals("http://127.0.0.1:9000", s.pythonEnvironment(File("/tmp/wha"))["WHA_BRIDGE_URL"])
    }
    @Test fun secretsAreNotInPlainPreferences() {
        val s = AppSettings(context); s.providerKey = "sk-secret"
        val plain = context.getSharedPreferences("wha", Context.MODE_PRIVATE).all.values.joinToString()
        assertFalse(plain.contains("sk-secret"))
    }
}
```

Add Robolectric: `testImplementation("org.robolectric:robolectric:4.14.1")`,
`testImplementation("androidx.test:core:1.6.1")`, and
`implementation("androidx.security:security-crypto:1.1.0-alpha06")`. Under Robolectric
`EncryptedSharedPreferences` needs a fake; `SecretStore` takes an interface
`SecretBacking` with a `PlainBacking` used only under test (annotated so, with the reason).

- [x] **Step 2: Run to verify failure, then write `AppSettings`**

```kotlin
// settings/AppSettings.kt
package dev.wha.app.settings

import android.content.Context
import java.io.File

class AppSettings(context: Context, private val secrets: SecretStore = SecretStore(context)) {
    private val prefs = context.getSharedPreferences("wha", Context.MODE_PRIVATE)

    var onboarded: Boolean
        get() = prefs.getBoolean("onboarded", false); set(v) = prefs.edit().putBoolean("onboarded", v).apply()
    var webhookHost: String
        get() = prefs.getString("webhook_host", "127.0.0.1")!!; set(v) = prefs.edit().putString("webhook_host", v).apply()
    var webhookPort: Int
        get() = prefs.getInt("webhook_port", 8787); set(v) = prefs.edit().putInt("webhook_port", v).apply()
    var providerBaseUrl: String
        get() = prefs.getString("provider_base_url", "")!!; set(v) = prefs.edit().putString("provider_base_url", v).apply()
    var providerModel: String
        get() = prefs.getString("provider_model", "")!!; set(v) = prefs.edit().putString("provider_model", v).apply()
    var subject: String
        get() = prefs.getString("subject", "me")!!; set(v) = prefs.edit().putString("subject", v).apply()
    var timezone: String
        get() = prefs.getString("timezone", java.util.TimeZone.getDefault().id)!!; set(v) = prefs.edit().putString("timezone", v).apply()
    var webhookToken: String
        get() = secrets.get("webhook_token"); set(v) = secrets.put("webhook_token", v)
    var providerKey: String
        get() = secrets.get("provider_key"); set(v) = secrets.put("provider_key", v)

    /** Exactly the variables the core reads (docs/CONTRACTS.md section 2). */
    fun pythonEnvironment(root: File): Map<String, String> {
        val url = "http://$webhookHost:$webhookPort"
        val hasProvider = providerKey.isNotBlank() && providerBaseUrl.isNotBlank()
        return mapOf(
            "WHA_DB_PATH" to File(root, "data/wha.sqlite").path,
            "WHA_DATA_DIR" to File(root, "data/datasets").path,
            "WHA_SUBJECT" to subject,
            "WHA_TIMEZONE" to timezone,
            "WHA_BRIDGE_URL" to url,
            "WHA_BRIDGE_HOST" to webhookHost,
            "WHA_BRIDGE_PORT" to webhookPort.toString(),
            "WHA_BRIDGE_TOKEN" to webhookToken,
            "WHA_LLM_PROVIDER" to if (hasProvider) "openai_compatible" else "cassette",
            "WHA_LLM_BASE_URL" to providerBaseUrl,
            "WHA_LLM_API_KEY" to providerKey,
            "WHA_LLM_MODEL" to providerModel,
            "WHA_CASSETTE_DIR" to File(root, "cassettes").path,
            "WHA_NOTIFY_CHANNEL" to "android",
        )
    }
}
```

Note the provider falls back to `cassette` with no key, which the core treats as offline
fixtures; the Today screen must say "no model provider configured" in that state (Task 17)
rather than let a cassette reply look real. Record this in `docs/DISCLOSURES.md` (Task 24).

- [x] **Step 3: Onboarding**

Four pages in a `HorizontalPager`, state in `OnboardingViewModel`:

1. **What it is**: `wording["home.what_it_is"]`, `wording["home.can"]`.
2. **What it cannot do**: `wording["home.cannot"]`, `wording["home.emergency"]`, and the
   full text of `DISCLAIMER.md` (bundled as a raw resource at build time by the same Copy
   task as the knowledge assets) behind a "Read the disclaimer" expander. A checkbox "I have
   read this" gates Next.
3. **Connections**: webhook host and port fields (defaults shown), token field, "Test
   connection" calling `core.diagnose("bridge", overridesJson)` and showing the result's
   `detail` in words; provider base URL, model and key fields, "Test provider" calling
   `core.diagnose("llm", ...)`. The key field is a password field. Neither test is required
   to continue, but the page says what will not work without each.
4. **Notifications and the corpus**: requests `POST_NOTIFICATIONS`; starts the corpus fetch
   (Task 16) with a progress line; "Finish" sets `onboarded = true`, enqueues the jobs
   (Task 14) and runs the startup catch-up.

`OnboardingViewModelTest` with `FakeWhaCore`: a successful `diagnose("bridge")` produces
`UiState.bridgeResult` with the fake's `detail`; an `Err(UNAVAILABLE)` produces the
"could not reach" text and not a crash; Finish is disabled until the disclaimer box is
ticked.

- [ ] **Step 4: Build, install, walk through onboarding on the phone** (unit tests green on remote; install and walkthrough deferred to Task 25 per owner)

Expected, written first: all four pages render; "Test connection" against the real
webhook on the phone reports the record types the core sees; entering a wrong port reports
`unavailable` in words; the provider test with the rotated key reports success; Finish
lands on Today (a placeholder until Task 17).

- [x] **Step 5: Commit**

```bash
git add android/app/src/main/java/dev/wha/app/settings android/app/src/main/java/dev/wha/app/ui/onboarding android/app/src/test android/app/src/main/res
git commit -m "Ask for consent and connections before the first reading, and keep the key in the keystore

Onboarding says what the system can and cannot do before it does anything, because the
first screen is where capability is learned. Secrets never touch a readable file."
```

---

### Task 14: Jobs and the foreground service

Spec section 4.5. The four schedules, on WorkManager.

**Files:**
- Create: `jobs/{IngestWorker.kt,NightlyWorker.kt,EpisodeTickWorker.kt,CatchupWorker.kt,Jobs.kt,InvestigationService.kt,BootReceiver.kt,RunState.kt}`
- Modify: `AndroidManifest.xml` (service, receiver)
- Test: `jobs/JobsTest.kt`

**Interfaces:**
- Produces: `Jobs.enqueueAll(context)` (idempotent, `ExistingPeriodicWorkPolicy.UPDATE`), `Jobs.runCatchupNow(context)`; `RunState` a process-wide `StateFlow<RunState.Status>` with `Idle` or `Running(job: String, since: Instant)` that the Record tab reads (Task 20); `InvestigationService` a foreground service that `EpisodeTickWorker` starts when `pending` is null and an episode is active, showing "Investigating last night" until the tick returns.

- [x] **Step 1: Failing test**

```kotlin
@RunWith(RobolectricTestRunner::class)
class JobsTest {
    @Test fun enqueueAllRegistersFourUniquePeriodicJobs() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        WorkManagerTestInitHelper.initializeTestWorkManager(context)
        Jobs.enqueueAll(context)
        val wm = WorkManager.getInstance(context)
        val names = listOf("ingest", "nightly", "episode_tick").map { wm.getWorkInfosForUniqueWork(it).get().size }
        assertEquals(listOf(1, 1, 1), names)
    }
    @Test fun ingestIntervalMatchesThePcScheduler() {
        assertEquals(30L, Jobs.INGEST_MINUTES)
        assertEquals(15L, Jobs.TICK_MINUTES)
    }
}
```

`Jobs.NIGHTLY_HOURS` is read from `config()["NIGHTLY_RESCORE_INTERVAL_HOURS"]` at enqueue
time, not typed into Kotlin, so the phone follows the constant. Ingest and tick intervals
are written in the PC scheduler as literals (`minutes=30`, `minutes=15`), not constants;
the Kotlin literals mirror them and a Python test
`tests/unit/android/test_job_intervals.py` reads `Jobs.kt` and `scheduler.py` and asserts
the numbers agree, so a change on either side fails.

Add: `implementation("androidx.work:work-runtime-ktx:2.10.0")`,
`testImplementation("androidx.work:work-testing:2.10.0")`.

- [x] **Step 2: Write the workers**

```kotlin
// jobs/Jobs.kt
package dev.wha.app.jobs

import android.content.Context
import androidx.work.*
import java.util.concurrent.TimeUnit

object Jobs {
    const val INGEST_MINUTES = 30L
    const val TICK_MINUTES = 15L

    fun enqueueAll(context: Context, nightlyHours: Long) {
        val wm = WorkManager.getInstance(context)
        wm.enqueueUniquePeriodicWork("ingest", ExistingPeriodicWorkPolicy.UPDATE,
            PeriodicWorkRequestBuilder<IngestWorker>(INGEST_MINUTES, TimeUnit.MINUTES).build())
        wm.enqueueUniquePeriodicWork("nightly", ExistingPeriodicWorkPolicy.UPDATE,
            PeriodicWorkRequestBuilder<NightlyWorker>(nightlyHours, TimeUnit.HOURS).build())
        wm.enqueueUniquePeriodicWork("episode_tick", ExistingPeriodicWorkPolicy.UPDATE,
            PeriodicWorkRequestBuilder<EpisodeTickWorker>(TICK_MINUTES, TimeUnit.MINUTES).build())
    }

    fun runCatchupNow(context: Context) {
        WorkManager.getInstance(context).enqueueUniqueWork(
            "startup_catchup", ExistingWorkPolicy.KEEP, OneTimeWorkRequestBuilder<CatchupWorker>().build())
    }
}
```

Each worker is a `CoroutineWorker` whose `doWork()` sets `RunState.running(name)`, calls
the matching `core.run*()`, records the result in `RunState`, and returns
`Result.success()` even on an `Err`, because a failed ingest is a fact for the status
screen, not a reason for WorkManager to back off and retry into the same wall. `Err(INTERNAL)`
is logged with its message. `EpisodeTickWorker`, before calling the tick, asks
`core.pending(subject)`; if null and `core.status(subject).activeEpisodeId != null`, it
runs the tick inside `InvestigationService` (start foreground with the
`investigating` channel notification, run, stop). `BootReceiver` re-enqueues on
`BOOT_COMPLETED`.

Battery: WorkManager's minimum periodic interval is fifteen minutes, so the tick runs at
its floor. No wake locks beyond the foreground service.

- [ ] **Step 3: Build, install, verify on the phone** (unit tests green on remote; install and verify deferred to Task 25 per owner)

Expected, written first: after onboarding, `adb shell dumpsys jobscheduler | grep dev.wha`
(or the Settings screen's diagnostics row in Task 23) shows the three periodic jobs; the
first ingest after Finish writes samples (Today shows "readings arrived" with a time after
the catch-up); an investigation, when one runs, shows the foreground notification.

- [x] **Step 4: Commit**

```bash
git add android/app/src/main/java/dev/wha/app/jobs android/app/src/main/AndroidManifest.xml android/app/src/test tests/unit/android/test_job_intervals.py
git commit -m "Run the PC's four background jobs on the phone's scheduler

Same functions, same intervals, one at a time. An investigation runs in a foreground
service with a visible notification because invisible work is where trust breaks."
```

---

### Task 15: Notifications

Spec sections 4.6 and 6.2. The phone as the transport; the rules unchanged.

**Files:**
- Create: `notify/{NotificationChannels.kt,NotificationSink.kt,AnswerReceiver.kt}`
- Modify: `AndroidManifest.xml` (receiver)
- Test: `notify/NotificationSinkTest.kt`

**Interfaces:**
- Consumes: the payload dict from `wha.notify.android` (Task 6): `kind`, `text`, `interaction_id`, `probe_id`, `options`.
- Produces: `NotificationSink.deliver(payload: Map<String, Any?>): Boolean` (called from Python); two channels `questions` (default importance) and `urgent` (high importance, for `ESCALATION`); `AnswerReceiver` handling `dev.wha.ANSWER` intents with extras `episode_id`, `probe_id`, `option_id`, `declined`.

- [ ] **Step 1: Failing test**

```kotlin
@RunWith(RobolectricTestRunner::class)
class NotificationSinkTest {
    @Test fun aQuestionPostsOneActionPerOptionPlusNotNow() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        NotificationChannels.ensure(context)
        val sink = NotificationSink(context)
        val ok = sink.deliver(mapOf(
            "kind" to "QUESTION", "text" to "Did you drink alcohol last night?",
            "interaction_id" to "int-1", "probe_id" to "alcohol", "recipient_id" to "me",
            "options" to listOf(mapOf("option_id" to "yes", "label" to "Yes"), mapOf("option_id" to "no", "label" to "No")),
            "url" to null))
        assertTrue(ok)
        val shown = Shadows.shadowOf(context.getSystemService(NotificationManager::class.java)).allNotifications
        assertEquals(1, shown.size)
        assertEquals(listOf("Yes", "No", "Not now"), shown[0].actions.map { it.title.toString() })
        assertEquals("questions", shown[0].channelId)
    }
    @Test fun anEscalationUsesTheUrgentChannelAndIsOngoing() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        NotificationChannels.ensure(context)
        NotificationSink(context).deliver(mapOf("kind" to "ESCALATION", "text" to "See a clinician today.",
            "interaction_id" to null, "probe_id" to null, "recipient_id" to "me", "options" to emptyList<Any>(), "url" to null))
        val n = Shadows.shadowOf(context.getSystemService(NotificationManager::class.java)).allNotifications.single()
        assertEquals("urgent", n.channelId)
        assertTrue(n.flags and Notification.FLAG_ONGOING_EVENT != 0)
    }
}
```

"Ongoing" for an escalation is the phone's rendering of the system's existing rule that an
escalation stays until acknowledged (the Today screen's acknowledge action clears it by
calling `acknowledge_urgency`, which the core records). It is not a new rule.

- [ ] **Step 2: Write the sink and receiver**

`NotificationSink.deliver` builds a `NotificationCompat.Builder` on the channel for the
kind, with `setContentText(text)`, `setStyle(BigTextStyle)`, one `addAction` per option
whose `PendingIntent` targets `AnswerReceiver` with the extras, plus "Not now" with
`declined=true`; escalations get `setOngoing(true)` and `setCategory(CATEGORY_ALARM)`;
outcomes and system messages go to `questions` with no actions. The notification id is a
hash of `interaction_id` or of the text and kind. Python's `interaction_id` alone does not
identify the episode; the receiver calls `core.pending(subject)` to obtain the episode id
for the current question, then `core.answer(...)`, then cancels the notification. Returns
`false` if `POST_NOTIFICATIONS` is not granted, which Python logs as not delivered.

- [ ] **Step 3: Build, install, verify with a real question**

Point the app's webhook at the PC's mock watch (Task 25 describes the scripted illness;
use its first two red nights here). Expected, written first: a question notification
arrives with the probe's options and "Not now"; tapping an option records it (Today shows
the answer in the thread) and the notification clears; "Not now" records a declined answer.

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/java/dev/wha/app/notify android/app/src/main/AndroidManifest.xml android/app/src/test
git commit -m "Deliver the agent's questions as notifications with one tap per answer

The rules that decide to ask are unchanged; the phone replaces Telegram as the surface.
An escalation stays until acknowledged because that is what the system already required."
```

---

### Task 16: The ONNX embedder and the corpus fetch

Spec sections 4.3, 6.3, 8.

**Files:**
- Create: `embed/OnnxEmbedder.kt`, `embed/WordPieceTokenizer.kt`
- Create: `corpus/CorpusFetch.kt`
- Test: `embed/OnnxEmbedderTest.kt` (instrumented, runs on the phone), `embed/WordPieceTokenizerTest.kt` (unit)

**Interfaces:**
- Produces: `OnnxEmbedder(context).embed(texts: List<String>): FloatArray` (row-major, `texts.size * 384`), called from `wha_boot._KotlinEmbedder`. `CorpusFetch.start(context)` runs `core.fetchCorpus()` in a `OneTimeWorkRequest` and exposes `StateFlow<CorpusState>` (`Missing`, `Fetching`, `Ready`, `Failed(message)`), read by onboarding and Today.

- [ ] **Step 1: Tokenizer unit test**

The `tokenizer.json` exported in Task 5 is a WordPiece tokenizer with a BERT
pre-tokenizer. Rather than depend on a JVM tokenizers library, implement WordPiece from
the vocab in that file (it is a few dozen lines) and test it against ids produced on the
PC:

```python
# tools/make_tokenizer_fixture.py
"""Writes android/app/src/test/resources/tokenizer_fixture.json: sentences and the ids
the PC tokenizer produces for them, so the Kotlin tokenizer can be tested for equality."""
import json
from pathlib import Path
from tokenizers import Tokenizer
tok = Tokenizer.from_file("android/app/src/main/assets/embedder/tokenizer.json")
sentences = ["A fever is a body temperature above normal.", "Resting heart rate rises during infection.", "Alcohol in the evening can raise overnight heart rate.", "Dizziness, nausea and vomiting since yesterday"]
Path("android/app/src/test/resources").mkdir(parents=True, exist_ok=True)
Path("android/app/src/test/resources/tokenizer_fixture.json").write_text(json.dumps({s: tok.encode(s).ids for s in sentences}, indent=1), encoding="utf-8")
```

```kotlin
class WordPieceTokenizerTest {
    @Test fun matchesThePcTokenizerOnTheFixture() {
        val vocabJson = File("src/main/assets/embedder/tokenizer.json").readText()
        val tok = WordPieceTokenizer.fromTokenizerJson(vocabJson)
        val fixture = Json.parseToJsonElement(File("src/test/resources/tokenizer_fixture.json").readText()).jsonObject
        for ((sentence, ids) in fixture) {
            assertEquals(sentence, ids.jsonArray.map { it.jsonPrimitive.int }, tok.encode(sentence))
        }
    }
}
```

- [ ] **Step 2: Write the tokenizer and the embedder**

`WordPieceTokenizer`: lowercase (the exported tokenizer's normalizer says `lowercase:
true`; read it from the JSON rather than assume), strip accents, split on whitespace and
punctuation, greedy longest-match WordPiece with `##` continuation, `[CLS]` and `[SEP]`,
`[UNK]` for misses, truncation at 512.

```kotlin
// embed/OnnxEmbedder.kt
package dev.wha.app.embed

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import android.content.Context
import java.nio.LongBuffer

class OnnxEmbedder(context: Context) {
    private val env = OrtEnvironment.getEnvironment()
    private val session = env.createSession(context.assets.open("embedder/model.onnx").readBytes())
    private val tokenizer = WordPieceTokenizer.fromTokenizerJson(context.assets.open("embedder/tokenizer.json").bufferedReader().readText())
    private val wantsTypeIds = "token_type_ids" in session.inputNames

    /** Row-major N x 384, CLS pooled, L2 normalised in Python (wha_boot). */
    fun embed(texts: List<String>): FloatArray {
        val encoded = texts.map { tokenizer.encode(it) }
        val length = encoded.maxOf { it.size }
        val n = texts.size
        val ids = LongArray(n * length); val mask = LongArray(n * length)
        encoded.forEachIndexed { i, row -> row.forEachIndexed { j, id -> ids[i * length + j] = id.toLong(); mask[i * length + j] = 1L } }
        val shape = longArrayOf(n.toLong(), length.toLong())
        val inputs = mutableMapOf(
            "input_ids" to OnnxTensor.createTensor(env, LongBuffer.wrap(ids), shape),
            "attention_mask" to OnnxTensor.createTensor(env, LongBuffer.wrap(mask), shape))
        if (wantsTypeIds) inputs["token_type_ids"] = OnnxTensor.createTensor(env, LongBuffer.wrap(LongArray(n * length)), shape)
        session.run(inputs).use { out ->
            @Suppress("UNCHECKED_CAST") val hidden = out[0].value as Array<Array<FloatArray>>   // N x T x 384
            val result = FloatArray(n * 384)
            for (i in 0 until n) System.arraycopy(hidden[i][0], 0, result, i * 384, 384)
            return result
        }
    }
}
```

Add `implementation("com.microsoft.onnxruntime:onnxruntime-android:1.20.0")`.

Instrumented test `OnnxEmbedderTest` (in `src/androidTest`, run on the phone with
`./gradlew connectedDebugAndroidTest` only when adb is available; otherwise a debug-only
"Self test" row in Settings runs the same check): embeds the three agreement sentences and
compares to vectors exported from the PC into `src/androidTest/resources/embedder_fixture.json`
by extending `tools/make_tokenizer_fixture.py`; asserts cosine at or above the same
`MIN_COSINE` as the Python test. This is the phone half of the agreement proof.

- [ ] **Step 3: Corpus fetch**

`CorpusFetch.start` enqueues a `CorpusWorker` (unique, KEEP) that calls
`core.fetchCorpus()` then `core.retrievalReady()`; state moves `Missing` to `Fetching` to
`Ready` or `Failed(message)`. The existing fetch code streams the release into
`data/corpus` under the working directory the boot set; nothing new in Python. Today shows
"General health information is not yet available to the assistant; downloading" while
`Fetching`, and a retry button on `Failed`.

- [ ] **Step 4: Build, install, verify**

Expected, written first: the corpus fetch completes on the phone and `retrieval_ready`
reports true; the Settings self-test row reports cosine agreement above the floor; a
conversation turn that asks about fever quotes a MedlinePlus passage with the National
Library of Medicine named.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/dev/wha/app/embed android/app/src/main/java/dev/wha/app/corpus android/app/src/test android/app/src/androidTest tools/make_tokenizer_fixture.py
git commit -m "Embed on the phone with the same model the PC uses, and fetch the corpus it retrieves from

Retrieval on the phone must rank the same passages as on the PC. The tokenizer is checked
against PC ids and the vectors against PC vectors, so the agreement is measured on the
device rather than assumed."
```

---
### Task 17: The shell and the Today screen

Spec sections 6.2, 6.4. Bottom bar, and the screen a person sees most.

**Files:**
- Create: `ui/Shell.kt` (Scaffold, `NavigationBar`, `NavHost` with routes `today`, `history`, `record`, `settings`, `investigation/{id}`)
- Create: `ui/today/{TodayScreen.kt,TodayViewModel.kt,TodayUiState.kt}`
- Create: `ui/common/{StatusWord.kt,SignalQualityLine.kt,ErrorCard.kt,Provenance.kt}`
- Modify: `MainActivity.kt` (onboarding or shell)
- Test: `ui/today/TodayViewModelTest.kt`

**Interfaces:**
- Consumes: `WhaCore.status`, `urgency`, `pending`, `night`, `nightPipeline`, `conversation`, `say`, `answer`, `review`, `acknowledgeUrgency`, `wording`, `config`, `CorpusFetch.state`.
- Produces: `TodayUiState(lastNight: LastNight?, signal: SignalQuality, pending: PendingInteraction?, urgency: Urgency?, quietReason: String?, providerConfigured: Boolean, corpus: CorpusState, thread: List<Turn>, error: WhaResult.Err?)`; `StatusWord(level: String)` composable rendering colour plus icon plus word for `GREEN`, `YELLOW`, `RED`, `NA`; `Provenance(layer: String)` chip rendering "arithmetic", "rule", "model", "you" with its layer colour; `ErrorCard(err, onRetry, onOpenSettings)` rendering the three error kinds in words.

- [ ] **Step 1: Failing view model test**

```kotlin
class TodayViewModelTest {
    private val core = FakeWhaCore()

    @Test fun aRedNightWithNoQuestionShowsTheReasonTheSystemIsQuiet() = runTest {
        core.canned["status"] = """{"components":[],"usable_nights":12,"rung":"SHRINKING","errors_24h":0,"quiet_nights_streak":0,"unmeasured_recent_nights":0}"""
        core.canned["pending"] = "null"
        core.canned["urgency"] = """{"urgency":"none","reason":"","set_on":null,"days_ago":null,"stale":false,"cleared":true}"""
        core.canned["night_pipeline"] = """{"subject_id":"me","night_date":"2026-09-09","episode_id":"e1","headline":{"level":"RED","flagged":true,"rung":"SHRINKING","coverage_minutes":340,"questions_asked":0,"sources_read":2},
            "steps":[{"step_id":"decide","ordinal":13,"layer":"agentic","status":"ran","reason":"Asking would not change what the system concludes, so it is watching another night.","outputs":{"action":"OBSERVE"}}]}"""
        core.canned["nights"] = """[{"night_date":"2026-09-09","level":"RED","usable":true,"coverage_minutes":340,"sleep_source":"recorded","episode_id":"e1"}]"""
        core.canned["conversation"] = "[]"
        val vm = TodayViewModel(core, subject = "me")
        vm.refresh(); advanceUntilIdle()
        val s = vm.state.value
        assertEquals("RED", s.lastNight?.level)
        assertEquals("Asking would not change what the system concludes, so it is watching another night.", s.quietReason)
        assertNull(s.pending)
    }

    @Test fun anUnavailableCoreBecomesAnErrorCardNotACrash() = runTest {
        core.canned["status"] = """{"error":{"kind":"unavailable","message":"no database yet"}}"""
        val vm = TodayViewModel(core, "me"); vm.refresh(); advanceUntilIdle()
        assertEquals(ErrorKind.UNAVAILABLE, vm.state.value.error?.kind)
    }

    @Test fun sayingSomethingAppendsToTheThreadThroughTheCore() = runTest {
        core.canned["say"] = """{"text":"Noted. Has the dizziness changed since yesterday?","citations":[],"refused":false}"""
        core.canned["conversation"] = """[{"role":"user","text":"I feel dizzy"},{"role":"assistant","text":"Noted. Has the dizziness changed since yesterday?"}]"""
        val vm = TodayViewModel(core, "me"); vm.say("I feel dizzy"); advanceUntilIdle()
        assertEquals(listOf("say", "conversation"), core.calls.takeLast(2))
        assertEquals(2, vm.state.value.thread.size)
    }
}
```

The `quietReason` rule: when there is no pending interaction and last night is flagged or
an episode is open, the reason is the `reason` sentence of the `decide` step in last
night's pipeline; when last night is not flagged, it is `wording["today.quiet.<level>"]`
(add these keys to `wording.py` in this task: one sentence per level saying what the level
means for why nothing was asked, containing no digit). This is the spec's rule that silence
shows its reasoning.

- [ ] **Step 2: Screen layout**

Top to bottom, in a `LazyColumn`:

1. **Last night card**: date in words, `StatusWord(level)`, `wording.level(level, rung)`
   rendered from the `wording` map with the same `_PERSONAL_RUNGS` qualification the Python
   helper applies (port `level()` to Kotlin in `ui/common/Wording.kt`, six lines, tested).
   Under it `SignalQualityLine`: contact minutes formatted from data, "over the sleep your
   watch recorded" or "over a clock window because no sleep was recorded" from
   `NightRow.sleep_source` (check the real field name at `models.py:409`), and the baseline
   line: `wording.rung(rung)` plus "from N nights" with N from `status.usable_nights`.
2. **Provider notice** when `!providerConfigured`: "No model provider is configured, so
   investigations cannot run and the assistant cannot reply. Readings are still watched."
   with a button to Settings. (Disclosure, Task 24.)
3. **Corpus notice** while fetching or failed (Task 16).
4. **Urgency card** when `urgency.urgency != "none"` and not cleared: the reason sentence,
   `wording["home.emergency"]`, and an "I have read this" button calling
   `acknowledgeUrgency`; the card stays until the core reports cleared.
5. **Pending card**: for `question`, the text, one `FilledTonalButton` per option and a
   "Not now" `TextButton`, plus a free-text field, each calling `answer`; for `review`, the
   draft outcome's prose with approve, edit (opens a text field prefilled), reject and
   escalate, calling `review`; for `measurement`, the request text and a "Done" button
   calling `answer` with `declined=false` (check how the dashboard submits a measurement at
   `1_Today.py:123-135` and mirror it exactly).
6. **Quiet reason card** when no pending: the sentence, with `Provenance("arithmetic")`
   if it came from the `decide` step (the policy is arithmetic) and a "See the steps" link
   to the Record tab on that night.
7. **Being looked into**: the open episode's summary line and a link to Investigation.
8. **Conversation thread**: turns as chat bubbles, citations under an assistant turn with
   the source label from the core's `citations` (the label text arrives from Python; never
   compose it here), an amber "not from a cited source" block rendered exactly when the
   turn carries the core's flag for it, and the input row at the bottom.

Every card has a `Refresh` on pull-down. Every core error renders `ErrorCard` in place of
the card that needed it, and the rest of the screen stays.

- [ ] **Step 3: Build, install, verify on the phone**

Expected, written first, on real data: the last night card shows the real level and the
real contact minutes; the baseline line says the rung the PC's dashboard says for the same
data; with no provider key the provider notice shows; typing "I feel dizzy" produces a
reply that names its source or carries the amber block; a screenshot of each state goes to
`docs/screenshots/android/today-*.png`.

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/java/dev/wha/app/ui android/app/src/test android/app/src/main/res src/wha/wording.py docs/screenshots/android
git commit -m "Show last night, what is pending, and why the system is quiet, on one screen

The reason for silence is drawn from the decide step's own sentence, labelled as
arithmetic, because a person who is getting worse must never read silence as safety."
```

---

### Task 18: History

Spec section 6.6, and the dataviz skill's rules.

**Files:**
- Create: `ui/history/{HistoryScreen.kt,HistoryViewModel.kt,NightChart.kt}`
- Test: `ui/history/HistoryViewModelTest.kt`, `ui/history/NightChartGeometryTest.kt`

**Interfaces:**
- Consumes: `WhaCore.nights`, `episodes`, `config` (for the band and threshold constants to label), `wording`.
- Produces: `NightChart(nights: List<NightSummary>, onTapNight: (String) -> Unit)` drawn with `Canvas`; a table view toggle listing the same rows.

- [ ] **Step 1: Chart rules, decided before drawing**

Form: change over time of one measure (resting heart rate) against a personal band. So:
one y axis; the band as a light fill of the accent at low alpha behind a 2px line of
`OnSurface`; each night a filled circle of at least 8dp in its status colour with a 2dp
surface ring; unmeasured nights drawn as an open circle in `Muted` and labelled "not
measured" in the table, never omitted, because a gap that looks like a quiet night is the
defect the status model names. No dual axis. Direct labels only on the newest night and
on flagged nights. Legend row above the chart with the three status words plus "usual
range" and "not measured", each with its icon. A table view button switches to the row
list with the same columns the dashboard shows (`2_History.py:95-110`). Hover is a tap:
tapping a point shows a tooltip with date, the reading, the band, and the level word, and
a second tap opens the Record tab on that night.

- [ ] **Step 2: Failing geometry test**

```kotlin
class NightChartGeometryTest {
    @Test fun yScaleMapsBandAndPointsIntoThePlotArea() {
        val nights = listOf(
            NightSummary(night_date = "2026-09-01", rhr_bpm = 60.0, band_lo = 57.0, band_hi = 63.0, level = "GREEN", usable = true, coverage_minutes = 400),
            NightSummary(night_date = "2026-09-02", rhr_bpm = 70.0, band_lo = 57.0, band_hi = 63.0, level = "RED", usable = true, coverage_minutes = 380),
            NightSummary(night_date = "2026-09-03", rhr_bpm = null, band_lo = null, band_hi = null, level = "NA", usable = false, coverage_minutes = 0))
        val g = NightChartGeometry(nights, plotHeightPx = 200f, plotWidthPx = 300f)
        assertTrue(g.y(70.0) < g.y(60.0))                   // higher rate is higher on screen
        assertEquals(3, g.xs.size)                          // unmeasured nights keep their slot
        assertTrue(g.yMin <= 57.0 - g.padding && g.yMax >= 70.0 + g.padding)
        assertNull(g.points[2].y)                           // and draw as open markers
    }
}
```

- [ ] **Step 3: Draw it, then validate the colours**

Run the dataviz validator on the three status colours plus the band accent in light mode
(`node scripts/validate_palette.js "#0CA30C,#FAB219,#D03B3B,#2F6F73" --mode light` from
the skill directory). Status colours are not a categorical palette, so a CVD failure
between amber and green is expected and is mitigated by the icon plus word rule; record
the run's output in `android/README.md` under "Chart colours" so the mitigation is
written where the numbers are. Anything else that fails is fixed before commit.

- [ ] **Step 4: Build, install, verify**

Expected, written first: sixty nights render with the band; a night the watch did not
measure shows as an open circle and reads "not measured" in the table; tapping the newest
night opens the Record tab on it; screenshot to `docs/screenshots/android/history.png`.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/dev/wha/app/ui/history android/app/src/test android/README.md docs/screenshots/android
git commit -m "Draw the nights against the person's own band, with missing nights visible

One axis, status by colour plus icon plus word, and an unmeasured night drawn as a gap
with a label rather than dropped, because a dropped night reads as a quiet one."
```

---

### Task 19: The Record tab: the graph frame and the step sheet

Spec sections 7.1 and 7.4.

**Files:**
- Create: `ui/record/{RecordScreen.kt,RecordViewModel.kt,PipelineGraph.kt,GraphLayout.kt,StepSheet.kt,RecordUiState.kt}`
- Test: `ui/record/GraphLayoutTest.kt`, `ui/record/RecordViewModelTest.kt`

**Interfaces:**
- Consumes: `WhaCore.pipelineNights`, `nightPipeline`, `lineage`, `wording`, `config`.
- Produces: `GraphLayout.build(steps: List<PipelineStepView>): List<Node>` with fixed group membership and positions; `PipelineGraph(layout, highlighted: Set<String>, running: String?, onTap: (String) -> Unit)`; `StepSheet(step: PipelineStepView, wording: Map<String, String>, onTapOutput: (String) -> Unit)`.

- [ ] **Step 1: Failing layout test**

```kotlin
class GraphLayoutTest {
    private fun step(id: String, ordinal: Int, layer: String, status: String = "ran") =
        PipelineStepView(step_id = id, ordinal = ordinal, layer = layer, status = status, reason = "")

    @Test fun twentyOneStepsFallIntoFiveGroupsInOrder() {
        val steps = CanonicalSteps.all.map { step(it.id, it.ordinal, it.layer) }
        val nodes = GraphLayout.build(steps)
        assertEquals(21, nodes.size)
        assertEquals(listOf("Reading the watch", "Comparing with your normal", "What you have told us", "The investigation", "The safety rules on your words"),
            nodes.map { it.group }.distinct())
        assertTrue(nodes.zipWithNext().all { (a, b) -> a.ordinal < b.ordinal })
    }

    @Test fun aSkippedStepStaysInPlaceDimmed() {
        val steps = CanonicalSteps.all.map { step(it.id, it.ordinal, it.layer, if (it.id == "ask") "skipped" else "ran") }
        val ask = GraphLayout.build(steps).single { it.id == "ask" }
        assertTrue(ask.dimmed)
        assertEquals(14, ask.ordinal)
    }

    @Test fun layerMapsToTheFourMachineWords() {
        assertEquals("arithmetic", GraphLayout.machineWord("deterministic"))
        assertEquals("rule", GraphLayout.machineWord("safety"))
        assertEquals("model", GraphLayout.machineWord("agentic"))
        assertEquals("you", GraphLayout.machineWord("user"))
    }
}
```

`CanonicalSteps.all` is generated: `tools/android_canonical_steps.py` writes
`android/app/src/main/java/dev/wha/app/core/CanonicalSteps.kt` from
`CANONICAL_PIPELINE_STEPS` and the group table in spec section 7.1, and a Python test
asserts the generated file equals what the generator produces now, so the graph frame
cannot drift from the step list.

- [ ] **Step 2: Draw the frame**

`PipelineGraph` is a `Canvas` inside a vertical scroll: five group headers with the group
name and its machine word; nodes as rounded rectangles 56dp tall, full width less margins,
in ordinal order, joined by 2dp connectors; the conditional branches after `decide`
(`ask`, `conclude`, or watching another night) and after `ask` (back to `investigate`)
drawn as labelled side connectors so the loop is visible. Each node shows: the ordinal,
the step's short title from `wording["step.<id>.what"]` first clause, the `Provenance`
chip, a tick or a dimmed state, and the headline figure if any. A `running` node pulses
with an animated alpha. A `highlighted` set draws nodes at full opacity and everything
else at reduced opacity (Task 21 uses it).

`StepSheet` is a `ModalBottomSheet` with: the title, the `reason` sentence, the layer
statement (`wording["layer.<layer>"]`, four new keys added to `wording.py`: what it means
that arithmetic, a rule, a model or the person produced this), the headline figure,
`occurred_utc` localised through `core.localise` when present, inputs and outputs as
labelled rows where each output row is tappable (Task 21), sources with the label text the
core supplies, and the full `detail_json` under an expander titled "Everything recorded".

- [ ] **Step 3: View model**

`RecordUiState(nights: List<PipelineNightRef>, selected: String?, pipeline: NightPipeline?,
lineage: List<LineageEdge>, highlighted: Set<String>, running: String?, replay: ReplayState,
sheet: PipelineStepView?, error)`. `RecordViewModel.select(date)` loads the pipeline;
`open(stepId)` sets the sheet. The night picker is a horizontal row of chips built from
`pipeline_nights`, newest first, each chip coloured by its level with the word.

- [ ] **Step 4: Build, install, verify**

Expected, written first: the newest night shows all twenty-one nodes; on a green night
the investigation group is dimmed with reasons like "no investigation was opened, because
the night was in your usual range"; tapping "detect" opens its sheet with the level, the
residual and the rule sentence; screenshot to `docs/screenshots/android/record-graph.png`.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/dev/wha/app/ui/record android/app/src/main/java/dev/wha/app/core/CanonicalSteps.kt tools/android_canonical_steps.py tests/unit/android android/app/src/test src/wha/wording.py docs/screenshots/android
git commit -m "Draw every night as the same twenty-one steps, labelled by which machine ran each

The frame is generated from the canonical step list so a step added on the PC appears on
the phone, and a step that did not run stays in place dimmed with its reason."
```

---

### Task 20: The Record tab: live progress and replay

Spec sections 7.2 and 7.3.

**Files:**
- Modify: `ui/record/{RecordViewModel.kt,RecordScreen.kt}`
- Create: `ui/record/{LivePoller.kt,Replay.kt,ReplayControls.kt}`
- Test: `ui/record/ReplayTest.kt`, `ui/record/LivePollerTest.kt`

**Interfaces:**
- Consumes: `RunState` (Task 14), `WhaCore.nightPipeline`.
- Produces: `LivePoller(core, subject).observe(): Flow<NightPipeline>` polling once a second while `RunState` is `Running`, emitting on change, stopping when idle; `Replay(steps).state: StateFlow<ReplayState(index, playing)>` with `play()`, `pause()`, `next()`, `previous()`, `seek(i)`, advancing every `cadenceMs` while playing.

- [ ] **Step 1: Failing tests**

```kotlin
class ReplayTest {
    @Test fun playAdvancesOneStepPerTickAndStopsAtTheEnd() = runTest {
        val replay = Replay(stepCount = 3, cadenceMs = 100, scope = this)
        replay.play(); advanceTimeBy(350)
        assertEquals(2, replay.state.value.index)
        assertFalse(replay.state.value.playing)
    }
    @Test fun previousDoesNotGoBelowZero() = runTest {
        val replay = Replay(3, 100, this); replay.previous()
        assertEquals(0, replay.state.value.index)
    }
}

class LivePollerTest {
    @Test fun pollsOnlyWhileRunningAndEmitsOnChange() = runTest {
        val core = FakeWhaCore()
        core.canned["night_pipeline"] = """{"subject_id":"me","night_date":"2026-09-09","headline":{"level":"NA","flagged":false,"coverage_minutes":0,"questions_asked":0,"sources_read":0},"steps":[]}"""
        RunState.set(RunState.Status.Running("nightly", Instant.EPOCH))
        val emitted = mutableListOf<NightPipeline>()
        val job = launch { LivePoller(core, "me", "2026-09-09", intervalMs = 100).observe().toList(emitted) }
        advanceTimeBy(250)
        core.canned["night_pipeline"] = core.canned["night_pipeline"]!!.replace("\"steps\":[]", "\"steps\":[{\"step_id\":\"collect\",\"ordinal\":1,\"layer\":\"deterministic\",\"status\":\"ran\",\"reason\":\"\"}]")
        advanceTimeBy(150)
        RunState.set(RunState.Status.Idle)
        advanceTimeBy(150); job.cancel()
        assertEquals(2, emitted.size)                       // initial, then the change; no emit on equal
        assertTrue(core.calls.count { it == "night_pipeline" } in 3..5)
    }
}
```

- [ ] **Step 2: Implement**

`LivePoller.observe()` is a `flow { }` that loops while `RunState.status` is `Running`,
calls `core.nightPipeline`, emits when the result differs from the last emitted (data
class equality), delays `intervalMs`, and completes when idle. The view model collects it
and sets `running` to the highest-ordinal step whose status is `ran` plus one, so the
next node pulses; when the run ends it reloads once and clears `running`.

If, on the phone, the agent half shows no intermediate steps during an investigation
(all tool calls appearing at once at the end), add the optional observer hook from spec
section 7.2: in `agent/graph.py`'s `bind`, wrap each node to write a row
`(episode_id, node, started_utc)` to a new `agent_progress` table before calling it, and
have `service/pipeline.py`'s `_agent_steps` read that table to report a step as running.
Add the table to `schema.sql` and the contract. Do this only if the polling alone is
judged too coarse when watched on the phone, and say in the commit which it was.

`Replay` is a small state machine; `ReplayControls` is a row of `IconButton`s (first,
previous, play or pause, next, last) with a caption under the graph showing the current
step's `reason` sentence and the note "Replay pacing is fixed for reading; it is not how
long each step took" (a `wording` key, disclosed in Task 24). During replay, nodes with
ordinal above the index are drawn dimmed and the current node is `running`.

- [ ] **Step 3: Build, install, verify**

Expected, written first: trigger the nightly job from Settings (Task 23 adds "Run now"
buttons); the graph animates through the deterministic group within a second and, on a
flagged night with the mock watch, the investigation nodes tick as the tool calls land;
replay of a past night steps at the fixed cadence with the caption changing; screenshots
to `docs/screenshots/android/record-live.png` and `record-replay.png`.

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/java/dev/wha/app/ui/record android/app/src/test src/wha/wording.py docs/screenshots/android
git commit -m "Show the pipeline moving while it runs, and let any night be replayed step by step

Progress is read from what each step wrote, so the picture cannot claim work that did not
happen. Replay pacing is fixed for reading and says so."
```

---

### Task 21: The Record tab: lineage on tap, and how it works by topic

Spec sections 7.5 and 7.6.

**Files:**
- Modify: `ui/record/{RecordViewModel.kt,StepSheet.kt,RecordScreen.kt}`
- Create: `ui/record/{Lineage.kt,HowItWorksTab.kt}`
- Test: `ui/record/LineageTest.kt`

**Interfaces:**
- Consumes: `WhaCore.lineage`, `config`, `wording`.
- Produces: `Lineage(edges).upstream(step, output): Set<String>` and `downstream(step, output): Set<String>`; tapping an output row in `StepSheet` closes the sheet and sets `highlighted = upstream + downstream + {step}` on the graph with a banner "Highlighting where this came from and what read it; tap anywhere to clear".

- [ ] **Step 1: Failing test**

```kotlin
class LineageTest {
    private val edges = listOf(
        LineageEdge("features", "resting_hr_bpm", "baseline"),
        LineageEdge("features", "resting_hr_bpm", "subtract_explained"),
        LineageEdge("baseline", "centre_bpm", "subtract_explained"),
        LineageEdge("subtract_explained", "residual_bpm", "detect"),
        LineageEdge("detect", "level", "safety_floor"))
    @Test fun downstreamFollowsEveryConsumerTransitively() {
        assertEquals(setOf("baseline", "subtract_explained", "detect", "safety_floor"), Lineage(edges).downstream("features", "resting_hr_bpm"))
    }
    @Test fun upstreamFollowsProducersOfWhatTheStepRead() {
        assertEquals(setOf("subtract_explained", "features", "baseline"), Lineage(edges).upstream("detect", "residual_bpm"))
    }
}
```

- [ ] **Step 2: Implement lineage and the topic tab**

`Lineage` builds two adjacency maps and walks them. `RecordScreen` gains a `TabRow` with
"This night" and "How it works". `HowItWorksTab` renders the same topic list as
`ui/components/how_it_works.py` (`TOPIC_STEPS` and its texts), which means those texts
move into `wording.py` under `topic.<n>.title` and `topic.<n>.body` keys in this task, with
every figure interpolated at render time from `config` exactly as the Streamlit component
does, and the Streamlit component reads the moved keys. The Python test that asserts
`TOPIC_STEPS` covers all twenty-one steps keeps running on the dashboard side; add a Kotlin
test asserting the generated `CanonicalSteps` are all covered by the topic table the app
renders, so the two surfaces cannot drift.

- [ ] **Step 3: Build, install, verify**

Expected, written first: tapping `residual_bpm` in the detect sheet highlights features,
baseline and subtract explained upstream and safety floor and episode open downstream;
the topic tab shows the thresholds as the dashboard shows them; screenshot to
`docs/screenshots/android/record-lineage.png`.

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/java/dev/wha/app/ui/record android/app/src/test src/wha/wording.py src/wha/ui/components/how_it_works.py docs/screenshots/android
git commit -m "Trace any result to the steps that made it and the steps that read it

Lineage is declared once in the core and walked on the phone. The topic explainer moves
into the shared wording so the phone and the dashboard describe the machinery identically."
```

---

### Task 22: Investigation

Spec section 6.5. Three layers.

**Files:**
- Create: `ui/investigation/{InvestigationScreen.kt,InvestigationViewModel.kt,BeliefBars.kt}`
- Test: `ui/investigation/InvestigationViewModelTest.kt`

**Interfaces:**
- Consumes: `WhaCore.episode`, `handover`, `review`, `wording`, `config`, `knowledgeProvenance`.
- Produces: `InvestigationUiState(detail: EpisodeDetail?, narrative: List<String>, causes: List<CauseBar>, handover: Handover?, error)`.

- [ ] **Step 1: Failing test**

```kotlin
class InvestigationViewModelTest {
    @Test fun causesAreRankedFromTheLatestBeliefAndNamedInWords() = runTest {
        val core = FakeWhaCore()
        core.canned["episode"] = """{"summary":{"episode_id":"e1","opened_on":"2026-09-08","state":"CLOSED","disposition":"LIKELY_BENIGN","night_span":["2026-09-07","2026-09-08"],"top_cause":"alcohol","top_probability":0.61},
          "outcome":{"disposition":"LIKELY_BENIGN","prose":"Your raised rate is most consistent with alcohol the evening before.","when_to_seek_care":"If you develop fever, see a clinician.","reviewed_by_person":true},
          "stages":[],"belief_history":[[1,"prior",{"marginals":{"alcohol":0.2,"infection":0.2}}],[2,"after answers",{"marginals":{"alcohol":0.61,"infection":0.12}}]],
          "interactions":[{"id":"i1","probe_id":"alcohol","question_text":"Did you drink last night?","text_source":"llm","options":[],"evsi":0.3,"interruption_cost":0.2,"rejected":[],"answer_option_id":"yes","status":"answered","asked_at_utc":"2026-09-08T09:00:00Z"}],
          "measurements":[],"citations":[],"stripped_claims":["It is probably a virus."]}"""
        core.canned["wording"] = """{"cause.alcohol":"alcohol the evening before","cause.infection":"an infection starting"}"""
        val vm = InvestigationViewModel(core, "e1"); vm.load(); advanceUntilIdle()
        val s = vm.state.value
        assertEquals(listOf("alcohol the evening before", "an infection starting"), s.causes.map { it.label })
        assertEquals(0.61, s.causes.first().probability, 1e-9)
        assertTrue(s.narrative.any { it.contains("Did you drink last night?") && it.contains("yes") })
        assertEquals(listOf("It is probably a virus."), s.detail?.stripped_claims)
    }
}
```

`cause.<id>` wording keys: add one per `CauseId` to `wording.py` with a Python test that
every member of `CauseId` has one. Check whether `explain.py` already has cause labels
under another key and reuse them if so.

- [ ] **Step 2: Screen**

1. **What it concluded**: `outcome.prose`, the disposition as a word from
   `wording["disposition.<value>"]` (check the dashboard's phrasing source,
   `service/phrasing.py`, and expose it through `wording` if it lives there), the review
   state ("checked by you on <date>" or "closed without review" from `reviewed_by_person`),
   and `when_to_seek_care`. If the episode is awaiting review, the four review buttons here
   too.
2. **Why**: the narrative built from `interactions` and `belief_history`: one sentence per
   question and answer ("You were asked … and answered …"), one per belief movement ("After
   that, the most likely cause became …"), each with a `Provenance` chip for the machine
   that produced it (question text: model or fallback per `text_source`; belief: arithmetic;
   answer: you). Then `BeliefBars`: horizontal bars for the twelve causes from the last
   belief, sorted, labels in words, probability formatted from data, the top bar in the
   accent and the rest in `Muted` with a 2dp gap between bars, direct label on the top bar
   only, a table toggle.
3. **The full trace**, collapsed by default: every stage from `stages` with its reason;
   every interaction's EVSI and interruption cost with the sentence
   `wording["policy.evsi_explained"]` (new key) beside them and the rejected probes listed;
   `measurements`; `citations` with the source label and a link; `stripped_claims` under
   the heading "Sentences removed because no source supported them".
4. **Summary for your doctor**: the handover text with a share button (Android share
   sheet, text only).

- [ ] **Step 3: Build, install, verify**

Expected, written first, on a mock-watch investigation: the conclusion paragraph matches
the dashboard's for the same episode; the bars match the belief on the Record tab's
believe step; the stripped sentences appear; share opens the sheet with the handover text;
screenshot to `docs/screenshots/android/investigation.png`.

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/java/dev/wha/app/ui/investigation android/app/src/test src/wha/wording.py tests/ docs/screenshots/android
git commit -m "Explain an investigation in layers: the conclusion, the why, then everything

Cause and effect in sentences before probabilities, each labelled by which machine said
it, and every sentence the critique removed shown rather than hidden."
```

---

### Task 23: Settings

Spec section 6.7.

**Files:**
- Create: `ui/settings/{SettingsScreen.kt,SettingsViewModel.kt,ConstantsList.kt,DisclosuresList.kt,DiagnosticsList.kt}`
- Test: `ui/settings/SettingsViewModelTest.kt`

**Interfaces:**
- Consumes: `AppSettings`, `WhaCore.settings`, `updateSettings`, `config`, `knowledgeProvenance`, `safetyProvenance`, `diagnose`, `doctor`, `auditExport`, the job runners, `CorpusFetch`, `OnnxEmbedder` self test.
- Produces: the screen sections below.

- [ ] **Step 1: Failing test**

```kotlin
class SettingsViewModelTest {
    @Test fun savingThePortRestartsNothingButChangesTheEnvironmentForNextBoot() = runTest {
        val settings = AppSettings(ApplicationProvider.getApplicationContext())
        val vm = SettingsViewModel(FakeWhaCore(), settings); vm.setWebhookPort("9000"); vm.save(); advanceUntilIdle()
        assertEquals(9000, settings.webhookPort)
        assertTrue(vm.state.value.restartNeeded)
    }
    @Test fun constantsComeFromConfigWithTheirProvenance() = runTest {
        val core = FakeWhaCore()
        core.canned["config"] = """{"RHR_YELLOW_BPM":3.0,"RHR_RED_BPM":4.0,"today":"2026-09-10","configured_subject":"me"}"""
        core.canned["knowledge_provenance"] = """{"RHR_RED_BPM":{"source":"NightSignal, Alavi et al. 2022","kind":"published"}}"""
        val vm = SettingsViewModel(core, AppSettings(ApplicationProvider.getApplicationContext())); vm.load(); advanceUntilIdle()
        val red = vm.state.value.constants.single { it.name == "RHR_RED_BPM" }
        assertEquals("4.0", red.value); assertEquals("NightSignal, Alavi et al. 2022", red.source)
    }
}
```

Use the real constant names from `constants.py` in the canned JSON.

- [ ] **Step 2: Sections**

1. **Data source**: host, port, token, "Test connection", last successful pull from
   `status.last_ingest_utc` localised, and the last ingest error from `status.components`.
   Saving writes `AppSettings` and shows "Takes effect when the app restarts" (Python reads
   the environment at start), with a "Restart now" button that finishes the activity and
   relaunches.
2. **Contact**: read-only list of which message kind goes to which channel, from the
   `MessageKind` enumeration the core exposes through `settings()`; the sentence that
   escalations use the urgent channel and stay until acknowledged.
3. **Model provider**: base URL, model, key (password field), "Test provider".
4. **How the system decides**: every upper-case constant from `config()` with its value,
   grouped as the dashboard groups them (`4_Settings.py`), each with its provenance from
   `knowledgeProvenance` or `safetyProvenance` where one exists and "operating parameter of
   the code" otherwise. Read only.
5. **Disclosures**: the list from `DisclosuresList`, whose entries are generated from
   `docs/DISCLOSURES.md` at build time by the same Copy task, filtered to those naming an
   Android screen, so the file remains the single source.
6. **Diagnostics**: `doctor()` rows with status words; "Run ingest now", "Score nights
   now", "Step episodes now" buttons calling the job runners and showing the returned
   result; the embedder self test (Task 16); the corpus state with retry.
7. **Your record**: "Export the record" calling `auditExport` and sharing the text;
   "Delete everything" is not offered (uninstall does it, and the sentence says so).
8. **About**: version, `LICENSE`, the MedlinePlus attribution sentence from
   `corpus-sources.json`, a link to the repository README.

- [ ] **Step 3: Build, install, verify**

Expected, written first: every constant on the dashboard's Settings page appears with the
same value; the provenance of the red threshold names its source; "Run ingest now"
returns a result and Today updates; export shares a JSONL text; screenshot to
`docs/screenshots/android/settings.png`.

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/java/dev/wha/app/ui/settings android/app/src/test android/app/build.gradle.kts docs/screenshots/android
git commit -m "Put every control, every constant and every disclosure on one screen

Global controls in one place, each number with where it came from, and the disclosures
read from the same file the documentation keeps so a limitation cannot live only in
markdown."
```

---
## Phase 3. Documents and verification

### Task 24: The documents this work owes

Spec section 12. Each of these is checked by a test that already exists or one added here.

**Files:**
- Modify: `docs/CONTRACTS.md` (final pass: sections 1, 2, 5, 6.2, 7, 12 as the tasks above required; confirm every facade function is listed)
- Modify: `docs/DISCLOSURES.md`
- Create: `docs/RESEARCH-HCI.md`
- Modify: `README.md` (Android section; `uv sync --extra pc`)
- Modify: `USER-GUIDE.md` (phone section)
- Modify: `android/README.md` (finish: build, install, measured start-up, chart colours, the remote rules)
- Modify: `docs/superpowers/specs/2026-09-10-android-app-design.md` (section 5: the facade lives at `src/wha_android/facade.py`, imported as `wha_android.facade`; section 4.5: the job functions moved to `service/jobs.py`)
- Test: `tests/unit/android/test_disclosures_name_android_screens.py`

- [ ] **Step 1: Failing disclosure test**

```python
# tests/unit/android/test_disclosures_name_android_screens.py
"""Every limitation the app creates is disclosed, and names the screen that shows it."""

from pathlib import Path

DISCLOSURES = Path("docs/DISCLOSURES.md").read_text(encoding="utf-8")

REQUIRED = {
    "no model provider configured": "Today",
    "general health information is not yet available": "Today",
    "provider unreachable": "Today",
    "webhook unreachable": "Today",
    "replay pacing": "Record",
    "webhook app serves without authentication": "Settings",
    "background work may be delayed by the phone": "Settings",
    "escalation stays until acknowledged": "Settings",
}


def test_every_android_limitation_is_disclosed_with_its_screen() -> None:
    lowered = DISCLOSURES.lower()
    missing = [k for k in REQUIRED if k not in lowered]
    assert not missing, f"docs/DISCLOSURES.md lacks: {missing}"
    for phrase, screen in REQUIRED.items():
        start = lowered.index(phrase)
        window = DISCLOSURES[start : start + 600]
        assert screen in window, f"{phrase!r} does not name the {screen} screen within its entry"
```

Match the phrases to the exact wording you write in the entries; the test's phrases are
lower-case substrings of the entry text.

- [ ] **Step 2: Write the disclosures**

One entry per key above, in the file's existing format (read the top of
`docs/DISCLOSURES.md` for the shape: what the limitation is, why it exists, the screen
that shows it, what a person can do). The "background work may be delayed" entry says
that Android may defer periodic work under battery saving and that the Today screen shows
the time of the last successful pull so a stale reading is visible rather than silent.

- [ ] **Step 3: Write `docs/RESEARCH-HCI.md`**

The five sources from spec section 6.1, each with: full citation, what was studied (method
and population), what it found, which rule in the app it justifies (by spec section 6.2
row), and whether it was read in full or located. The closing paragraph says none studied
this system and that these are interface rules, not clinical ones. No em-dash. Link it
from `README.md`'s document table.

- [ ] **Step 4: README, USER-GUIDE, android/README**

`README.md`: a section "The Android app" after the setup block: what it is in three
sentences, that the PC remains the main system, a link to `android/README.md` and to the
spec, and the line that installing it needs the APK built on a machine with the toolchain
described there. Add `docs/RESEARCH-HCI.md` to the documents table. Change `uv sync` to
`uv sync --extra pc` in the setup block and wherever else it appears
(`test_readme_quickstart_commands_exist` will tell you).

`USER-GUIDE.md`: a section "On your phone" mirroring the guide's existing structure
(what each screen is for, what a notification looks like, what to do when the watch box is
red), written for the person whose health it is.

`android/README.md`: finish with a "Building" section (the three scripts, the wheel
rebuild, the assets copy), "Installing" (sideload and adb), "Measured start-up" (the
timing observed in Task 11, as an engineering observation), "Chart colours" (the validator
output from Task 18), and "What is not built" (no emulator, no release signing yet, no
Play Store).

- [ ] **Step 5: Run the document tests**

Run: `uv run pytest tests/unit/test_docs.py tests/unit/test_contracts.py tests/unit/test_documented_numbers.py tests/unit/android -n auto -q`
Expected: pass. The em-dash sweep covers every new markdown file.

- [ ] **Step 6: Commit**

```bash
git add docs/ README.md USER-GUIDE.md android/README.md tests/unit/android/test_disclosures_name_android_screens.py
git commit -m "Write down what the phone cannot do, where it says so, and why the screens are shaped as they are

A limitation living only in markdown is not disclosed, so each names its screen and a test
holds them to it. The interface rules are traced to the studies that justify them."
```

---

### Task 25: The two on-phone runs, the full suite, and the pull request

Spec section 10, and `AGENTS.md` "How to work" steps 5 to 7.

**Files:**
- Create: `android/verification/2026-09-run1-fresh-install.md`
- Create: `android/verification/2026-09-run2-scripted-illness.md`
- Create: `tools/mock_watch_phone.md` (how to point the phone at the PC's mock watch)

- [ ] **Step 1: Write the expected outcomes first**

Before touching the phone, write both files with an "Expected" column filled and an
"Observed" column empty. Run 1, fresh install against the real webhook:

| Step | Expected |
|---|---|
| Uninstall any previous build, install the release-candidate APK | Onboarding page one shows |
| Pages one and two | Wording matches `wording.py`; Next disabled until the disclaimer is ticked |
| Test connection with the real port | Reports the record types the core sees; a wrong port reports unavailable in words |
| Test provider with the rotated key | Reports success |
| Finish | Notification permission asked; corpus fetch starts; Today shows the provider notice absent and the corpus notice present |
| Within one minute | Today shows the last pull time and last night with its level |
| History | Thirty days of nights; unmeasured nights open circles; the band present once the rung allows |
| Record | Newest night's twenty-one steps; investigation group dimmed with reasons |
| Settings | Every constant matches the dashboard on the PC for the same constant |
| Corpus finished | Retrieval ready; a chat turn about fever quotes MedlinePlus with the Library named |

Run 2, scripted illness from the mock watch. `tools/mock_watch_phone.md` explains: run
`uv run python tools/mock_watch.py` on the PC (read `docs/RUNBOOK-SIMULATION.md` for the
scenario flags), find the PC's address on the phone's hotspot network, set the app's
webhook host to it in Settings, restart the app, and use "Run ingest now" and "Score nights
now" per simulated day.

| Day | Expected |
|---|---|
| Quiet nights | Green, no notification, Today's quiet reason from the level wording |
| First red night | Red, no investigation (rule needs two), quiet reason says a second night is needed |
| Second red night | Investigation opens; foreground notification while it runs; Record tab animates through the investigation group; a question arrives as a notification |
| Tap an option | Recorded; Today's thread shows it; the notification clears; Record's answer step ran |
| Next tick | Belief moves; a conclusion or another question per the policy; the Investigation screen's narrative reads in order |
| Type a Tier A phrase in chat | Escalation notification on the urgent channel, ongoing; Today's urgency card; acknowledge clears it and the audit shows the acknowledgement |
| Review pending | The draft with four buttons; approve closes it; History lists the episode |
| Replay that night | Steps in order with the captions; lineage from the detect residual highlights the right steps |
| Kill the app during an investigation, reopen | The episode resumes from its checkpoint on the next tick, not from the start |

- [ ] **Step 2: Run them, fill "Observed", fix, re-run from scratch**

Per the owner's standing rule: record every finding, fix afterwards, then retest from a
fresh install. Each defect found gets its own commit with the observation in the message.
The verification files are committed with both columns filled and the date.

- [ ] **Step 3: The full suite and ruff, once**

Run: `uv run ruff check . && uv run ruff format --check . && uv run pytest -n auto -q`
Expected: clean, all tests pass, including the UI tests that drive the Streamlit pages
through AppTest, which proves the dashboard survived the wording move and the dependency
split. Then on the remote: `./gradlew --no-daemon --max-workers=8 :app:testDebugUnitTest lint && ./gradlew --stop`.

- [ ] **Step 4: Update memory and the spec's status line**

Add a line under the spec's title: "**Status:** implemented on `feat/android-app`, PR
#N, verified on the owner's phone on <date> (see `android/verification/`)".

- [ ] **Step 5: Push and open the PR**

```bash
git push -u origin feat/android-app
gh pr create --title "Run the whole system on the phone as a standalone Android app" --body-file android/PR.md
```

`android/PR.md` (not committed; written for the PR body) states: what was built, the wheel
outcome chosen and why, the two verification runs with links, what was deliberately not
done (release signing, Play Store, emulator, a second language), and the sentence that
merging into `main` needs the admin override and is the owner's decision.

- [ ] **Step 6: Stop the Gradle daemon and leave the remote clean**

Run: `bash android/remote/run.sh 'cd android && ./gradlew --stop; ls /home/liangsheng/brian/android'`
Expected: no daemon running; only `env.sh`, `tools/`, `wha/`, `wheels/` and
`wheel-work/` present, nothing outside our directory touched.

---

## Self-review against the spec

| Spec section | Task |
|---|---|
| 1 decisions | Global constraints; 11 (localhost webhook, port setting), 17 (chat in Today), 15 (notifications as the system has them), 19 to 21 (Record) |
| 2 what this is not | Global constraints; 13 (provider fallback disclosed); 24 |
| 3 shape | 3, 11, 12 |
| 4.1 dependency split | 4 |
| 4.2 wheels and the three outcomes | 2, 10 |
| 4.3 embedder | 5, 16 |
| 4.4 paths | 11 |
| 4.5 schedule | 14 (and `service/jobs.py` in 7) |
| 4.6 notifier | 6, 15 |
| 4.7 provider key | 13 |
| 5 facade | 7, 12 |
| 6.1 sources | 24 |
| 6.2 rules | 11 (colour plus word plus icon, no digits), 17, 22 |
| 6.3 onboarding | 13 |
| 6.4 Today | 17 |
| 6.5 Investigation | 22 |
| 6.6 History | 18 |
| 6.7 Settings | 23 |
| 7.1 frame | 19 |
| 7.2 live | 20 |
| 7.3 replay | 20 |
| 7.4 inspect | 19 |
| 7.5 lineage | 8, 21 |
| 7.6 by topic | 21 |
| 8 storage and offline | 11, 16, 17 (notices), 23 (export) |
| 9 errors | 7, 12, 17 |
| 10 testing | every task's tests; 25 |
| 11 toolchain | 1, 3 |
| 12 documents | 24 |
| 13 risks | 2 (wheels), 11 (start-up measured), 14 (battery), 11 and 18 (calm look), 9 (wording drift) |

Type consistency checked: `WhaResult`, `ErrorKind`, `WhaCore` method names and the
facade function names match between Tasks 7, 12 and every screen task; `RunState` is
defined in Task 14 and read in Task 20; `Provenance` and `StatusWord` are defined in Task
17 and used in 19 and 22; `CanonicalSteps` is generated in Task 19 and used in 21;
`wording` keys added: `today.quiet.<level>` (17), `layer.<layer>` (19), `cause.<id>`,
`disposition.<value>`, `policy.evsi_explained` (22), `topic.<n>.*` (21), the replay note
(20).
