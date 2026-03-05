"""Integration tests for FastAPI endpoints.

Requires: pytest, fastapi, httpx (compatible versions).
Run: python3 -m pytest tests/test_api.py -v
"""

from unittest.mock import MagicMock

import pytest

from gerty.llm.router import Router
from gerty.tools import ToolExecutor, TimeDateTool, AlarmsTool, TimersTool
from gerty.ui.server import create_app


@pytest.fixture
def app(monkeypatch):
    mock_openrouter = MagicMock()
    mock_openrouter.is_available.return_value = False
    monkeypatch.setattr("gerty.llm.router.OpenRouterClient", lambda: mock_openrouter)

    executor = ToolExecutor()
    executor.register(TimeDateTool(), ["time", "date"])
    executor.register(AlarmsTool())
    executor.register(TimersTool())
    router = Router(tool_executor=executor.execute)
    return create_app(router)


def test_app_creation(app):
    """Verify FastAPI app can be created."""
    assert app is not None
