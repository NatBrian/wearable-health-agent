#!/usr/bin/env bash
# android/remote/build-apk.sh [assembleDebug|assembleRelease]
# Syncs, builds on the remote under nice with capped workers, copies the APK back to
# android/out/, and stops the Gradle daemon so nothing of ours lingers on a shared box.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/../.." && pwd)"
TASK="${1:-assembleDebug}"
HOST="${WHA_REMOTE_HOST:-huawei_blue_1_ppt}"
REMOTE_ANDROID=/home/liangsheng/brian/android/wha/android
bash "$HERE/android/remote/sync.sh"
bash "$HERE/android/remote/run.sh" "cd android && chmod +x gradlew && ./gradlew --no-daemon --max-workers=8 $TASK; status=\$?; ./gradlew --stop > /dev/null 2>&1 || true; exit \$status"
mkdir -p "$HERE/android/out"
if [ "$TASK" = "assembleRelease" ]; then
  scp "$HOST:$REMOTE_ANDROID/app/build/outputs/apk/release/app-release.apk" "$HERE/android/out/"
else
  scp "$HOST:$REMOTE_ANDROID/app/build/outputs/apk/debug/app-debug.apk" "$HERE/android/out/"
fi
ls -la "$HERE/android/out/"
