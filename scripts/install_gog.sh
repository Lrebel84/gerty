#!/bin/bash
# Install gog (Google Workspace CLI) on Linux - required for gog skill
set -e
GOG_VERSION="${GOG_VERSION:-0.12.0}"
INSTALL_DIR="${HOME}/.local/bin"
ARCH=$(uname -m)
case "$ARCH" in
  x86_64) ARCH=amd64 ;;
  aarch64|arm64) ARCH=arm64 ;;
  *) echo "Unsupported arch: $ARCH"; exit 1 ;;
esac
mkdir -p "$INSTALL_DIR"
cd /tmp
curl -sL "https://github.com/steipete/gogcli/releases/download/v${GOG_VERSION}/gogcli_${GOG_VERSION}_linux_${ARCH}.tar.gz" -o gog.tar.gz
tar xzf gog.tar.gz
mv gog "$INSTALL_DIR/gog"
chmod +x "$INSTALL_DIR/gog"
echo "Installed: $INSTALL_DIR/gog"
"$INSTALL_DIR/gog" --help | head -3
