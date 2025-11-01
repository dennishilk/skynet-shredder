#!/usr/bin/env bash
set -e

APPDIR="$HOME/.local/share/skynet-shredder"
DESKTOP_FILE="$HOME/.local/share/applications/skynet-shredder.desktop"

echo "[Skynet Shredder] Uninstalling..."
echo

# Remove application directory
if [ -d "$APPDIR" ]; then
  echo "Removing app directory: $APPDIR"
  rm -rf "$APPDIR"
else
  echo "App directory not found: $APPDIR (already removed?)"
fi

# Remove desktop entry
if [ -f "$DESKTOP_FILE" ]; then
  echo "Removing desktop entry: $DESKTOP_FILE"
  rm -f "$DESKTOP_FILE"
else
  echo "Desktop entry not found: $DESKTOP_FILE (already removed?)"
fi

# Update desktop database (optional)
if command -v update-desktop-database >/dev/null 2>&1; then
  echo "Updating application database..."
  update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
fi

echo
echo "✅ Skynet Shredder has been successfully uninstalled."
echo "   (Python dependencies like PyQt5 remain installed, uninstall via apt if desired.)"
