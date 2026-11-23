# Security Policy

`rule-engine-mini` is designed from the ground up for mission-critical, secure environments. It strictly enforces:
- **Zero dynamic code execution**: No `eval()`, `exec()`, or dynamic `getattr` on untrusted context.
- **Zero runtime dependencies**: No supply-chain risk or third-party transitive vulnerability footprint.
- **Strict recursion protection**: Hard bounds against deeply nested AST recursion denial-of-service (`EvaluationRecursionError`).

---

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.5.x   | :white_check_mark: |
| 0.4.x   | :white_check_mark: |
| 0.3.x   | :white_check_mark: |
| < 0.3.0 | :x:                |

---

## Reporting a Vulnerability

If you discover a security vulnerability within `rule-engine-mini`, please **do NOT** open a public issue.

Instead, please report security issues privately via:
1. **GitHub Private Security Advisory**: Navigate to the [Security Advisories](https://github.com/BuhoZurdo/rule-engine-mini/security/advisories) tab and click **New draft advisory**.
2. **Email Disclosure**: Send details directly to `security@buhozurdo.com`.

### Our Security SLA
- **Initial Acknowledgment**: Within 24-48 hours of receipt.
- **Triage & Assessment**: Within 72 hours.
- **Remediation & Patch**: Critical severity issues will have a patch released to PyPI within 7 calendar days.

### Safe Harbor
Any research conducted in good faith following standard responsible disclosure practices is protected under our Safe Harbor pledge: we will not pursue legal action against security researchers acting in good faith.
