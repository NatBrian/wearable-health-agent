#!/usr/bin/env bash
# android/remote/install-toolchain.sh
# Run ONCE on the remote: bash install-toolchain.sh. Idempotent: skips what exists.
# Everything lands under /home/liangsheng/brian/android/tools. No sudo, nothing outside it.
set -euo pipefail
BASE=/home/liangsheng/brian/android
T=$BASE/tools
mkdir -p "$T"
cp "$BASE/wha/android/remote/env.sh" "$BASE/env.sh"
# shellcheck disable=SC1090
source "$BASE/env.sh"

# JDK 17 (Temurin, Linux x64)
if [ ! -x "$T/jdk/bin/java" ]; then
  echo "== installing JDK 17"
  curl -fsSL -o /tmp/wha-jdk.tgz "https://api.adoptium.net/v3/binary/latest/17/ga/linux/x64/jdk/hotspot/normal/eclipse"
  mkdir -p "$T/jdk" && tar -xzf /tmp/wha-jdk.tgz -C "$T/jdk" --strip-components=1 && rm /tmp/wha-jdk.tgz
fi
java -version

# Android command-line tools, one platform, one build-tools, one NDK
if [ ! -x "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" ]; then
  echo "== installing Android command-line tools"
  mkdir -p "$ANDROID_HOME/cmdline-tools"
  curl -fsSL -o /tmp/wha-clt.zip "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
  rm -rf /tmp/wha-clt && unzip -q /tmp/wha-clt.zip -d /tmp/wha-clt && rm /tmp/wha-clt.zip
  mv /tmp/wha-clt/cmdline-tools "$ANDROID_HOME/cmdline-tools/latest"
fi
yes | sdkmanager --licenses > /dev/null 2>&1 || true
sdkmanager "platform-tools" "platforms;android-35" "build-tools;35.0.0" "ndk;27.2.12479018"

# Rust with the Android target, in our own homes
if [ ! -x "$CARGO_HOME/bin/rustup" ]; then
  echo "== installing rustup"
  curl -fsSL https://sh.rustup.rs | sh -s -- -y --no-modify-path --profile minimal
fi
rustup target add aarch64-linux-android

# uv and a Python 3.13 for cibuildwheel and for building pure wheels
if [ ! -x "$T/uv/uv" ]; then
  echo "== installing uv"
  mkdir -p "$T/uv"
  curl -fsSL https://astral.sh/uv/install.sh | UV_INSTALL_DIR="$T/uv" UV_NO_MODIFY_PATH=1 sh
fi
uv python install 3.13
uv tool install --python 3.13 "cibuildwheel>=3.2,<4"
echo "toolchain ready"
