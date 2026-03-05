"""Calculator tool: basic arithmetic and percentages."""

import ast
import operator
import re

from gerty.tools.base import Tool

# Safe operations for calculator
OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _safe_eval(expr: str) -> float | None:
    """Evaluate a safe math expression. Only numbers and + - * / ** % allowed."""
    try:
        tree = ast.parse(expr.strip(), mode="eval")
        return _eval_node(tree.body)
    except (SyntaxError, ValueError, ZeroDivisionError):
        return None


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand)
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        op = OPS.get(type(node.op))
        if op is None:
            raise ValueError("Unsupported operator")
        return op(left, right)
    raise ValueError("Unsupported expression")


def _extract_math(message: str) -> str | None:
    """Extract a math expression from natural language."""
    lower = message.lower()
    # "15% of 80" -> 0.15 * 80
    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:of|off)\s*(\d+(?:\.\d+)?)", lower)
    if m:
        pct, val = float(m.group(1)), float(m.group(2))
        return f"{pct / 100} * {val}"

    # "what is X" or "calculate X" or "X plus Y"
    for prefix in ("what is", "what's", "calculate", "compute", "evaluate", "="):
        if prefix in lower:
            idx = lower.rfind(prefix) + len(prefix)
            rest = message[idx:].strip()
            # Replace words with operators
            rest = re.sub(r"\bplus\b", "+", rest, flags=re.I)
            rest = re.sub(r"\bminus\b", "-", rest, flags=re.I)
            rest = re.sub(r"\btimes\b", "*", rest, flags=re.I)
            rest = re.sub(r"\bdivided by\b", "/", rest, flags=re.I)
            rest = re.sub(r"\bpercent\b", "/ 100", rest, flags=re.I)
            rest = re.sub(r"\bsquared\b", "** 2", rest, flags=re.I)
            rest = re.sub(r"\bcubed\b", "** 3", rest, flags=re.I)
            # Only allow safe chars
            if re.match(r"^[\d\s\+\-\*\/\.\*\*\(\)\%]+$", rest.replace(" ", "")):
                return rest

    # Bare expression: "2 + 2" or "sqrt(144)" - skip sqrt for simplicity
    nums = re.findall(r"[\d\.]+", message)
    ops = re.findall(r"[+\-*/]", message)
    if nums and (ops or len(nums) == 1):
        return message.strip()

    return None


class CalculatorTool(Tool):
    """Basic calculator: arithmetic, percentages."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Basic arithmetic and percentages"

    def execute(self, intent: str, message: str) -> str:
        expr = _extract_math(message)
        if not expr:
            return "I couldn't find a math expression. Try: what is 15% of 80"
        result = _safe_eval(expr)
        if result is None:
            return "I couldn't evaluate that. Try something like: 2 + 2 or 15% of 80"
        if result == int(result):
            return str(int(result))
        return f"{result:.6g}"
