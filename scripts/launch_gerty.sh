#!/bin/bash
# Launch Gerty, starting OpenClaw daemon in background if enabled.
# Used by the desktop launcher.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Desktop launcher has minimal env: often PATH=/usr/bin:/bin (Node 20), no DBUS.
# OpenClaw needs Node 22+ and may need session vars for systemctl checks.
OPENCLAW_PATH="/usr/local/bin:$HOME/.npm-global/bin:$HOME/.local/bin:/usr/bin:/bin"
export PATH="$OPENCLAW_PATH:$PATH"

# Inherit session vars if missing (desktop apps usually have these; background processes might not)
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

# Check if OpenClaw integration is enabled
OPENCLAW_ENABLED=0
if [ -f .env ]; then
    val=$(grep -E "^GERTY_OPENCLAW_ENABLED=" .env 2>/dev/null | cut -d= -f2 | tr -d ' ' | tr '[:upper:]' '[:lower:]')
    [[ "$val" =~ ^(1|true|yes)$ ]] && OPENCLAW_ENABLED=1
fi

# When enabled: ensure OpenClaw daemon is running before launching Gerty.
# Use env to force Node 22+ (desktop launcher often has Node 20 first in PATH).
if [ "$OPENCLAW_ENABLED" = "1" ] && command -v openclaw &>/dev/null; then
    port_ready() {
        "$PROJECT_ROOT/.venv/bin/python" -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(1)
try:
    s.connect(('127.0.0.1', 18789))
    s.close()
    exit(0)
except Exception:
    exit(1)
" 2>/dev/null
    }
    if ! port_ready; then
        env PATH="$OPENCLAW_PATH" DBUS_SESSION_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS" XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" \
            openclaw daemon start >> "$PROJECT_ROOT/gerty.log" 2>&1 &
        for i in $(seq 1 20); do
            sleep 1
            port_ready && break
        done
    fi
fi

# Launch Gerty (python -B avoids stale .pyc; ensures latest code)
exec "$PROJECT_ROOT/.venv/bin/python" -B -m gerty
