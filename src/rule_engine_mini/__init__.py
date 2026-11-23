"""
rule-engine-mini — Pure Python safe AST rule engine.
"""

from .evaluator import RuleEvaluator
from .exceptions import (
    EvaluationRecursionError,
    OperatorNotFoundError,
    RuleEngineError,
    RuleValidationError,
)
from .trace import ExecutionTrace, TraceStep

__version__ = "0.5.0"
__all__ = [
    "RuleEvaluator",
    "RuleEngineError",
    "RuleValidationError",
    "OperatorNotFoundError",
    "EvaluationRecursionError",
    "ExecutionTrace",
    "TraceStep",
]
