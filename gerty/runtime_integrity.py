"""Desktop runtime integrity: config, daemon, env, routing trace.

Used to verify the desktop app uses the same working path as terminal.
"""

import hashlib
import logging
import socket
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from gerty.config import (
    GERTY_GOOGLE_NATIVE_ENABLED,
    GERTY_OPENCLAW_ENABLED,
    OPENCLAW_CREDENTIALS_PATH,
    OPENCLAW_GATEWAY_WS_URL,
    OPENCLAW_HOME_PATH,
    PROJECT_ROOT,
)

logger = logging.getLogger(__name__)


def _gateway_reachable() -> bool:
    """Check if OpenClaw gateway port is listening."""
    try:
        parsed = urlparse(OPENCLAW_GATEWAY_WS_URL)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 18789
        with socket.create_connection((host, port), timeout=2):
            return True
    except (OSError, socket.timeout, ValueError, TypeError):
        return False


def _gog_available() -> bool:
    """Check if gog skill is installed in OpenClaw workspace."""
    skills_dir = OPENCLAW_HOME_PATH / "workspace" / "skills"
    if not skills_dir.exists():
        return False
    for d in skills_dir.iterdir():
        if d.is_dir() and d.name.lower() == "gog":
            return True
    return False


def _openclaw_env_loaded() -> bool:
    """Check if ~/.openclaw/.env exists (OpenClaw daemon loads it)."""
    env_path = OPENCLAW_HOME_PATH / ".env"
    return env_path.exists() and env_path.is_file()


def get_runtime_integrity_report() -> dict:
    """
    Full runtime integrity report for desktop app verification.
    Call from /api/runtime-integrity to confirm config, daemon, gog, env.
    """
    cfg = f"{PROJECT_ROOT}|openclaw={GERTY_OPENCLAW_ENABLED}|google_native={GERTY_GOOGLE_NATIVE_ENABLED}"
    config_hash = hashlib.sha256(cfg.encode()).hexdigest()[:16]

    daemon_reachable = _gateway_reachable() if GERTY_OPENCLAW_ENABLED else None
    gog_available = _gog_available() if GERTY_OPENCLAW_ENABLED else None
    openclaw_env_exists = _openclaw_env_loaded()

    return {
        "project_root": str(PROJECT_ROOT),
        "config_hash": config_hash,
        "openclaw_enabled": GERTY_OPENCLAW_ENABLED,
        "google_native_enabled": GERTY_GOOGLE_NATIVE_ENABLED,
        "daemon_reachable": daemon_reachable,
        "gog_available": gog_available,
        "openclaw_env_exists": openclaw_env_exists,
        "openclaw_home": str(OPENCLAW_HOME_PATH),
        "openclaw_credentials_exists": OPENCLAW_CREDENTIALS_PATH.exists(),
        "stabilization_mode": not GERTY_GOOGLE_NATIVE_ENABLED,
        "google_routing": "openclaw:gog" if (not GERTY_GOOGLE_NATIVE_ENABLED and GERTY_OPENCLAW_ENABLED) else ("native" if GERTY_GOOGLE_NATIVE_ENABLED else "app_unavailable"),
    }
