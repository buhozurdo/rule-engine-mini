import inspect
import operator
from functools import lru_cache
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from .exceptions import (
    EvaluationRecursionError,
    OperatorNotFoundError,
    RuleEngineError,
    RuleValidationError,
)

_MISSING = object()


@lru_cache(maxsize=1024)
def _split_path(path: str) -> tuple:
    """Pre-splits and caches dot-separated property paths."""
    return tuple(path.split("."))


def _get_child(container: Any, key: str) -> Any:
    """Extract a key or numeric index from a container without raising exceptions."""
    if isinstance(container, (dict, Mapping)):
        return container[key] if key in container else _MISSING
    if isinstance(container, Sequence) and not isinstance(container, (str, bytes)):
        if key.isdigit():
            idx = int(key)
            if idx < len(container):
                return container[idx]
    return _MISSING


# C-level comparison dispatch table
_COMPARISON_OPS: Dict[str, Callable[[Any, Any], bool]] = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "===": operator.eq,
    "!=": operator.ne,
    "!==": operator.ne,
}

_MATH_OPS = {"+", "-", "*", "/", "%", "min", "max"}

_BUILTIN_OPS = {
    "var",
    "and",
    "or",
    "not",
    "!",
    "!!",
    "in",
    "if",
    *_COMPARISON_OPS.keys(),
    *_MATH_OPS,
}


