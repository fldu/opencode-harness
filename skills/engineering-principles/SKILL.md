---
name: engineering-principles
description: Apply the repo's nine decision principles in a fixed order as the tie-breaker when rules collide, a reviewer objects without naming a rule, or a choice must be made between a minimal fix and a general framework; Use when two skills or two conventions disagree, when an abstraction or an optimization is proposed without evidence, when designing for growth or for failure, or when something is "obviously fine" and nobody can say why.
metadata:
  owner: Jeff
  domain: shared
---

# Engineering Principles

## When to use
- Two rules, two skills, or two reviewers demand opposite things and one must lose.
- A design, abstraction, optimization, or cache is justified by intuition rather than by evidence.
- The happy path is correct and you are choosing what happens when the process dies, the clock skews, or the load multiplies.

## Rules
Apply in this order; earlier principles outrank later ones. They are principles, not laws — a documented, measured exception beats blind compliance.

1. **Keep It Simple** — the smallest change that fully solves the problem.
   - In code: one obvious way to do a thing; no knob without a caller, no abstraction before a second real use, no flag for a hypothetical future.
   - In review: "which of these lines can be deleted without changing behavior?" If none can, the diff is too big.
2. **Compute It's Worth It** — optimize only where a measurement shows it matters.
   - In code: the hot path is faster because a profile said so, and the evidence is cited (`performance-measurement`).
   - In review: an optimization with no before/after number is rejected, not merged "as a precaution".
3. **Don't Put Holes in the Abstractions** — never leak platform, transport, or vendor detail through an interface.
   - In code: callers pass domain values; the edge module is the only place that knows it is HTTP, SQL, or that vendor.
   - In review: a signature that forces the caller to know the backend is a hole; push the special case to the edge.
4. **Plan for Reuse and Extensibility** — one obvious way, at one layer.
   - In code: a second implementation gets an interface behind the first, never a fork of it.
   - In review: duplication across call sites is the signal to extract; duplication inside one function is not.
5. **Amortization of Resources** — batch, reuse, and cap.
   - In code: buffered I/O, pooled connections and handles, bounded queues and buffers (`concurrency-resources`).
   - In review: any collection that can grow without a stated bound is a defect, not a tuning question.
6. **Design for the Long Term** — the code outlives the ticket and the author.
   - In code: comments say *why*, not *what*; a comment the code makes false is deleted, not kept. Docs and ADRs carry *what*.
   - In review: "will the next reader understand the constraint this line exists to satisfy?"
7. **Data Doesn't Lie / Measure Everything** — never reason from averages.
   - In code: latency as p50/p95/p99, plus throughput, error rate, saturation (queue depth, pool use), cost per op.
   - In review: "what number would prove this claim, and was it collected?" No number means no claim.
8. **Unpredictability of Scaling** — assume crashes mid-write, clock skew, partitions, slow dependencies, and every peer retrying at once.
   - In code: idempotent handlers, monotonic durations, retry budgets, backpressure (`resilience`).
   - In review: "what happens when 100 peers fail simultaneously?" Single-failure reasoning is incomplete.
9. **Design for Failure in the Real World** — plan soft vs hard state, quotas, and graceful degradation.
   - In code: derived state is rebuildable from a source of truth; quotas exist per caller; overload behavior is chosen in advance, not discovered.
   - In review: "what does the user see at 10x load?" If the answer is "nothing, it just queues", reject it.

## Verify
- Every significant choice in `handoff-report` names the principle that justified it, and the evidence if the principle is not self-evident.
- Every optimization cites a before/after measurement; every abstraction cites its second use.
- Every growth path has a cap or a documented rejection.

## Anti-patterns
- Not "principles are guidance, feel free" — name the principle that overrides the one you are breaking.
- Not "simple means smallest diff" — simple means fewest concepts.
- Not "designed for scale" — show the bound, the queue policy, and the saturation gauge.
- Not "we'll optimize later" — later is never measured, and the hot path becomes the default path.
- Not "fail closed everywhere" — unavailable is a valid failure mode when it is documented (`escalation-rules`).