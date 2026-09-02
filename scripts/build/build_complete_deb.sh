#!/bin/bash
#
# Complete Flutter deb build script
# Builds everything needed including Android gen_snapshot for APK building
#
# Usage: ./build_complete_deb.sh
#
# Prerequisites:
# - WSL Ubuntu with build dependencies installed
# - depot_tools in PATH
# - Engine source synced (gclient sync completed)
#

set -e

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"
export PATH="${DEPOT_TOOLS_DIR:-$ROOT_DIR/depot_tools}:$PATH"

echo "=========================================="
echo " Flutter deb Complete Build Script"
echo " Includes Android gen_snapshot for APK"
echo "=========================================="
echo ""

ARCH="arm64"
VERSION="3.47.2"

# Step 1: Build Linux debug
echo "[1/6] Building linux_debug_arm64..."
python3 build.py configure --arch=$ARCH --mode=debug
python3 build.py build --arch=$ARCH --mode=debug
echo "✓ linux_debug_arm64 complete"

# Step 2: Build Linux release
echo ""
echo "[2/6] Building linux_release_arm64..."
python3 build.py configure --arch=$ARCH --mode=release
python3 build.py build --arch=$ARCH --mode=release
echo "✓ linux_release_arm64 complete"

# Step 3: Build Linux profile
echo ""
echo "[3/6] Building linux_profile_arm64..."
python3 build.py configure --arch=$ARCH --mode=profile
python3 build.py build --arch=$ARCH --mode=profile
echo "✓ linux_profile_arm64 complete"

# Step 4: Build Android release gen_snapshot (for flutter build apk)
echo ""
echo "[4/7] Building Android gen_snapshot..."
python3 build.py configure_android --arch=$ARCH --mode=release
python3 build.py build_android_gen_snapshot --arch=$ARCH --mode=release
echo "✓ android_release_arm64 gen_snapshot complete"

# Step 5: Build Android profile gen_snapshot (for flutter build apk --profile)
echo ""
echo "[5/7] Building Android profile gen_snapshot..."
python3 build.py configure_android --arch=$ARCH --mode=profile
python3 build.py build_android_gen_snapshot --arch=$ARCH --mode=profile
echo "✓ android_profile_arm64 gen_snapshot complete"

# Step 6: Verify all builds
echo ""
echo "[6/7] Verifying builds..."
ls -la flutter/engine/src/out/linux_debug_arm64/gen_snapshot
ls -la flutter/engine/src/out/linux_release_arm64/gen_snapshot
ls -la flutter/engine/src/out/linux_profile_arm64/gen_snapshot
ls -la flutter/engine/src/out/android_release_arm64/clang_arm64/gen_snapshot
ls -la flutter/engine/src/out/android_profile_arm64/clang_arm64/gen_snapshot
echo "✓ All builds verified"

# Step 7: Package deb
echo ""
echo "[7/7] Packaging deb..."
mkdir -p release
python3 build.py debuild --arch=$ARCH
echo "✓ deb package complete"

# Show result
echo ""
echo "=========================================="
echo " Build Complete!"
echo "=========================================="
ls -la release/*.deb

echo ""
echo "Next steps:"
echo "1. Upload to GitHub Release"
echo "2. Test installation on Termux"
