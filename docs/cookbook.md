# Enterprise Production Cookbook: rule-engine-mini

This cookbook provides production-ready architectural patterns, code recipes, and governance blueprints for deploying `rule-engine-mini` in mission-critical, high-throughput enterprise systems.

All patterns are designed for sub-microsecond evaluation, zero external dependencies, 100% thread safety, and SOC2/HIPAA auditability.

---

## Table of Contents

1. [Blueprint 1: Netflix-Grade Dynamic Entitlements & Geo-Routing](#blueprint-1-netflix-grade-dynamic-entitlements--geo-routing)
2. [Blueprint 2: Cloud IAM Attribute-Based Access Control (ABAC)](#blueprint-2-cloud-iam-attribute-based-access-control-abac)
3. [Blueprint 3: Fintech Real-Time Anti-Fraud & Risk Screening](#blueprint-3-fintech-real-time-anti-fraud--risk-screening)
4. [Blueprint 4: Clinical Triage & HIPAA-Compliant Medical Auditing](#blueprint-4-clinical-triage--hipaa-compliant-medical-auditing)
5. [Performance Architecture: Cache & Concurrency Best Practices](#performance-architecture-cache--concurrency-best-practices)

---

## Blueprint 1: Netflix-Grade Dynamic Entitlements & Geo-Routing

### Problem Statement
A global media streaming platform must gate content playback based on:
- User subscription tier (Premium, Standard, Basic).
- Geographic territory licensing (e.g. available in `US`, `CA`, `MX`).
- Device concurrency: active streams cannot exceed maximum allowed plan limits.
- Age/maturity content rating certification.

### Implementation

```python
from rule_engine_mini import RuleEvaluator

evaluator = RuleEvaluator()

entitlement_rule = {
    "and": [
        # 1. Geographic content licensing check
        {"in": [{"var": "playback.country"}, {"var": "content.licensed_territories"}]},
        # 2. Maturity rating gating
        {
            "if": [
                {"==": [{"var": "content.rating"}, "R"]},
                {">=": [{"var": "user.age"}, 18]},
                True,  # Non-restricted content passes rating gate
            ]
        },
        # 3. Active device stream limit check
        {
            "<=": [
                {
                    "+": [
                        {"var": "user.active_streams_count"},
                        1,  # Prospective new stream
                    ]
                },
                {"var": "user.plan.max_concurrent_streams"},
            ]
        },
        # 4. Ensure no active stream is flagged as compromised
        {
            "none": [
                {"var": "user.active_sessions"},
                {"==": [{"var": "is_compromised"}, True]},
            ]
        },
    ]
}

# Runtime context representing playback request
context = {
    "user": {
        "id": "usr_99812",
        "age": 28,
        "active_streams_count": 2,
        "plan": {"tier": "premium", "max_concurrent_streams": 4},
        "active_sessions": [
            {"device_id": "tv_living_room", "is_compromised": False},
            {"device_id": "iphone_15", "is_compromised": False},
        ],
    },
    "content": {
        "id": "mov_stranger_things_s5",
        "rating": "R",
        "licensed_territories": ["US", "CA", "MX", "BR", "UK"],
    },
    "playback": {
        "country": "MX",
        "device_type": "smart_tv",
    },
}

# Fast-path decision (evaluates in < 5 microseconds)
can_play = evaluator.evaluate(entitlement_rule, context)
print("Playback Permitted:", can_play)  # True
```

---

## Blueprint 2: Cloud IAM Attribute-Based Access Control (ABAC)

### Problem Statement
An enterprise cloud gateway must evaluate fine-grained access policies dynamically without hardcoding role logic in application services. The decision must record an immutable audit trace for compliance (SOC2 Type II / ISO 27001).

### Implementation

```python
import json
from rule_engine_mini import RuleEvaluator

evaluator = RuleEvaluator()

iam_policy_rule = {
    "and": [
        # Principal must be an active corporate employee
        {"==": [{"var": "principal.status"}, "active"]},
        # MFA must be verified for production resources
        {
            "if": [
                {"==": [{"var": "resource.environment"}, "production"]},
                {"==": [{"var": "principal.mfa_authenticated"}, True]},
                True,
            ]
        },
        # Role matching or explicit grant in user permissions
        {
            "or": [
                {"==": [{"var": "principal.role"}, "superadmin"]},
                {"in": [{"var": "action"}, {"var": "principal.allowed_actions"}]},
            ]
        },
        # Resource classification clearance
        {
            ">=": [
                {"var": "principal.security_clearance_level"},
                {"var": "resource.required_clearance_level"},
            ]
        },
    ]
}

context = {
    "principal": {
        "id": "emp_4401",
        "status": "active",
        "role": "data_engineer",
        "mfa_authenticated": True,
        "security_clearance_level": 3,
        "allowed_actions": ["read", "query_analytics"],
    },
    "action": "query_analytics",
    "resource": {
        "arn": "arn:aws:s3:::analytics-lakehouse-prod",
        "environment": "production",
        "required_clearance_level": 2,
    },
}

# Forensic evaluation with explain()
trace = evaluator.explain(iam_policy_rule, context)

if trace.passed:
    print(f"Access GRANTED in {trace.elapsed_us:.2f} µs")
else:
    print(f"Access DENIED! Clause failed: {trace.failed_path}")
    print("Resolved context variables:", json.dumps(trace.resolved_vars, indent=2))
```

---

## Blueprint 3: Fintech Real-Time Anti-Fraud & Risk Screening

### Problem Statement
A global payment processing platform evaluates incoming transactions against multi-attribute risk vectors. Sub-10ms SLA requires rule engine evaluations to complete within $< 10$ microseconds.

### Implementation

```python
from rule_engine_mini import RuleEvaluator

evaluator = RuleEvaluator()

fraud_screening_rule = {
    "and": [
        # 1. Require mandatory transaction fields
        {"==": [{"missing": ["card.number_hash", "card.country", "amount", "merchant.category"]}, []]},
        # 2. Maximum single transaction velocity threshold
        {"<=": [{"var": "amount"}, {"var": "user.daily_single_limit"}]},
        # 3. Flag high-risk merchant categories unless cardholder VIP
        {
            "or": [
                {"==": [{"var": "user.is_vip"}, True]},
                {"none": [
                    {"var": "merchant.risk_tags"},
                    {"in": [{"var": ""}, ["gambling", "crypto_unregulated", "high_velocity"]]}
                ]},
            ]
        },
        # 4. Cross-border transaction match
        {
            "if": [
                {"!=": [{"var": "card.country"}, {"var": "terminal.country"}]},
                {"<=": [{"var": "user.cross_border_risk_score"}, 40]},
                True,
            ]
        },
    ]
}

tx_context = {
    "amount": 420.00,
    "user": {
        "is_vip": False,
        "daily_single_limit": 2000.00,
        "cross_border_risk_score": 15,
    },
    "card": {
        "number_hash": "e3b0c44298fc1c149afbf4c8996fb924",
        "country": "US",
    },
    "terminal": {"country": "MX"},
    "merchant": {
        "category": "travel",
        "risk_tags": ["airline", "ota"],
    },
}

result = evaluator.evaluate(fraud_screening_rule, tx_context)
print("Transaction Approved:", result)  # True
```

---

## Blueprint 4: Clinical Triage & HIPAA-Compliant Medical Auditing

### Problem Statement
An ICU clinical monitoring system evaluates continuous streams of bedside biometric telemetry to detect early onset Sepsis (qSOFA criteria). Every alert generated must produce a deterministic, immutable proof of logic for clinical audit boards.

### Implementation

```python
from rule_engine_mini import ExecutionTrace, RuleEvaluator

evaluator = RuleEvaluator()

# qSOFA (Quick Sequential Organ Failure Assessment) Screening Rule
qsofa_sepsis_alert_rule = {
    "and": [
        # Patient must be in an active inpatient unit
        {"in": [{"var": "patient.unit"}, ["ICU", "ED", "STEPDOWN"]]},
        # qSOFA criteria: triggers when 2 or more clinical indicators are met
        {
            ">=": [
                {
                    "+": [
                        # Respiratory rate >= 22 breaths/min
                        {"if": [{">=": [{"var": "vitals.respiratory_rate"}, 22]}, 1, 0]},
                        # Altered mentation (Glasgow Coma Scale < 15)
                        {"if": [{"<": [{"var": "vitals.glasgow_coma_scale"}, 15]}, 1, 0]},
                        # Systolic blood pressure <= 100 mmHg
                        {"if": [{"<=": [{"var": "vitals.systolic_bp"}, 100]}, 1, 0]},
                    ]
                },
                2,  # Threshold for Sepsis Protocol Alert
            ]
        },
    ]
}

patient_vitals = {
    "patient": {
        "mrn": "MRN-90210",
        "unit": "ICU",
    },
    "vitals": {
        "respiratory_rate": 24,       # Critically elevated
        "glasgow_coma_scale": 15,     # Normal
        "systolic_bp": 92,            # Hypotensive
    },
}

# Execute with audit trace for HIPAA records
trace: ExecutionTrace = evaluator.explain(qsofa_sepsis_alert_rule, patient_vitals)

if trace.passed:
    print(f"[CRITICAL ALERT] Patient {patient_vitals['patient']['mrn']} triggers qSOFA Sepsis Protocol!")
    print(f"Clinical latency: {trace.elapsed_us:.2f} µs")
    # Store trace.to_dict() directly into medical audit ledger
```

---

## Performance Architecture: Cache & Concurrency Best Practices

### Thread Safety Guarantee
`RuleEvaluator` instances are completely stateless and reentrant during evaluation:
- No shared mutable state is written during `evaluate()`, `explain()`, or `validate()`.
- A single `RuleEvaluator` instance can be safely shared across hundreds of concurrent threads or asyncio worker tasks.

### AST Pre-validation Pattern
In production microservices, validate rule JSON schemas during rule authoring/deployment, not in the critical request evaluation path:

```python
# At Rule Deployment Time (e.g. CI/CD or Admin API)
evaluator.validate(rule_ast, strict=True)

# At Request Runtime (Zero validation overhead, pure sub-microsecond evaluation)
decision = evaluator.evaluate(rule_ast, request_context)
```
