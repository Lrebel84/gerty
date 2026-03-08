"""App launching: parse .desktop files and launch applications by name."""

import configparser
import logging
import shutil
import subprocess
from pathlib import Path

from gerty.config import GERTY_SYSTEM_TOOLS
from gerty.tools.base import Tool

logger = logging.getLogger(__name__)

# XDG desktop file directories
_DESKTOP_DIRS = [
    Path("/usr/share/applications"),
    Path("/usr/local/share/applications"),
    Path.home() / ".local" / "share" / "applications",
]

# Index: lowercase search term -> list of (desktop_path, display_name)
_app_index: dict[str, list[tuple[Path, str]]] | None = None


def _parse_desktop(path: Path) -> tuple[str | None, str | None, bool] | None:
    """Parse .desktop file. Returns (Name, GenericName, should_skip) or None on error."""
    try:
        config = configparser.ConfigParser(interpolation=None)
        config.read(path, encoding="utf-8")
        if "Desktop Entry" not in config:
            return None
        entry = config["Desktop Entry"]
        if entry.get("Type", "").lower() != "application":
            return None
        if entry.get("NoDisplay", "false").lower() == "true":
            return (None, None, True)
        if entry.get("Hidden", "false").lower() == "true":
            return (None, None, True)
        name = entry.get("Name", "").strip()
        generic = entry.get("GenericName", "").strip()
        return name or None, generic or None, False
    except Exception as e:
        logger.debug("Failed to parse %s: %s", path, e)
        return None


def _build_app_index() -> dict[str, list[tuple[Path, str]]]:
    """Scan desktop dirs and build lookup index."""
    global _app_index
    if _app_index is not None:
        return _app_index
    index: dict[str, list[tuple[Path, str]]] = {}
    for base in _DESKTOP_DIRS:
        if not base.exists():
            continue
        for path in base.glob("*.desktop"):
            parsed = _parse_desktop(path)
            if parsed is None:
                continue
            name, generic, skip = parsed
            if skip:
                continue
            display = name or path.stem
            # Index by desktop basename (e.g. firefox, code)
            stem_lower = path.stem.lower()
            if stem_lower not in index:
                index[stem_lower] = []
            index[stem_lower].append((path, display))
            # Index by Name
            if name:
                key = name.lower()
                if key not in index:
                    index[key] = []
                index[key].append((path, display))
            # Index by GenericName
            if generic:
                key = generic.lower()
                if key not in index:
                    index[key] = []
                index[key].append((path, display))
    _app_index = index
    return _app_index


def _extract_app_name(message: str) -> str | None:
    """Extract app name from 'open firefox', 'launch vs code', etc."""
    lower = message.lower().strip()
    prefixes = ["open ", "launch ", "start ", "run "]
    for prefix in prefixes:
        if lower.startswith(prefix):
            name = message[len(prefix) :].strip().rstrip("?.!,")
            # Normalize: "vs code" -> "code", "visual studio code" -> "code"
            name_lower = name.lower()
            if "vs code" in name_lower or "visual studio code" in name_lower:
                return "code"
            if "vscode" in name_lower:
                return "code"
            return name if len(name) >= 2 else None
    return None


def _find_app(app_name: str) -> tuple[Path, str] | None:
    """Find best matching desktop file. Returns (path, display_name) or None."""
    index = _build_app_index()
    # Direct match on stem
    stem = app_name.lower().replace(" ", "")
    if stem in index:
        entries = index[stem]
        return entries[0]
    # Substring match
    for key, entries in index.items():
        if stem in key or key in stem:
            return entries[0]
    # Word match: "fire fox" -> firefox
    words = app_name.lower().split()
    for key, entries in index.items():
        if all(w in key for w in words if len(w) >= 2):
            return entries[0]
    return None


def _launch_app(desktop_path: Path, display_name: str) -> tuple[bool, str]:
    """Launch app via gtk-launch or gio. Returns (success, message)."""
    if shutil.which("gtk-launch"):
        try:
            result = subprocess.run(
                ["gtk-launch", desktop_path.stem],
                capture_output=True,
                text=True,
                timeout=10,
                shell=False,
            )
            if result.returncode == 0:
                return True, ""
            err = (result.stderr or "").strip()
            return False, err or "Launch failed."
        except Exception as e:
            logger.debug("gtk-launch failed: %s", e)
            return False, str(e)
    if shutil.which("gio"):
        try:
            result = subprocess.run(
                ["gio", "launch", str(desktop_path)],
                capture_output=True,
                text=True,
                timeout=10,
                shell=False,
            )
            if result.returncode == 0:
                return True, ""
            err = (result.stderr or "").strip()
            return False, err or "Launch failed."
        except Exception as e:
            logger.debug("gio launch failed: %s", e)
            return False, str(e)
    return False, "gtk-launch or gio not found. Install libgtk-3-0 or glib2."


class AppLaunchTool(Tool):
    """Launch applications by name from .desktop files."""

    @property
    def name(self) -> str:
        return "app_launch"

    @property
    def description(self) -> str:
        return "Open or launch applications by name"

    def execute(self, intent: str, message: str) -> str:
        if not GERTY_SYSTEM_TOOLS:
            return "App launching is disabled. Set GERTY_SYSTEM_TOOLS=1 in .env to enable."

        app_name = _extract_app_name(message)
        if not app_name:
            return "Try: open Firefox, launch VS Code, or start Terminal."

        match = _find_app(app_name)
        if not match:
            return f"I couldn't find an app named '{app_name}'. Try a different name."

        desktop_path, display_name = match
        ok, err = _launch_app(desktop_path, display_name)
        if ok:
            return f"Launched {display_name}."
        return f"Could not launch {display_name}: {err}"
