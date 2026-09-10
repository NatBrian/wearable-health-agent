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
export UV_TOOL_DIR=$WHA_ANDROID_BASE/tools/uv-tools
export UV_TOOL_BIN_DIR=$WHA_ANDROID_BASE/tools/uv-tool-bin
export PATH=$JAVA_HOME/bin:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$CARGO_HOME/bin:$WHA_ANDROID_BASE/tools/uv:$UV_TOOL_BIN_DIR:$PATH
# Gradle must not saturate a shared box.
export GRADLE_OPTS="-Dorg.gradle.workers.max=8 -Dorg.gradle.daemon=true -Xmx6g"
