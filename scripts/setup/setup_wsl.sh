#!/bin/bash
# Flutter Termux 編譯環境設置腳本
# 在 WSL Ubuntu 中執行此腳本

set -e

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

echo "=========================================="
echo "Flutter Termux 編譯環境設置"
echo "=========================================="

# 1. 安裝編譯依賴
echo "[1/4] 安裝編譯依賴..."
sudo apt update
sudo apt install -y \
    git python3 python3-pip python3-venv \
    ninja-build cmake clang pkg-config \
    libgtk-3-dev libglib2.0-dev \
    curl wget unzip zip xz-utils

# 2. 安裝 Python 依賴
echo "[2/4] 安裝 Python 依賴..."
pip3 install -r "$ROOT_DIR/requirements.txt"

# 3. 下載 Android NDK r27
echo "[3/4] 下載 Android NDK r27d..."
NDK_VERSION="r27d"
NDK_DIR="/opt/android-ndk-${NDK_VERSION}"

if [ -d "$NDK_DIR" ]; then
    echo "NDK 已存在: $NDK_DIR"
else
    # This helper runs on the WSL build host, not inside Termux.
    cd /tmp
    wget -q --show-progress https://dl.google.com/android/repository/android-ndk-${NDK_VERSION}-linux.zip
    echo "解壓縮 NDK..."
    sudo unzip -q android-ndk-${NDK_VERSION}-linux.zip -d /opt/
    rm android-ndk-${NDK_VERSION}-linux.zip
    echo "NDK 安裝完成: $NDK_DIR"
fi

# 4. 設置環境變數
echo "[4/4] 設置環境變數..."
BASHRC_LINE="export ANDROID_NDK=${NDK_DIR}"
if ! grep -q "ANDROID_NDK" ~/.bashrc; then
    echo "$BASHRC_LINE" >> ~/.bashrc
    echo "已添加 ANDROID_NDK 到 ~/.bashrc"
fi

export ANDROID_NDK="$NDK_DIR"

# 檢查 Clang 版本
CLANG_VERSION=$(ls ${NDK_DIR}/toolchains/llvm/prebuilt/linux-x86_64/lib/clang/ | head -1)
echo ""
echo "=========================================="
echo "環境設置完成！"
echo "=========================================="
echo "NDK 路徑: $NDK_DIR"
echo "Clang 版本: $CLANG_VERSION"
echo ""
echo "請執行: source ~/.bashrc"
echo "然後可以開始編譯！"
