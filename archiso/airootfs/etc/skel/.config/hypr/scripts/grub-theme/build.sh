#!/usr/bin/env bash
# Build and install the Matrix GRUB theme to /boot/grub/themes/matrix/.
# Requires sudo for the /boot copy + grub-mkconfig.

set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SRC_DIR}/build"
DEST_DIR="/boot/grub/themes/matrix"

JBM_REG="/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf"
JBM_BOLD="/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Bold.ttf"

for f in "$JBM_REG" "$JBM_BOLD"; do
    [[ -f "$f" ]] || { echo "missing font: $f" >&2; exit 1; }
done

mkdir -p "$BUILD_DIR"

echo "[1/4] generating background..."
python3 "${SRC_DIR}/gen_matrix_bg.py" "${BUILD_DIR}/background.png"

echo "[2/4] building PF2 fonts..."
grub-mkfont -s 14 -n "JetBrainsMono" \
    -o "${BUILD_DIR}/jetbrains-14.pf2" "$JBM_REG" 2>/dev/null
grub-mkfont -s 18 -n "JetBrainsMono" \
    -o "${BUILD_DIR}/jetbrains-bold-18.pf2" "$JBM_BOLD" 2>/dev/null

for f in jetbrains-14.pf2 jetbrains-bold-18.pf2; do
    [[ -s "${BUILD_DIR}/$f" ]] || { echo "empty PF2: $f" >&2; exit 1; }
done

cp "${SRC_DIR}/theme.txt" "${BUILD_DIR}/theme.txt"

echo "[3/4] installing to ${DEST_DIR}..."
sudo mkdir -p "$DEST_DIR"
sudo cp "${BUILD_DIR}/background.png" \
        "${BUILD_DIR}/jetbrains-14.pf2" \
        "${BUILD_DIR}/jetbrains-bold-18.pf2" \
        "${BUILD_DIR}/theme.txt" \
        "$DEST_DIR/"

echo "[4/4] installed files:"
sudo ls -lh "$DEST_DIR"

echo
echo "next: set GRUB_THEME in /etc/default/grub and run grub-mkconfig"
echo "  sudo sed -i 's|GRUB_THEME=.*|GRUB_THEME=\"${DEST_DIR}/theme.txt\"|' /etc/default/grub"
echo "  sudo grub-mkconfig -o /boot/grub/grub.cfg"
