# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## What This Is

Cross-compile Flutter SDK for Termux (Android/Bionic ARM64). Produces a `.deb` package installable on Termux that enables `flutter run`, `flutter build apk`, and `flutter build linux`.

## Current Version

- Flutter: **3.47.2** (stable)
- Dart: **3.13.2**
- Target: aarch64 (ARM64)
- Patches directory: `patches/3.47.2/`

## Build Commands

```bash
# Full build (~2-4 hours on 24-thread machine)
python3 build.py build_all --arch=arm64

# Individual steps
python3 build.py clone                                    # Clone Flutter 3.47.2
python3 build.py sync                                     # gclient sync (~30GB)
python3 build.py patch_engine && python3 build.py patch_dart && python3 build.py patch_skia
python3 build.py sysroot --arch=arm64                     # Assemble Termux sysroot from apt
python3 build.py configure --arch=arm64 --mode=debug      # GN configure
python3 build.py build --arch=arm64 --mode=debug          # ninja build
python3 build.py build_dart --arch=arm64 --mode=debug     # dart binary (separate!)
python3 build.py build_impellerc --arch=arm64 --mode=debug
python3 build.py build_const_finder --arch=arm64 --mode=debug
python3 build.py configure --arch=arm64 --mode=release    # Linux release engine
python3 build.py build --arch=arm64 --mode=release
python3 build.py configure --arch=arm64 --mode=profile    # Linux profile engine
python3 build.py build --arch=arm64 --mode=profile
python3 build.py configure_android --arch=arm64 --mode=release
python3 build.py build_android_gen_snapshot --arch=arm64 --mode=release
python3 build.py debuild --arch=arm64                     # Package .deb
```

## Lightweight Verification

```bash
python -m py_compile build.py package.py sysroot.py utils.py scripts/ci/check_repo.py
bash -n scripts/install/post_install.sh scripts/test/gh_e2e_test.sh scripts/device/termux_smoke.sh
python scripts/ci/check_repo.py
git diff --check
```

## Critical Implementation Details

1. **`ninja flutter` does NOT build `dart` binary**. Must run `build_dart()` separately.
2. **Only ARM64 APK gen_snapshot works**. 32-bit ARM fails (BoringSSL), x64 fails (sysroot mismatch).
3. **Linux target builds all three modes** (debug, release, profile). `build_all()` runs configure+build for each mode.
4. **GN flag `is_termux=true`** activates custom BUILD.gn rules that add `-llog -lm` for Android logging symbols.
5. **`utils.py __MODE__` must be `('debug', 'release', 'profile')`** — debug first!

## Termux Runtime: post_install.sh Auto-Fixes

`post_install.sh` automatically handles these ARM64 compatibility issues:
- **compileSdkVersion 36→34**: Termux aapt2 (v2.19) cannot load android-35/36 `android.jar`
- **NDK clang wrappers**: Replaces x86_64 clang/clang++ with Termux ARM64 native wrappers
- **Shebang fix**: All generated wrapper scripts use `#!/data/data/com.termux/files/usr/bin/sh`

## Termux Runtime: Per-Project Configuration

Each Flutter project needs in `android/gradle.properties`:
```properties
android.aapt2FromMavenOverride=/data/data/com.termux/files/usr/bin/aapt2
```

And in `android/app/build.gradle.kts`:
```kotlin
android {
    compileSdk = 34  // Must use API 34 (Termux aapt2 limitation)
    defaultConfig {
        targetSdk = 34
        ndk { abiFilters += listOf("arm64-v8a") }
    }
}
```

## Environment

- Build: WSL2 Ubuntu on Windows, NDK r27d at `/opt/android-ndk-r27d`
- WSL path: `<workspace-root>/`
- Target: aarch64, Flutter 3.47.2
- Test device: Samsung SM-X716B / Android 16
- Use PowerShell (not Git Bash) for `adb push` to avoid path mangling

## Upgrade Notes (3.44.9 → 3.47.2)

- Dart SDK: 3.12.2 → 3.13.2 (breaking changes possible)
- Engine commit changed: must verify patches apply cleanly
- New patches directory: `patches/3.47.2/`
- Run `python3 build.py clone --force` to re-clone with new tag
