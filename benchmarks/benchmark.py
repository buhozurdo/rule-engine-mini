"""
Empirical Benchmark Suite for rule-engine-mini.

Measures latency percentiles (p50, p90, p95, p99, p99.9), ops/sec throughput,
and memory allocations across standard industrial workloads.
"""

import gc
import json
import os
import statistics
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from rule_engine_mini import RuleEvaluator


def run_benchmark(
    name: str,
    rule: Any,
    context: Any,
    iterations: int = 100_000,
    warmup: int = 10_000,
    use_explain: bool = False,
) -> Dict[str, Any]:
    evaluator = RuleEvaluator()

    # Warmup phase (JIT/tier-2 adaptive specialization warming)
    if use_explain:
        for _ in range(warmup):
            evaluator.explain(rule, context)
    else:
        for _ in range(warmup):
            evaluator.evaluate(rule, context)

    # Disable GC during tight measurement loops to measure pure execution latency
    gc.collect()
    gc.disable()

    latencies_ns: List[int] = []
    append_time = latencies_ns.append

    t_start = time.perf_counter()
    if use_explain:
        for _ in range(iterations):
            t0 = time.perf_counter_ns()
            evaluator.explain(rule, context)
            append_time(time.perf_counter_ns() - t0)
    else:
        for _ in range(iterations):
            t0 = time.perf_counter_ns()
            evaluator.evaluate(rule, context)
            append_time(time.perf_counter_ns() - t0)
    total_time = time.perf_counter() - t_start

    gc.enable()

    # Memory profiling
    tracemalloc.start()
    m0_current, m0_peak = tracemalloc.get_traced_memory()
    for _ in range(1_000):
        if use_explain:
            evaluator.explain(rule, context)
        else:
            evaluator.evaluate(rule, context)
    m1_current, m1_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    latencies_ns.sort()
    n = len(latencies_ns)

    def percentile(p: float) -> float:
        idx = min(int(n * p), n - 1)
        return latencies_ns[idx] / 1000.0  # microseconds

    p50 = percentile(0.50)
    p90 = percentile(0.90)
    p95 = percentile(0.95)
    p99 = percentile(0.99)
    p999 = percentile(0.999)
    mean_us = (statistics.fmean(latencies_ns)) / 1000.0
    throughput = iterations / total_time

    return {
        "workload": name,
        "iterations": iterations,
        "ops_per_sec": int(throughput),
        "mean_us": round(mean_us, 3),
        "p50_us": round(p50, 3),
        "p90_us": round(p90, 3),
        "p95_us": round(p95, 3),
        "p99_us": round(p99, 3),
        "p999_us": round(p999, 3),
        "peak_mem_bytes": m1_peak - m0_peak,
    }


def main() -> None:
    workloads: List[Tuple[str, Any, Any, bool]] = [
        (
            "Micro Comparison (single >)",
            {">": [{"var": "cart.total"}, 100]},
            {"cart": {"total": 150}},
            False,
        ),
        (
            "Short-Circuit Fast-Path (or[0]=True)",
            {"or": [{"==": [{"var": "tier"}, "platinum"]}, {">": [{"var": "points"}, 50000]}]},
            {"tier": "platinum", "points": 100},
            False,
        ),
        (
            "Production Composite (4-way and)",
            {
                "and": [
                    {">=": [{"var": "order.total"}, 100]},
                    {"in": [{"var": "shipping.country"}, ["US", "CA", "MX"]]},
                    {"==": [{"var": "user.is_verified"}, True]},
                    {"<": [{"var": "user.risk_score"}, 25]},
                ]
            },
            {
                "order": {"total": 240},
                "shipping": {"country": "MX"},
                "user": {"is_verified": True, "risk_score": 12},
            },
            False,
        ),
        (
            "Collection Quantifier (all items active)",
            {"all": [{"var": "users"}, {"==": [{"var": "status"}, "active"]}]},
            {"users": [{"status": "active"} for _ in range(10)]},
            False,
        ),
        (
            "Collection Projection (filter + map)",
            {
                "map": [
                    {"filter": [{"var": "items"}, {">=": [{"var": "price"}, 50]}]},
                    {"*": [{"var": "price"}, 0.9]},
                ]
            },
            {"items": [{"price": 20}, {"price": 60}, {"price": 100}, {"price": 40}]},
            False,
        ),
        (
            "Audit Trace explain() Engine",
            {
                "and": [
                    {">=": [{"var": "order.total"}, 100]},
                    {"in": [{"var": "shipping.country"}, ["US", "CA", "MX"]]},
                    {"==": [{"var": "user.is_verified"}, True]},
                ]
            },
            {
                "order": {"total": 240},
                "shipping": {"country": "MX"},
                "user": {"is_verified": True},
            },
            True,
        ),
    ]

    print("\n==========================================================================================")
    print("                     RULE-ENGINE-MINI EMPIRICAL BENCHMARKS")
    print("==========================================================================================")

    results = []
    for name, rule, ctx, use_explain in workloads:
        res = run_benchmark(name, rule, ctx, iterations=100_000, use_explain=use_explain)
        results.append(res)
        print(f"-> {name:<42} | Throughput: {res['ops_per_sec']:>10,d} ops/s | p50: {res['p50_us']:>5.2f} us | p99: {res['p99_us']:>5.2f} us")

    print("\n### Markdown Benchmark Table\n")
    print("| Workload | Throughput (ops/sec) | Mean | p50 (Median) | p90 | p95 | p99 | p99.9 | Alloc Overhead |")
    print("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    for r in results:
        print(
            f"| **{r['workload']}** | {r['ops_per_sec']:,} | {r['mean_us']} µs | {r['p50_us']} µs | {r['p90_us']} µs | {r['p95_us']} µs | {r['p99_us']} µs | {r['p999_us']} µs | {r['peak_mem_bytes']} bytes |"
        )

    with open("benchmarks/results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved benchmark metrics to benchmarks/results.json\n")


if __name__ == "__main__":
    main()
