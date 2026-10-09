---
name: performance-regression-gates
description: Gate merges on measurable performance loss using a benchmark whose noise floor is known and whose comparison is a distribution rather than a single run; Use when adding a benchmark to CI, choosing which metrics are stable enough to gate, storing or comparing a baseline across branches, or when a performance gate keeps false-alarming and is about to be disabled or downgraded to a warning.
metadata:
  owner: Jozef
  domain: infrastructure
---

# Performance Regression Gates

> Scope — the gate around the benchmark. How to measure (method, workload, distributions, dead-code elimination) is `performance-measurement`; this skill owns noise, thresholds, baselines, and block-or-warn.

## When to use
- Adding a benchmark to CI, or repairing one that false-alarms.
- A regression reached production that a benchmark could have caught.
- Deciding whether a metric is stable enough to block a merge.
- Someone proposes "just add a perf check" and nobody has said what it compares against.

## Rules

**A gate needs a noise floor before it needs a threshold**
- Measure the floor first — run the unchanged commit N times (N ≥ 10 for anything sub-percent) on a fixed runner class, and record the median plus the run-to-run spread. Without that number a threshold is a feeling.
- Remove the variance you control: fixed runner or host class labelled in the job definition, pinned toolchain and dependencies, fixed input data and seed, no noisy neighbours, discarded warmup, and no parallel job competing for the same cores.
- Compare **distributions, not single runs**. One run against a stored baseline is a false-alarm generator, and it is the usual reason gates get switched off.
- Fail when the median of N runs regresses by more than `threshold × measured noise floor` (3× the observed relative spread is a common starting point), expressed in config, not in a comment.
- Gate on relative regression against a baseline; the absolute budget is a separate check (`performance-measurement`).

**What to gate, and what to leave alone**
- Gate metrics that are cheap, stable, and causally linked to user cost: allocations per operation and bytes per op, latency at a fixed small workload, binary or image size, cold-start time, query or syscall count, dependency count.
- Do not gate networked or shared-service wall-clock latency in CI — that variance belongs to the environment, not the code, and the gate will teach everyone to ignore it.
- Do not gate a metric whose harness overhead is comparable to the effect it claims to detect.
- One gate per regression class. Fifteen noisy gates are fifteen reasons to ignore the wall.
- Every gated metric has a named owner who may fix it, and a stated path for when it cannot be fixed quickly.

**Baselines**
- Store the baseline where CI can read it without a human — artifact, cache keyed by commit, or results store — named with the metric, the machine class, and the commit.
- Compare against the merge base with the mainline branch, not the branch tip, so a regression accumulated over a long branch is still caught.
- Record the environment with the number (runner class, toolchain version, data-set hash). A baseline without its environment is not comparable.
- Never update a baseline as a side effect of a failing gate. That is baseline laundering; a baseline bump is a reviewed change with a stated reason.
- Keep a short history per metric, so "2% above where we were three months ago" is answerable.

**Honest harness**
- Consume the measured result so the optimizer cannot delete the work, and confirm the work survives in the binary or the profile (`performance-measurement`).
- The benchmark must not be able to detect or shortcut the gate — no expected value from an env var, config file, or fixture path. A benchmark that can see the gate will be tuned to it.
- Pin the harness version with the baseline; changing harness and code in one run makes the comparison meaningless and must fail rather than silently re-baseline.
- Fail loudly when the harness errors. A benchmark that skipped and reported pass is worse than no benchmark.

**Block, do not warn**
- A failing gate **blocks the merge**. A warning gate is a comment, and comments do not prevent regressions.
- The only permitted downgrade is a brand-new metric — land it in warn mode, record its measured noise floor, promote it to blocking in a follow-up change that states the threshold.
- Disabling or downgrading an existing gate requires the evidence (false-alarm count, noise measurements) in the change and a named owner; escalate if the pressure is not technical (`escalation-rules`).
- A gate that fires more than about once in two weeks on unchanged code is miscalibrated — fix the threshold or the harness. Do not add a retry loop; that only trains everyone to re-run.

## Verify
- The noise floor is written down — N, runner class, and the observed spread of the unchanged commit — quoted from a run.
- The threshold in config is a multiple of that measured floor.
- A deliberately injected regression (N% slower, or one extra allocation per op) is caught on a scratch branch, and the output names the metric, both numbers, and the baseline commit.
- A no-op change does not fail the gate across 10 consecutive runs.
- The baseline names commit and environment, and the comparison uses the merge base with mainline.
- Delete the baseline and the harness cache, re-run, and confirm the job still returns a decision rather than a skip.

## Anti-patterns
- Not a single run against a stored number — N runs, compared as distributions against a measured floor.
- Not a hardcoded "10% slower" with no measured spread behind it.
- Not a warning-only gate — it blocks, or it is not a gate.
- Not re-baselining in the run that failed, and not a retry loop to smooth a flake.
- Not gating a networked benchmark whose variance belongs to the environment.
- Not a benchmark that can shortcut the gate, and not one that passes when the harness errors.
- Not adding a metric to the gate before measuring its noise floor.
