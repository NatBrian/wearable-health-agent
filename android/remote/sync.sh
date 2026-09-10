#!/usr/bin/env bash
# Push this worktree to the shared build machine. tar over ssh, because the PC has no rsync
# and the remote must never clone the private repository with its own GitHub key.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/../.." && pwd)"
HOST="${WHA_REMOTE_HOST:-huawei_blue_1_ppt}"
DEST="/home/liangsheng/brian/android/wha"
cd "$HERE"
ssh -o BatchMode=yes "$HOST" "mkdir -p '$DEST'"
tar --exclude-from=android/sync-exclude.txt -czf - . \
  | ssh -o BatchMode=yes "$HOST" "tar --warning=no-timestamp -xzf - -C '$DEST'"
REV=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)
echo "synced $REV to $HOST:$DEST"
