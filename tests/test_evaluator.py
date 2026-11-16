import unittest
from rule_engine_mini import RuleEvaluator


class TestRuleEvaluator(unittest.TestCase):
    def setUp(self):
        self.evaluator = RuleEvaluator()

    def test_nested_logic_evaluation(self):
        rule = {
            "and": [
                {">": [{"var": "cart.total"}, 5000]},
                {"in": [{"var": "transaction.country"}, ["MX", "US"]]},
                {"==": [{"var": "user.is_blacklisted"}, False]}
            ]
        }
        context = {
            "cart": {"total": 8400},
            "transaction": {"country": "MX"},
            "user": {"is_blacklisted": False}
        }
        result = self.evaluator.evaluate(rule, context)
        self.assertTrue(result)

    def test_false_branch(self):
        rule = {">": [{"var": "cart.total"}, 10000]}
        context = {"cart": {"total": 8400}}
        result = self.evaluator.evaluate(rule, context)
        self.assertFalse(result)

    def test_missing_var_default(self):
        rule = {"==": [{"var": ["patient.allergies", "none"]}, "none"]}
        context = {"patient": {}}
        result = self.evaluator.evaluate(rule, context)
        self.assertTrue(result)

    def test_primitives_and_empty_nodes(self):
        self.assertEqual(self.evaluator.evaluate(42, {}), 42)
        self.assertEqual(self.evaluator.evaluate("hello", {}), "hello")
        self.assertTrue(self.evaluator.evaluate({}, {}))

    def test_flat_variable_resolution(self):
        self.assertEqual(self.evaluator.evaluate({"var": "age"}, {"age": 30}), 30)
        self.assertEqual(self.evaluator.evaluate({"var": ["city", "CDMX"]}, {}), "CDMX")
        self.assertIsNone(self.evaluator.evaluate({"var": "unknown"}, {}))

    def test_empty_var_returns_context(self):
        ctx = {"key": "val"}
        self.assertEqual(self.evaluator.evaluate({"var": ""}, ctx), ctx)
        self.assertEqual(self.evaluator.evaluate({"var": []}, ctx), ctx)

    def test_sequence_indexing(self):
        ctx = {
            "items": [
                {"name": "Laptop", "price": 1200},
                {"name": "Mouse", "price": 25}
            ]
        }
        self.assertEqual(self.evaluator.evaluate({"var": "items.0.name"}, ctx), "Laptop")
        self.assertEqual(self.evaluator.evaluate({"var": "items.1.price"}, ctx), 25)
        self.assertIsNone(self.evaluator.evaluate({"var": "items.99.name"}, ctx))
        self.assertEqual(self.evaluator.evaluate({"var": ["items.not_a_number", "fallback"]}, ctx), "fallback")

    def test_comparisons(self):
        self.assertTrue(self.evaluator.evaluate({">": [10, 5]}, {}))
        self.assertTrue(self.evaluator.evaluate({">=": [10, 10]}, {}))
        self.assertTrue(self.evaluator.evaluate({"<": [5, 10]}, {}))
        self.assertTrue(self.evaluator.evaluate({"<=": [10, 10]}, {}))
        self.assertTrue(self.evaluator.evaluate({"==": ["a", "a"]}, {}))
        self.assertTrue(self.evaluator.evaluate({"===": ["a", "a"]}, {}))
        self.assertTrue(self.evaluator.evaluate({"!=": ["a", "b"]}, {}))
        self.assertTrue(self.evaluator.evaluate({"!==": ["a", "b"]}, {}))

        # Malformed comparisons
        self.assertFalse(self.evaluator.evaluate({">": [10]}, {}))
        self.assertFalse(self.evaluator.evaluate({">": [10, 20, 30]}, {}))

        # Incompatible types gracefully return False
        self.assertFalse(self.evaluator.evaluate({">": ["text", 100]}, {}))
        self.assertFalse(self.evaluator.evaluate({"<=": [None, 5]}, {}))

    def test_membership_in(self):
        self.assertTrue(self.evaluator.evaluate({"in": ["MX", ["MX", "US"]]}, {}))
        self.assertFalse(self.evaluator.evaluate({"in": ["ES", ["MX", "US"]]}, {}))
        self.assertTrue(self.evaluator.evaluate({"in": ["cat", "concatenate"]}, {}))
        self.assertFalse(self.evaluator.evaluate({"in": ["dog", "concatenate"]}, {}))
        self.assertFalse(self.evaluator.evaluate({"in": ["val", None]}, {}))
        self.assertFalse(self.evaluator.evaluate({"in": ["val"]}, {}))

    def test_boolean_logic(self):
        self.assertTrue(self.evaluator.evaluate({"and": [True, True, True]}, {}))
        self.assertFalse(self.evaluator.evaluate({"and": [True, False, True]}, {}))
        self.assertTrue(self.evaluator.evaluate({"or": [False, True, False]}, {}))
        self.assertFalse(self.evaluator.evaluate({"or": [False, False]}, {}))

        # Non-list args in boolean logic
        self.assertTrue(self.evaluator.evaluate({"and": True}, {}))
        self.assertFalse(self.evaluator.evaluate({"or": False}, {}))

        # Negation
        self.assertFalse(self.evaluator.evaluate({"not": True}, {}))
        self.assertTrue(self.evaluator.evaluate({"not": [False]}, {}))
        self.assertFalse(self.evaluator.evaluate({"!": True}, {}))
        self.assertTrue(self.evaluator.evaluate({"!": [False]}, {}))
        self.assertTrue(self.evaluator.evaluate({"!!": "truthy text"}, {}))
        self.assertFalse(self.evaluator.evaluate({"!!": ""}, {}))

    def test_conditional_if(self):
        # Ternary: if-then-else
        rule_true = {"if": [{">": [10, 5]}, "greater", "smaller"]}
        rule_false = {"if": [{">": [2, 5]}, "greater", "smaller"]}
        self.assertEqual(self.evaluator.evaluate(rule_true, {}), "greater")
        self.assertEqual(self.evaluator.evaluate(rule_false, {}), "smaller")

        # Multi-branch if-elsif-else
        rule_multi = {
            "if": [
                {"==": [{"var": "grade"}, "A"]}, "Excellent",
                {"==": [{"var": "grade"}, "B"]}, "Good",
                "Needs improvement"
            ]
        }
        self.assertEqual(self.evaluator.evaluate(rule_multi, {"grade": "A"}), "Excellent")
        self.assertEqual(self.evaluator.evaluate(rule_multi, {"grade": "B"}), "Good")
        self.assertEqual(self.evaluator.evaluate(rule_multi, {"grade": "F"}), "Needs improvement")

        # Lazy evaluation check (unreached branch with error node shouldn't execute)
        rule_lazy = {
            "if": [
                True,
                "success",
                {"/": [10, 0]}  # If evaluated, would be division by zero
            ]
        }
        self.assertEqual(self.evaluator.evaluate(rule_lazy, {}), "success")
        self.assertIsNone(self.evaluator.evaluate({"if": []}, {}))

    def test_arithmetic_operations(self):
        # Addition
        self.assertEqual(self.evaluator.evaluate({"+": [5, 10, 15]}, {}), 30)
        self.assertEqual(self.evaluator.evaluate({"+": []}, {}), 0)
        self.assertEqual(self.evaluator.evaluate({"+": 42}, {}), 42)

        # Subtraction & Unary Negation
        self.assertEqual(self.evaluator.evaluate({"-": [100, 30]}, {}), 70)
        self.assertEqual(self.evaluator.evaluate({"-": [5]}, {}), -5)
        self.assertEqual(self.evaluator.evaluate({"-": 12}, {}), -12)

        # Multiplication
        self.assertEqual(self.evaluator.evaluate({"*": [3, 4, 2]}, {}), 24)
        self.assertIsNone(self.evaluator.evaluate({"*": []}, {}))

        # Division & Modulo with ZeroDivision safety
        self.assertEqual(self.evaluator.evaluate({"/": [20, 4]}, {}), 5.0)
        self.assertIsNone(self.evaluator.evaluate({"/": [10, 0]}, {}))
        self.assertIsNone(self.evaluator.evaluate({"/": [10]}, {}))
        self.assertEqual(self.evaluator.evaluate({"%": [10, 3]}, {}), 1)
        self.assertIsNone(self.evaluator.evaluate({"%": [10, 0]}, {}))

        # Min & Max
        self.assertEqual(self.evaluator.evaluate({"min": [10, 4, 8, 2]}, {}), 2)
        self.assertEqual(self.evaluator.evaluate({"max": [10, 4, 8, 2]}, {}), 10)
        self.assertIsNone(self.evaluator.evaluate({"min": []}, {}))

    def test_custom_operator_registration(self):
        evaluator = RuleEvaluator()

        # 3-arg custom operator (args, context, evaluator)
        evaluator.register_operator(
            "between",
            lambda args, ctx, ev: ev.evaluate(args[1], ctx) <= ev.evaluate(args[0], ctx) <= ev.evaluate(args[2], ctx)
        )

        rule = {"between": [{"var": "score"}, 50, 100]}
        self.assertTrue(evaluator.evaluate(rule, {"score": 75}))
        self.assertFalse(evaluator.evaluate(rule, {"score": 25}))

        # 2-arg custom operator fallback (args, context)
        evaluator.register_operator("is_empty", lambda args, ctx: len(args[0]) == 0)
        self.assertTrue(evaluator.evaluate({"is_empty": [[]]}, {}))

        # Custom operator exception gracefully returns False
        evaluator.register_operator("broken", lambda args, ctx: 1 / 0)
        self.assertFalse(evaluator.evaluate({"broken": [1]}, {}))

    def test_recursion_depth_protection(self):
        evaluator = RuleEvaluator(max_depth=5)

        # Build deeply nested AST
        nested_rule = {"var": "x"}
        for _ in range(10):
            nested_rule = {"and": [nested_rule]}

        with self.assertRaises(ValueError) as ctx:
            evaluator.evaluate(nested_rule, {"x": 1})
        self.assertIn("Rule evaluation exceeded maximum depth limit", str(ctx.exception))


    def test_custom_mapping(self):
        from collections import UserDict
        custom_ctx = UserDict({"flat": 123, "nested": UserDict({"deep": 456})})
        self.assertEqual(self.evaluator.evaluate({"var": "flat"}, custom_ctx), 123)
        self.assertEqual(self.evaluator.evaluate({"var": "nested.deep"}, custom_ctx), 456)
        self.assertIsNone(self.evaluator.evaluate({"var": "nested.missing"}, custom_ctx))
        self.assertEqual(self.evaluator.evaluate({"var": ["missing_flat", "d"]}, custom_ctx), "d")

    def test_arithmetic_error_handling(self):
        # TypeError in addition
        self.assertIsNone(self.evaluator.evaluate({"+": ["string", 10]}, {}))
        # TypeError in subtraction
        self.assertIsNone(self.evaluator.evaluate({"-": ["string", 10]}, {}))
        self.assertIsNone(self.evaluator.evaluate({"-": "not_a_number"}, {}))
        # TypeError in multiplication
        self.assertIsNone(self.evaluator.evaluate({"*": [None, 5]}, {}))
        # TypeError in division and modulo
        self.assertIsNone(self.evaluator.evaluate({"/": ["a", "b"]}, {}))
        self.assertIsNone(self.evaluator.evaluate({"%": ["a", "b"]}, {}))
        # TypeError in min/max
        self.assertIsNone(self.evaluator.evaluate({"min": ["string", 10]}, {}))
        self.assertIsNone(self.evaluator.evaluate({"max": ["string", 10]}, {}))

    def test_unknown_operator_and_edge_cases(self):
        self.assertFalse(self.evaluator.evaluate({"unknown_op": [1, 2]}, {}))
        self.assertIsNone(self.evaluator.evaluate({"if": "not_a_list"}, {}))

    def test_builtin_operator_registration(self):
        evaluator = RuleEvaluator()
        evaluator.register_operator("len", len)
        self.assertEqual(evaluator.evaluate({"len": [1, 2, 3]}, {}), 3)

        # 1-arg custom operator wrapper
        evaluator.register_operator("sum", lambda args: sum(args))
        self.assertEqual(evaluator.evaluate({"sum": [1, 2, 3]}, {}), 6)

        # Uninspectable object falls back to param_count=2
        evaluator.register_operator("uninspectable", object())
        self.assertFalse(evaluator.evaluate({"uninspectable": [1]}, {}))

    def test_additional_edge_cases(self):
        # Empty if clause
        self.assertIsNone(self.evaluator.evaluate({"if": []}, {}))
        # Addition with mixed types in list
        self.assertIsNone(self.evaluator.evaluate({"+": [10, "bad"]}, {}))
        # Traversing a primitive as if it were a dict/sequence
        self.assertIsNone(self.evaluator.evaluate({"var": "user.name.first"}, {"user": "not_a_dict"}))
        # Modulo by zero and invalid arg count
        self.assertIsNone(self.evaluator.evaluate({"%": [10, 0]}, {}))
        self.assertIsNone(self.evaluator.evaluate({"%": [10]}, {}))
        # 'in' with non-iterable right operand
        self.assertFalse(self.evaluator.evaluate({"in": ["item", 12345]}, {}))
        # 'if' without else where condition is false
        self.assertIsNone(self.evaluator.evaluate({"if": [False, "val"]}, {}))


if __name__ == "__main__":
    unittest.main()

