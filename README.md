# Mini Rule Engine (rule-engine-mini)

<p align="center">
  <strong>Deterministic AST business rules evaluator in pure Python.</strong><br>
  Zero <code>eval()</code> • Zero dependencies • Sub-microsecond latency • Bulletproof JSON Logic.
</p>

<p align="center">
  <a href="https://pypi.org/project/rule-engine-mini/"><img src="https://img.shields.io/pypi/v/rule-engine-mini.svg?style=flat-square&color=blue" alt="PyPI Version"></a>
  <a href="https://pypi.org/project/rule-engine-mini/"><img src="https://img.shields.io/pypi/pyversions/rule-engine-mini.svg?style=flat-square" alt="Python Versions"></a>
  <img src="https://img.shields.io/badge/coverage-100%25-brightgreen.svg?style=flat-square" alt="100% Core Coverage">
  <img src="https://img.shields.io/badge/dependencies-0-brightgreen.svg?style=flat-square" alt="Zero Dependencies">
  <img src="https://img.shields.io/badge/security-zero--eval-success.svg?style=flat-square" alt="Zero eval">
  <img src="https://img.shields.io/badge/speed-~0.8µs-orange.svg?style=flat-square" alt="Sub-microsecond Speed">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-purple.svg?style=flat-square" alt="License: MIT"></a>
</p>

---

## ⚡ The Problem: Business Rules Shouldn't Risk Remote Code Execution

Every backend eventually needs dynamic rules:
- **Fintech**: *"Flag transactions over \$5,000 originating outside MX or US."*
- **E-commerce**: *"Apply VIP discount if cart > \$100 and loyalty tier is Gold."*
- **Healthtech**: *"Trigger urgent triage if oxygen saturation < 90% or heart rate > 120."*

Most teams face a frustrating dilemma:

1. **The Naive Trap (`eval()` or `exec()`)**: You store Python expressions in the database. One unescaped input later, an attacker gets a shell on your production cluster (RCE).
2. **The Heavyweight Trap (Enterprise Rule Engines)**: You pull in massive DSLs or bloated frameworks with 50 transitive dependencies and a steep learning curve.

### The Solution: `rule-engine-mini`

A **lightweight, auditable, pure Python** evaluator that parses declarative JSON Abstract Syntax Trees (ASTs). 

- 🛡️ **Zero `eval()`, Zero `exec()`**: Immune to code injection by mathematical construction.
- 🚀 **Sub-microsecond performance**: Evaluates flat rules in **~0.8 µs** (>1,180,000 ops/sec) and composite nested rules in **~3.3 µs** (>295,000 ops/sec).
- 📦 **Zero dependencies**: Built strictly on the Python standard library. No supply-chain vulnerabilities.
- 🗄️ **Database & API Ready**: Store rules natively in PostgreSQL `JSONB`, MongoDB, Redis, or send them directly from frontend forms.
- 🧵 **Stateless & Thread-Safe**: Drop it into FastAPI, Celery, Django, or AWS Lambda without concurrency locks.
- 🧯 **DoS & Recursion Bomb Shield**: Configurable `max_depth` protects against maliciously nested payloads.
- 🧩 **Extensible**: Register custom domain operators in one line without forking.
- 🏷️ **PEP 561 Typed**: Full `py.typed` compliance for mypy, Pyright, and VS Code.

---

## 📊 Quick Comparison

| Feature | `eval()` / `exec()` | Heavy Rule Engines | `rule-engine-mini` |
| :--- | :---: | :---: | :---: |
| **RCE Safe** | ❌ Critical Risk | ⚠️ Complex Sandbox | ✅ **100% Deterministic** |
| **External Dependencies** | 0 | ❌ 10+ packages | ✅ **0 (Pure Standard Library)** |
| **Audit Time** | Impossible to secure | Hours / Days | ✅ **5 Minutes (Single File)** |
| **JSON-Native** | ❌ No (Raw strings) | ⚠️ Proprietary DSL | ✅ **Standard JSON-Logic AST** |
| **Execution Speed** | Medium | Slow startup | ✅ **0.8 µs – 3.3 µs per rule** |
| **Recursion Protection** | ❌ Stack overflow | ⚠️ Complex setup | ✅ **Built-in `max_depth` limit** |
| **Custom Operators** | Dangerous | Complex plugins | ✅ **`register_operator` API** |
| **Graceful Typing** | 💥 Crashes on mismatch | Configurable | ✅ **Safe fallback (`False`)** |

