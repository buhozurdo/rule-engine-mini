# Release Process & Guidelines — rule-engine-mini

This document outlines the branching strategy, release train pipeline, tagging conventions, step-by-step checklist, and the complete registry of release notes for all published tags.

---

## 🌳 Branching Strategy

The repository follows a modified Gitflow / Release Train workflow:

```
[ feature/* ] ────────▶ [ dev ] ────────▶ [ release/vX.Y.0 ] ────────▶ [ main ]
(Individual features)  (Integration &   (Stabilization & Beta)        (Production GA)
                       Alpha releases)
```

1. **`main` (Production / GA):**
   - Strictly reserved for stable, production-ready releases.
   - Every commit corresponding to a release bump receives an annotated Git tag: `vX.Y.Z`.
2. **`dev` (Active Integration & Alphas):**
   - The primary staging branch for active engineering work.
   - Feature branches (`feature/*`) and bugfix branches (`fix/*`) merge into `dev` via `--no-ff`.
   - Alpha releases are cut and tagged directly on `dev`: `vX.Y.Z-alpha`.
3. **`release/vX.Y.0` (Stabilization & Betas):**
   - Forked from `dev` when planned features for a minor release are ready for stabilization.
   - Enters feature freeze: only bug fixes, edge-case hardening, and documentation updates are accepted.
   - Tagged as `vX.Y.Z-beta`.
   - Once validated, merged with `--no-ff` into `main` (for GA tag `vX.Y.Z`) and merged back into `dev`.

---

## 🏷️ Versioning & Tagging Scheme

