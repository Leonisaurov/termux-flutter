#!/bin/bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
DEPOT_TOOLS_DIR="${DEPOT_TOOLS_DIR:-$ROOT_DIR/depot_tools}"
export PATH="$DEPOT_TOOLS_DIR:/usr/local/bin:/usr/bin:/bin"
cd "$ROOT_DIR/flutter/engine/src/out/android_release_arm64"
ninja flutter/third_party/dart/runtime/bin:gen_snapshot