---

## 🚀 Installation

```bash
pip install rule-engine-mini
```

*Requirements: Python 3.9+ (Zero external dependencies).*

---

## 💡 Quickstart in 30 Seconds

```python
from rule_engine_mini import RuleEvaluator

evaluator = RuleEvaluator()

# 1. Define a rule as a declarative JSON structure
fraud_prevention_rule = {
    "and": [
        {">": [{"var": "transaction.amount"}, 5000]},
        {"in": [{"var": "transaction.country"}, ["MX", "US", "CA"]]},
        {"==": [{"var": "user.is_flagged"}, False]}
    ]
}

# 2. Provide the runtime context (nested dicts, lists, booleans, etc.)
context = {
    "transaction": {
        "amount": 7500,
        "country": "MX"
    },
    "user": {
        "id": "usr_99",
        "is_flagged": False
    }
}

# 3. Evaluate safely in ~3.3 microseconds
is_approved = evaluator.evaluate(fraud_prevention_rule, context)
print(is_approved)  # 👉 True
```

---

## 🛠️ Key Capabilities

### 1. Deep Path Navigation (Dot Notation & Array Indices)
Traverse deeply nested dictionaries and array indexes without `KeyError` or `IndexError`:

```python
rule = {">": [{"var": "cart.items.0.price"}, 100]}

context = {
    "cart": {
        "items": [
            {"sku": "A1", "price": 150},
            {"sku": "B2", "price": 80}
        ]
    }
}

evaluator.evaluate(rule, context)  # True
```

### 2. Safe Fallbacks for Missing Variables
Pass a default fallback value if a key might be missing in production context:

```python
# {"var": ["path.to.variable", default_value]}
rule = {"==": [{"var": ["user.membership", "standard"]}, "vip"]}

# When context has no 'membership' key, it safely evaluates to "standard"
context = {"user": {"name": "Alice"}}
evaluator.evaluate(rule, context)  # False (no KeyError!)
```

### 3. Conditional Branching (`if` / Ternary)
Supports lazy evaluation: unexecuted branches are never calculated!

```python
# {"if": [condition, then_value, else_value]}
tax_rule = {
    "if": [
        {"==": [{"var": "country"}, "MX"]},
        {"*": [{"var": "subtotal"}, 0.16]},
        {"*": [{"var": "subtotal"}, 0.08]}
    ]
}

evaluator.evaluate(tax_rule, {"country": "MX", "subtotal": 1000})  # 160.0
```

### 4. Custom Operators in One Line
Extend the engine with domain-specific logic safely:

```python
# Register a custom 'between' operator
evaluator.register_operator(
    "between",
    lambda args, ctx, ev: ev.evaluate(args[1], ctx) <= ev.evaluate(args[0], ctx) <= ev.evaluate(args[2], ctx)
)

rule = {"between": [{"var": "score"}, 70, 100]}
evaluator.evaluate(rule, {"score": 85})  # True
```

### 5. Graceful Type Safety & Zero-Division Shield
If mismatched types are compared or division by zero occurs, `rule-engine-mini` handles it safely instead of crashing your service:

```python
evaluator.evaluate({">": [{"var": "score"}, 50]}, {"score": "invalid"})  # False
evaluator.evaluate({"/": [100, 0]}, {})  # None (ZeroDivisionError protected)
```

### 6. Static Rule Validation & Error Inspection (`validate`)
Validate AST rules before storing them in your database or sending them to production:

```python
from rule_engine_mini import RuleEvaluator, RuleValidationError, OperatorNotFoundError

evaluator = RuleEvaluator()

# Non-strict mode: returns boolean
is_valid = evaluator.validate({">": [{"var": "amount"}, 100]}, strict=False)  # True

# Strict mode: raises descriptive exceptions with exact AST error path
try:
    evaluator.validate({"and": [{">": [10]}, {"unknown": [1]}]}, strict=True)
except RuleValidationError as e:
    print(f"Error at {e.path}: {e}")
```

---

## 📖 Supported Operators

