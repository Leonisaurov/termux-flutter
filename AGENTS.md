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

## Setup & Test

```bash
# Python deps (required for build.py, sysroot.py, package.py)
pip install -r requirements.txt

# Unit tests (fast, no engine build)
pytest tests/

# Lightweight verification (CI runs these on every PR)
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
6. **Dart 3.10+ requires `dartvm` binary** next to `dart`. The package.yaml maps `exe.unstripped/dartvm` from debug build output. If missing, Flutter commands fail with "dartvm not found".
7. **Patches are version-specific**. `patches/{tag}/` must match `build.toml` tag exactly. Copying patches from a prior version is a starting point — they often need rebasing for engine/Dart API changes.

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
Run `useMyApt` inside the project (or `useMyApt --project <dir>`) to add or replace that line; the deb
installs it at `$prefix/bin/useMyApt` (`scripts/install/useMyApt.sh`). `scripts/install/flutter_project_config.sh`
does the same plus the build.gradle tweaks below, with Mode A/B selection and rollback.

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
- Release CI: GitHub-hosted `ubuntu-latest` (see `.github/workflows/build-deb.yml`, `runner` input)
- WSL path: `<workspace-root>/`
- Target: aarch64, Flutter 3.47.2
- Test device: Samsung SM-X716B / Android 16
- Use PowerShell (not Git Bash) for `adb push` to avoid path mangling

## CI, Release Pipeline & Install-Time Invariants

- **CI** (`.github/workflows/ci.yml`, `ubuntu-latest`, every PR/push to `master`, ~2-3 min):
  `pytest tests/` plus `py_compile`, `bash -n`, shellcheck, actionlint, `check_repo.py`,
  `check_version_drift.py` and `git diff --check`. It is the only automated gate — keep it green.
- **Build deb** (`.github/workflows/build-deb.yml`, manual `workflow_dispatch`, ~5 h):
  inputs `flutter_version` (must match `build.toml`), `arch` (arm64), `force`, `runner`.
  Runs `build.py build_all`, then uploads artifact `flutter-termux-<tag>-<arch>` containing the
  `.deb`, `.deb.sha256`, `.deb.size.txt`, `build_metadata.json`, `build_evidence.json` and
  `inventory.txt`. Cache keys include `github.sha`, so a new commit restores the previous cache
  through `restore-keys` (a stale cache is why the sysroot gets verified/rebuilt at all).

Invariants that have already broken the pipeline once — keep them intact:

1. **`sysroot.lock.json` pins exact Termux `.deb` URLs + sha256, and Termux is a rolling repo.**
   Old versions are purged from the pool, so pinned URLs start returning 404 mid-build.
   `Sysroot.build(..., refresh_lock=True)` (default) re-resolves the current versions from the
   repository index, retries the download and rewrites the lock with a fresh `tree_hash`;
   `refresh_lock=False` keeps strict lock semantics, and if the index itself is unreachable the
   original download error is re-raised (never mask the root cause).
   `build.py sysroot(...)` forwards the same flag.
   Refresh the committed lock deliberately with `python3 build.py sysroot_lock --arch=arm64`
   (it downloads every package to recompute `tree_hash` — ~87 MB for arm64).
2. **Every `file://` URI in `packages/flutter_tools/.dart_tool/package_config.json` must stay inside
   the flutter tree.** `build_all()` pre-resolves those packages with the host Dart SDK that `sync()`
   installs, using `PUB_CACHE=<flutter_root>/.pub-cache`, so a device install needs no `pub get`.
   `prepare_flutter_tools_packages()` validates the invariant and discards the generated cache when
   any URI escapes the tree (the install then falls back to `pub get` on device).
3. **`bin/cache/flutter_tools.stamp` must carry the launcher's compile key.**
   `bin/internal/shared.sh` compares `"$(git -C "$FLUTTER_ROOT" rev-parse HEAD):$FLUTTER_TOOL_ARGS"`,
   so `post_install.sh` must write the checkout revision — writing the engine version instead makes
   the first `flutter` run throw the snapshot away and rebuild the tool.
4. **`post_install.sh` derives `TMPDIR` from `PREFIX`.** A hardcoded `/data/data/com.termux/...`
   default makes any run with an overridden `PREFIX` (CI runners, tests) try to `mkdir /data` and
   fail closed.
5. **The `forceNdkDownload()` early return must stay a runtime condition.** Termux ships the NDK, so
   `patch_plugin_utils` returns before Flutter's synthetic NDK/CMake provisioning. Written as a bare
   `return` it makes the rest of the function unreachable, and Kotlin then refuses the smart cast on
   `androidComponents` — `FlutterPluginUtils.kt:817: "only safe (?.) or non-null asserted (!!.) calls
   are allowed on a nullable receiver of type 'AndroidComponentsExtension<*, *, *>?'"` — which fails
   `:gradle:compileKotlin` and every `flutter build apk` with `BUILD FAILED`. Keep
   `if (System.getenv("TERMUX_NDK_PROVISIONING") == null) return` (proven against the real compiler:
   bare form reproduces the error, guarded form compiles).
6. **`patch_state.json` records a `func_digest` per patch.** `apply_patches` skips a patch only when
   the file hash *and* the digest of the current implementation both match, so editing a patch
   function re-evaluates it on existing installs (via a scratch-copy comparison) instead of trusting
   a postimage written by an older implementation. Without it, a patch fix never reaches anyone who
   already installed the deb.

## Verifying a released .deb (no install required)

```bash
gh run download <run_id> -n flutter-termux-<tag>-arm64 -D /tmp/art
sha256sum flutter_3.47.2_aarch64.deb        # must equal .sha256 and build_metadata.json:sha256
stat -c%s flutter_3.47.2_aarch64.deb        # must equal .size.txt
dpkg-deb -I flutter_3.47.2_aarch64.deb      # Package: flutter / Version / Architecture: aarch64
dpkg-deb -x flutter_3.47.2_aarch64.deb /tmp/debroot        # foreground: backgrounded extracts get killed
/tmp/debroot/data/data/com.termux/files/usr/opt/flutter/bin/cache/dart-sdk/bin/dart --version
```

- Expect `Dart SDK version: 3.13.2 ... on "linux_arm64"`, and `... on "android_arm64"` from
  `bin/cache/artifacts/engine/android-arm64-release/linux-arm64/gen_snapshot --version`.
- Use `dartvm <script>.dart` to prove the VM executes code; `dart run` needs a writable `$HOME`.
- Not shipped on purpose: `bin/cache/flutter_tools.snapshot` (compiled on device by
  `post_install.sh`) and the Android SDK (~430 MB, fetched at install time).
- Install flow on a pacman-based Termux: `dpkg -i --force-depends <deb>` (dpkg's database does not
  see pacman packages, so `Depends` look unsatisfied), then `bash $PREFIX/share/flutter/post_install.sh`.
  Budget ~6 min, ~5 of them for the tool snapshot; a valid stamp means the first `flutter` run does
  **not** print `Building flutter tool...`.

## Upgrade Notes (3.44.9 → 3.47.2)

- Dart SDK: 3.12.2 → 3.13.2 (breaking changes possible)
- Engine commit changed: must verify patches apply cleanly
- New patches directory: `patches/3.47.2/`
- Run `python3 build.py clone --force` to re-clone with new tag
