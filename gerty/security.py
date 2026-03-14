"""
Security policy (Sprint 10). Reduces risk surface before wider autonomy.
- Forbidden command/action categories
- Sensitive path protections
- Action classification (inspect / safe_edit / risky_operational)
- Trusted tool allowlist

Enforced at runtime. Testable. Does not weaken existing autonomy or validation.
"""

import logging
import re
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Action classes (separate inspect / safe edit / risky operational)
# ---------------------------------------------------------------------------
ACTION_INSPECT = "inspect"           # Read-only: list, summarize, diagnose, logs
ACTION_SAFE_EDIT = "safe_edit"      # Non-destructive writes: notes, maintenance artifacts, RAG
ACTION_RISKY_OPERATIONAL = "risky_operational"  # Shell, package manager, git, credentials

# ---------------------------------------------------------------------------
# Trusted built-in tools (prefer over third-party skills)
# ---------------------------------------------------------------------------
TRUSTED_TOOLS: tuple[str, ...] = (
    "time_date",
    "alarms",
    "timers",
    "calculator",
    "units",
    "random",
    "notes",
    "stopwatch",
    "timezone",
    "weather",
    "rag",
    "screen_vision",
    "search",
    "pomodoro",
    "system_command",
    "media_control",
    "app_launch",
    "browse",
    "sys_monitor",
    "calendar",
    "maintenance",
    "personal_context",
    "agent_factory",
    "agent_runner",
    "agent_designer",
    "intent_orchestrator",
)

# ---------------------------------------------------------------------------
# Forbidden command categories (blocked when checking arbitrary commands)
# ---------------------------------------------------------------------------
# Destructive filesystem
_FORBIDDEN_FS = (
    r"\brm\s+-[rf]",
    r"\brmdir\s+",
    r"\bdel\s+",
    r"\bformat\s+",
    r"\bmkfs\b",
    r"\bdd\s+",
    r">\s*/dev/sd",
)

# Dangerous shell
_FORBIDDEN_SHELL = (
    r"\bsudo\b",
    r"\bsu\s+-",
    r"\bchmod\s+[0-7]{3,4}\s+",
    r"\bchown\s+",
    r"\bcurl\s+.*\|\s*sh\b",
    r"\bwget\s+.*\|\s*sh\b",
    r"\bbash\s+-c\s+",
    r"\bsh\s+-c\s+",
)

# Package manager / dependency
_FORBIDDEN_PKG = (
    r"\bapt\s+(install|remove|purge|autoremove)",
    r"\bapt-get\s+(install|remove|purge|dist-upgrade)",
    r"\baptitude\s+",
    r"\bdpkg\s+-[iP]",
    r"\bpip\s+install\s+",
    r"\bpip\s+uninstall\s+",
    r"\bpip3\s+install\s+",
    r"\bnpm\s+install\s+",
    r"\bnpm\s+uninstall\s+",
    r"\byarn\s+",
    r"\bcargo\s+install\s+",
)

# Destructive git
_FORBIDDEN_GIT = (
    r"\bgit\s+push\s+--force",
    r"\bgit\s+reset\s+--hard",
    r"\bgit\s+clean\s+-fd",
    r"\bgit\s+checkout\s+-f",
    r"\bgit\s+rebase\s+",
    r"\bgit\s+merge\s+.*--no-ff",
)

# Credential / token access
_FORBIDDEN_CREDS = (
    r"\bpass\s+",
    r"\bgnome-keyring\s+",
    r"\bsecret-tool\s+",
    r"\bcat\s+.*\.env",
    r"\bcat\s+.*token",
    r"\bcat\s+.*secret",
    r"\bcat\s+.*credential",
)

# SSH key access
_FORBIDDEN_SSH = (
    r"\bssh-add\s+",
    r"\bssh-keygen\s+-",
    r"\bcat\s+.*\.ssh/",
    r"\bscp\s+.*\.ssh/",
)

# Shell init / dotfile modification
_FORBIDDEN_DOTFILES = (
    r"\b(echo|printf)\s+.*>>\s+\.(bashrc|profile|zshrc|bash_profile)",
    r"\bsed\s+.*\.(bashrc|profile|zshrc)",
    r"\bchmod\s+.*\.(bashrc|profile|zshrc)",
)

_FORBIDDEN_PATTERNS = (
    _FORBIDDEN_FS
    + _FORBIDDEN_SHELL
    + _FORBIDDEN_PKG
    + _FORBIDDEN_GIT
    + _FORBIDDEN_CREDS
    + _FORBIDDEN_SSH
    + _FORBIDDEN_DOTFILES
)

