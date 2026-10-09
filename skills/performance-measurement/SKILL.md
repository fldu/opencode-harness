---
name: performance-measurement
description: Measure before and after and report distributions together with method, input size, and concurrency level; Use when claiming a path is faster or cheaper, when touching a hot path or allocation pattern, when setting or checking a latency budget, or when a micro-benchmark looks suspiciously good and you need to know whether it can detect the regression it claims.
metadata:
  owner: Jeff
  domain: implementation
---

# Performance Measurement

## When to use
- Any change to a hot path, allocation pattern, serialization, or query.
- Before and after any performance claim, including "this should be faster".
- When a budget exists, or should exist, for a request path, job, or render.

## Rules
- **Measure before and after.** Report the numbers *and the method*: command, machine class, input size, concurrency level, run count, warmup. "Faster" without a number is not a result — write "no measurable change" when there is none (`handoff-report`).
- **Report distributions, never means**: p50, p95, p99, plus max where tails matter. A mean hides the tail that pages you. State the sample size.
- **State the workload explicitly**: input size, concurrency level, and whether the run was steady-state or included warmup and cold-cache effects. A number without these is not comparable to anything.
- **Budgets are defects, not aspirations**: an explicit per-operation budget for a hot path, checked in the same place as correctness. Exceeding it fails like a test.
- **Optimize the dominant cost only**, citing the profile, trace, or measurement that identified it. Optimizing a 2% term is churn.
- **Know your benchmark's blind spots** — a benchmark cannot detect a regression it does not exercise:
  - dead-code elimination — the compiler deletes work whose result is unused; consume the result and confirm the optimizer kept it;
  - insufficient warmup — tiered, JIT, or lazily-populated caches make first runs look like wins;
  - allocator noise — reuse allocator state, or measure allocations and bytes per op, not only wall time;
  - cache and alignment effects — a micro-benchmark on one hot cache line is not a workload;
  - harness overhead — the measurement cost must sit below the effect being claimed.
- **Keep benchmarks out of the correctness gate** unless they are stable; a noisy gate teaches everyone to ignore it.

## Verify
- The report shows before and after numbers, the command, and the input and concurrency level.
- Re-running the benchmark at least twice reproduces the same order of magnitude.
- The claim names the evidence that identified the dominant cost.
- If the result is within noise, the report says so instead of claiming an improvement.

## Anti-patterns
- Not "reduced allocations" with no count — report allocations and bytes per op.
- Not a mean latency in a ticket.
- Not a micro-benchmark with one iteration and no warmup.
- Not comparing numbers taken at different input sizes.
- Not a benchmark that cannot fail — if it never varies, it detects nothing.