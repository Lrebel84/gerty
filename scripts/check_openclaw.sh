#!/bin/bash
# Diagnostic: check if OpenClaw daemon is running and reachable.
# Run from project root: ./scripts/check_openclaw.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

export PATH="$HOME/.npm-global/bin:$HOME/.local/bin:$PATH"

# Port 18789 = OpenClaw gateway. If listening, daemon is running.
DAEMON_UP=0
if (command -v ss &>/dev/null && ss -tlnp 2>/dev/null | grep -q 18789) || \
   (command -v netstat &>/dev/null && netstat -tlnp 2>/dev/null | grep -q 18789); then
    DAEMON_UP=1
fi

EXEC_GATEWAY=0
[ -f "$HOME/.openclaw/openclaw.json" ] && grep -q '"host"[[:space:]]*:[[:space:]]*"gateway"' "$HOME/.openclaw/openclaw.json" 2>/dev/null && EXEC_GATEWAY=1

PYTHON_ALLOWED=0
python_path="$PROJECT_ROOT/.venv/bin/python"
[ -f "$HOME/.openclaw/exec-approvals.json" ] && grep -q "$python_path" "$HOME/.openclaw/exec-approvals.json" 2>/dev/null && PYTHON_ALLOWED=1

echo "=== OpenClaw diagnostic ==="
echo ""
echo "1. Gerty: OpenClaw enabled?"
grep -E "^GERTY_OPENCLAW_ENABLED=" .env 2>/dev/null | cut -d= -f2 | tr -d ' ' || echo "   (no .env or not set)"

echo ""
echo "2. OpenClaw daemon running?"
if [ "$DAEMON_UP" = "1" ]; then
    echo "   YES - port 18789 is listening"
else
    echo "   NO - port 18789 not listening"
    echo "   Fix: run 'openclaw daemon start' (or launch Gerty from the app launcher)"
fi

echo ""
echo "3. Exec runs on your machine (gateway)?"
if [ "$EXEC_GATEWAY" = "1" ]; then
    echo "   YES - exec can read your Google token"
else
    echo "   NO - exec is in sandbox, cannot read ~/.openclaw/credentials/"
    echo "   Fix: set tools.exec.host to \"gateway\" in ~/.openclaw/openclaw.json"
fi

echo ""
echo "4. Python allowlisted for exec?"
if [ "$PYTHON_ALLOWED" = "1" ]; then
    echo "   YES"
else
    echo "   NO - add $python_path to ~/.openclaw/exec-approvals.json"
fi

echo ""
echo "5. Connection test (Gerty -> OpenClaw):"
if [ -f "$PROJECT_ROOT/.venv/bin/python" ] && [ "$DAEMON_UP" = "1" ]; then
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
elif [ "$DAEMON_UP" = "0" ]; then
    echo "   (skip: daemon not running)"
else
    echo "   (skip: no .venv)"
fi

echo ""
echo "6. Tool execution test (main agent bug #39971):"
if [ "$DAEMON_UP" = "1" ] && command -v openclaw &>/dev/null; then
    # Ask main agent to run a simple command. If tools work, we get real output.
    tool_out=$(timeout 45 openclaw agent --agent main --message 'Run exactly: echo TOOL_TEST_OK' 2>&1) || true
    if echo "$tool_out" | grep -q "TOOL_TEST_OK"; then
        echo "   OK - main agent executed the command (real tool output)"
    elif echo "$tool_out" | grep -qi "exec(command:"; then
        echo "   BUG - main agent outputs tool text instead of executing (see docs/OPENCLAW_DIAGNOSIS.md)"
    else
        echo "   (unclear - check output manually)"
    fi
else
    [ "$DAEMON_UP" = "0" ] && echo "   (skip: daemon not running)"
    command -v openclaw &>/dev/null || echo "   (skip: openclaw not in PATH)"
fi

echo ""
echo "=== Summary ==="
if [ "$DAEMON_UP" = "1" ] && [ "$EXEC_GATEWAY" = "1" ] && [ "$PYTHON_ALLOWED" = "1" ]; then
    echo "All good. Calendar/Gmail should work when you ask Gerty."
else
    [ "$DAEMON_UP" = "0" ] && echo "- Start daemon: openclaw daemon start"
    [ "$EXEC_GATEWAY" = "0" ] && echo "- Set exec host: edit ~/.openclaw/openclaw.json, tools.exec.host = \"gateway\""
    [ "$PYTHON_ALLOWED" = "0" ] && echo "- Allowlist Python: add $python_path to ~/.openclaw/exec-approvals.json"
fi
