"""Tests for Intent Orchestrator (System 4)."""

import json
from unittest.mock import patch

import pytest

from gerty.intent_orchestrator import (
    ACTION_DESIGN_AGENT,
    ACTION_DIRECT_ANSWER,
    ACTION_RECOMMEND_NEW_TOOL,
    ACTION_RUN_AGENT,
    ACTION_USE_TOOL,
    REQUEST_AMBIGUOUS,
    REQUEST_BROAD,
    REQUEST_SIMPLE,
    REQUEST_SPECIFIC,
    analyze_request,
    build_execution_plan,
    choose_action_path,
    classify_outcome_request,
    suggest_missing_capability,
)
from gerty.tools.intent_orchestrator_tool import (
    IntentOrchestratorTool,
    _extract_task_from_message,
)


class TestClassifyOutcomeRequest:
    def test_broad_phrases(self):
        assert classify_outcome_request("help me explore tattoo AI ideas") == REQUEST_BROAD
        assert classify_outcome_request("help me organize this business idea") == REQUEST_BROAD
        assert classify_outcome_request("turn this into a real project") == REQUEST_BROAD
        assert classify_outcome_request("build whatever agent we need") == REQUEST_BROAD
        assert classify_outcome_request("if we don't have the right tool, propose one") == REQUEST_BROAD
        assert classify_outcome_request("best next step for this goal") == REQUEST_BROAD
        assert classify_outcome_request("what's the best way to get started") == REQUEST_BROAD
        assert classify_outcome_request("what should i do next") == REQUEST_BROAD

    def test_specific_phrases(self):
        assert classify_outcome_request("create project structure") == REQUEST_SPECIFIC
        assert classify_outcome_request("design agent for research") == REQUEST_SPECIFIC
        assert classify_outcome_request("run agent market_researcher") == REQUEST_SPECIFIC

    def test_ambiguous(self):
        assert classify_outcome_request("") == REQUEST_AMBIGUOUS
        assert classify_outcome_request("   ") == REQUEST_AMBIGUOUS

    def test_simple_short_question(self):
        # Short questions with ? may be REQUEST_SIMPLE
        result = classify_outcome_request("what time?")
        assert result in (REQUEST_SIMPLE, REQUEST_AMBIGUOUS)


class TestChooseActionPath:
    def test_returns_structured_result(self):
        mock_response = json.dumps({
            "request_type": "broad",
            "recommended_action": ACTION_RUN_AGENT,
            "reasoning_summary": "User wants to explore; market_researcher exists.",
            "tool_name": None,
            "agent_name": "market_researcher",
            "needs_new_agent": False,
            "needs_new_tool": False,
            "suggested_next_step": "Invoke market_researcher",
            "safe_to_execute_now": True,
        })
        with patch("gerty.intent_orchestrator._call_llm", return_value=mock_response):
            result = choose_action_path("help me explore tattoo AI ideas")
        assert result["recommended_action"] == ACTION_RUN_AGENT
        assert result["agent_name"] == "market_researcher"
        assert result["safe_to_execute_now"] is True
        assert result["reasoning_summary"]

    def test_invalid_json_fallback(self):
        with patch("gerty.intent_orchestrator._call_llm", return_value="not json"):
            result = choose_action_path("help me explore X")
        assert result["recommended_action"] == ACTION_DIRECT_ANSWER
        assert result["safe_to_execute_now"] is False
        assert "Could not parse" in result.get("reasoning_summary", "")

    def test_invalid_action_fallback(self):
        mock_response = json.dumps({
            "recommended_action": "invalid_action",
            "reasoning_summary": "x",
            "safe_to_execute_now": False,
        })
        with patch("gerty.intent_orchestrator._call_llm", return_value=mock_response):
            result = choose_action_path("something")
        assert result["recommended_action"] == ACTION_DIRECT_ANSWER


class TestBuildExecutionPlan:
    def test_direct_answer_plan(self):
        action_result = {
            "recommended_action": ACTION_DIRECT_ANSWER,
            "reasoning_summary": "Simple question",
            "safe_to_execute_now": True,
        }
        plan = build_execution_plan("what is X?", action_result)
        assert plan["steps"]
        descs = [s.get("description", "") for s in plan["steps"]]
        assert any("answer" in d.lower() or "direct" in d.lower() or "respond" in d.lower() for d in descs)

    def test_run_agent_plan(self):
        action_result = {
            "recommended_action": ACTION_RUN_AGENT,
            "agent_name": "market_researcher",
            "reasoning_summary": "x",
            "safe_to_execute_now": True,
        }
        plan = build_execution_plan("explore tattoo AI", action_result)
        assert plan["steps"]
        steps_str = " ".join(str(s) for s in plan["steps"])
        assert "agent" in steps_str.lower()

    def test_design_agent_plan(self):
        action_result = {
            "recommended_action": ACTION_DESIGN_AGENT,
            "needs_new_agent": True,
            "reasoning_summary": "x",
            "safe_to_execute_now": False,
        }
        plan = build_execution_plan("build whatever agent we need", action_result)
        assert len(plan["steps"]) >= 2

    def test_recommend_new_tool_plan(self):
        action_result = {
            "recommended_action": ACTION_RECOMMEND_NEW_TOOL,
            "needs_new_tool": True,
            "reasoning_summary": "x",
            "safe_to_execute_now": False,
        }
        plan = build_execution_plan("if we don't have the right tool, propose one", action_result)
        assert plan["steps"]


