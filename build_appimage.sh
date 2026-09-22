#!/usr/bin/env bash
# build_appimage.sh
#
# Builds standalone Linux binaries for the CLI (vault_create.py,
# vault_recover.py, vault_create_prime.py, vault_recover_prime.py) and
# GUI (vault_gui.py) programs via PyInstaller, and packages each into a
# single-file .AppImage using appimagetool.
# The resulting .AppImages need nothing installed on the target
# machine -- not Python, not tkinter, not `cryptography`, not
# `argon2-cffi`.
#
# Usage:
#   ./build_appimage.sh
#
# Requires (on the BUILD machine only):
#   - Python 3.9+ with pip
#   - python3-tk (for the GUI build; e.g. `apt install python3-tk`)
#   - internet access to download appimagetool from GitHub releases
#   - all the project .py files in the same directory as this script
#
# Output:
#   dist/VaultTool-x86_64.AppImage       (CLI: create/recover/create-prime/recover-prime subcommands)
#   dist/VaultToolGUI-x86_64.AppImage    (GUI)

set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

echo "[*] Installing build-time dependencies (pyinstaller, cryptography, argon2-cffi, pillow) ..."
pip install --quiet --break-system-packages pyinstaller cryptography argon2-cffi pillow \
  || pip install --quiet pyinstaller cryptography argon2-cffi pillow

echo "[*] Fetching appimagetool ..."
APPIMAGETOOL="$WORKDIR/appimagetool.AppImage"
curl -fsSL -o "$APPIMAGETOOL" \
  "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
chmod +x "$APPIMAGETOOL"

echo "[*] Generating shared icon ..."
ICON_PNG="$WORKDIR/vaulttool.png"
python3 - "$ICON_PNG" << 'PYEOF'
import sys
from PIL import Image, ImageDraw
img = Image.new("RGBA", (256, 256), (30, 30, 40, 255))
d = ImageDraw.Draw(img)
d.rounded_rectangle([48, 110, 208, 220], radius=18, fill=(90, 140, 220, 255))
d.arc([78, 40, 178, 160], start=180, end=360, fill=(90, 140, 220, 255), width=22)
d.ellipse([112, 150, 144, 182], fill=(30, 30, 40, 255))
img.save(sys.argv[1])
PYEOF

mkdir -p dist

# ---------------------------------------------------------------------------
# CLI AppImage: vault-create + vault-recover, dispatched by subcommand
# ---------------------------------------------------------------------------
echo "[*] Building CLI binaries with PyInstaller ..."
pyinstaller --onefile --name vault-create        --distpath "$WORKDIR/bin" --workpath "$WORKDIR/build" --specpath "$WORKDIR" vault_create.py
pyinstaller --onefile --name vault-recover        --distpath "$WORKDIR/bin" --workpath "$WORKDIR/build" --specpath "$WORKDIR" vault_recover.py
pyinstaller --onefile --name vault-create-prime   --distpath "$WORKDIR/bin" --workpath "$WORKDIR/build" --specpath "$WORKDIR" vault_create_prime.py
pyinstaller --onefile --name vault-recover-prime  --distpath "$WORKDIR/bin" --workpath "$WORKDIR/build" --specpath "$WORKDIR" vault_recover_prime.py

echo "[*] Assembling CLI AppDir ..."
CLI_APPDIR="$WORKDIR/VaultTool.AppDir"
mkdir -p "$CLI_APPDIR/usr/bin"
cp "$WORKDIR/bin/vault-create"         "$CLI_APPDIR/usr/bin/"
cp "$WORKDIR/bin/vault-recover"        "$CLI_APPDIR/usr/bin/"
cp "$WORKDIR/bin/vault-create-prime"   "$CLI_APPDIR/usr/bin/"
cp "$WORKDIR/bin/vault-recover-prime"  "$CLI_APPDIR/usr/bin/"
chmod +x "$CLI_APPDIR/usr/bin/"*
cp "$ICON_PNG" "$CLI_APPDIR/vaulttool.png"

