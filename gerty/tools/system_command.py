"""System command tool: safe, allowlist-based terminal commands (lock, suspend, reboot, shutdown)."""

import logging
import shutil
import subprocess

from gerty.config import GERTY_SYSTEM_TOOLS
from gerty.tools.base import Tool

logger = logging.getLogger(__name__)

# Allowlist: intent -> (command, args). No user input passed to shell.
_COMMAND_ALLOWLIST: dict[str, tuple[str, list[str]]] = {
    "lock": ("loginctl", ["lock-session"]),
    "suspend": ("systemctl", ["suspend"]),
    "reboot": ("systemctl", ["reboot"]),
    "shutdown": ("systemctl", ["poweroff"]),
}

# Keywords that map to each intent (checked in order of specificity)
_LOCK_KEYWORDS = ["lock screen", "lock my screen", "lock the screen", "lock computer"]
_SUSPEND_KEYWORDS = ["suspend", "sleep", "put to sleep", "hibernate"]
_REBOOT_KEYWORDS = ["reboot", "restart", "restart computer"]
_SHUTDOWN_KEYWORDS = ["shut down", "shutdown", "power off", "turn off", "power down"]


def _classify_system_intent(message: str) -> str | None:
    """Map message to allowlisted intent, or None if no match."""
    lower = message.lower().strip()
    for kw in _LOCK_KEYWORDS:
        if kw in lower:
            return "lock"
    for kw in _SUSPEND_KEYWORDS:
        if kw in lower:
            return "suspend"
    for kw in _REBOOT_KEYWORDS:
        if kw in lower:
            return "reboot"
    for kw in _SHUTDOWN_KEYWORDS:
        if kw in lower:
            return "shutdown"
    return None


def _run_command(cmd: str, args: list[str], timeout: int = 10) -> tuple[bool, str]:
    """Run allowlisted command. Returns (success, message)."""
    if not shutil.which(cmd):
        return False, f"Command '{cmd}' not found. Install the required system package."
    try:
        result = subprocess.run(
            [cmd] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        if result.returncode == 0:
            return True, ""
        err = (result.stderr or result.stdout or "").strip()
        return False, err or f"Command failed with code {result.returncode}"
    except subprocess.TimeoutExpired:
        return False, "Command timed out."
    except Exception as e:
        logger.debug("System command failed: %s", e)
        return False, str(e)


class SystemCommandTool(Tool):
    """Execute safe, predefined system commands (lock, suspend, reboot, shutdown)."""

    @property
    def name(self) -> str:
        return "system_command"

    @property
    def description(self) -> str:
        return "Lock screen, suspend, reboot, or shutdown (opt-in)"

    def execute(self, intent: str, message: str) -> str:
        if not GERTY_SYSTEM_TOOLS:
            return "System commands are disabled. Set GERTY_SYSTEM_TOOLS=1 in .env to enable."

        resolved = _classify_system_intent(message)
        if not resolved or resolved not in _COMMAND_ALLOWLIST:
            return "I can lock the screen, suspend, reboot, or shut down. What would you like?"

        cmd, args = _COMMAND_ALLOWLIST[resolved]
        ok, err = _run_command(cmd, args)
        if ok:
            labels = {"lock": "Screen locked", "suspend": "Suspending", "reboot": "Rebooting", "shutdown": "Shutting down"}
            return f"{labels[resolved]}."
        return f"Could not {resolved}: {err}"
