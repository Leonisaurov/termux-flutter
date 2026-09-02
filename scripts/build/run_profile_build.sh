#!/bin/bash
set -e
# Clean PATH
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
DEPOT_TOOLS_DIR="${DEPOT_TOOLS_DIR:-$ROOT_DIR/depot_tools}"
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$DEPOT_TOOLS_DIR"

cd "$ROOT_DIR/flutter/engine/src"
exec ninja -C out/android_profile_arm64 -j24 gen_snapshot