cat > "$CLI_APPDIR/vaulttool.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=VaultTool
Comment=Threshold-recoverable encrypted vault (Shamir secret sharing)
Exec=AppRun %F
Icon=vaulttool
Categories=Utility;Security;
Terminal=true
EOF

cat > "$CLI_APPDIR/AppRun" << 'EOF'
#!/bin/bash
# VaultTool AppImage dispatcher.
set -e
HERE="$(dirname "$(readlink -f "${0}")")"
SELF_NAME="${ARGV0:-$(basename "$0")}"
CMD="${1:-}"
if [ -n "$CMD" ]; then shift; fi

case "$CMD" in
  create|encrypt)
    exec "$HERE/usr/bin/vault-create" "$@"
    ;;
  recover|decrypt)
    exec "$HERE/usr/bin/vault-recover" "$@"
    ;;
  create-prime)
    exec "$HERE/usr/bin/vault-create-prime" "$@"
    ;;
  recover-prime)
    exec "$HERE/usr/bin/vault-recover-prime" "$@"
    ;;
  ""|-h|--help)
    echo "VaultTool - threshold-recoverable encrypted vault"
    echo
    echo "Usage:"
    echo "  $SELF_NAME create  --input PATH --trustees T --threshold D --word-length N [options]"
    echo "  $SELF_NAME recover VAULT.krypt [options]"
    echo "  $SELF_NAME create-prime  --input PATH --trustees T --threshold D --word-length N [options]"
    echo "  $SELF_NAME recover-prime VAULT.krypt [options]"
    echo
    echo "Run '$SELF_NAME create --help', '$SELF_NAME recover --help', etc. for full option lists."
    ;;
  *)
    echo "Unknown command: $CMD" >&2
    echo "Expected 'create', 'recover', 'create-prime', or 'recover-prime'. Run with --help for usage." >&2
    exit 1
    ;;
esac
EOF
chmod +x "$CLI_APPDIR/AppRun"

echo "[*] Packaging CLI AppImage ..."
rm -f dist/VaultTool-x86_64.AppImage
"$APPIMAGETOOL" --appimage-extract-and-run "$CLI_APPDIR" dist/VaultTool-x86_64.AppImage

# ---------------------------------------------------------------------------
# GUI AppImage: VaultTool-GUI, windowed
# ---------------------------------------------------------------------------
echo "[*] Building GUI binary with PyInstaller ..."
pyinstaller --onefile --windowed --name VaultTool-GUI --distpath "$WORKDIR/bin" --workpath "$WORKDIR/build" --specpath "$WORKDIR" vault_gui.py

echo "[*] Assembling GUI AppDir ..."
GUI_APPDIR="$WORKDIR/VaultToolGUI.AppDir"
mkdir -p "$GUI_APPDIR/usr/bin"
cp "$WORKDIR/bin/VaultTool-GUI" "$GUI_APPDIR/usr/bin/"
chmod +x "$GUI_APPDIR/usr/bin/"*
cp "$ICON_PNG" "$GUI_APPDIR/vaulttool.png"

cat > "$GUI_APPDIR/vaulttool.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=VaultTool GUI
Comment=Threshold-recoverable encrypted vault (Shamir secret sharing) - GUI
Exec=AppRun %F
Icon=vaulttool
Categories=Utility;Security;
Terminal=false
EOF

cat > "$GUI_APPDIR/AppRun" << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
exec "$HERE/usr/bin/VaultTool-GUI" "$@"
EOF
chmod +x "$GUI_APPDIR/AppRun"

echo "[*] Packaging GUI AppImage ..."
rm -f dist/VaultToolGUI-x86_64.AppImage
"$APPIMAGETOOL" --appimage-extract-and-run "$GUI_APPDIR" dist/VaultToolGUI-x86_64.AppImage

echo
echo "[+] Done:"
echo "    dist/VaultTool-x86_64.AppImage      ./dist/VaultTool-x86_64.AppImage create|recover|create-prime|recover-prime ..."
echo "    dist/VaultToolGUI-x86_64.AppImage   ./dist/VaultToolGUI-x86_64.AppImage  (double-click, or run it)"
