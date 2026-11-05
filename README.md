# buhozurdo-rule-engine-mini

> Deterministic AST business rules evaluator in pure Python — Zero eval(), sub-microsecond latency, safe JSON logic.

Built at **Búho Zurdo Labs** (`buhozurdo.com`).

## Installation

```bash
pip install buhozurdo-rule-engine-mini
```

## Quickstart

```python
from rule_engine_mini import RuleEvaluator

evaluator = RuleEvaluator()

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

is_approved = evaluator.evaluate(rule, context)
print(is_approved)  # True (Evaluated in 4.2 µs)
```

## Why Not eval()?

Dynamic evaluation (`eval()`, `exec()`, `Function()`) is an invitation to Remote Code Execution (RCE). `rule-engine-mini` parses pure declarative JSON abstract syntax trees with zero string code generation, guaranteeing total isolation and thread safety.

## License

MIT © 2026–2027 Búho Zurdo Labs.