class TestSuggestMissingCapability:
    def test_returns_structured_suggestion(self):
        mock_response = json.dumps({
            "suggestion": "A market research tool",
            "category": "tool",
            "rationale": "Would help explore business ideas",
        })
        with patch("gerty.intent_orchestrator._call_llm", return_value=mock_response):
            result = suggest_missing_capability("help me explore tattoo AI ideas")
        assert result["suggestion"]
        assert result["category"] in ("tool", "agent", "workflow")
        assert result["rationale"]

    def test_bad_response_fallback(self):
        with patch("gerty.intent_orchestrator._call_llm", return_value="garbage"):
            result = suggest_missing_capability("something")
        assert "suggestion" in result
        assert "category" in result
        assert "rationale" in result


class TestAnalyzeRequest:
    def test_returns_combined_result(self):
        mock_response = json.dumps({
            "request_type": "broad",
            "recommended_action": ACTION_USE_TOOL,
            "reasoning_summary": "Use search",
            "tool_name": "search",
            "agent_name": None,
            "needs_new_agent": False,
            "needs_new_tool": False,
            "suggested_next_step": "Search for it",
            "safe_to_execute_now": False,
        })
        with patch("gerty.intent_orchestrator._call_llm", return_value=mock_response):
            result = analyze_request("help me explore tattoo AI")
        assert "request_type" in result
        assert "recommended_action" in result
        assert "execution_plan" in result
        assert "reasoning_summary" in result


class TestIntentOrchestratorTool:
    def test_execute_returns_plan_when_no_executor(self):
        tool = IntentOrchestratorTool(tool_executor=None)
        with patch("gerty.intent_orchestrator._call_llm", return_value=json.dumps({
            "request_type": "broad",
            "recommended_action": ACTION_DESIGN_AGENT,
            "reasoning_summary": "Design an agent",
            "tool_name": None,
            "agent_name": None,
            "needs_new_agent": True,
            "needs_new_tool": False,
            "suggested_next_step": "Suggest agent",
            "safe_to_execute_now": False,
        })):
            out = tool.execute("intent_orchestrator", "help me explore tattoo AI")
        assert "Recommended path" in out
        assert "Reasoning" in out
        assert "Execution plan" in out or "suggest agent" in out.lower()

    def test_extract_task_from_message(self):
        assert _extract_task_from_message("help me explore tattoo AI ideas") == "tattoo AI ideas"
        assert _extract_task_from_message("help me organize this business idea") == "this business idea"
        assert _extract_task_from_message("I want to research market gaps") == "research market gaps"
        assert _extract_task_from_message("random message") == "random message"


class TestSafeRecommendationBehavior:
    """Orchestrator should prefer plans over auto-execution for broad requests."""

    def test_broad_request_safe_to_execute_false_by_default(self):
        mock_response = json.dumps({
            "request_type": "broad",
            "recommended_action": ACTION_DESIGN_AGENT,
            "reasoning_summary": "Broad request",
            "tool_name": None,
            "agent_name": None,
            "needs_new_agent": True,
            "needs_new_tool": False,
            "suggested_next_step": "Design first",
            "safe_to_execute_now": False,
        })
        with patch("gerty.intent_orchestrator._call_llm", return_value=mock_response):
            result = choose_action_path("help me explore tattoo AI business ideas")
        assert result["safe_to_execute_now"] is False
        assert result["needs_new_agent"] is True


class TestRoutingPrecedence:
    """Direct commands must still win over orchestrator keywords."""

    def test_direct_commands_win_via_router(self):
        from gerty.llm.router import classify_intent

        # "list agents" has "agent" but should match agent_factory, not orchestrator
        assert classify_intent("list agents") == "agent_factory"
        # "design agent" matches agent_designer first
        assert classify_intent("design agent: x - y") == "agent_designer"
        # "ask agent X: task" matches agent_runner
        assert classify_intent("ask agent market_researcher: summarize") == "agent_runner"
        # "help me explore" has no direct command match → orchestrator
        assert classify_intent("help me explore tattoo AI ideas") == "intent_orchestrator"
        # "best next step" → orchestrator
        assert classify_intent("what is the best next step for this goal") == "intent_orchestrator"
