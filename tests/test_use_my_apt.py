"""Tests for useMyApt — points a Flutter project's Gradle build at the Termux-native aapt2.

AGP resolves aapt2 from Maven, and that artifact is an x86_64 Linux binary that cannot execute on
Android/aarch64, so resource processing fails. Every Flutter project on Termux therefore needs

    android.aapt2FromMavenOverride=/data/data/com.termux/files/usr/bin/aapt2

in its android/gradle.properties. useMyApt adds or replaces exactly that line (and nothing else).
"""

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
USE_MY_APT = REPO_ROOT / "scripts" / "install" / "useMyApt.sh"
PACKAGE_YAML = REPO_ROOT / "package.yaml"

from conftest import to_bash_path

OVERRIDE_KEY = "android.aapt2FromMavenOverride"


def make_project(tmp_path, gradle_properties=None):
    """A minimal Flutter-shaped project: only android/ matters to useMyApt."""
    proj = tmp_path / "app"
    (proj / "android" / "app").mkdir(parents=True)
    if gradle_properties is not None:
        (proj / "android" / "gradle.properties").write_text(gradle_properties, newline="\n")
    return proj


def make_aapt2(tmp_path, name="aapt2", executable=True):
    p = tmp_path / name
    p.write_text("#!/bin/sh\nexit 0\n")
    os.chmod(p, 0o755 if executable else 0o644)
    return p


def run_use_my_apt(*args, cwd=None, env=None):
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        ["bash", to_bash_path(USE_MY_APT), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=full_env,
    )


def props_of(proj):
    return (proj / "android" / "gradle.properties").read_text()


def test_adds_override_when_missing(tmp_path):
    proj = make_project(tmp_path, "org.gradle.jvmargs=-Xmx2048m\nandroid.useAndroidX=true\n")
    aapt2 = make_aapt2(tmp_path)

    res = run_use_my_apt("--project", to_bash_path(proj), "--aapt2", to_bash_path(aapt2))

    assert res.returncode == 0, res.stderr
    assert props_of(proj) == (
        "org.gradle.jvmargs=-Xmx2048m\n"
        "android.useAndroidX=true\n"
        f"{OVERRIDE_KEY}={to_bash_path(aapt2)}\n"
    )


def test_replaces_existing_override_in_place(tmp_path):
    proj = make_project(
        tmp_path,
        "# keep me\nandroid.useAndroidX=true\n"
        f"{OVERRIDE_KEY}=/stale/other/aapt2\nandroid.enableJetifier=true\n",
    )
    aapt2 = make_aapt2(tmp_path)

    res = run_use_my_apt("--project", to_bash_path(proj), "--aapt2", to_bash_path(aapt2))

    assert res.returncode == 0, res.stderr
    assert props_of(proj) == (
        "# keep me\nandroid.useAndroidX=true\n"
        f"{OVERRIDE_KEY}={to_bash_path(aapt2)}\nandroid.enableJetifier=true\n"
    )


@pytest.mark.parametrize(
    "existing",
    [
        f"{OVERRIDE_KEY}=/stale/aapt2\n",
        f"  {OVERRIDE_KEY}=/stale/aapt2\n",
        f"{OVERRIDE_KEY} : /stale/aapt2\n",
        f"\t{OVERRIDE_KEY}=/stale/aapt2\n",
    ],
)
def test_rewrites_spaced_and_colon_variants(tmp_path, existing):
    proj = make_project(tmp_path, existing)
    aapt2 = make_aapt2(tmp_path)

    res = run_use_my_apt("--project", to_bash_path(proj), "--aapt2", to_bash_path(aapt2))

    assert res.returncode == 0, res.stderr
    assert props_of(proj) == f"{OVERRIDE_KEY}={to_bash_path(aapt2)}\n"


def test_is_idempotent(tmp_path):
    proj = make_project(tmp_path, "org.gradle.jvmargs=-Xmx2048m\n")
    aapt2 = make_aapt2(tmp_path)
    args = ("--project", to_bash_path(proj), "--aapt2", to_bash_path(aapt2))

    first = run_use_my_apt(*args)
    assert first.returncode == 0, first.stderr
    after_first = props_of(proj)

    second = run_use_my_apt(*args)
    assert second.returncode == 0, second.stderr
    assert props_of(proj) == after_first
    assert "already" in (second.stdout + second.stderr).lower()


