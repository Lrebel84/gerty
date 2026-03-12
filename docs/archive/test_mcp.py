#!/usr/bin/env python3
"""Diagnostic script for MCP (Rube/Composio) integration.

Tests:
1. Groq Remote MCP - direct responses.create with Rube URL
2. Local MCP client - list_tools and single call_tool latency

Run from project root: python scripts/test_mcp.py
Requires: COMPOSIO_API_KEY, GROQ_API_KEY (for Groq test)
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")


def test_groq_remote_mcp() -> bool:
    """Test Groq Remote MCP with Rube. Returns True if successful."""
    from gerty.config import COMPOSIO_API_KEY, GROQ_API_KEY, RUBE_MCP_URL

    if not GROQ_API_KEY:
        print("SKIP: GROQ_API_KEY not set")
        return False
    if not COMPOSIO_API_KEY:
        print("SKIP: COMPOSIO_API_KEY not set (required for Rube auth)")
        return False

    print("\n--- Groq Remote MCP ---")
    print(f"Rube URL: {RUBE_MCP_URL}")

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )
        mcp_config = {
            "type": "mcp",
            "server_label": "Rube",
            "server_url": RUBE_MCP_URL.rstrip("/"),
            "server_description": "Google Calendar, Gmail, Drive, Tasks, and 500+ apps.",
            "require_approval": "never",
            "headers": {"Authorization": f"Bearer {COMPOSIO_API_KEY}"},
        }
        start = time.perf_counter()
        response = client.responses.create(
            model="llama-3.1-8b-instant",
            input="List the first 3 tools available from Rube. Just name them.",
            tools=[mcp_config],
            instructions="Use Rube tools to answer. Be brief.",
        )
        elapsed = time.perf_counter() - start
        text = getattr(response, "output_text", None) or ""
        if not text and hasattr(response, "output"):
            for item in response.output or []:
                itype = item.get("type") if isinstance(item, dict) else getattr(item, "type", None)
                if itype == "message":
                    content = item.get("content", []) if isinstance(item, dict) else getattr(item, "content", []) or []
                    for c in content:
                        if (c.get("type") if isinstance(c, dict) else getattr(c, "type", None)) == "output_text":
                            text = (c.get("text") or getattr(c, "text", "")) or text
                            break
        print(f"OK in {elapsed:.1f}s")
        print(f"Response: {text[:500]}..." if len(text) > 500 else f"Response: {text}")
        return True
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_local_mcp_client() -> bool:
    """Test local MCP client list_tools and call_tool. Measures latency."""
    from gerty.config import COMPOSIO_API_KEY, RUBE_MCP_URL

    if not COMPOSIO_API_KEY:
        print("SKIP: COMPOSIO_API_KEY not set")
        return False

    print("\n--- Local MCP Client ---")
    print(f"Rube URL: {RUBE_MCP_URL}")

    try:
        from gerty.mcp.client import MCPClient

        client = MCPClient()

        # list_tools
        start = time.perf_counter()
        tools = client.list_tools()
        elapsed = time.perf_counter() - start
        print(f"list_tools: {len(tools)} tools in {elapsed:.1f}s")

        if not tools:
            print("No tools returned")
            return False

        # Pick a tool that might work with minimal args (search/list style)
        first_tool = tools[0]
        name = first_tool.get("function", {}).get("name", "")
        print(f"First tool: {name}")

        # call_tool (simple call - may fail if tool needs specific args)
        start = time.perf_counter()
        result = client.call_tool(name, {})
        elapsed = time.perf_counter() - start
        print(f"call_tool({name}): {elapsed:.1f}s")
        print(f"Result preview: {str(result)[:300]}...")
        return True
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


def main() -> None:
    print("MCP Diagnostic Script")
    print("=" * 50)
    groq_ok = test_groq_remote_mcp()
    local_ok = test_local_mcp_client()
    print("\n" + "=" * 50)
    print(f"Groq Remote MCP: {'PASS' if groq_ok else 'FAIL/SKIP'}")
    print(f"Local MCP Client: {'PASS' if local_ok else 'FAIL/SKIP'}")


if __name__ == "__main__":
    main()
