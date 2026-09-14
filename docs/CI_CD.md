# CI/CD and Device Lab

This repository uses two classes of GitHub Actions:

1. **GitHub-hosted checks** for fast, free, public-repository validation.
2. **Self-hosted workflows** for the expensive Flutter Engine build and Android tablet smoke tests.

The goal is to keep pull requests cheap and safe while still making release builds reproducible.

## GitHub Actions cost and limits

This is a public open-source repository, so standard GitHub-hosted runner
minutes are free for the lightweight `CI` and `Release check` workflows. The
manual `Build deb` and `Device smoke` workflows now also run on GitHub-hosted
runners, so a release build spends roughly a five-hour slice of those free
minutes — trigger it deliberately, not on every push.

That does **not** mean Actions are unlimited:

- GitHub still enforces workflow, queue, API, concurrency, cache, and artifact
  limits. For example, GitHub-hosted jobs have a 6-hour execution limit, and
  self-hosted jobs have a 5-day execution limit.
- Larger GitHub-hosted runners are charged even for public repositories.
- Artifacts and caches should be kept small and short-lived. Large `.deb`
  release payloads belong in GitHub Releases, not as long-retained workflow
  artifacts.
- Self-hosted runner capacity is limited by the maintainer's own WSL/Windows
  machine, disk space, tablet availability, and network.

References:

- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [GitHub Actions limits](https://docs.github.com/en/actions/reference/limits)

## Workflow map

| Workflow | File | Runner | Trigger | Purpose |
|----------|------|--------|---------|---------|
| CI | `.github/workflows/ci.yml` | `ubuntu-latest` | PR, push to `master`, manual | `pytest tests/`, Python/shell/PowerShell syntax, shellcheck + actionlint, package/docs/workflow sanity, version drift, whitespace checks |
| Build deb | `.github/workflows/build-deb.yml` | `ubuntu-latest` (choice: `ubuntu-latest`, `ubuntu-latest-4-cores`, `ubuntu-latest-8-cores`) | manual | Full `build.py build_all` pipeline (~5 h), `.deb` packaging, artifact upload |
| Device smoke | `.github/workflows/device-smoke.yml` | `ubuntu-latest` | manual | Install deb in Termux/device flow, run `post_install.sh`, `flutter doctor`, APK/Linux smoke |
| Release check | `.github/workflows/release-check.yml` | `ubuntu-latest` | release publish/edit, manual | Verify release asset name, size, and SHA256 digest |

## Why the split exists

Public repositories can use standard GitHub-hosted runners for free, but this project's full build is not a normal CI job:

- `gclient sync` downloads tens of GB.
- Flutter Engine builds take hours (~5 h even with warm caches).
- Real release confidence requires installing the `.deb` in a real Termux.
- The engine build needs an Android NDK (r27d) plus the Termux sysroot assembled
  from apt packages.

Therefore:

- **PR CI must stay lightweight** (~2-3 min) and never build the engine.
- **Full build and device verification are manual gates** triggered by a maintainer.
- **Release publishing is manual**, not automatic on every merge to `master`.

## PR / push CI

`ci.yml` runs on every PR and push to `master`:

```text
pytest tests/
python -m py_compile build.py package.py sysroot.py utils.py scripts/ci/check_repo.py
bash -n install_flutter_complete.sh scripts/install/*.sh scripts/test/gh_e2e_test.sh scripts/device/termux_smoke.sh
ShellCheck --severity=error on the shell entrypoints, actionlint on .github/workflows/*.yml
PowerShell parser check for scripts/device/run_termux_smoke.ps1
build.toml schema check
python scripts/ci/check_repo.py
python scripts/ci/check_version_drift.py
git diff --check
```

`pytest tests/` is the only behavioural gate — the shell/lint steps above it cannot
catch a broken pipeline, so never leave it red.

`check_repo.py` validates repo-specific contracts, including:

- workflow YAML parses
- self-hosted workflows are not triggered by `pull_request`
- `package.yaml` still packages `dart`, `dartvm`, `dartaotruntime`, and `post_install`
- `post_install.sh` still contains the Flutter 3.44 `PLATFORM_ABI_LIST` and Android-host patches
- installer defaults remain on Flutter 3.47.2 and NDK r29 for Termux installs
- release/download docs do not regress to stale 3.41.5 commands

## Full deb build

Manual workflow: **Build deb** (`.github/workflows/build-deb.yml`, `ubuntu-latest` by default)

Inputs:

```text
flutter_version: (optional) must match the build.toml tag or the job fails early
arch: arm64
force: false            # force a full rebuild, ignoring cached engine artifacts
runner: ubuntu-latest   # or ubuntu-latest-4-cores / ubuntu-latest-8-cores
```

Steps: checkout → free disk space → Python 3.12 + `requirements.txt` → system dependencies →
cache `depot_tools`, engine source, sysroot and build artifacts → `python build.py build_all --arch=<arch>`
(~5 h; 4h57m measured for a cached 3.47.2 run) → collect metadata → upload artifact.

The artifact is `flutter-termux-<tag>-<arch>` and contains:

- `flutter_<tag>_aarch64.deb`
- `flutter_<tag>_aarch64.deb.sha256` and `flutter_<tag>_aarch64.deb.size.txt`
- `build_metadata.json` (version, arch, run id, source commit, tree sha, sha256, size, duration)
- `build_evidence.json` (same, plus `inventory_file_count`)
- `inventory.txt` (`dpkg-deb -c` listing of everything packaged)

On failure it also uploads `flutter-termux-<tag>-<arch>-build-log` with the raw `build.log`.

Two mechanisms inside `build_all()` keep this pipeline alive; both were added after real failures:

1. **Sysroot self-healing.** `sysroot.lock.json` pins exact Termux `.deb` URLs + sha256, but the
   Termux pool is rolling and purges old versions, so pinned downloads start returning 404
   (observed: `mesa_26.0.6-2_aarch64.deb`). `Sysroot.build()` then re-resolves the current versions
   from the repository index, retries the download, and rewrites the lock with a fresh `tree_hash`
   instead of killing the release build. `refresh_lock=False` restores strict lock semantics, and a
   deliberate committed-lock refresh is `python3 build.py sysroot_lock --arch=arm64`.
2. **flutter_tools package pre-resolution.** `prepare_flutter_tools_packages()` runs `dart pub get`
   with the host (linux-x64) Dart SDK that `sync()` installs, using `PUB_CACHE=<flutter_root>/.pub-cache`
   so every `file://` URI stays inside the packaged tree — exactly what `post_install.sh`'s path
   rewrite expects. If any URI escapes the tree the generated cache is discarded and installs fall
   back to on-device `pub get`.

Cache notes: every `actions/cache` key includes `${{ github.sha }}`, so a new commit misses the
exact key and restores the previous cache through `restore-keys`. A stale sysroot cache is therefore
normal, and it is what triggers the verify/rebuild path (and the 404 that the self-heal above absorbs).

## Release policy

Merging to `master` does **not** publish a GitHub Release. The current release
flow is intentionally maintainer-triggered:

1. Merge only after PR CI passes.
2. Trigger **Build deb** manually on the chosen commit and wait for artifact
   `flutter-termux-<tag>-<arch>`.
3. Verify the artifact first: sha256 against `.sha256` / `build_metadata.json`,
   then the extract-and-run smoke test documented in `AGENTS.md`.
4. Run **Device smoke** with the build's `artifact_run_id`, `artifact_name` and
   `expected_sha256`: it re-verifies the digest, inspects the `.deb`, does a
   dry-run installability check, and — only with `promote_release=true` plus a
   `release_tag` — creates/updates the GitHub Release for that tag.
5. Let **Release check** verify the release asset metadata after publish/edit.

This avoids accidental multi-hour engine builds and prevents unreviewed merges
from overwriting a public release asset. A future release pipeline may chain
build → device smoke → publish, but the current project keeps publish as an
explicit maintainer action.

## Device smoke

Manual workflow: **Device smoke** (`.github/workflows/device-smoke.yml`,
`ubuntu-latest`, 30-minute timeout)

Inputs:

```text
artifact_run_id: run id of the Build deb run that produced the deb
artifact_name:   e.g. flutter-termux-3.47.2-arm64
expected_sha256: must match the downloaded .deb
promote_release: false            # true publishes a GitHub Release
release_tag:     v3.47.2-termux   # required when promote_release=true
timeout_minutes: 30
```

The job downloads the artifact, verifies the SHA256, inspects the `.deb`
contents, performs a dry-run installability check, generates smoke evidence and
only then optionally promotes the release.

An actual on-device Termux run is still a manual step (the historical
self-hosted Windows + ADB + `scripts/device/termux_smoke.sh` flow, kept in the
repo for that purpose). Its required markers are:

```text
INSTALL_STATUS=0
POST_INSTALL_STATUS=0
FLUTTER_VERSION_STATUS=0
DART_VERSION_STATUS=0
DARTVM_VERSION_STATUS=0
DOCTOR_STATUS=0
CREATE_STATUS=0
BUILD_APK_STATUS=0
APK_MANIFEST_STATUS=0
APK_RESOURCES_STATUS=0
APK_COPY_STATUS=0
BUILD_LINUX_STATUS=0
DONE
```

## Release check

`release-check.yml` verifies release metadata from GitHub:

- expected tag exists
- expected asset exists
- asset size is plausible
- asset digest matches the expected SHA256 when GitHub exposes the digest

This workflow is safe to run on GitHub-hosted runners because it only reads public release metadata.

## Security model

- Fork PRs only get `ci.yml` on GitHub-hosted runners.
- `Build deb` and `Device smoke` are `workflow_dispatch` only, so no untrusted PR can start a
  five-hour build or touch a release.
- `Device smoke` never runs PR code; it only verifies a maintainer-selected artifact.
- Release publishing requires `contents: write` and happens only from the manual `Device smoke`
  run with `promote_release=true` plus an explicit `release_tag`.

## Branch Protection and Repository Governance

The repository governance rules for the `master` branch are codified in `.github/rulesets/master_protection_ruleset.json`:

- **Pull Request Requirements**: Mandatory PR review and thread resolution before merge.
- **Status Checks**: Strict status checks require `ci.yml` (Python/Shell/Actionlint sanity, contract validation, version drift checks) to pass cleanly before merging.
- **History & Integrity**: Linear git history is enforced; force pushes (`non_fast_forward`) and branch deletion are blocked.
- **Repository Hygiene**: Automated pre-merge checks prevent scratch artifacts, test caches, backups, and stage receipts from leaking into git tracking.

## Local equivalents

Fast local checks:

```bash
pytest tests/
python -m py_compile build.py package.py sysroot.py utils.py scripts/ci/check_repo.py scripts/ci/check_version_drift.py
bash -n install_flutter_complete.sh scripts/install/*.sh scripts/test/gh_e2e_test.sh scripts/device/termux_smoke.sh
python scripts/ci/check_repo.py
python scripts/ci/check_version_drift.py
git diff --check
```

Manual Termux release E2E test inside Termux:

```bash
bash scripts/test/gh_e2e_test.sh
```

Manual Windows-to-tablet smoke:

```powershell
scripts/device/run_termux_smoke.ps1 `
  -AdbPath "C:\Users\aa223\AppData\Local\Android\Sdk\platform-tools\adb.exe" `
  -DebUrl "https://github.com/ImL1s/termux-flutter-wsl/releases/download/v3.47.2-termux/flutter_3.47.2_aarch64.deb"
```