def test_creates_gradle_properties_when_absent(tmp_path):
    proj = make_project(tmp_path, None)
    aapt2 = make_aapt2(tmp_path)

    res = run_use_my_apt("--project", to_bash_path(proj), "--aapt2", to_bash_path(aapt2))

    assert res.returncode == 0, res.stderr
    assert props_of(proj) == f"{OVERRIDE_KEY}={to_bash_path(aapt2)}\n"


def test_appends_newline_when_file_lacks_trailing_one(tmp_path):
    proj = make_project(tmp_path, "android.useAndroidX=true")
    aapt2 = make_aapt2(tmp_path)

    res = run_use_my_apt("--project", to_bash_path(proj), "--aapt2", to_bash_path(aapt2))

    assert res.returncode == 0, res.stderr
    assert props_of(proj) == (
        "android.useAndroidX=true\n" f"{OVERRIDE_KEY}={to_bash_path(aapt2)}\n"
    )


def test_defaults_to_current_directory(tmp_path):
    proj = make_project(tmp_path, "android.useAndroidX=true\n")
    aapt2 = make_aapt2(tmp_path)

    res = run_use_my_apt("--aapt2", to_bash_path(aapt2), cwd=to_bash_path(proj))

    assert res.returncode == 0, res.stderr
    assert f"{OVERRIDE_KEY}={to_bash_path(aapt2)}" in props_of(proj)


def test_rejects_non_flutter_project(tmp_path):
    not_a_project = tmp_path / "random_dir"
    not_a_project.mkdir()
    aapt2 = make_aapt2(tmp_path)

    res = run_use_my_apt("--project", to_bash_path(not_a_project), "--aapt2", to_bash_path(aapt2))

    assert res.returncode != 0
    assert "android" in (res.stdout + res.stderr)


def test_rejects_missing_aapt2_binary(tmp_path):
    proj = make_project(tmp_path, "android.useAndroidX=true\n")

    res = run_use_my_apt("--project", to_bash_path(proj), "--aapt2", to_bash_path(tmp_path / "nope"))

    assert res.returncode != 0
    assert OVERRIDE_KEY not in props_of(proj)


def test_rejects_non_executable_aapt2_binary(tmp_path):
    proj = make_project(tmp_path, "android.useAndroidX=true\n")
    aapt2 = make_aapt2(tmp_path, executable=False)

    res = run_use_my_apt("--project", to_bash_path(proj), "--aapt2", to_bash_path(aapt2))

    assert res.returncode != 0


def test_default_aapt2_comes_from_prefix(tmp_path):
    proj = make_project(tmp_path, "android.useAndroidX=true\n")
    prefix = tmp_path / "usr"
    (prefix / "bin").mkdir(parents=True)
    aapt2 = prefix / "bin" / "aapt2"
    aapt2.write_text("#!/bin/sh\nexit 0\n")
    os.chmod(aapt2, 0o755)

    res = run_use_my_apt(
        "--project", to_bash_path(proj), env={"PREFIX": to_bash_path(prefix)}
    )

    assert res.returncode == 0, res.stderr
    assert f"{OVERRIDE_KEY}={to_bash_path(aapt2)}" in props_of(proj)


def test_unknown_flag_is_rejected(tmp_path):
    proj = make_project(tmp_path, "android.useAndroidX=true\n")

    res = run_use_my_apt("--nope", "--project", to_bash_path(proj))

    assert res.returncode == 2
    assert "usage" in (res.stdout + res.stderr).lower()


def test_help_exits_zero(tmp_path):
    res = run_use_my_apt("--help")
    assert res.returncode == 0
    assert "usage" in (res.stdout + res.stderr).lower()


def test_bad_project_path_is_rejected(tmp_path):
    aapt2 = make_aapt2(tmp_path)

    res = run_use_my_apt("--project", to_bash_path(tmp_path / "missing"), "--aapt2", to_bash_path(aapt2))

    assert res.returncode != 0


def test_shipped_on_path_by_the_deb_manifest():
    """The script only helps if the deb installs it as a command, like flutter-termux."""
    text = PACKAGE_YAML.read_text()
    assert "scripts/install/useMyApt.sh" in text
    assert "$prefix/bin/useMyApt" in text
