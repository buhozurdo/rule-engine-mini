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


if __name__ == "__main__":
    unittest.main()
