"""
Unit tests for String Manipulation & Missing Key operators:
cat, substr, missing, missing_some.
"""

import pytest
from rule_engine_mini import RuleEvaluator, RuleValidationError


class TestStringAndMissingOperators:
    def setup_method(self) -> None:
        self.evaluator = RuleEvaluator()

    def test_cat_operator(self) -> None:
        rule = {"cat": ["ID-", {"var": "country"}, "-", {"var": "id"}]}
        ctx = {"country": "MX", "id": 1001}
        assert self.evaluator.evaluate(rule, ctx) == "ID-MX-1001"

        # None is treated as empty string
        assert self.evaluator.evaluate({"cat": ["Prefix-", {"var": "missing"}]}, {}) == "Prefix-"

        # Single arg cat
        assert self.evaluator.evaluate({"cat": "hello"}, {}) == "hello"
        assert self.evaluator.evaluate({"cat": None}, {}) == ""

    def test_substr_operator(self) -> None:
        # start only
        assert self.evaluator.evaluate({"substr": ["jsonlogic", 4]}, {}) == "logic"
        # start + positive length
        assert self.evaluator.evaluate({"substr": ["jsonlogic", 0, 4]}, {}) == "json"
        # start + negative length
        assert self.evaluator.evaluate({"substr": ["jsonlogic", 4, -2]}, {}) == "log"
        # non-string or None target
        assert self.evaluator.evaluate({"substr": [None, 0, 2]}, {}) == ""
        # invalid start
        assert self.evaluator.evaluate({"substr": ["abc", "invalid"]}, {}) == "abc"
        # invalid length falls back to text[start:]
        assert self.evaluator.evaluate({"substr": ["abcde", 1, "invalid_len"]}, {}) == "bcde"
        # non-list or less than 2 args
        assert self.evaluator.evaluate({"substr": "invalid"}, {}) == ""
        assert self.evaluator.evaluate({"substr": ["only_one"]}, {}) == ""

    def test_missing_operator(self) -> None:
        rule = {"missing": ["a", "b", "c"]}
        ctx = {"a": 1, "c": 3}
        assert self.evaluator.evaluate(rule, ctx) == ["b"]
        assert self.evaluator.evaluate(rule, {"a": 1, "b": 2, "c": 3}) == []

        # Single key
        assert self.evaluator.evaluate({"missing": "x"}, {}) == ["x"]

    def test_missing_some_operator(self) -> None:
        rule = {"missing_some": [2, ["first", "last", "email"]]}
        # 1 present, need 2 -> returns missing keys
        assert self.evaluator.evaluate(rule, {"first": "Alice"}) == ["last", "email"]
        # 2 present, need 2 -> passes (empty missing list)
        assert self.evaluator.evaluate(rule, {"first": "Alice", "email": "a@test.com"}) == []

        # Invalid args
        assert self.evaluator.evaluate({"missing_some": ["not_int", ["a"]]}, {}) == []
        assert self.evaluator.evaluate({"missing_some": 1}, {}) == []

    def test_validation_for_strings_and_missing(self) -> None:
        assert self.evaluator.validate({"cat": ["a", "b"]}) is True
        assert self.evaluator.validate({"substr": ["hello", 0, 2]}) is True
        assert self.evaluator.validate({"missing": ["a", "b"]}) is True
        assert self.evaluator.validate({"missing_some": [1, ["a", "b"]]}) is True

        with pytest.raises(RuleValidationError):
            self.evaluator.validate({"substr": ["only_one"]}, strict=True)

        with pytest.raises(RuleValidationError):
            self.evaluator.validate({"missing_some": [1]}, strict=True)
