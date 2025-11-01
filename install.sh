#!/usr/bin/env bash
set -e
echo "[Skynet Shredder] Installing dependencies..."
sudo apt update
sudo apt install -y python3 python3-pyqt5 coreutils util-linux findutils mount
if ! dpkg -s secure-delete >/dev/null 2>&1; then
  echo "[i] Optional: sudo apt install secure-delete  # provides 'srm' fallback"
fi

APPDIR="$HOME/.local/share/skynet-shredder"
mkdir -p "$APPDIR/assets"
cp -f skynet_shredder.py "$APPDIR/"
cp -f assets/icon.png "$APPDIR/assets/icon.png"

DESK="$HOME/.local/share/applications/skynet-shredder.desktop"
cat > "$DESK" <<EOF
[Desktop Entry]
Name=Skynet Shredder
Comment=Securely delete files and folders (HDD/SSD aware)
Exec=python3 $APPDIR/skynet_shredder.py
Icon=$APPDIR/assets/icon.png
Terminal=false
Type=Application
Categories=Utility;Security;System;
EOF

update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true

echo "Installed. Launch via your app menu or run: python3 $APPDIR/skynet_shredder.py"
