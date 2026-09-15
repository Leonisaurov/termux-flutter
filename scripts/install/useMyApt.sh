#!/bin/bash
# useMyApt — point a Flutter project's Gradle build at the Termux-native aapt2.
#
# Why this exists: AGP resolves its aapt2 from Maven, and that artifact is an x86_64 Linux binary
# that cannot execute on Android/aarch64, so the build dies during resource processing. Every Flutter
# project on Termux therefore needs
#
#     android.aapt2FromMavenOverride=/data/data/com.termux/files/usr/bin/aapt2
#
# in its android/gradle.properties. useMyApt adds that line, or replaces an existing (stale) one,
# and touches nothing else in the file. Running it twice is a no-op.
#
# Usage:
#   cd my_flutter_app && useMyApt
#   useMyApt --project ~/path/to/app
#   useMyApt --aapt2 /path/to/aapt2 --project ~/path/to/app

set -e

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
DEFAULT_AAPT2="$PREFIX/bin/aapt2"
OVERRIDE_KEY="android.aapt2FromMavenOverride"

usage() {
    cat <<EOF
Usage: useMyApt [options]

Writes $OVERRIDE_KEY=<aapt2> into a Flutter project's android/gradle.properties.
Required on Termux/Android aarch64 because AGP's own aapt2 is an x86_64 binary.

Options:
  --project DIR   Flutter project root (default: current directory; must contain android/)
  --aapt2 PATH    aapt2 binary to use (default: $DEFAULT_AAPT2)
  -h, --help      Show this help

Exit codes: 0 ok · 1 bad project/aapt2 · 2 bad arguments
EOF
}

AAPT2=""
PROJECT=""

while [ $# -gt 0 ]; do
    case "$1" in
        --project|-p)
            [ $# -ge 2 ] || { echo "useMyApt: --project needs a value" >&2; usage >&2; exit 2; }
            PROJECT="$2"; shift 2 ;;
        --project=*)
            PROJECT="${1#*=}"; shift ;;
        --aapt2|-a)
            [ $# -ge 2 ] || { echo "useMyApt: --aapt2 needs a value" >&2; usage >&2; exit 2; }
            AAPT2="$2"; shift 2 ;;
        --aapt2=*)
            AAPT2="${1#*=}"; shift ;;
        -h|--help)
            usage; exit 0 ;;
        *)
            echo "useMyApt: unknown argument: $1" >&2
            usage >&2
            exit 2 ;;
    esac
done

PROJECT="${PROJECT:-$PWD}"
[ -d "$PROJECT" ] || { echo "useMyApt: project directory not found: $PROJECT" >&2; exit 1; }
PROJECT="$(cd "$PROJECT" && pwd)"
[ -d "$PROJECT/android" ] || {
    echo "useMyApt: $PROJECT is not a Flutter project (no android/ directory)" >&2
    echo "  Run it from a Flutter project root, or pass --project <dir>." >&2
    exit 1
}

AAPT2="${AAPT2:-$DEFAULT_AAPT2}"
[ -e "$AAPT2" ] || {
    echo "useMyApt: aapt2 not found: $AAPT2" >&2
    echo "  Install it, or pass a different one with --aapt2 <path>." >&2
    exit 1
}
[ -x "$AAPT2" ] || { echo "useMyApt: aapt2 is not executable: $AAPT2" >&2; exit 1; }

GRADLE_PROPS="$PROJECT/android/gradle.properties"
LINE="$OVERRIDE_KEY=$AAPT2"

if [ ! -f "$GRADLE_PROPS" ]; then
    printf '%s\n' "$LINE" > "$GRADLE_PROPS"
    echo "useMyApt: created $GRADLE_PROPS"
    echo "useMyApt: set $LINE"
    exit 0
fi

# Already exactly right: leave the file byte-identical.
if grep -q -x -F "$LINE" "$GRADLE_PROPS"; then
    echo "useMyApt: already set in $GRADLE_PROPS"
    echo "useMyApt:   $LINE"
    exit 0
fi

# Replace an existing override (any value, spacing or '=' / ':' form) where it stands.
TMP="$GRADLE_PROPS.useMyApt.$$"
if awk -v line="$LINE" '
    BEGIN { replaced = 0 }
    /^[[:space:]]*android\.aapt2FromMavenOverride[[:space:]]*[=:]/ {
        if (!replaced) { print line; replaced = 1 }
        next
    }
    { print }
    END { if (!replaced) exit 3 }
' "$GRADLE_PROPS" > "$TMP"; then
    mv "$TMP" "$GRADLE_PROPS"
    echo "useMyApt: updated $GRADLE_PROPS"
    echo "useMyApt: set $LINE"
else
    rm -f "$TMP"
    # No override line yet: append it, terminating the previous line first if needed.
    if [ -s "$GRADLE_PROPS" ] && [ -n "$(tail -c 1 "$GRADLE_PROPS")" ]; then
        printf '\n' >> "$GRADLE_PROPS"
    fi
    printf '%s\n' "$LINE" >> "$GRADLE_PROPS"
    echo "useMyApt: added to $GRADLE_PROPS"
    echo "useMyApt: set $LINE"
fi