# ---------------------------------------------------------------------------
# Sensitive paths (block read/write when path is under these)
# ---------------------------------------------------------------------------
def _sensitive_path_components() -> tuple[str, ...]:
    """Path components that indicate sensitive locations. Resolved at call time."""
    home = Path.home()
    return (
        str(home / ".ssh"),
        str(home / ".gnupg"),
        str(home / ".config" / "systemd" / "user"),
        str(home / ".local" / "share" / "keyrings"),
        "/etc/passwd",
        "/etc/shadow",
        "/etc/sudoers",
        "/root",
        "/boot",
        str(home / ".bashrc"),
        str(home / ".profile"),
        str(home / ".zshrc"),
        str(home / ".bash_profile"),
        str(home / ".env"),
        str(home / ".netrc"),
        str(home / ".aws" / "credentials"),
        str(home / ".config" / "gcloud"),
    )


def is_path_sensitive(path: str | Path) -> bool:
    """
    Return True if path is under a sensitive location (SSH, credentials, dotfiles, etc.).
    Use before read/write of user-provided or derived paths.
    """
    try:
        resolved = Path(path).resolve()
        path_str = str(resolved)
        for sensitive in _sensitive_path_components():
            if path_str == sensitive or path_str.startswith(sensitive + "/"):
                return True
        return False
    except (OSError, RuntimeError):
        return True  # Err on side of caution


def is_path_under_allowed(path: str | Path, allowed_roots: tuple[Path, ...]) -> bool:
    """
    Return True if path is under one of the allowed roots.
    Use to ensure writes stay within DATA_DIR, PROJECT_ROOT, etc.
    """
    try:
        resolved = Path(path).resolve()
        for root in allowed_roots:
            try:
                root_resolved = root.resolve()
                if str(resolved).startswith(str(root_resolved) + "/") or resolved == root_resolved:
                    return True
            except (OSError, RuntimeError):
                continue
        return False
    except (OSError, RuntimeError):
        return False


def is_command_blocked(cmd: str, args: list[str] | None = None) -> tuple[bool, str]:
    """
    Check if a command (and optional args) matches forbidden patterns.
    Returns (blocked, reason). blocked=True means the command should not run.
    Use when validating arbitrary commands (e.g. future "run command" tool).
    """
    full = cmd
    if args:
        full = " ".join([cmd] + args)
    full_lower = full.lower()
    for pattern in _FORBIDDEN_PATTERNS:
        if re.search(pattern, full_lower, re.IGNORECASE):
            return True, f"Command matches forbidden pattern: {pattern[:50]}..."
    return False, ""


def screen_openclaw_message(message: str) -> tuple[bool, str]:
    """
    Screen an OpenClaw-bound message for risky actions (Sprint 10a).
    Reuses Sprint 10 forbidden patterns. Returns (blocked, denial_reason).
    Use before passing message to OpenClaw execute/stream.
    """
    if not (message or "").strip():
        return False, ""
    text = message.strip()
    # Reuse forbidden command patterns on message text (user may say "run rm -rf" etc.)
    blocked, reason = is_command_blocked("", args=[text])
    if blocked:
        return True, reason
    # Check for sensitive path mentions in action context (run/execute/cat/read + path)
    _action_words = r"\b(run|execute|exec|cat|read|write|edit|modify|chmod|chown)\b"
    _sensitive_refs = (
        r"~?/\.ssh/",
        r"~?/\.env\b",
        r"~?/\.bashrc",
        r"~?/\.profile",
        r"~?/\.netrc",
        r"/etc/passwd",
        r"/etc/shadow",
        r"\.aws/credentials",
    )
    if re.search(_action_words, text, re.IGNORECASE):
        for pat in _sensitive_refs:
            if re.search(pat, text, re.IGNORECASE):
                return True, "Request involves sensitive path (SSH, credentials, dotfiles, etc.)"
    return False, ""


def check_path_safe_for_write(path: str | Path, allowed_roots: tuple[Path, ...]) -> tuple[bool, str]:
    """
    Ensure path is safe for write: under allowed roots and not sensitive.
    Returns (safe, reason). safe=False means do not write.
    """
    if is_path_sensitive(path):
        return False, "Path is in a sensitive location (SSH, credentials, dotfiles, etc.)"
    if not is_path_under_allowed(path, allowed_roots):
        return False, "Path is outside allowed write roots"
    return True, ""


def classify_action(category: str) -> str:
    """
    Map autonomy/shell category to action class.
    """
    if category in ("filesystem_writes", "maintenance_writes"):
        return ACTION_SAFE_EDIT
    if category in ("shell_commands", "service_restart"):
        return ACTION_RISKY_OPERATIONAL
    return ACTION_INSPECT


def get_security_summary() -> dict[str, Any]:
    """Return security policy summary for diagnostics."""
    return {
        "trusted_tools_count": len(TRUSTED_TOOLS),
        "forbidden_pattern_count": len(_FORBIDDEN_PATTERNS),
        "sensitive_path_count": len(_sensitive_path_components()),
        "action_classes": [ACTION_INSPECT, ACTION_SAFE_EDIT, ACTION_RISKY_OPERATIONAL],
    }
