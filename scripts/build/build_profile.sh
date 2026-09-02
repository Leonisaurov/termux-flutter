#!/bin/bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${DEPOT_TOOLS_DIR:-$ROOT_DIR/depot_tools}"
cd "$ROOT_DIR/flutter/engine/src/out/linux_profile_arm64"
exec ninja flutter flutter/shell/platform/linux:flutter_gtk -j24
