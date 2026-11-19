"""
Structured exception hierarchy for rule-engine-mini.
"""

from typing import Any, Optional


class RuleEngineError(Exception):
    """Base exception for all errors raised by rule-engine-mini."""


class RuleValidationError(RuleEngineError):
    """Raised when an Abstract Syntax Tree (AST) does not conform to structural validation rules."""

    def __init__(self, message: str, path: str = "$", node: Any = None) -> None:
        full_msg = f"Invalid rule at '{path}': {message}" if path else message
        super().__init__(full_msg)
        self.message = message
        self.path = path
        self.node = node


class OperatorNotFoundError(RuleValidationError):
    """Raised when a rule AST references an unknown or unregistered operator."""

    def __init__(self, operator: str, path: str = "$", node: Any = None) -> None:
        super().__init__(f"Unknown operator '{operator}'", path=path, node=node)
        self.operator = operator


class EvaluationRecursionError(RuleEngineError, ValueError):
    """Raised when rule evaluation or validation exceeds the maximum recursion depth limit."""

    def __init__(self, max_depth: int, path: str = "$") -> None:
        full_msg = f"Rule evaluation exceeded maximum depth limit of {max_depth}"
        if path and path != "$":
            full_msg += f" at '{path}'"
        super().__init__(full_msg)
        self.max_depth = max_depth
        self.path = path
