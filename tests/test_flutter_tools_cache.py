"""Shipping the flutter_tools package resolution inside the .deb.

The CI-built deb used to ship no ``packages/flutter_tools/.dart_tool/package_config.json``
(and no pub cache), so every install ran ``dart pub get`` — network included — before it
could compile the tool snapshot. The build now pre-resolves those packages with the host
Dart SDK and a PUB_CACHE placed *inside* the flutter tree, which keeps every ``file://``
URI under the packaged root: exactly the shape post_install.sh's path rewrite expects
(``s|file://.*/flutter/|file://$FLUTTER_ROOT/|g``).

These tests are hermetic: no network, no Dart SDK, no real pub get.
"""
import json
import pathlib
import subprocess
import sys
from unittest.mock import patch

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from build import Build, package_config_uris_outside_tree


def _write_package_config(path, package_uris):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "configVersion": 2,
        "packages": [
            {"name": f"pkg{i}", "rootUri": uri, "packageUri": "lib/", "languageVersion": "3.0"}
            for i, uri in enumerate(package_uris)
        ],
    }), encoding="utf-8")


def test_package_config_uris_outside_tree_flags_build_machine_paths(tmp_path):
    tree = tmp_path / "flutter"
    inside = (tree / ".pub-cache" / "hosted" / "pub.dev" / "args-2.6.0").resolve()
    outside = (tmp_path / "elsewhere" / "cached-1.0.0").resolve()
    config = tree / "packages" / "flutter_tools" / ".dart_tool" / "package_config.json"
    _write_package_config(config, [f"file://{inside}", f"file://{outside}", "https://example.com/pkg"])

    offenders = package_config_uris_outside_tree(config, tree)

    assert offenders == [f"file://{outside}"]


def test_package_config_uris_outside_tree_accepts_fully_local_tree(tmp_path):
    tree = tmp_path / "flutter"
    inside = (tree / ".pub-cache" / "hosted" / "pub.dev" / "yaml-3.1.2").resolve()
    config = tree / "packages" / "flutter_tools" / ".dart_tool" / "package_config.json"
    _write_package_config(config, [f"file://{inside}", f"file://{tree.resolve()}"])

    assert package_config_uris_outside_tree(config, tree) == []


def test_package_config_uris_outside_tree_unreadable_config_is_reported(tmp_path):
    tree = tmp_path / "flutter"
    config = tree / "packages" / "flutter_tools" / ".dart_tool" / "package_config.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text("{not json", encoding="utf-8")

    offenders = package_config_uris_outside_tree(config, tree)

    assert offenders, "an unreadable package_config.json must not be treated as shippable"


def test_packager_includes_prepared_flutter_tools_cache(tmp_path):
    """The packager must not drop .pub-cache / .dart_tool, or the optimisation is lost."""
    import package

    tree = tmp_path / "flutter"
    config = tree / "packages" / "flutter_tools" / ".dart_tool" / "package_config.json"
    config.parent.mkdir(parents=True)
    config.write_text("{}", encoding="utf-8")
    cached = tree / ".pub-cache" / "hosted" / "pub.dev" / "args-2.6.0" / "lib" / "args.dart"
    cached.parent.mkdir(parents=True)
    cached.write_text("// args\n", encoding="utf-8")

    seen = {str(p).replace("\\", "/") for p in package.explore_file(tree)}

    assert "packages/flutter_tools/.dart_tool/package_config.json" in seen
    assert any(p.startswith(".pub-cache/hosted/pub.dev/args-2.6.0/lib/args.dart") for p in seen)


def test_prepare_flutter_tools_packages_without_host_dart_is_a_noop(tmp_path):
    b = Build()
    b.root = str(tmp_path / "flutter")
    (pathlib.Path(b.root) / "packages" / "flutter_tools").mkdir(parents=True)
    (pathlib.Path(b.root) / "packages" / "flutter_tools" / "pubspec.yaml").write_text("name: flutter_tools\n")

    with patch.object(Build, "_host_dart_bin", return_value=None), \
         patch("build.subprocess.run") as mock_run:
        assert b.prepare_flutter_tools_packages() is False

    mock_run.assert_not_called()


def test_prepare_flutter_tools_packages_discards_cache_kept_outside_tree(tmp_path):
    b = Build()
    b.root = str(tmp_path / "flutter")
    tools_dir = pathlib.Path(b.root) / "packages" / "flutter_tools"
    tools_dir.mkdir(parents=True)
    (tools_dir / "pubspec.yaml").write_text("name: flutter_tools\n")
    config = tools_dir / ".dart_tool" / "package_config.json"
    outside = (tmp_path / "other" / "cached-1.0.0").resolve()

    def fake_run(cmd, cwd=None, env=None, **kwargs):
        assert env["PUB_CACHE"].startswith(b.root), "PUB_CACHE must live inside the packaged tree"
        _write_package_config(config, [f"file://{outside}"])
        return subprocess.CompletedProcess(cmd, 0)

    with patch.object(Build, "_host_dart_bin", return_value=tmp_path / "dart"), \
         patch("build.subprocess.run", side_effect=fake_run):
        assert b.prepare_flutter_tools_packages() is False

    assert not config.exists(), "a cache pointing outside the tree must not be shipped"


def test_prepare_flutter_tools_packages_accepts_in_tree_cache(tmp_path):
    b = Build()
    b.root = str(tmp_path / "flutter")
    tools_dir = pathlib.Path(b.root) / "packages" / "flutter_tools"
    tools_dir.mkdir(parents=True)
    (tools_dir / "pubspec.yaml").write_text("name: flutter_tools\n")
    config = tools_dir / ".dart_tool" / "package_config.json"
    cache_pkg = (pathlib.Path(b.root) / ".pub-cache" / "hosted" / "pub.dev" / "args-2.6.0").resolve()
    cache_pkg.mkdir(parents=True)

    def fake_run(cmd, cwd=None, env=None, **kwargs):
        _write_package_config(config, [f"file://{cache_pkg}"])
        return subprocess.CompletedProcess(cmd, 0)

    with patch.object(Build, "_host_dart_bin", return_value=tmp_path / "dart"), \
         patch("build.subprocess.run", side_effect=fake_run):
        assert b.prepare_flutter_tools_packages() is True

    assert config.exists()
