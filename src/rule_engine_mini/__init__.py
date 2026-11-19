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

__version__ = "0.3.0"
__all__ = [
    "RuleEvaluator",
    "RuleEngineError",
    "RuleValidationError",
    "OperatorNotFoundError",
    "EvaluationRecursionError",
]
