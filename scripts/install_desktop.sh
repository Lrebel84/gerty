#!/bin/bash
# Install Gerty desktop launcher for Pop!_OS / Ubuntu
# Enables launching from the app launcher and pinning to the dock
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_SRC="$PROJECT_ROOT/gerty.desktop"
DESKTOP_DEST="$HOME/.local/share/applications/gerty.desktop"

# Substitute project path in desktop file
mkdir -p "$(dirname "$DESKTOP_DEST")"
sed "s|/home/liam/gerty|$PROJECT_ROOT|g" "$DESKTOP_SRC" > "$DESKTOP_DEST"
chmod +x "$DESKTOP_DEST"

# Update desktop database so the launcher picks it up
if command -v update-desktop-database &>/dev/null; then
  update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo "Installed: $DESKTOP_DEST"
echo ""
echo "To launch Gerty:"
echo "  1. Press Super (Windows key) and search for 'Gerty'"
echo "  2. Click to launch"
echo ""
echo "To pin to the dock/toolbar:"
echo "  1. Launch Gerty (from launcher or: python -m gerty)"
echo "  2. Right-click the Gerty icon in the dock"
echo "  3. Select 'Pin to dock' or 'Add to Favorites'"
