# Flutter 3.47.2 for Termux ARM64

**Flutter 3.47.2 / Dart 3.13.2 for Android-bionic ARM64 hosts.**

This release updates the Termux Flutter SDK package to Flutter 3.47.2. It incorporates all post-v3.44.2 installer hardening, dynamic JAVA_HOME auto-detection, robust PREFIX quoting under `set -euo pipefail`, and refreshed Termux toolchain sysroot packages.

## Package

| Item | Value |
|------|-------|
| Package | `flutter_3.47.2_aarch64.deb` |
| Size | Pending first 3.47.2 build |
| SHA256 | Published with the `.deb.sha256` companion asset |
| Flutter | 3.47.2 |
| Flutter Tools Dart | 3.13.2 |
| Dart VM | post-install `dartvm` resolves to Dart 3.13.2 (`android_arm64`) |
| Target host | Termux / Android bionic / ARM64 |

## Install

```bash
pkg update -y
pkg install -y x11-repo wget openjdk-21 openjdk-17
wget https://github.com/ImL1s/termux-flutter-wsl/releases/download/v3.47.2-termux/flutter_3.47.2_aarch64.deb
dpkg -i flutter_3.47.2_aarch64.deb
apt --fix-broken install -y
bash $PREFIX/share/flutter/post_install.sh
source $PREFIX/etc/profile.d/flutter.sh
flutter doctor -v
```

## Validation status

The 3.47.2 source and patch contracts are updated. The first `.deb` build and
Samsung SM-X716B / Android 16 device smoke are pending publication/ execution.

| Command | Result |
|---------|--------|
| `flutter --version` | Pending first package build |
| `dart --version` | Pending first package build |
| `dartvm --version` | Pending first package build |
| `flutter doctor -v` | Pending device smoke |
| `flutter create --platforms=android,linux` | Pending device smoke |
| `flutter build apk --release --target-platform android-arm64 --no-tree-shake-icons` | Pending device smoke |
| `flutter build linux --release` | Pending device smoke |
| deb artifact validator | Pending first package build |

## Highlights

### Flutter 3.47.2 update

- Updated package metadata, NDK configurations, and patches to target Flutter 3.47.2 (Dart 3.13.2).
- Keeps Flutter CLI on Termux JIT Dart while preserving engine VM tools for snapshots.

### Installer & Environment Hardening

- Fully guarded `$PREFIX` paths against whitespace and `set -u` unbound variable errors.
- Dynamic `JAVA_HOME` discovery across Termux OpenJDK installations.
- Automated dependency resolution including OpenJDK 21 and 17.

### Post-install Dart VM detection fix

- Fixed the `post_install.sh` system Dart VM replacement logic to directly inspect the target path (`/data/data/com.termux/files/usr/bin/dart`) rather than using `command -v`, preventing path shadowing issues.

### Technical Details

- Build output directories: `linux_debug_arm64/`, `linux_release_arm64/`, `linux_profile_arm64/`, `android_release_arm64/`, `android_profile_arm64/`
- Deb package size will be recorded after the first reproducible build.

## Required per-project Android settings

To build APKs successfully on Termux, you must configure the following project properties:

```properties
# android/gradle.properties
android.aapt2FromMavenOverride=/data/data/com.termux/files/usr/bin/aapt2
android.enableResourceOptimizations=false
```

```kotlin
// android/app/build.gradle.kts
android {
    compileSdk = 34
    defaultConfig {
        targetSdk = 34
        ndk { abiFilters += listOf("arm64-v8a") }
    }
    buildTypes {
        release {
            isMinifyEnabled = false
            isShrinkResources = false
        }
    }
}
```

Build with:

```bash
flutter build apk --release --target-platform android-arm64 --no-tree-shake-icons
```

## Known limitations

- Android APK targets are ARM64-only (`android-arm64` / `arm64-v8a`).
- `flutter run` for Android requires ADB pairing/connection from inside Termux.
- Some Flutter doctor warnings about unknown channel/source are expected for this repackaged SDK.
- Termux aapt2 currently requires projects to compile against API 34 even though Android SDK Platform 36 is installed for Flutter metadata compatibility.

## Previous releases

### v3.41.5 (2026-04-13)

- Flutter SDK upgraded to 3.41.5 (Dart 3.11.3).
- Added `flutter build linux` support.
- Fixed post-install sed delimiter and flutter_tools snapshot invalidation.

### v3.35.0 (2026-01-07)

- First public release.
- APK build and hot reload support for ARM64 Termux.
