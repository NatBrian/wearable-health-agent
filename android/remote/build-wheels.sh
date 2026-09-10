#!/usr/bin/env bash
# android/remote/build-wheels.sh [package ...]
# Build Android arm64 wheels for the packages Chaquopy does not provide, at the exact
# versions uv.lock pins, with cibuildwheel. Output: /home/liangsheng/brian/android/wheels.
# Runs on the remote. Every failure is appended to wheels/FAILED.txt and never hidden.
set -uo pipefail
# shellcheck disable=SC1091
source /home/liangsheng/brian/android/env.sh
OUT=$WHA_ANDROID_BASE/wheels
WORK=$WHA_ANDROID_BASE/wheel-work
LOGS=$OUT/logs
mkdir -p "$OUT" "$WORK" "$LOGS"
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
export CIBW_BEFORE_BUILD="rustup target add aarch64-linux-android"

packages=("$@")
if [ ${#packages[@]} -eq 0 ]; then
  packages=(pydantic-core orjson ormsgpack xxhash sqlite-vec)
fi

for name in "${packages[@]}"; do
  ver=$(locked_version "$name") || { echo "FAILED: $name (not in uv.lock)" | tee -a "$OUT/FAILED.txt"; continue; }
  echo "== $name $ver"
  rm -rf "$WORK/$name" && mkdir -p "$WORK/$name"
  # The sdist straight from PyPI's JSON index. `pip download --no-binary` would build the
  # package's metadata first, which for a Rust package means compiling maturin from source.
  if ! (cd "$WORK/$name" && uv run --python 3.13 --no-project python - "$name" "$ver" > "$LOGS/$name-download.log" 2>&1 <<'PY'
import json, sys, urllib.request
name, ver = sys.argv[1], sys.argv[2]
meta = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{name}/{ver}/json"))
sdists = [u for u in meta["urls"] if u["packagetype"] == "sdist"]
if not sdists:
    sys.exit(f"no sdist on PyPI for {name}=={ver}")
url = sdists[0]["url"]
print("downloading", url)
urllib.request.urlretrieve(url, url.rsplit("/", 1)[-1])
PY
  ); then
    echo "FAILED: $name $ver (sdist download, see logs/$name-download.log)" | tee -a "$OUT/FAILED.txt"; continue
  fi
  sdist=$(ls "$WORK/$name"/*.tar.gz | head -1)
  tar -xzf "$sdist" -C "$WORK/$name"
  src=$(find "$WORK/$name" -mindepth 1 -maxdepth 1 -type d | head -1)
  # A package's own [tool.cibuildwheel] table is ignored unless WHA_KEEP_CIBW_CONFIG=1:
  # xxhash's table breaks the parse, while numpy's carries Android settings it needs.
  config_args=(--config-file "$WHA_ANDROID_BASE/wha/android/remote/cibw-override.toml")
  if [ "${WHA_KEEP_CIBW_CONFIG:-0}" = "1" ]; then config_args=(); fi
  if ( cd "$src" && nice -n 10 cibuildwheel --platform android "${config_args[@]}" --output-dir "$OUT" > "$LOGS/$name-build.log" 2>&1 ); then
    echo "built: $name $ver"
  else
    echo "FAILED: $name $ver (build, see logs/$name-build.log)" | tee -a "$OUT/FAILED.txt"
    tail -40 "$LOGS/$name-build.log"
  fi
done
ls -la "$OUT"
( cd "$OUT" && ls ./*.whl > /dev/null 2>&1 && sha256sum ./*.whl > SHA256SUMS ) || true
