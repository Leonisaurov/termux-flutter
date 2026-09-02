#!/bin/bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
DEPOT_TOOLS_DIR="${DEPOT_TOOLS_DIR:-$ROOT_DIR/depot_tools}"
export PATH="$DEPOT_TOOLS_DIR:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
cd "$ROOT_DIR/flutter/engine/src"

# Configure Android profile arm64
./flutter/tools/gn --android --android-cpu=arm64 --runtime-mode=profile --no-goma --target-toolchain=//build/toolchain/termux:arm64 --target-sysroot="$ROOT_DIR/sysroot" --target-triple=aarch64-linux-android --termux-prefix=/data/data/com.termux/files/usr

# Build gen_snapshot for profile
ninja -C out/android_profile_arm64 -j24 gen_snapshot
