#!/usr/bin/env bash
# android/remote/run.sh '<command>'
# Run one command on the shared build machine inside the working copy with the toolchain
# on PATH. Always nice, because other people are using that machine.
set -euo pipefail
HOST="${WHA_REMOTE_HOST:-huawei_blue_1_ppt}"
BASE="/home/liangsheng/brian/android"
ssh -o BatchMode=yes "$HOST" "source '$BASE/env.sh' && cd '$BASE/wha' && nice -n 10 bash -lc $(printf '%q' "$*")"
