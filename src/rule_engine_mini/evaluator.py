import inspect
import operator
import time
from functools import lru_cache
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from .exceptions import (
    EvaluationRecursionError,
    OperatorNotFoundError,
    RuleEngineError,
    RuleValidationError,
)
from .trace import ExecutionTrace, TraceStep

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
_LOGICAL_OPS = {"and", "or", "not", "!", "!!", "if"}
_COLLECTION_OPS = {"some", "all", "none", "filter", "map"}
_STRING_OPS = {"cat", "substr"}
_AGG_OPS = {"merge", "missing", "missing_some"}

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
    *_COLLECTION_OPS,
    *_STRING_OPS,
    *_AGG_OPS,
}

_EXACT_2_OPS = set(_COMPARISON_OPS.keys()) | {"in", "/", "%"} | _COLLECTION_OPS | {"missing_some"}
_MAX_1_OPS = {"not", "!", "!!"}
_MAX_2_OPS = {"-", "var"}


def _check_fixed_arity(op: str, is_list: bool, count: int) -> Optional[str]:
    if op in _EXACT_2_OPS:
        if not is_list or count != 2:
            return f"Operator '{op}' requires exactly 2 arguments"
    if op in _MAX_1_OPS and is_list and count > 1:
        return f"Operator '{op}' accepts at most 1 argument, got {count}"
    if op in _MAX_2_OPS and is_list and count > 2:
        return f"Operator '{op}' accepts at most 2 arguments, got {count}"
    return None


def _check_special_arity(op: str, is_list: bool, count: int) -> Optional[str]:
    if op == "if":
        if not is_list or count < 2:
            return "Operator 'if' requires at least 2 arguments [condition, then, ...]"
    if op == "substr":
        if not is_list or not (2 <= count <= 3):
            return "Operator 'substr' requires 2 or 3 arguments [string, start, optional_length]"
    return None


