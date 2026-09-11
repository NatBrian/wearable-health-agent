# The Android app

Built on the shared remote machine, installed on the owner's phone. The design is
`docs/superpowers/specs/2026-09-10-android-app-design.md`; the plan is
`docs/superpowers/plans/2026-09-10-android-app.md`; the build steps are here.

## Remote machine rules

Only `/home/liangsheng/brian/android` is ours. No sudo, nothing outside it, nothing
killed that is not ours, no shell profile edits, builds under `nice`, Gradle daemon stopped
after a session (`android/remote/run.sh 'cd android && ./gradlew --stop'`).

The remote's GitHub key belongs to a different account, so it never clones this
repository. Source travels by tar over SSH with `android/sync-exclude.txt` applied, and a
test keeps that list honest.

## Scripts

| Script | Does |
|---|---|
| `android/remote/sync.sh` | Pushes this worktree to the remote with `android/sync-exclude.txt` applied |
| `android/remote/run.sh '<cmd>'` | Runs a command on the remote with the toolchain on PATH |
| `android/remote/install-toolchain.sh` | One-time toolchain install, pinned versions, user space only |

## Pinned versions

JDK 17 (Temurin latest GA), command-line tools 11076708, platform 35, build-tools 35.0.0,
NDK 27.2.12479018, Python 3.13 via uv, cibuildwheel 3.x.

## Building

```bash
bash android/remote/sync.sh                                  # push this tree to the remote
bash android/remote/run.sh 'cd android && ./gradlew --no-daemon --max-workers=8 :app:testDebugUnitTest'
bash android/remote/build-apk.sh                             # assemble the APK
```

The phone's Python comes from `uv.lock` via `tools/android_requirements.py`, which
writes `android/app/requirements-android.txt`; prebuilt wheels that Chaquopy cannot
use live under `android/wheels/` with their provenance in `android/wheels/BUILD.md`.
Rebuilding a wheel is documented there. `data/knowledge/`, the disclaimer, the
disclosures, the licence and the embedder self-test fixture are copied into the APK
at build time by Copy tasks in `android/app/build.gradle.kts`, so the repository
stays the single source for each.

## Installing

Sideload the APK from `android/app/build/outputs/apk/debug/`:

```bash
adb install -r app-debug.apk
```

or copy it to the phone and open it. Point the app's data source at the watch box
address on the same network (see `tools/mock_watch_phone.md` for the mock watch),
enter the model address, and finish onboarding. Uninstalling removes everything
the app holds: there is no account and no server copy.

## Measured start-up

Not measured yet. The first install is Task 25, which notes the time from tap to
the first screen here as a plain engineering observation.

## Chart colours

Status colours, light mode: usual `#0CA30C`, raised `#FAB219`, high `#D03B3B`,
usual range `#2F6F73` at low alpha behind the line. Amber and green are expected
to differ under some colour vision; the mitigation is that status is never
colour alone: every point carries an icon plus a word, and the tooltip and the
table repeat the word. The dataviz validator run is deferred to the first phone
build (Task 25): it lives in the skill directory, not in this repository.

## What is not built

No emulator runs (every check is on the owner's phone or Robolectric), no
release signing yet, no Play Store listing, and one language.
