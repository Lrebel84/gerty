"""Tool interface and executor."""

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """Base class for Gerty tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool identifier."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description for routing."""
        pass

    @abstractmethod
    def execute(self, intent: str, message: str) -> str:
        """Execute intent with user message. Returns response text."""
        pass


class ToolExecutor:
    """Dispatches to registered tools."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool, names: list[str] | None = None):
        """Register a tool. Optionally register under multiple intent names."""
        for name in names or [tool.name]:
            self._tools[name] = tool

    def execute(self, intent: str, message: str) -> str:
        """Execute tool for intent. Returns response or empty if no match."""
        tool = self._tools.get(intent)
        if tool:
            return tool.execute(intent, message)
        return ""
