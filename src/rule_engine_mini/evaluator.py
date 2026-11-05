from typing import Any, Dict, List, Union


class RuleEvaluator:
    """
    Deterministic AST Evaluator for JSON Logic rules.
    Executes in pure Python without dynamic eval() or exec().
    """

    def resolve_var(self, path: str, context: Dict[str, Any], default: Any = None) -> Any:
        if not path:
            return context
        parts = path.split(".")
        current = context
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
                current = current[int(part)]
            else:
                return default
        return current

    def evaluate(self, node: Any, context: Dict[str, Any]) -> Any:
        # Primitives return themselves
        if not isinstance(node, dict):
            return node

        if not node:
            return True

        op, args = next(iter(node.items()))

        if op == "var":
            var_name = args if isinstance(args, str) else (args[0] if isinstance(args, list) and args else "")
            default_val = args[1] if isinstance(args, list) and len(args) > 1 else None
            return self.resolve_var(var_name, context, default_val)

        # Boolean logic
        if op == "and":
            return all(self.evaluate(arg, context) for arg in args)
        if op == "or":
            return any(self.evaluate(arg, context) for arg in args)
        if op == "not":
            val = args[0] if isinstance(args, list) else args
            return not self.evaluate(val, context)

        # Comparisons
        if op in {">", ">=", "<", "<=", "==", "!=", "in"}:
            if not isinstance(args, list) or len(args) != 2:
                return False
            left = self.evaluate(args[0], context)
            right = self.evaluate(args[1], context)

            try:
                if op == ">":
                    return left > right
                if op == ">=":
                    return left >= right
                if op == "<":
                    return left < right
                if op == "<=":
                    return left <= right
                if op == "==":
                    return left == right
                if op == "!=":
                    return left != right
                if op == "in":
                    return left in right if right is not None else False
            except TypeError:
                return False

        return False