class RuleEvaluator:
    """
    Deterministic AST Evaluator for JSON Logic rules in pure Python.
    Executes with zero eval() or exec(), sub-microsecond latency, and thread safety.
    """

    def __init__(self, max_depth: int = 50) -> None:
        """
        Initialize the rule evaluator.

        :param max_depth: Maximum allowed AST nesting depth to guard against
                          stack overflow or recursion-bomb attacks.
        """
        self.max_depth = max_depth
        self._custom_ops: Dict[str, Tuple[Callable[..., Any], int]] = {}

    def register_operator(self, name: str, handler: Callable[..., Any]) -> None:
        """
        Register a custom operator handler.

        The handler can accept (args), (args, context), or (args, context, evaluator).
        Example:
            evaluator.register_operator("between", lambda args, ctx, ev:
                ev.evaluate(args[1], ctx) <= ev.evaluate(args[0], ctx) <= ev.evaluate(args[2], ctx)
            )
        """
        try:
            sig = inspect.signature(handler)
            param_count = len(sig.parameters)
        except (ValueError, TypeError):
            param_count = 2
        self._custom_ops[name] = (handler, param_count)

    def resolve_var(self, path: str, context: Mapping[str, Any], default: Any = None) -> Any:
        """
        Safely resolve a dotted path (e.g. 'cart.items.0.price') within a context.
        Returns `default` if any segment is missing or index out of bounds.
        """
        if not path:
            return context

        current: Any = context
        for part in _split_path(path):
            current = _get_child(current, part)
            if current is _MISSING:
                return default

        return current

    def _eval_var(self, args: Any, context: Mapping[str, Any]) -> Any:
        if isinstance(args, str):
            return self.resolve_var(args, context, None)
        var_name = args[0] if isinstance(args, list) and args and isinstance(args[0], str) else ""
        default_val = args[1] if isinstance(args, list) and len(args) > 1 else None
        return self.resolve_var(var_name, context, default_val)

    def _eval_and(self, args: Any, context: Mapping[str, Any], depth: int) -> bool:
        if not isinstance(args, list):
            return bool(args)
        for arg in args:
            if not self.evaluate(arg, context, depth + 1):
                return False
        return True

    def _eval_or(self, args: Any, context: Mapping[str, Any], depth: int) -> bool:
        if not isinstance(args, list):
            return bool(args)
        for arg in args:
            if self.evaluate(arg, context, depth + 1):
                return True
        return False

    def _eval_not(self, op: str, args: Any, context: Mapping[str, Any], depth: int) -> bool:
        val = args[0] if isinstance(args, list) and args else args
        evaluated = self.evaluate(val, context, depth + 1)
        return bool(evaluated) if op == "!!" else not evaluated

    def _eval_cmp(self, op: str, args: Any, context: Mapping[str, Any], depth: int) -> bool:
        if not isinstance(args, list) or len(args) != 2:
            return False
        left = self.evaluate(args[0], context, depth + 1)
        right = self.evaluate(args[1], context, depth + 1)
        if op == "in":
            if right is None:
                return False
            try:
                return left in right
            except TypeError:
                return False
        cmp_fn = _COMPARISON_OPS[op]
        try:
            return bool(cmp_fn(left, right))
        except TypeError:
            return False

    def _eval_if(self, args: Any, context: Mapping[str, Any], depth: int) -> Any:
        if not isinstance(args, list) or not args:
            return None
        i = 0
        n = len(args)
        while i < n - 1:
            if self.evaluate(args[i], context, depth + 1):
                return self.evaluate(args[i + 1], context, depth + 1)
            i += 2
        if i < n:
            return self.evaluate(args[i], context, depth + 1)
        return None

    def _eval_add(self, args: Any, context: Mapping[str, Any], depth: int) -> Any:
        if not isinstance(args, list):
            return self.evaluate(args, context, depth + 1)
        if not args:
            return 0
        try:
            total = self.evaluate(args[0], context, depth + 1)
            for item in args[1:]:
                total += self.evaluate(item, context, depth + 1)
            return total
        except (TypeError, ValueError):
            return None

    def _eval_sub(self, args: Any, context: Mapping[str, Any], depth: int) -> Any:
        if not isinstance(args, list) or not args:
            val = self.evaluate(args, context, depth + 1)
            return -val if isinstance(val, (int, float)) else None
        if len(args) == 1:
            val = self.evaluate(args[0], context, depth + 1)
            return -val if isinstance(val, (int, float)) else None
        try:
            return self.evaluate(args[0], context, depth + 1) - self.evaluate(args[1], context, depth + 1)
        except (TypeError, ValueError):
            return None

    def _eval_mul(self, args: Any, context: Mapping[str, Any], depth: int) -> Any:
        if not isinstance(args, list) or not args:
            return None
        try:
            product = self.evaluate(args[0], context, depth + 1)
            for item in args[1:]:
                product *= self.evaluate(item, context, depth + 1)
            return product
        except (TypeError, ValueError):
            return None

    def _eval_div_mod(self, op: str, args: Any, context: Mapping[str, Any], depth: int) -> Any:
        if not isinstance(args, list) or len(args) != 2:
            return None
        try:
            left = self.evaluate(args[0], context, depth + 1)
            right = self.evaluate(args[1], context, depth + 1)
            return left / right if op == "/" else left % right
        except (ZeroDivisionError, TypeError, ValueError):
            return None

    def _eval_min_max(self, op: str, args: Any, context: Mapping[str, Any], depth: int) -> Any:
        if not isinstance(args, list) or not args:
            return None
        try:
            fn = min if op == "min" else max
            return fn([self.evaluate(a, context, depth + 1) for a in args])
        except (TypeError, ValueError):
            return None

    def _eval_math(self, op: str, args: Any, context: Mapping[str, Any], depth: int) -> Any:
        if op == "+":
            return self._eval_add(args, context, depth)
        if op == "-":
            return self._eval_sub(args, context, depth)
        if op == "*":
            return self._eval_mul(args, context, depth)
        if op in ("/", "%"):
            return self._eval_div_mod(op, args, context, depth)
        return self._eval_min_max(op, args, context, depth)

    def _eval_custom(self, op: str, args: Any, context: Mapping[str, Any]) -> Any:
        handler, param_count = self._custom_ops[op]
        try:
            if param_count == 1:
                return handler(args)
            if param_count >= 3:
                return handler(args, context, self)
            return handler(args, context)
        except Exception:
            return False

    def evaluate(self, node: Any, context: Mapping[str, Any], depth: int = 0) -> Any:
        """
        Evaluate an AST node against a runtime context dictionary.
        """
        # Primitives return themselves
        if not isinstance(node, dict):
            return node

        if not node:
            return True

        if depth > self.max_depth:
            raise EvaluationRecursionError(self.max_depth)

        op, args = next(iter(node.items()))

        if op == "var":
            return self._eval_var(args, context)
        if op == "and":
            return self._eval_and(args, context, depth)
        if op == "or":
            return self._eval_or(args, context, depth)
        if op in ("not", "!", "!!"):
            return self._eval_not(op, args, context, depth)
        if op in _COMPARISON_OPS or op == "in":
            return self._eval_cmp(op, args, context, depth)
        if op == "if":
            return self._eval_if(args, context, depth)
        if op in _MATH_OPS:
            return self._eval_math(op, args, context, depth)
        if self._custom_ops and op in self._custom_ops:
            return self._eval_custom(op, args, context)

        return False

    def _validate_arity(self, op: str, args: Any, path: str, node: Any) -> None:
        if op in _COMPARISON_OPS or op == "in" or op in ("/", "%"):
            if not isinstance(args, list) or len(args) != 2:
                raise RuleValidationError(
                    f"Operator '{op}' requires exactly 2 arguments", path=path, node=node
                )
        elif op in ("not", "!", "!!"):
            if isinstance(args, list) and len(args) > 1:
                raise RuleValidationError(
                    f"Operator '{op}' accepts at most 1 argument, got {len(args)}",
                    path=path,
                    node=node,
                )
        elif op == "if":
            if not isinstance(args, list) or len(args) < 2:
                raise RuleValidationError(
                    "Operator 'if' requires at least 2 arguments [condition, then, ...]",
                    path=path,
                    node=node,
                )
        elif op == "-":
            if isinstance(args, list) and len(args) > 2:
                raise RuleValidationError(
                    f"Operator '-' accepts at most 2 arguments, got {len(args)}",
                    path=path,
                    node=node,
                )
        elif op == "var":
            if isinstance(args, list) and len(args) > 2:
                raise RuleValidationError(
                    f"Operator 'var' accepts at most 2 arguments [path, default], got {len(args)}",
                    path=path,
                    node=node,
                )

    def _validate_operator(self, op: Any, args: Any, path: str, depth: int, node: Any) -> None:
        if not isinstance(op, str):
            raise RuleValidationError(
                f"Operator key must be a string, got {type(op).__name__}",
                path=path,
                node=node,
            )

        if op not in _BUILTIN_OPS and op not in self._custom_ops:
            raise OperatorNotFoundError(op, path=path, node=node)

        self._validate_arity(op, args, path, node)

        sub_path = f"{path}.{op}" if path != "$" else f"$.{op}"
        if isinstance(args, list):
            for i, arg in enumerate(args):
                self._validate_node(arg, f"{sub_path}[{i}]", depth + 1)
        elif isinstance(args, dict):
            self._validate_node(args, sub_path, depth + 1)

    def _validate_node(self, node: Any, path: str, depth: int) -> None:
        if depth > self.max_depth:
            raise EvaluationRecursionError(self.max_depth, path=path)

        if isinstance(node, list):
            for i, item in enumerate(node):
                self._validate_node(item, f"{path}[{i}]", depth + 1)
            return

        if not isinstance(node, dict):
            return

        if not node:
            return

        if len(node) > 1:
            keys = list(node.keys())
            raise RuleValidationError(
                f"Rule node must have exactly 1 operator key, found {len(node)}: {keys}",
                path=path,
                node=node,
            )

        op, args = next(iter(node.items()))
        self._validate_operator(op, args, path, depth, node)

    def validate(self, rule: Any, strict: bool = True) -> bool:
        """
        Validate an AST rule structure without executing it.

        :param rule: The rule AST node to validate.
        :param strict: If True, raises RuleValidationError or OperatorNotFoundError
                       on failure. If False, returns False on any structural error.
        :return: True if the rule AST is valid, False otherwise (when strict=False).
        :raises RuleValidationError: If the rule is structurally invalid and strict=True.
        :raises OperatorNotFoundError: If an unknown operator is referenced and strict=True.
        :raises EvaluationRecursionError: If recursion depth exceeds max_depth and strict=True.
        """
        try:
            self._validate_node(rule, path="$", depth=0)
            return True
        except RuleEngineError:
            if strict:
                raise
            return False
