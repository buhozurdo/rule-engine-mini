"""
Comprehensive unit tests for AST structural validation and custom exceptions in rule-engine-mini.
"""

import pytest
from rule_engine_mini import (
    EvaluationRecursionError,
    OperatorNotFoundError,
    RuleEngineError,
    RuleEvaluator,
    RuleValidationError,
)


class TestRuleValidation:
    """Tests covering validate() method, strict mode, and exception hierarchies."""

    def setup_method(self) -> None:
        self.evaluator = RuleEvaluator(max_depth=10)

    def test_valid_primitive_rules(self) -> None:
        assert self.evaluator.validate(True) is True
        assert self.evaluator.validate(False) is True
        assert self.evaluator.validate(100) is True
        assert self.evaluator.validate(3.14) is True
        assert self.evaluator.validate("constant_string") is True
        assert self.evaluator.validate(None) is True

    def test_valid_empty_and_list_rules(self) -> None:
        assert self.evaluator.validate({}) is True
        assert self.evaluator.validate([]) is True
        assert self.evaluator.validate([{"==": [{"var": "a"}, 1]}, {"<": [2, 3]}]) is True

    def test_valid_standard_operators(self) -> None:
        assert self.evaluator.validate({"var": "user.age"}) is True
        assert self.evaluator.validate({"var": ["user.age", 18]}) is True
        assert self.evaluator.validate({"==": [{"var": "status"}, "active"]}) is True
        assert self.evaluator.validate({">=": [10, 5]}) is True
        assert self.evaluator.validate({"in": ["admin", {"var": "roles"}]}) is True
        assert self.evaluator.validate({"!": [{"var": "is_blocked"}]}) is True
        assert self.evaluator.validate({"!!": {"var": "token"}}) is True
        assert self.evaluator.validate({"if": [{"var": "is_vip"}, 100, 50]}) is True
        assert self.evaluator.validate({"if": [{"var": "c1"}, "a", {"var": "c2"}, "b", "default"]}) is True
        assert self.evaluator.validate({"+": [1, 2, 3]}) is True
        assert self.evaluator.validate({"-": [10, 5]}) is True
        assert self.evaluator.validate({"-": [10]}) is True
        assert self.evaluator.validate({"*": [2, 3, 4]}) is True
        assert self.evaluator.validate({"/": [10, 2]}) is True
        assert self.evaluator.validate({"%": [10, 3]}) is True
        assert self.evaluator.validate({"min": [1, 2, 3]}) is True
        assert self.evaluator.validate({"max": [1, 2, 3]}) is True
        assert self.evaluator.validate({"and": [{">": [10, 2]}, {"<": [5, 20]}]}) is True
        assert self.evaluator.validate({"or": [{"==": [1, 1]}, {"==": [2, 2]}]}) is True

    def test_valid_custom_operator(self) -> None:
        self.evaluator.register_operator("between", lambda args: True)
        assert self.evaluator.validate({"between": [10, 5, 20]}) is True

    def test_unknown_operator_strict_mode(self) -> None:
        with pytest.raises(OperatorNotFoundError) as exc_info:
            self.evaluator.validate({"unknown_op": [1, 2]}, strict=True)
        assert exc_info.value.operator == "unknown_op"
        assert exc_info.value.path == "$"
        assert isinstance(exc_info.value, RuleValidationError)
        assert isinstance(exc_info.value, RuleEngineError)

    def test_unknown_operator_non_strict_mode(self) -> None:
        assert self.evaluator.validate({"unknown_op": [1, 2]}, strict=False) is False

    def test_multi_key_node_rejected(self) -> None:
        invalid_node = {"==": [1, 1], ">": [2, 1]}
        with pytest.raises(RuleValidationError) as exc_info:
            self.evaluator.validate(invalid_node, strict=True)
        assert "exactly 1 operator key" in str(exc_info.value)
        assert self.evaluator.validate(invalid_node, strict=False) is False

    def test_non_string_operator_key_rejected(self) -> None:
        invalid_node = {123: [1, 2]}  # type: ignore[dict-item]
        with pytest.raises(RuleValidationError) as exc_info:
            self.evaluator.validate(invalid_node, strict=True)
        assert "must be a string" in str(exc_info.value)
        assert self.evaluator.validate(invalid_node, strict=False) is False

    def test_comparison_arity_validation(self) -> None:
        # 1 argument instead of 2
        with pytest.raises(RuleValidationError) as exc_info:
            self.evaluator.validate({">": [10]}, strict=True)
        assert "requires exactly 2 arguments" in str(exc_info.value)
        assert self.evaluator.validate({">": [10]}, strict=False) is False

        # 3 arguments instead of 2
        with pytest.raises(RuleValidationError) as exc_info:
            self.evaluator.validate({"==": [1, 2, 3]}, strict=True)
        assert "requires exactly 2 arguments" in str(exc_info.value)

        # non-list argument
        with pytest.raises(RuleValidationError) as exc_info:
            self.evaluator.validate({"<=": 10}, strict=True)
        assert "requires exactly 2 arguments" in str(exc_info.value)

    def test_unary_arity_validation(self) -> None:
        with pytest.raises(RuleValidationError) as exc_info:
            self.evaluator.validate({"!": [True, False]}, strict=True)
        assert "accepts at most 1 argument" in str(exc_info.value)
        assert self.evaluator.validate({"!": [True, False]}, strict=False) is False

    def test_if_arity_validation(self) -> None:
        with pytest.raises(RuleValidationError) as exc_info:
            self.evaluator.validate({"if": [True]}, strict=True)
        assert "requires at least 2 arguments" in str(exc_info.value)
        assert self.evaluator.validate({"if": [True]}, strict=False) is False

        with pytest.raises(RuleValidationError) as exc_info:
            self.evaluator.validate({"if": "not_a_list"}, strict=True)
        assert "requires at least 2 arguments" in str(exc_info.value)

    def test_division_and_modulo_arity_validation(self) -> None:
        with pytest.raises(RuleValidationError) as exc_info:
            self.evaluator.validate({"/": [10]}, strict=True)
        assert "requires exactly 2 arguments" in str(exc_info.value)

        with pytest.raises(RuleValidationError) as exc_info:
            self.evaluator.validate({"%": [10, 2, 3]}, strict=True)
        assert "requires exactly 2 arguments" in str(exc_info.value)

    def test_subtraction_arity_validation(self) -> None:
        with pytest.raises(RuleValidationError) as exc_info:
            self.evaluator.validate({"-": [10, 5, 2]}, strict=True)
        assert "accepts at most 2 arguments" in str(exc_info.value)
        assert self.evaluator.validate({"-": [10, 5, 2]}, strict=False) is False

    def test_var_arity_validation(self) -> None:
        with pytest.raises(RuleValidationError) as exc_info:
            self.evaluator.validate({"var": ["user.name", "default", "extra"]}, strict=True)
        assert "accepts at most 2 arguments" in str(exc_info.value)
        assert self.evaluator.validate({"var": ["user.name", "default", "extra"]}, strict=False) is False

    def test_nested_path_reporting(self) -> None:
        nested_rule = {
            "and": [
                {">": [10, 2]},
                {"or": [
                    {"==": [1, 1]},
                    {"unknown_child": [42]}
                ]}
            ]
        }
        with pytest.raises(OperatorNotFoundError) as exc_info:
            self.evaluator.validate(nested_rule, strict=True)
        assert exc_info.value.operator == "unknown_child"
        assert exc_info.value.path == "$.and[1].or[1]"
        assert self.evaluator.validate(nested_rule, strict=False) is False

    def test_recursion_depth_protection(self) -> None:
        deep_evaluator = RuleEvaluator(max_depth=3)
        # Deeply nested rule exceeding depth 3
        deep_rule = {"!": {"!": {"!": {"!": {"!": True}}}}}
        with pytest.raises(EvaluationRecursionError) as exc_info:
            deep_evaluator.validate(deep_rule, strict=True)
        assert exc_info.value.max_depth == 3
        assert isinstance(exc_info.value, ValueError)
        assert isinstance(exc_info.value, RuleEngineError)
        assert deep_evaluator.validate(deep_rule, strict=False) is False

    def test_exception_properties_and_str(self) -> None:
        err = RuleValidationError("Sample error", path="$.cart.price", node={"price": -1})
        assert "Invalid rule at '$.cart.price': Sample error" in str(err)
        assert err.path == "$.cart.price"
        assert err.node == {"price": -1}

        err_no_path = RuleValidationError("Root error", path="")
        assert str(err_no_path) == "Root error"

        op_err = OperatorNotFoundError("foo", path="$.filter")
        assert "Unknown operator 'foo'" in str(op_err)
        assert op_err.operator == "foo"
        assert op_err.path == "$.filter"

        rec_err = EvaluationRecursionError(50, path="$.deep")
        assert "maximum depth limit of 50 at '$.deep'" in str(rec_err)
