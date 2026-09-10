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
