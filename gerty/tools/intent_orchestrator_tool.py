"""Intent Orchestrator Tool — route high-level outcome requests to the right capability."""

from __future__ import annotations

from typing import Callable

from gerty.agent_registry import agent_exists
from gerty.intent_orchestrator import (
    ACTION_DESIGN_AGENT,
    ACTION_DIRECT_ANSWER,
    ACTION_ESCALATE_TO_MAINTENANCE,
    ACTION_RECOMMEND_NEW_TOOL,
    ACTION_RUN_AGENT,
    ACTION_USE_TOOL,
    ACTION_CREATE_PROJECT_STRUCTURE,
    analyze_request,
    suggest_missing_capability,
)
from gerty.tools.base import Tool


class IntentOrchestratorTool(Tool):
    """
    Interpret natural-language outcome requests and choose the best path.
    v1: Prefer planning and recommendation; invoke only when simple and safe.
    """

    def __init__(self, tool_executor: Callable[[str, str], str] | None = None):
        """
        Args:
            tool_executor: Optional callback (intent, message) -> response.
                When provided and safe_to_execute_now, we can invoke the chosen path.
        """
        self._executor = tool_executor

    @property
    def name(self) -> str:
        return "intent_orchestrator"

    @property
    def description(self) -> str:
        return (
            "Interpret high-level outcome requests (help me explore, best next step, "
            "organize this, build whatever agent we need) and recommend or invoke the right path"
        )

    def execute(self, intent: str, message: str) -> str:
        result = analyze_request(message)

        recommended = result.get("recommended_action", ACTION_DIRECT_ANSWER)
        safe = result.get("safe_to_execute_now", False)
        tool_name = result.get("tool_name")
        agent_name = result.get("agent_name")
        needs_new_agent = result.get("needs_new_agent", False)
        needs_new_tool = result.get("needs_new_tool", False)

        # Build response header
        lines = [
            f"**Recommended path:** {recommended}",
            f"**Reasoning:** {result.get('reasoning_summary', '')}",
            "",
        ]

        # Optional direct invocation when safe and we have a clear path
        if safe and self._executor:
            if recommended == ACTION_RUN_AGENT and agent_name and agent_exists(agent_name):
                task = _extract_task_from_message(message)
                invoke_msg = f"ask agent {agent_name}: {task}"
                out = self._executor("agent_runner", invoke_msg)
                lines.append(f"*Invoked agent `{agent_name}`:*\n\n{out}")
                return "\n".join(lines)

            if recommended == ACTION_USE_TOOL and tool_name:
                out = self._executor(tool_name, message)
                lines.append(f"*Invoked `{tool_name}`:*\n\n{out}")
                return "\n".join(lines)

        # Otherwise: plan and recommendation
        if needs_new_tool or recommended == ACTION_RECOMMEND_NEW_TOOL:
            cap = suggest_missing_capability(message)
            lines.append(
                f"**Suggested capability:** {cap.get('suggestion', '')}\n"
                f"*Category:* {cap.get('category', 'tool')}\n"
                f"*Rationale:* {cap.get('rationale', '')}"
            )
            lines.append("")
        elif needs_new_agent or recommended == ACTION_DESIGN_AGENT:
            lines.append(
                "**Next step:** Use the agent designer: "
                f"*suggest agent for: {message[:80]}{'...' if len(message) > 80 else ''}*"
            )
            lines.append("")
        elif recommended == ACTION_CREATE_PROJECT_STRUCTURE:
            lines.append(
                "**Next step:** Add this to your projects or notes. "
                "Say *add project: <name>* or *add idea: <description>* to capture it."
            )
            lines.append("")
        elif recommended == ACTION_ESCALATE_TO_MAINTENANCE:
            lines.append(
                "**Next step:** Say *create incident: <description>* or *maintenance* to log this."
            )
            lines.append("")
        else:
            step = result.get("suggested_next_step", "")
            if step:
                lines.append(f"**Suggested next step:** {step}")
                lines.append("")

        plan = result.get("execution_plan", {})
        if plan.get("steps"):
            lines.append("**Execution plan:**")
            for i, s in enumerate(plan["steps"], 1):
                desc = s.get("description", str(s))
                lines.append(f"  {i}. {desc}")
            lines.append("")

        lines.append(
            "*Direct commands still work: `ask agent X: task`, `design agent: name - role`, "
            "`list agents`, `my goals`, etc.*"
        )
        return "\n".join(lines)


def _extract_task_from_message(message: str) -> str:
    """Extract task portion from user message for agent invocation."""
    # Remove common prefixes
    lower = message.lower()
    for prefix in (
        "help me explore ",
        "help me organize ",
        "help me ",
        "i want to ",
        "what's the best way to ",
        "what is the best next step for ",
        "best next step for ",
    ):
        if lower.startswith(prefix):
            return message[len(prefix) :].strip()
    return message.strip()