def _check_arity_bounds(op: str, args: Any) -> Optional[str]:
    is_list = isinstance(args, list)
    count = len(args) if is_list else 1
    return _check_fixed_arity(op, is_list, count) or _check_special_arity(op, is_list, count)


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

    def resolve_var(self, path: str, context: Any, default: Any = None) -> Any:
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

    def _eval_var(self, args: Any, context: Any) -> Any:
        if isinstance(args, str):
            return self.resolve_var(args, context, None)
        var_name = args[0] if isinstance(args, list) and args and isinstance(args[0], str) else ""
        default_val = args[1] if isinstance(args, list) and len(args) > 1 else None
        return self.resolve_var(var_name, context, default_val)

    def _eval_and(self, args: Any, context: Any, depth: int) -> bool:
        if not isinstance(args, list):
            return bool(args)
        for arg in args:
            if not self.evaluate(arg, context, depth + 1):
                return False
        return True

    def _eval_or(self, args: Any, context: Any, depth: int) -> bool:
        if not isinstance(args, list):
            return bool(args)
        for arg in args:
            if self.evaluate(arg, context, depth + 1):
                return True
        return False

    def _eval_not(self, op: str, args: Any, context: Any, depth: int) -> bool:
        val = args[0] if isinstance(args, list) and args else args
        evaluated = self.evaluate(val, context, depth + 1)
        return bool(evaluated) if op == "!!" else not evaluated

    def _eval_cmp(self, op: str, args: Any, context: Any, depth: int) -> bool:
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

    def _eval_if(self, args: Any, context: Any, depth: int) -> Any:
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

    def _eval_add(self, args: Any, context: Any, depth: int) -> Any:
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

    def _eval_sub(self, args: Any, context: Any, depth: int) -> Any:
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

    def _eval_mul(self, args: Any, context: Any, depth: int) -> Any:
        if not isinstance(args, list) or not args:
            return None
        try:
            product = self.evaluate(args[0], context, depth + 1)
            for item in args[1:]:
                product *= self.evaluate(item, context, depth + 1)
            return product
        except (TypeError, ValueError):
            return None

    def _eval_div_mod(self, op: str, args: Any, context: Any, depth: int) -> Any:
        if not isinstance(args, list) or len(args) != 2:
            return None
        try:
            left = self.evaluate(args[0], context, depth + 1)
            right = self.evaluate(args[1], context, depth + 1)
            return left / right if op == "/" else left % right
        except (ZeroDivisionError, TypeError, ValueError):
            return None

    def _eval_min_max(self, op: str, args: Any, context: Any, depth: int) -> Any:
        if not isinstance(args, list) or not args:
            return None
        try:
            fn = min if op == "min" else max
            return fn([self.evaluate(a, context, depth + 1) for a in args])
        except (TypeError, ValueError):
            return None

    def _eval_math(self, op: str, args: Any, context: Any, depth: int) -> Any:
        if op == "+":
            return self._eval_add(args, context, depth)
        if op == "-":
            return self._eval_sub(args, context, depth)
        if op == "*":
            return self._eval_mul(args, context, depth)
        if op in ("/", "%"):
            return self._eval_div_mod(op, args, context, depth)
        return self._eval_min_max(op, args, context, depth)

    def _eval_quantifier(self, op: str, items: list, predicate: Any, depth: int) -> bool:
        if op == "some":
            return any(bool(self.evaluate(predicate, item, depth + 1)) for item in items)
        if not items:
            return False if op == "all" else True
        if op == "all":
            return all(bool(self.evaluate(predicate, item, depth + 1)) for item in items)
        return not any(bool(self.evaluate(predicate, item, depth + 1)) for item in items)

    def _eval_projection(self, op: str, items: list, rule: Any, depth: int) -> list:
        if op == "filter":
            return [it for it in items if self.evaluate(rule, it, depth + 1)]
        return [self.evaluate(rule, it, depth + 1) for it in items]

    def _eval_collection(self, op: str, args: Any, context: Any, depth: int) -> Any:
        if not isinstance(args, list) or len(args) != 2:
            return False if op in ("some", "all") else ([] if op in ("filter", "map") else True)

        raw_items = self.evaluate(args[0], context, depth + 1)
        if not isinstance(raw_items, list):
            return False if op in ("some", "all") else ([] if op in ("filter", "map") else True)

        if op in ("some", "all", "none"):
            return self._eval_quantifier(op, raw_items, args[1], depth)
        return self._eval_projection(op, raw_items, args[1], depth)

    def _append_merge_item(self, item: Any, res: list, context: Any, depth: int) -> None:
        if isinstance(item, list):
            for sub in item:
                res.append(self.evaluate(sub, context, depth + 1))
        else:
            evaluated = self.evaluate(item, context, depth + 1)
            if isinstance(evaluated, list):
                res.extend(evaluated)
            else:
                res.append(evaluated)

    def _eval_merge(self, args: Any, context: Any, depth: int) -> list:
        if not isinstance(args, list):
            val = self.evaluate(args, context, depth + 1)
            return val if isinstance(val, list) else [val]
        res = []
        for item in args:
            self._append_merge_item(item, res, context, depth)
        return res

    def _eval_cat(self, args: Any, context: Any, depth: int) -> str:
        if not isinstance(args, list):
            val = self.evaluate(args, context, depth + 1)
            return "" if val is None else str(val)
        parts = []
        for item in args:
            val = self.evaluate(item, context, depth + 1)
            parts.append("" if val is None else str(val))
        return "".join(parts)

    def _eval_substr(self, args: Any, context: Any, depth: int) -> str:
        if not isinstance(args, list) or len(args) < 2:
            return ""
        val = self.evaluate(args[0], context, depth + 1)
        if val is None:
            return ""
        text = str(val)
        try:
            start = int(self.evaluate(args[1], context, depth + 1))
        except (ValueError, TypeError):
            start = 0

        if len(args) >= 3:
            try:
                length = int(self.evaluate(args[2], context, depth + 1))
                end = len(text) + length if length < 0 else start + length
                return text[start:end]
            except (ValueError, TypeError):
                pass
        return text[start:]

    def _eval_string(self, op: str, args: Any, context: Any, depth: int) -> Any:
        if op == "cat":
            return self._eval_cat(args, context, depth)
        return self._eval_substr(args, context, depth)

    def _eval_missing(self, args: Any, context: Any) -> list:
        keys = args if isinstance(args, list) else [args]
        missing = []
        for k in keys:
            if isinstance(k, str) and self.resolve_var(k, context, _MISSING) is _MISSING:
                missing.append(k)
        return missing

    def _eval_missing_some(self, args: Any, context: Any) -> list:
        if not isinstance(args, list) or len(args) != 2:
            return []
        try:
            min_count = int(args[0])
        except (ValueError, TypeError):
            return []
        keys = args[1] if isinstance(args[1], list) else [args[1]]
        missing = [k for k in keys if isinstance(k, str) and self.resolve_var(k, context, _MISSING) is _MISSING]
        present_count = len(keys) - len(missing)
        return missing if present_count < min_count else []

    def _eval_custom(self, op: str, args: Any, context: Any) -> Any:
        handler, param_count = self._custom_ops[op]
        try:
            if param_count == 1:
                return handler(args)
            if param_count >= 3:
                return handler(args, context, self)
            return handler(args, context)
        except Exception:
            return False

    def _eval_extended(self, op: str, args: Any, context: Any, depth: int) -> Any:
        if op in _COLLECTION_OPS:
            return self._eval_collection(op, args, context, depth)
        if op in _STRING_OPS:
            return self._eval_string(op, args, context, depth)
        if op == "merge":
            return self._eval_merge(args, context, depth)
        if op == "missing":
            return self._eval_missing(args, context)
        if op == "missing_some":
            return self._eval_missing_some(args, context)
        if self._custom_ops and op in self._custom_ops:
            return self._eval_custom(op, args, context)
        return False

    def _eval_logical(self, op: str, args: Any, context: Any, depth: int) -> Any:
        if op == "and":
            return self._eval_and(args, context, depth)
        if op == "or":
            return self._eval_or(args, context, depth)
        if op in ("not", "!", "!!"):
            return self._eval_not(op, args, context, depth)
        return self._eval_if(args, context, depth)

    def evaluate(self, node: Any, context: Any, depth: int = 0) -> Any:
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
        if op in _LOGICAL_OPS:
            return self._eval_logical(op, args, context, depth)
        if op in _COMPARISON_OPS or op == "in":
            return self._eval_cmp(op, args, context, depth)
        if op in _MATH_OPS:
            return self._eval_math(op, args, context, depth)

        return self._eval_extended(op, args, context, depth)

    def _validate_arity(self, op: str, args: Any, path: str, node: Any) -> None:
        err = _check_arity_bounds(op, args)
        if err:
            raise RuleValidationError(err, path=path, node=node)

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

    def _find_failed_leaf(self, step: TraceStep) -> TraceStep:
        if not step.children or not isinstance(step.node, dict):
            return step
        op = next(iter(step.node.keys())) if step.node else ""
        if op in ("and", "or"):
            for child in step.children:
                if not bool(child.result):
                    return self._find_failed_leaf(child)
        return step

    def _trace_logic(
        self,
        op: str,
        items: list,
        context: Any,
        path: str,
        depth: int,
        resolved_vars: Dict[str, Any],
    ) -> Tuple[bool, bool, List[TraceStep]]:
        children: List[TraceStep] = []
        target_val = True if op == "or" else False
        short_circuited = False

        for i, child_node in enumerate(items):
            child_step = self._trace_evaluate(child_node, context, f"{path}.{op}[{i}]", depth + 1, resolved_vars)
            children.append(child_step)
            if bool(child_step.result) == target_val:
                short_circuited = i < len(items) - 1
                return target_val, short_circuited, children

        return not target_val, short_circuited, children

    def _trace_children(
        self, op: str, args: Any, context: Any, path: str, depth: int, resolved_vars: Dict[str, Any]
    ) -> List[TraceStep]:
        children: List[TraceStep] = []
        if isinstance(args, list):
            for i, arg in enumerate(args):
                if isinstance(arg, dict):
                    children.append(self._trace_evaluate(arg, context, f"{path}.{op}[{i}]", depth + 1, resolved_vars))
        elif isinstance(args, dict):
            children.append(self._trace_evaluate(args, context, f"{path}.{op}", depth + 1, resolved_vars))
        return children

    def _trace_evaluate(
        self,
        node: Any,
        context: Any,
        path: str,
        depth: int,
        resolved_vars: Dict[str, Any],
    ) -> TraceStep:
        t0 = time.perf_counter_ns()
        if not isinstance(node, dict):
            elapsed = (time.perf_counter_ns() - t0) / 1000.0
            return TraceStep(path=path, node=node, result=node, elapsed_us=elapsed)

        if not node:
            elapsed = (time.perf_counter_ns() - t0) / 1000.0
            return TraceStep(path=path, node=node, result=True, elapsed_us=elapsed)

        if depth > self.max_depth:
            raise EvaluationRecursionError(self.max_depth, path=path)

        op, args = next(iter(node.items()))

        if op == "var":
            var_name = args if isinstance(args, str) else (args[0] if isinstance(args, list) and args else "")
            val = self.evaluate(node, context, depth)
            resolved_vars[str(var_name)] = val
            elapsed = (time.perf_counter_ns() - t0) / 1000.0
            return TraceStep(path=path, node=node, result=val, elapsed_us=elapsed)

        if op in ("and", "or"):
            items = args if isinstance(args, list) else [args]
            final_res, sc, children = self._trace_logic(op, items, context, path, depth, resolved_vars)
            elapsed = (time.perf_counter_ns() - t0) / 1000.0
            return TraceStep(path=path, node=node, result=final_res, elapsed_us=elapsed, short_circuited=sc, children=children)

        children = self._trace_children(op, args, context, path, depth, resolved_vars)
        res = self.evaluate(node, context, depth)
        elapsed = (time.perf_counter_ns() - t0) / 1000.0
        return TraceStep(path=path, node=node, result=res, elapsed_us=elapsed, children=children)

    def explain(self, rule: Any, context: Any) -> ExecutionTrace:
        """
        Execute an AST rule and generate a detailed forensic ExecutionTrace.

        Records node-level results, variable resolutions, evaluation timings in microseconds,
        and identifies the exact sub-clause responsible for a failure.
        """
        resolved_vars: Dict[str, Any] = {}
        t0 = time.perf_counter_ns()
        root_step = self._trace_evaluate(rule, context, "$", 0, resolved_vars)
        total_elapsed_us = (time.perf_counter_ns() - t0) / 1000.0

        passed = bool(root_step.result)
        failed_path = None
        failed_node = None

        if not passed:
            failed_step = self._find_failed_leaf(root_step)
            failed_path = failed_step.path
            failed_node = failed_step.node

        return ExecutionTrace(
            result=root_step.result,
            passed=passed,
            elapsed_us=total_elapsed_us,
            resolved_vars=resolved_vars,
            failed_node=failed_node,
            failed_path=failed_path,
            root_step=root_step,
        )
