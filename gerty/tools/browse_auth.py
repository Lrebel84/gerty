"""Helper to resolve Playwright storage-state path by domain for authenticated browsing."""

import logging
from pathlib import Path

from gerty.config import BROWSE_AUTH_SITES, BROWSE_STORAGE_STATE_DIR

logger = logging.getLogger(__name__)


def get_storage_state_for_message(message: str) -> str | None:
    """
    Return path to storage-state JSON if message mentions a configured auth site.
    BROWSE_AUTH_SITES format: "github.com:github.json,gmail.com:gmail.json"
    """
    if not BROWSE_AUTH_SITES or not BROWSE_STORAGE_STATE_DIR:
        return None
    lower = message.lower()
    for entry in BROWSE_AUTH_SITES.split(","):
        entry = entry.strip()
        if ":" in entry:
            domain, filename = entry.split(":", 1)
            domain = domain.strip().lower()
            filename = filename.strip()
            if domain in lower:
                path = BROWSE_STORAGE_STATE_DIR / filename
                if path.exists():
                    return str(path)
                logger.debug("Auth storage-state not found: %s", path)
    return None