We adhere to [Semantic Versioning 2.0.0](https://semver.org/) and PEP 440:

| Stage | Git Tag Format | `pyproject.toml` version | Purpose |
| :--- | :--- | :--- | :--- |
| **Alpha** | `vX.Y.0-alpha` | `X.Y.0a0` | Active feature development on `dev`. |
| **Beta** | `vX.Y.0-beta` | `X.Y.0b0` | Feature-frozen stabilization on `release/vX.Y.0`. |
| **Release (GA)** | `vX.Y.0` | `X.Y.0` | Production general availability on `main`. |
| **Patch** | `vX.Y.Z` | `X.Y.Z` | Critical bug fixes or security patches. |

### 🏷️ Official Git Tag Registry (All Published Tags)

| Git Tag | Release Date | Target Commit | Channel | Release Summary |
| :--- | :---: | :---: | :---: | :--- |
| [`v0.2.2`](#v022-pypi-package-name-alignment-to-rule-engine-mini--wheel-distribution-patch) | 2026-11-16 | `v0.2.2` | **Patch** | Official PyPI Package Name (`rule-engine-mini`), Wheel Distribution & Metadata Synchronization |
| [`v0.2.1`](#v021-pypi-package-metadata-alignment--release-automation-patch) | 2026-11-16 | `v0.2.1` | **Patch** | PyPI Deployment Metadata Alignment & Release CI Workflow Enhancement |
| [`v0.2.0`](#v020-deterministic-ast-engine-sub-microsecond-latency-extended-json-logic--sonar-hardening) | 2026-11-16 | `v0.2.0` | **GA** | Deterministic AST Engine, Sub-microsecond Latency, Extended JSON Logic, DoS Shield & Sonar Hardening |

---

## 📋 Step-by-Step Release Checklist

### 1. Preparing an Alpha Release (`vX.Y.0-alpha`)
1. Ensure all targeted features are merged into `dev` via `--no-ff`.
2. Run the test suite: `python -m pytest -v --tb=short`.
3. Update `pyproject.toml` and `src/rule_engine_mini/__init__.py` to `X.Y.0a0` / `X.Y.0-alpha`.
4. Update `RELEASE.md` with features added.
5. Commit and tag:
   ```bash
   git commit -am "chore(release): bump version to vX.Y.0-alpha"
   git tag -a vX.Y.0-alpha -m "Release vX.Y.0-alpha: <Summary>"
   ```

### 2. Preparing a Beta Release (`vX.Y.0-beta`)
1. Cut the release branch from `dev`:
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b release/vX.Y.0
   ```
2. Update versions to `X.Y.0b0` / `X.Y.0-beta`.
3. Conduct regression tests, security audit, and edge-case verification.
4. Commit and tag:
   ```bash
   git tag -a vX.Y.0-beta -m "Release vX.Y.0-beta: Stabilization & Hardening"
   ```

### 3. Publishing a GA Production Release (`vX.Y.0`)
1. Finalize documentation, `README.md`, and `RELEASE.md`.
2. Update versions to `X.Y.0` in `pyproject.toml` and `src/rule_engine_mini/__init__.py`.
3. Merge `release/vX.Y.0` into `main`:
   ```bash
   git checkout main
   git merge --no-ff release/vX.Y.0 -m "Merge branch 'release/vX.Y.0' into main"
   git tag -a vX.Y.0 -m "Release vX.Y.0: <Title>"
   ```
4. Merge back into `dev` to propagate fixes:
   ```bash
   git checkout dev
   git merge --no-ff release/vX.Y.0 -m "Merge branch 'release/vX.Y.0' into dev"
   git branch -d release/vX.Y.0
   ```
5. Push commits and tags:
   ```bash
   git push origin main dev --tags
   ```

---

## 🚀 Release History & Release Notes

## v0.2.2: PyPI Package Name Alignment to `rule-engine-mini` & Wheel Distribution Patch

> 🏷️ **Git Tag:** `v0.2.2` | 📅 **Release Date:** `2026-11-16` | 🔗 **Target Ref:** `v0.2.2` | 📦 **Release Channel:** `Patch Maintenance`  
> 🔀 **PR Title:** `fix(packaging): align package name to rule-engine-mini on PyPI and build wheel distributions`  
> 📝 **PR Description:** Fixes PyPI package distribution name to `rule-engine-mini` in `pyproject.toml`, ensuring built wheel artifacts (`rule_engine_mini-0.2.2-py3-none-any.whl`) match the project registered with PyPI Trusted Publishing. Updates documentation, installation commands, badges, and module docstring.

This release formally establishes `rule-engine-mini` as the official canonical package distribution name on the Python Package Index (PyPI).

---

### ⚡ Key Changes & Fixes:

* **Package Distribution Name Alignment:**
  * Updated `[project] name` to `"rule-engine-mini"` in `pyproject.toml`.
  * Validated build artifacts: `python -m build` now generates `rule_engine_mini-0.2.2-py3-none-any.whl` and `rule_engine_mini-0.2.2.tar.gz`.
  * Full alignment with PyPI Trusted Publisher authentication (`https://pypi.org/p/rule-engine-mini`).

* **Documentation & Badges:**
  * Updated installation instructions in `README.md` to `pip install rule-engine-mini`.
  * Updated PyPI version and python-version shields in `README.md`.
  * Updated package docstring in `src/rule_engine_mini/__init__.py`.

* **Versioning & Verification:**
  * Version bumped to `0.2.2` across `pyproject.toml` and `src/rule_engine_mini/__init__.py`.
  * 100% test coverage maintained (19/19 unit tests passing, zero regressions).

---

## v0.2.1: PyPI Package Metadata Alignment & Release Automation Patch

> 🏷️ **Git Tag:** `v0.2.1` | 📅 **Release Date:** `2026-11-16` | 🔗 **Target Ref:** `v0.2.1` | 📦 **Release Channel:** `Patch Maintenance`  
> 🔀 **PR Title:** `fix(release): align PyPI environment URL and prepare v0.2.1 patch release`  
> 📝 **PR Description:** Maintenance patch aligning deployment environment URL for PyPI Trusted Publishing in GitHub Actions (`.github/workflows/release.yml`), bumping package version to `0.2.1` across `pyproject.toml` and `src/rule_engine_mini/__init__.py`, and updating the official release registry.

This patch release addresses metadata synchronization for the automated PyPI deployment pipeline.

---

### ⚡ Key Changes & Fixes:

* **CI/CD & Deployment Environment Alignment:**
  * Updated `.github/workflows/release.yml` environment target URL to point directly to `https://pypi.org/p/rule-engine-mini`.
  * Verified OIDC Trusted Publisher authentication compatibility for automated release publishing on GitHub release triggers.

* **Versioning & Packaging:**
  * Version incremented from `0.2.0` to `0.2.1` in `pyproject.toml` and `src/rule_engine_mini/__init__.py`.
  * Preserved 100% test coverage (19/19 unit tests passing) and sub-microsecond latency benchmarks.

---

## v0.2.0: Deterministic AST Engine, Sub-microsecond Latency, Extended JSON Logic & Sonar Hardening

> 🏷️ **Git Tag:** `v0.2.0` | 📅 **Release Date:** `2026-11-16` | 🔗 **Target Ref:** `v0.2.0` | 📦 **Release Channel:** `GA Production`  
> 🔀 **PR Title:** `release: v0.2.0 - Deterministic AST Engine, Sub-microsecond Latency, Extended JSON Logic & CI Automation`  
> 📝 **PR Description:** First official production release of `buhozurdo-rule-engine-mini`. Delivers sub-microsecond AST rule evaluation in pure Python without dynamic code generation, zero external dependencies, comprehensive JSON Logic operators (`if`, math, comparison, membership), custom operator registration, DoS recursion bomb shield, 100% test coverage, and complete SonarCloud / GitHub Actions hardening.

This milestone release marks the General Availability (GA) of `buhozurdo-rule-engine-mini`. Engineered specifically for high-throughput, security-critical environments (fintech transaction screening, healthtech triage, fraud detection, and SaaS entitlement policies).

---

### ⚡ Key Capabilities & Enhancements:

* **Sub-Microsecond Pure Python Latency:**
  * Flat rule evaluation (e.g., `amount > 100`): **~0.82 µs** (>1,220,000 evaluations/sec per core).
  * Composite 3-clause rule evaluation (nested dict navigation + membership check): **~3.46 µs** (>289,000 evaluations/sec per core).
  * Direct C-level operator dispatch table using native Python `operator` module (`gt`, `ge`, `lt`, `le`, `eq`, `ne`).
  * Loop unrolling with early exit in `and` / `or` logic, eliminating frame object allocation overhead from generator expressions.
  * Dot-notation path pre-splitting with `@lru_cache(maxsize=1024)` and O(1) single-key dictionary access.

* **Extended JSON Logic Operators:**
  * **Branching:** `if` operator supporting lazy ternary (`[cond, then, else]`) and multi-branch condition evaluation (unreached branches are never executed).
  * **Safe Arithmetic:** `+`, `-`, `*`, `/`, `%` with built-in `ZeroDivisionError` and `TypeError` protection (returns `None` without crashing).
  * **Comparisons:** `>`, `>=`, `<`, `<=`, `==`, `===`, `!=`, `!==` with graceful `False` return on incompatible types.
  * **Membership:** `in` operator supporting both array membership and substring search.
  * **Truthiness:** `!` (logical inversion) and `!!` (strict boolean casting).
  * **Extremes:** `min` and `max` operations over argument arrays.

* **Custom Operator Registry (`register_operator`):**
  * Allows registering domain-specific operators without forking.
  * Dynamic parameter inspection supporting 1-argument (`handler(args)`), 2-argument (`handler(args, context)`), and 3-argument (`handler(args, context, evaluator)`) signatures.

* **Security & DoS Protection:**
  * Zero `eval()`, zero `exec()`, zero string compilation — immune to Remote Code Execution (RCE) by mathematical construction.
  * Configurable `max_depth` (default: 50) guarding against stack overflow and recursion-bomb attacks.

* **Code Quality & SonarCloud Hardening:**
  * Refactored into clean, single-responsibility helper functions with Cognitive Complexity $\le 10$ across all routines (well below SonarCloud's limit of 15).
  * Eliminated duplicate branch conditions in path traversal.
  * Fully pinned dependencies in CI workflows and `requirements.txt` satisfying Sonar supply-chain security rules (`githubactions:S8544`).

* **Testing & Coverage:**
  * 19 unit tests passing in **0.24s**.
  * **100% statement coverage** and **100% branch coverage** across all core source modules (`src/rule_engine_mini/`).

* **CI/CD & Distribution:**
  * `.github/workflows/ci.yml`: Automated testing across Python 3.11 with pip caching and Codecov coverage reporting.
  * `.github/workflows/sonar.yml`: SonarQube / SonarCloud static analysis and quality gate verification.
  * `.github/workflows/release.yml`: Automated OIDC Trusted Publishing to PyPI (`buhozurdo-rule-engine-mini`).
  * `.github/workflows/python-publish.yml`: Release asset generation (`.whl` and `.tar.gz`) attached to GitHub Releases.
  * `py.typed`: PEP 561 compliance marker for static type checkers (mypy, Pyright).
