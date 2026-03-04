#!/bin/bash
# Install Gerty desktop launcher for Pop!_OS
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_SRC="$PROJECT_ROOT/gerty.desktop"
DESKTOP_DEST="$HOME/.local/share/applications/gerty.desktop"

# Substitute project path in desktop file
mkdir -p "$(dirname "$DESKTOP_DEST")"
sed "s|/home/liam/gerty|$PROJECT_ROOT|g" "$DESKTOP_SRC" > "$DESKTOP_DEST"
chmod +x "$DESKTOP_DEST"
echo "Installed: $DESKTOP_DEST"
echo "You can now find Gerty in your application launcher and pin it to the dock."
