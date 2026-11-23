"""
Unit tests for the explain() Observability and Forensic Auditing engine.
"""

from rule_engine_mini import EvaluationRecursionError, ExecutionTrace, RuleEvaluator
import pytest


class TestExplainEngine:
    def setup_method(self) -> None:
        self.evaluator = RuleEvaluator()

    def test_explain_passing_rule(self) -> None:
        rule = {
            "and": [
                {">": [{"var": "amount"}, 100]},
                {"in": [{"var": "country"}, ["MX", "US"]]},
            ]
        }
        ctx = {"amount": 250, "country": "MX"}
        trace: ExecutionTrace = self.evaluator.explain(rule, ctx)

        assert trace.passed is True
        assert trace.result is True
        assert trace.failed_node is None
        assert trace.failed_path is None
        assert trace.resolved_vars == {"amount": 250, "country": "MX"}
        assert trace.elapsed_us > 0.0

        trace_dict = trace.to_dict()
        assert trace_dict["passed"] is True
        assert "root_step" in trace_dict

    def test_explain_failing_composite_rule_pinpoints_clause(self) -> None:
        rule = {
            "and": [
                {">": [{"var": "order.total"}, 500]},
                {"==": [{"var": "user.is_verified"}, True]},  # This will fail
                {"<": [{"var": "order.risk_score"}, 30]},
            ]
        }
        ctx = {
            "order": {"total": 1200, "risk_score": 10},
            "user": {"is_verified": False},
        }

        trace = self.evaluator.explain(rule, ctx)

        assert trace.passed is False
        assert trace.failed_path == "$.and[1]"
        assert trace.failed_node == {"==": [{"var": "user.is_verified"}, True]}
        assert trace.resolved_vars["order.total"] == 1200
        assert trace.resolved_vars["user.is_verified"] is False
        # Because of short-circuiting, risk_score shouldn't even be resolved!
        assert "order.risk_score" not in trace.resolved_vars

    def test_explain_short_circuit_flag(self) -> None:
        rule = {
            "or": [
                {"==": [{"var": "tier"}, "vip"]},
                {">": [{"var": "cart"}, 1000]},
            ]
        }
        trace = self.evaluator.explain(rule, {"tier": "vip", "cart": 50})

        assert trace.passed is True
        assert trace.root_step is not None
        assert trace.root_step.short_circuited is True
        assert len(trace.root_step.children) == 1

    def test_explain_primitive_and_empty(self) -> None:
        assert self.evaluator.explain(True, {}).passed is True
        assert self.evaluator.explain({}, {}).passed is True
        assert self.evaluator.explain(False, {}).passed is False

    def test_explain_dict_operand_and_empty_var(self) -> None:
        rule = {"!": {"var": "flag"}}
        trace = self.evaluator.explain(rule, {"flag": False})
        assert trace.passed is True
        assert trace.root_step is not None
        assert len(trace.root_step.children) == 1

    def test_explain_recursion_limit(self) -> None:
        evaluator = RuleEvaluator(max_depth=2)
        nested = {"and": [{"and": [{"and": [{"and": [True]}]}]}]}
        with pytest.raises(EvaluationRecursionError) as exc:
            evaluator.explain(nested, {})
        assert "exceeded maximum depth" in str(exc.value)

    def test_explain_or_failure_and_non_dict_step(self) -> None:
        rule = {"or": [{"==": [{"var": "a"}, 1]}, {"==": [{"var": "b"}, 2]}]}
        trace = self.evaluator.explain(rule, {"a": 0, "b": 0})
        assert trace.passed is False
        assert trace.failed_path == "$.or[0]"

        # Direct root comparison failure (non-composite)
        single_rule = {">": [{"var": "x"}, 100]}
        trace_single = self.evaluator.explain(single_rule, {"x": 50})
        assert trace_single.passed is False
        assert trace_single.failed_path == "$"
        assert trace_single.failed_node == single_rule

        # Non-container args in non-logical operator
        trace_prim = self.evaluator.explain({"!": False}, {})
        assert trace_prim.passed is True

        # Fallback when all children in logic op are truthy
        from rule_engine_mini.trace import TraceStep
        dummy_step = TraceStep(path="$", node={"and": [True]}, result=False, elapsed_us=1.0, children=[TraceStep(path="$.and[0]", node=True, result=True, elapsed_us=1.0)])
        assert self.evaluator._find_failed_leaf(dummy_step) == dummy_step
