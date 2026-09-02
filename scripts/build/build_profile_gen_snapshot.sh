#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
DEPOT_TOOLS_DIR="${DEPOT_TOOLS_DIR:-$ROOT_DIR/depot_tools}"
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$DEPOT_TOOLS_DIR"

# Check vpython3
if ! which vpython3 > /dev/null 2>&1; then
    echo "Creating vpython3 wrapper..."
    # This helper runs on the WSL build host, not inside Termux.
    cat > /tmp/vpython3 << 'SCRIPT'
#!/bin/bash
exec python3 "$@"
SCRIPT
    chmod +x /tmp/vpython3
    sudo mv /tmp/vpython3 /usr/local/bin/vpython3
fi

echo "vpython3 path: $(which vpython3)"

cd "$ROOT_DIR/flutter/engine/src"
ninja -C out/android_profile_arm64 -j24 gen_snapshot
