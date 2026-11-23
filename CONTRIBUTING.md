# Contributing to rule-engine-mini

Thank you for your interest in contributing to `rule-engine-mini`!

`rule-engine-mini` is an ultra-fast, zero-dependency, deterministic JSON Logic rule evaluation engine engineered for enterprise production environments.

---

## Architectural Principles & Quality Gates

To maintain library integrity, all contributions must strictly adhere to our core architectural invariants:

1. **Zero External Runtime Dependencies**: `dependencies = []` in `pyproject.toml`. Only standard library components (`operator`, `collections.abc`, `typing`, `time`) are permitted.
2. **Sub-Microsecond Latency**: Core operators must evaluate in $\le 1.5$ microseconds. No regressions in `benchmarks/benchmark.py`.
3. **100% Test Coverage**: Statement and branch test coverage must be 100% across all modules.
4. **SonarCloud Cognitive Complexity $\le 10$**: Every function or method must maintain cognitive complexity of 10 or below.
5. **Type Safety**: 100% type annotations compatible with PEP 561 (`py.typed`).

---

## Local Development Workflow

### Setup

```bash
git clone https://github.com/BuhoZurdo/rule-engine-mini.git
cd rule-engine-mini
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Running Tests & Coverage

```bash
python -m pytest --cov=rule_engine_mini --cov-branch --cov-report=term-missing tests/
```

### Running the Empirical Benchmark Suite

```bash
python benchmarks/benchmark.py
```

---

## Pull Request Checklist

Before submitting a Pull Request:
- [ ] Added unit tests covering all success paths, edge cases, and failure modes.
- [ ] Confirmed 100% statement and branch test coverage.
- [ ] Verified cognitive complexity $\le 10$ for any modified or added functions.
- [ ] Executed `benchmarks/benchmark.py` to ensure zero performance regression.
- [ ] Adhered to standard Conventional Commits (`feat:`, `fix:`, `perf:`, `docs:`, `test:`).
