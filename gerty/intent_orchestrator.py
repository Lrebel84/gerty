"""Intent Orchestrator — interpret high-level outcome requests and choose the best internal path.

System 4. Cautious v1: planning and recommendation before aggressive automation.
No background autonomy, no recursive agent chains, no shell/code execution.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Action paths the orchestrator can recommend
ACTION_DIRECT_ANSWER = "direct_answer"
ACTION_USE_TOOL = "use_tool"
ACTION_RUN_AGENT = "run_agent"
ACTION_DESIGN_AGENT = "design_agent"
ACTION_CREATE_PROJECT_STRUCTURE = "create_project_structure"
ACTION_RECOMMEND_NEW_TOOL = "recommend_new_tool"
ACTION_ESCALATE_TO_MAINTENANCE = "escalate_to_maintenance"

ACTION_PATHS = (
    ACTION_DIRECT_ANSWER,
    ACTION_USE_TOOL,
    ACTION_RUN_AGENT,
    ACTION_DESIGN_AGENT,
    ACTION_CREATE_PROJECT_STRUCTURE,
    ACTION_RECOMMEND_NEW_TOOL,
    ACTION_ESCALATE_TO_MAINTENANCE,
)

# Request types for classification
REQUEST_SIMPLE = "simple"
REQUEST_BROAD = "broad"
REQUEST_AMBIGUOUS = "ambiguous"
REQUEST_SPECIFIC = "specific"

DEFAULT_RESULT = {
    "request_type": REQUEST_AMBIGUOUS,
    "recommended_action": ACTION_DIRECT_ANSWER,
    "reasoning_summary": "",
    "tool_name": None,
    "agent_name": None,
    "needs_new_agent": False,
    "needs_new_tool": False,
    "suggested_next_step": "",
    "safe_to_execute_now": False,
}


def _call_llm(prompt: str, system_prompt: str) -> str:
    """Call LLM and return raw response."""
    from gerty.config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OLLAMA_CHAT_MODEL
    from gerty.llm.ollama_client import OllamaClient
    from gerty.llm.openrouter_client import OpenRouterClient

    ollama = OllamaClient()
    openrouter = OpenRouterClient()

    try:
        if ollama.is_available():
            return ollama.chat(
                prompt,
                history=[],
                model=OLLAMA_CHAT_MODEL or "llama3.2",
                system_prompt=system_prompt,
            )
        if OPENROUTER_API_KEY and openrouter.is_available():
            return openrouter.chat(
                prompt,
                history=[],
                model=OPENROUTER_MODEL,
                system_prompt=system_prompt,
            )
    except Exception as e:
        logger.exception("Intent orchestrator LLM call failed: %s", e)
    return ""


def _parse_json_from_response(response: str) -> dict[str, Any] | None:
    """Extract JSON object from LLM response."""
    if not response or not response.strip():
        return None
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
    if json_match:
        try:
            parsed = json.loads(json_match.group(1).strip())
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass
    try:
        parsed = json.loads(response.strip())
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    return None


def classify_outcome_request(message: str) -> str:
    """
    Fast keyword-based classification of outcome-oriented requests.
    Returns REQUEST_SIMPLE, REQUEST_BROAD, REQUEST_AMBIGUOUS, or REQUEST_SPECIFIC.
    """
    lower = message.lower().strip()
    if not lower:
        return REQUEST_AMBIGUOUS

    # Broad outcome phrases
    broad_phrases = [
        "help me explore",
        "help me organize",
        "turn this into",
        "build whatever agent",
        "if we don't have the right tool",
        "if we do not have the right tool",
        "propose one",
        "best next step",
        "what's the best way to",
        "what is the best next step",
        "organize this",
        "what should i do",
        "how do i get started",
        "i want to turn this into",
    ]
    for phrase in broad_phrases:
        if phrase in lower:
            return REQUEST_BROAD

    # Specific outcome phrases (clear intent)
    specific_phrases = [
        "create project",
        "set up project",
        "new project structure",
        "design agent",
        "suggest agent",
        "run agent",
        "use agent",
        "ask agent",
    ]
    for phrase in specific_phrases:
        if phrase in lower:
            return REQUEST_SPECIFIC

    # Short, simple questions
    if len(lower.split()) <= 6 and "?" in message:
        return REQUEST_SIMPLE

    return REQUEST_AMBIGUOUS


def _get_available_tools() -> list[str]:
    """Return list of available tool intent names for orchestration context."""
    from gerty.llm.router import TOOL_INTENTS

    return list(TOOL_INTENTS)


def _get_available_agents() -> list[str]:
    """Return list of available agent names."""
    from gerty.agent_registry import list_agents

    agents = list_agents()
    return [a.get("name", "") for a in agents if a.get("name")]


def choose_action_path(message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Use LLM to choose the best action path for a user request.
    Returns structured result dict.
    """
    tools = _get_available_tools()
    agents = _get_available_agents()
    ctx = context or {}

    system = """You are an intent orchestrator. Given a user's high-level request, you decide the best internal path.

Available action paths:
- direct_answer: Answer directly (factual, opinion, explanation)
- use_tool: Use an existing Gerty tool (time, notes, search, rag, calendar, etc.)
- run_agent: Invoke an existing agent by name for a bounded task
- design_agent: Design or suggest a new agent (use agent designer)
- create_project_structure: Set up project/task structure (notes, folders)
- recommend_new_tool: Propose a new tool/capability we don't have
- escalate_to_maintenance: Log as maintenance task for later

Rules:
- Prefer existing tools and agents over creating new ones
- If the request is broad/ambiguous, set safe_to_execute_now=false and provide suggested_next_step
- If the request is simple and we have a clear match, set safe_to_execute_now=true
- NEVER recommend shell/code execution
- NEVER recommend recursive multi-agent chains
- For "help me explore X" or "research X", prefer run_agent (market_researcher, etc.) or design_agent if no match
- For "organize this" or "turn into project", prefer create_project_structure or design_agent
- For "if we don't have the right tool, propose one", use recommend_new_tool

Respond with valid JSON only:
{
  "request_type": "simple|broad|ambiguous|specific",
  "recommended_action": "direct_answer|use_tool|run_agent|design_agent|create_project_structure|recommend_new_tool|escalate_to_maintenance",
  "reasoning_summary": "1-2 sentence explanation",
  "tool_name": null or "tool_intent_name",
  "agent_name": null or "agent_name",
  "needs_new_agent": false,
  "needs_new_tool": false,
  "suggested_next_step": "What the user should do or what we'll do next",
  "safe_to_execute_now": true or false
}"""

    tools_str = ", ".join(tools[:40])  # Limit for prompt size
    agents_str = ", ".join(agents) if agents else "(none)"
    extra = ""
    if ctx.get("recent_agents"):
        extra += f"\nRecent agents mentioned: {ctx.get('recent_agents')}"
    if ctx.get("recent_topic"):
        extra += f"\nRecent topic: {ctx.get('recent_topic')}"

    prompt = f"""User request: "{message}"

Available tools (intent names): {tools_str}
Available agents: {agents_str}
{extra}

Return JSON only."""

    response = _call_llm(prompt, system)
    parsed = _parse_json_from_response(response)
    if not parsed:
        result = {**DEFAULT_RESULT}
        result["reasoning_summary"] = "Could not parse orchestrator response; defaulting to recommendation."
        result["suggested_next_step"] = "Rephrase your request or try a more specific command."
        return result

    result = {**DEFAULT_RESULT}
    for k, v in parsed.items():
        if k in result:
            if k == "safe_to_execute_now":
                result[k] = bool(v) if isinstance(v, bool) else str(v).lower() in ("true", "1", "yes")
            elif k in ("needs_new_agent", "needs_new_tool"):
                result[k] = bool(v) if isinstance(v, bool) else str(v).lower() in ("true", "1", "yes")
            elif k in ("tool_name", "agent_name") and v is not None:
                result[k] = str(v).strip() or None
            elif k in ("request_type", "recommended_action"):
                result[k] = str(v).strip() if v else result[k]
            elif k in ("reasoning_summary", "suggested_next_step"):
                result[k] = str(v).strip() if v else result[k]

    # Validate recommended_action
    if result["recommended_action"] not in ACTION_PATHS:
        result["recommended_action"] = ACTION_DIRECT_ANSWER

    return result


