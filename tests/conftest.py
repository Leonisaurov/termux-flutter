"""Pytest fixtures and cross-platform test helpers for Flutter Termux SDK."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Union

# Ensure repository root and tests directory are in sys.path
TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

_IS_WSL_BASH = None


def is_wsl_bash() -> bool:
    """Dynamically detect if 'bash' command executes WSL bash or MSYS2/Git-Bash."""
    global _IS_WSL_BASH
    if _IS_WSL_BASH is not None:
        return _IS_WSL_BASH
    if sys.platform != "win32":
        _IS_WSL_BASH = False
        return False
    try:
        res = subprocess.run(["bash", "-c", "echo $WSL_DISTRO_NAME"], capture_output=True, text=True, timeout=3)
        if res.stdout.strip():
            _IS_WSL_BASH = True
            return True
        res2 = subprocess.run(["bash", "-c", "uname -r"], capture_output=True, text=True, timeout=3)
        _IS_WSL_BASH = "microsoft" in res2.stdout.lower() or "wsl" in res2.stdout.lower()
    except Exception:
        _IS_WSL_BASH = False
    return _IS_WSL_BASH


def to_bash_path(path: Union[str, Path]) -> str:
    """Convert a file path to the appropriate POSIX path format for the detected bash environment.

    - On Windows with WSL bash: C:\\foo\\bar -> /mnt/c/foo/bar
    - On Windows with Git-Bash/MSYS2: C:\\foo\\bar -> /c/foo/bar
    - On Linux/macOS: /foo/bar -> /foo/bar
    """
    p = Path(path).resolve()
    if sys.platform == "win32":
        if p.drive:
            drive = p.drive[0].lower()
            rel = p.as_posix()[len(p.drive):]  # strip 'C:' or 'D:'
            if is_wsl_bash():
                return f"/mnt/{drive}{rel}"
            else:
                return f"/{drive}{rel}"
        return p.as_posix()
    return p.as_posix()


to_wsl_posix = to_bash_path
to_bash_posix = to_bash_path


# chrome.dart needs more than a one-line stub: post_install's patch_chrome anchors on the
# kLinuxExecutable declaration, on the `return kLinuxExecutable;` it replaces, and on the two doc
# comments it inserts before. A stub without them is unpatchable and post_install must abort on it,
# so every mock environment builds this fixture instead.
CHROME_FIXTURE = (
    "const kLinuxExecutable = 'google-chrome';\n"
    "\n"
    "String findChromeExecutable(Platform platform, FileSystem fileSystem) {\n"
    "  if (platform.isLinux) {\n"
    "    return kLinuxExecutable;\n"
    "  }\n"
    "  throwToolExit('Platform ${platform.operatingSystem} is not supported.');\n"
    "}\n"
    "\n"
    "/// The expected executable name on macOS.\n"
    "const kMacOSExecutable = '/Applications/Google Chrome.app';\n"
    "\n"
    "/// Find the Microsoft Edge executable on the current platform.\n"
    "String findEdgeExecutable(Platform platform, FileSystem fileSystem) {\n"
    "  return '';\n"
    "}\n"
)

# The state an install already on the released deb carries: the previous patch_chrome only added
# the Android lookup, never the candidate list that makes `chromium-browser` discoverable.
CHROME_LEGACY_PREIMAGE = CHROME_FIXTURE.replace(
    "  if (platform.isLinux) {",
    "  if (platform.isLinux || platform.isAndroid) { // Termux: use Linux Chrome lookup on Android host.",
)

# Marker that proves patch_chrome upgraded a file to the current postimage.
CHROME_CANDIDATES_MARKER = "kLinuxExecutableCandidates"
