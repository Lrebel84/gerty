#!/bin/bash
# Diagnostic: check if OpenClaw daemon is running and reachable.
# Run from project root: ./scripts/check_openclaw.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== OpenClaw diagnostic ==="

# 1. Check .env
echo ""
echo "1. Gerty config (.env):"
if [ -f .env ]; then
    val=$(grep -E "^GERTY_OPENCLAW_ENABLED=" .env 2>/dev/null | cut -d= -f2 | tr -d ' ')
    echo "   GERTY_OPENCLAW_ENABLED=$val"
else
    echo "   .env not found"
fi

# 2. Find openclaw
echo ""
echo "2. OpenClaw CLI:"
export PATH="$HOME/.npm-global/bin:$HOME/.local/bin:$PATH"
if command -v openclaw &>/dev/null; then
    echo "   Found: $(which openclaw)"
    openclaw --version 2>/dev/null || echo "   (version unknown)"
else
    echo "   NOT FOUND in PATH"
    echo "   Try: npm install -g openclaw  (or pnpm add -g openclaw)"
fi

# 3. Process check
echo ""
echo "3. Daemon process:"
if pgrep -f "openclaw" &>/dev/null; then
    echo "   Running:"
    ps aux | grep -E "[o]penclaw" || true
else
    echo "   NOT RUNNING"
fi

# 4. Port check
echo ""
echo "4. Gateway port (18789):"
if command -v ss &>/dev/null; then
    ss -tlnp 2>/dev/null | grep 18789 || echo "   Port 18789 not listening"
elif command -v netstat &>/dev/null; then
    netstat -tlnp 2>/dev/null | grep 18789 || echo "   Port 18789 not listening"
else
    echo "   (ss/netstat not available)"
fi

# 5. OpenClaw config
echo ""
echo "5. OpenClaw config (~/.openclaw):"
if [ -d "$HOME/.openclaw" ]; then
    echo "   Exists"
    [ -f "$HOME/.openclaw/.env" ] && echo "   .env: present" || echo "   .env: missing"
else
    echo "   Directory not found - run: openclaw onboard"
fi

# 6. Connection + execute test (Gerty SDK)
echo ""
echo "6. Gerty → OpenClaw connection:"
if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    out=$("$PROJECT_ROOT/.venv/bin/python" -c "
from gerty.openclaw.client import is_reachable, execute
if not is_reachable():
    print('FAIL: not reachable')
    exit(1)
r = execute('list my skills')
if 'action system' in r.lower() or 'isnt running' in r.lower():
    print('FAIL:', r[:80])
    exit(1)
print('OK')
" 2>&1) || true
    echo "   $out"
else
    echo "   (skip: no .venv)"
fi

echo ""
echo "=== Quick fix ==="
echo "If daemon not running: openclaw daemon start"
echo "If openclaw not found: npm install -g openclaw"
echo "If config missing: openclaw onboard"
