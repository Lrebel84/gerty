"""Calculator tool: basic arithmetic and percentages."""

import ast
import operator
import re

from gerty.tools.base import Tool
from gerty.utils.math_extract import extract_math

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


class CalculatorTool(Tool):
    """Basic calculator: arithmetic, percentages."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Basic arithmetic and percentages"

    def execute(self, intent: str, message: str) -> str:
        expr = extract_math(message)
        if not expr:
            return "I couldn't find a math expression. Try: what is 15% of 80"
        result = _safe_eval(expr)
        if result is None:
            return "I couldn't evaluate that. Try something like: 2 + 2 or 15% of 80"
        if result == int(result):
            return str(int(result))
        return f"{result:.6g}"
