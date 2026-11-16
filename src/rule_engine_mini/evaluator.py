import operator
from functools import lru_cache
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Union


@lru_cache(maxsize=1024)
def _split_path(path: str) -> tuple:
    """Pre-splits and caches dot-separated property paths."""
    return tuple(path.split("."))


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
        self._custom_ops: Dict[str, Callable[..., Any]] = {}

    def register_operator(self, name: str, handler: Callable[..., Any]) -> None:
        """
        Register a custom operator handler.

        The handler can accept (args, context) or (args, context, evaluator).
        Example:
            evaluator.register_operator("between", lambda args, ctx, ev:
                ev.evaluate(args[1], ctx) <= ev.evaluate(args[0], ctx) <= ev.evaluate(args[2], ctx)
            )
        """
        import inspect
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

        # Fast path for flat dictionaries (single key without dots)
        if "." not in path:
            if isinstance(context, dict):
                return context.get(path, default)
            if isinstance(context, Mapping) and path in context:
                return context[path]
            return default

        current: Any = context
        for part in _split_path(path):
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                    continue
                return default
            elif isinstance(current, Mapping):
                if part in current:
                    current = current[part]
                    continue
                return default
            elif isinstance(current, Sequence) and not isinstance(current, (str, bytes)):
                if part.isdigit():
                    idx = int(part)
                    if idx < len(current):
                        current = current[idx]
                        continue
                return default
            else:
                return default

        return current

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
            raise ValueError(f"Rule evaluation exceeded maximum depth limit of {self.max_depth}")

        op, args = next(iter(node.items()))

        # Variable resolution
        if op == "var":
            if isinstance(args, str):
                var_name = args
                default_val = None
            elif isinstance(args, list) and args:
                var_name = args[0] if isinstance(args[0], str) else ""
                default_val = args[1] if len(args) > 1 else None
            else:
                var_name = ""
                default_val = None
            return self.resolve_var(var_name, context, default_val)

        # Boolean logic (loop with early exit for maximum speed without generator overhead)
        if op == "and":
            if not isinstance(args, list):
                return bool(args)
            for arg in args:
                if not self.evaluate(arg, context, depth + 1):
                    return False
            return True

        if op == "or":
            if not isinstance(args, list):
                return bool(args)
            for arg in args:
                if self.evaluate(arg, context, depth + 1):
                    return True
            return False

        if op in ("not", "!"):
            val = args[0] if isinstance(args, list) and args else args
            return not self.evaluate(val, context, depth + 1)

        if op == "!!":
            val = args[0] if isinstance(args, list) and args else args
            return bool(self.evaluate(val, context, depth + 1))

        # Comparisons using C-level operator table
        cmp_fn = _COMPARISON_OPS.get(op)
        if cmp_fn is not None:
            if not isinstance(args, list) or len(args) != 2:
                return False
            left = self.evaluate(args[0], context, depth + 1)
            right = self.evaluate(args[1], context, depth + 1)
            try:
                return bool(cmp_fn(left, right))
            except TypeError:
                return False

        # Membership check ('in')
        if op == "in":
            if not isinstance(args, list) or len(args) != 2:
                return False
            left = self.evaluate(args[0], context, depth + 1)
            right = self.evaluate(args[1], context, depth + 1)
            if right is None:
                return False
            try:
                return left in right
            except TypeError:
                return False

        # Conditional 'if' (lazy evaluation: only the chosen branch is evaluated)
        if op == "if":
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

        # Arithmetic operations
        if op == "+":
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

        if op == "-":
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

        if op == "*":
            if not isinstance(args, list) or not args:
                return None
            try:
                product = self.evaluate(args[0], context, depth + 1)
                for item in args[1:]:
                    product *= self.evaluate(item, context, depth + 1)
                return product
            except (TypeError, ValueError):
                return None

        if op == "/":
            if not isinstance(args, list) or len(args) != 2:
                return None
            try:
                return self.evaluate(args[0], context, depth + 1) / self.evaluate(args[1], context, depth + 1)
            except (ZeroDivisionError, TypeError, ValueError):
                return None

        if op == "%":
            if not isinstance(args, list) or len(args) != 2:
                return None
            try:
                return self.evaluate(args[0], context, depth + 1) % self.evaluate(args[1], context, depth + 1)
            except (ZeroDivisionError, TypeError, ValueError):
                return None

        if op in ("min", "max"):
            if not isinstance(args, list) or not args:
                return None
            try:
                fn = min if op == "min" else max
                eval_args = [self.evaluate(a, context, depth + 1) for a in args]
                return fn(eval_args)
            except (TypeError, ValueError):
                return None

        # Custom operators
        if self._custom_ops and op in self._custom_ops:
            handler, param_count = self._custom_ops[op]
            try:
                if param_count == 1:
                    return handler(args)
                elif param_count >= 3:
                    return handler(args, context, self)
                return handler(args, context)
            except Exception:
                return False

        return False
