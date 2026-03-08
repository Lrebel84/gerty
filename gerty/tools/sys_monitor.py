"""System monitoring: CPU, memory, and top processes via psutil."""

import logging

from gerty.tools.base import Tool

logger = logging.getLogger(__name__)

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore


def _get_system_status() -> str:
    """Return human-readable system status (CPU, RAM, top processes)."""
    if not psutil:
        return "psutil not installed. Run: pip install psutil"

    parts = []
    # CPU
    try:
        cpu = psutil.cpu_percent(interval=1)
        parts.append(f"CPU is at {cpu:.0f}%")
    except Exception as e:
        logger.debug("CPU percent failed: %s", e)
        parts.append("CPU: unavailable")

    # Memory
    try:
        mem = psutil.virtual_memory()
        parts.append(f"RAM: {mem.percent:.0f}% used ({mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB)")
    except Exception as e:
        logger.debug("Memory failed: %s", e)
        parts.append("RAM: unavailable")

    # Top processes by CPU
    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = p.info
                cpu_pct = info.get("cpu_percent") or 0
                if cpu_pct > 0:
                    procs.append((info.get("name") or "?", cpu_pct))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda x: x[1], reverse=True)
        top = procs[:5]
        if top:
            proc_str = "; ".join(f"{name} ({pct:.0f}%)" for name, pct in top)
            parts.append(f"Top processes: {proc_str}")
    except Exception as e:
        logger.debug("Process iter failed: %s", e)

    return ". ".join(parts) + "."


def _classify_sysmon_intent(message: str) -> bool:
    """Check if message asks for system diagnostics."""
    lower = message.lower().strip()
    keywords = [
        "why are my fans",
        "fans spinning",
        "cpu usage",
        "memory usage",
        "what's using",
        "what is using",
        "system status",
        "diagnose",
        "why is my computer",
        "why is my pc",
        "what's using cpu",
        "what's using memory",
    ]
    return any(kw in lower for kw in keywords)


class SysMonitorTool(Tool):
    """Diagnose CPU, memory, and top processes."""

    @property
    def name(self) -> str:
        return "sys_monitor"

    @property
    def description(self) -> str:
        return "System diagnostics: CPU, RAM, top processes"

    def execute(self, intent: str, message: str) -> str:
        return _get_system_status()