def build_execution_plan(message: str, action_result: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Build a step-by-step execution plan for a request.
    If action_result is provided, uses it; otherwise calls choose_action_path.
    """
    if action_result is None:
        action_result = choose_action_path(message)

    plan = {
        "steps": [],
        "summary": action_result.get("reasoning_summary", ""),
        "safe_to_execute_now": action_result.get("safe_to_execute_now", False),
    }

    action = action_result.get("recommended_action", ACTION_DIRECT_ANSWER)
    tool_name = action_result.get("tool_name")
    agent_name = action_result.get("agent_name")
    needs_new_agent = action_result.get("needs_new_agent", False)
    needs_new_tool = action_result.get("needs_new_tool", False)

    if action == ACTION_DIRECT_ANSWER:
        plan["steps"] = [{"action": "answer", "description": "Respond directly to the user"}]
    elif action == ACTION_USE_TOOL and tool_name:
        plan["steps"] = [{"action": "use_tool", "tool": tool_name, "description": f"Use {tool_name} tool"}]
    elif action == ACTION_RUN_AGENT and agent_name:
        plan["steps"] = [{"action": "run_agent", "agent": agent_name, "description": f"Invoke agent {agent_name}"}]
    elif action == ACTION_DESIGN_AGENT or needs_new_agent:
        plan["steps"] = [
            {"action": "design_agent", "description": "Design or suggest agent via agent designer"},
            {"action": "user_review", "description": "User reviews design before creation"},
        ]
    elif action == ACTION_CREATE_PROJECT_STRUCTURE:
        plan["steps"] = [
            {"action": "create_structure", "description": "Create project/task structure (notes, areas)"},
            {"action": "user_review", "description": "User confirms structure"},
        ]
    elif action == ACTION_RECOMMEND_NEW_TOOL or needs_new_tool:
        plan["steps"] = [
            {"action": "recommend_tool", "description": "Propose new tool/capability"},
            {"action": "user_review", "description": "User decides whether to implement"},
        ]
    elif action == ACTION_ESCALATE_TO_MAINTENANCE:
        plan["steps"] = [
            {"action": "maintenance", "description": "Log as maintenance task"},
            {"action": "user_review", "description": "User reviews maintenance backlog"},
        ]
    else:
        plan["steps"] = [
            {"action": "recommend", "description": action_result.get("suggested_next_step", "Provide recommendation")},
        ]

    return plan


def suggest_missing_capability(message: str) -> dict[str, Any]:
    """
    When the user asks for something we don't have, suggest a new capability.
    Returns: { "suggestion": str, "category": "tool|agent|workflow", "rationale": str }
    """
    system = """You suggest new capabilities when the user needs something we don't have.
Return JSON only:
{
  "suggestion": "Brief description of the proposed capability",
  "category": "tool|agent|workflow",
  "rationale": "Why this would help"
}"""

    prompt = f"""User said: "{message}"

They seem to need a capability we don't have. Suggest one new capability (tool, agent, or workflow).
Return JSON only."""

    response = _call_llm(prompt, system)
    parsed = _parse_json_from_response(response)
    if parsed and isinstance(parsed, dict):
        return {
            "suggestion": str(parsed.get("suggestion", "")).strip(),
            "category": str(parsed.get("category", "tool")).strip().lower(),
            "rationale": str(parsed.get("rationale", "")).strip(),
        }
    return {
        "suggestion": "A dedicated capability for this type of request",
        "category": "tool",
        "rationale": "The request suggests a gap in current capabilities.",
    }


def analyze_request(message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Full analysis: classify, choose path, build plan.
    Returns combined result for the orchestrator tool.
    """
    request_class = classify_outcome_request(message)
    action_result = choose_action_path(message, context)
    plan = build_execution_plan(message, action_result)

    return {
        "request_type": action_result.get("request_type", request_class),
        "recommended_action": action_result.get("recommended_action", ACTION_DIRECT_ANSWER),
        "reasoning_summary": action_result.get("reasoning_summary", ""),
        "tool_name": action_result.get("tool_name"),
        "agent_name": action_result.get("agent_name"),
        "needs_new_agent": action_result.get("needs_new_agent", False),
        "needs_new_tool": action_result.get("needs_new_tool", False),
        "suggested_next_step": action_result.get("suggested_next_step", ""),
        "safe_to_execute_now": action_result.get("safe_to_execute_now", False),
        "execution_plan": plan,
    }
