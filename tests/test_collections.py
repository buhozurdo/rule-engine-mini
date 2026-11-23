"""
Unit tests for Collection & Array operators in rule-engine-mini:
some, all, none, filter, map, merge.
"""

import pytest
from rule_engine_mini import RuleEvaluator, RuleValidationError


class TestCollectionOperators:
    def setup_method(self) -> None:
        self.evaluator = RuleEvaluator()

    def test_some_with_objects(self) -> None:
        rule = {"some": [{"var": "cart.items"}, {">": [{"var": "price"}, 100]}]}
        ctx_pass = {"cart": {"items": [{"price": 50}, {"price": 150}]}}
        ctx_fail = {"cart": {"items": [{"price": 50}, {"price": 80}]}}
        ctx_empty = {"cart": {"items": []}}
        ctx_invalid = {"cart": {"items": "not_a_list"}}

        assert self.evaluator.evaluate(rule, ctx_pass) is True
        assert self.evaluator.evaluate(rule, ctx_fail) is False
        assert self.evaluator.evaluate(rule, ctx_empty) is False
        assert self.evaluator.evaluate(rule, ctx_invalid) is False

    def test_some_with_primitives(self) -> None:
        rule = {"some": [{"var": "numbers"}, {">": [{"var": ""}, 10]}]}
        assert self.evaluator.evaluate(rule, {"numbers": [2, 5, 12, 8]}) is True
        assert self.evaluator.evaluate(rule, {"numbers": [1, 2, 3]}) is False

    def test_all_with_objects(self) -> None:
        rule = {"all": [{"var": "users"}, {"==": [{"var": "active"}, True]}]}
        ctx_pass = {"users": [{"active": True}, {"active": True}]}
        ctx_fail = {"users": [{"active": True}, {"active": False}]}
        ctx_empty = {"users": []}

        assert self.evaluator.evaluate(rule, ctx_pass) is True
        assert self.evaluator.evaluate(rule, ctx_fail) is False
        # In JsonLogic standard, all on empty array is False
        assert self.evaluator.evaluate(rule, ctx_empty) is False

    def test_none_with_objects(self) -> None:
        rule = {"none": [{"var": "users"}, {"==": [{"var": "banned"}, True]}]}
        ctx_pass = {"users": [{"banned": False}, {"banned": False}]}
        ctx_fail = {"users": [{"banned": False}, {"banned": True}]}
        ctx_empty = {"users": []}

        assert self.evaluator.evaluate(rule, ctx_pass) is True
        assert self.evaluator.evaluate(rule, ctx_fail) is False
        assert self.evaluator.evaluate(rule, ctx_empty) is True

    def test_filter_operator(self) -> None:
        rule = {"filter": [{"var": "scores"}, {">=": [{"var": ""}, 70]}]}
        ctx = {"scores": [55, 70, 85, 40, 92]}
        result = self.evaluator.evaluate(rule, ctx)
        assert result == [70, 85, 92]

        # Filter on non-list
        assert self.evaluator.evaluate({"filter": [{"var": "missing"}, True]}, {}) == []

    def test_map_operator(self) -> None:
        rule = {"map": [{"var": "items"}, {"*": [{"var": "price"}, 2]}]}
        ctx = {"items": [{"price": 10}, {"price": 25}, {"price": 50}]}
        assert self.evaluator.evaluate(rule, ctx) == [20, 50, 100]

        # Map on non-list
        assert self.evaluator.evaluate({"map": ["invalid", True]}, {}) == []

    def test_merge_operator(self) -> None:
        rule = {"merge": [[1, 2], [3, 4], 5, [{"var": "extra"}]]}
        ctx = {"extra": 6}
        assert self.evaluator.evaluate(rule, ctx) == [1, 2, 3, 4, 5, 6]

        # Single argument merge
        assert self.evaluator.evaluate({"merge": [1, 2, 3]}, {}) == [1, 2, 3]
        assert self.evaluator.evaluate({"merge": "single"}, {}) == ["single"]
        assert self.evaluator.evaluate({"merge": [1, {"var": "sublist"}]}, {"sublist": [2, 3]}) == [1, 2, 3]

    def test_collection_invalid_args(self) -> None:
        assert self.evaluator.evaluate({"some": "invalid"}, {}) is False
        assert self.evaluator.evaluate({"all": "invalid"}, {}) is False
        assert self.evaluator.evaluate({"filter": "invalid"}, {}) == []
        assert self.evaluator.evaluate({"map": "invalid"}, {}) == []
        assert self.evaluator.evaluate({"none": "invalid"}, {}) is True

    def test_collection_validation(self) -> None:
        # Arity error: some needs exactly 2 arguments
        with pytest.raises(RuleValidationError) as exc:
            self.evaluator.validate({"some": [[1, 2]]}, strict=True)
        assert "requires exactly 2 arguments" in str(exc.value)

        assert self.evaluator.validate({"some": [[1, 2], {">": [{"var": ""}, 0]}]}) is True
        assert self.evaluator.validate({"all": [[1, 2], {">": [{"var": ""}, 0]}]}) is True
        assert self.evaluator.validate({"none": [[1, 2], {">": [{"var": ""}, 0]}]}) is True
        assert self.evaluator.validate({"filter": [[1, 2], {">": [{"var": ""}, 0]}]}) is True
        assert self.evaluator.validate({"map": [[1, 2], {"*": [{"var": ""}, 2]}]}) is True
        assert self.evaluator.validate({"merge": [[1, 2], [3]]}) is True