| Category | Operator | Syntax Example | Description |
| :--- | :--- | :--- | :--- |
| **Variables** | `var` | `{"var": "user.age"}` | Resolves nested path via dot notation |
| | `var` *(default)* | `{"var": ["user.tier", "free"]}` | Fallback value if variable is missing |
| **Logic** | `and` | `{"and": [c1, c2, ...]}` | Short-circuit `True` if all clauses are truthy |
| | `or` | `{"or": [c1, c2, ...]}` | Short-circuit `True` if any clause is truthy |
| | `not` / `!` | `{"!": clause}` | Inverts boolean truthiness |
| | `!!` | `{"!!": clause}` | Casts value to strict boolean |
| **Branching** | `if` | `{"if": [cond, then, else]}` | Lazy ternary / multi-branch condition |
| **Comparisons** | `>`, `>=` | `{">": [{"var": "total"}, 500]}` | Greater than / Greater than or equal |
| | `<`, `<=` | `{"<": [{"var": "age"}, 18]}` | Less than / Less than or equal |
| | `==`, `===` | `{"==": [{"var": "status"}, "active"]}` | Equality check |
| | `!=`, `!==` | `{"!=": [{"var": "status"}, "banned"]}` | Inequality check |
| **Membership** | `in` | `{"in": [{"var": "country"}, ["MX", "US"]]}` | Checks item in list or substring in string |
| **Arithmetic** | `+` | `{"+": [10, 20, 5]}` | Addition / numeric sum |
| | `-` | `{"-": [100, 30]}` or `{"-": 5}` | Subtraction / unary negation |
| | `*` | `{"*": [5, 4]}` | Multiplication |
| | `/` | `{"/": [100, 4]}` | Safe division (returns `None` on 0) |
| | `%` | `{"%": [10, 3]}` | Safe modulo (returns `None` on 0) |
| | `min`, `max` | `{"min": [10, 5, 20]}` | Minimum / Maximum value |

---

## 🏗️ Real-World Recipe: FastAPI Dynamic Policy Engine

Store rules in your database and let business operations update logic in real time without redeploying your backend:

```python
from fastapi import FastAPI
from pydantic import BaseModel
from rule_engine_mini import RuleEvaluator

app = FastAPI()
evaluator = RuleEvaluator()

# Imagine this rule is fetched dynamically from PostgreSQL JSONB or Redis
DISCOUNT_RULE = {
    "or": [
        {">=": [{"var": "cart.total"}, 1000]},
        {"and": [
            {"==": [{"var": "user.is_subscriber"}, True]},
            {">=": [{"var": "cart.total"}, 500]}
        ]}
    ]
}

class CheckoutRequest(BaseModel):
    user: dict
    cart: dict

@app.post("/checkout/discount")
def check_discount(payload: CheckoutRequest):
    context = payload.model_dump()
    qualifies = evaluator.evaluate(DISCOUNT_RULE, context)
    return {"discount_applied": qualifies}
```

---

## ⏱️ Benchmark

Tested on x86-64 hardware with Python 3.12 (100,000 iterations):

```
Operation                               Latency           Throughput
-------------------------------------------------------------------------
Flat single rule (e.g. amount > 100)    0.84 µs / eval    ~1,180,000 ops/sec
Composite 3-clause rule                 3.37 µs / eval      ~296,000 ops/sec
Memory allocations per evaluation       0 (Stack frames only)
```

---

## 🧪 Testing & Coverage

Run the full test suite with Python's standard `unittest` or `coverage`:

```bash
# Run tests
python -m unittest discover tests -v

# Run with coverage (enforces 100% core coverage)
coverage run -m unittest discover tests
coverage report -m
```

---

## 🦉 Built at Búho Zurdo Labs

Designed and battle-tested for high-throughput, mission-critical systems at **Búho Zurdo Labs** ([buhozurdo.com](https://buhozurdo.com)).

### Authors
- **Juan Rael Corrales Arellano** ([@buhozurdo](https://github.com/buhozurdo)) — `rael@buhozurdo.com`
- **Búho Zurdo Labs** — `dev@buhozurdo.com`

### License
MIT License © 2026–2027 Búho Zurdo Labs. Free to use in commercial and open-source projects.
