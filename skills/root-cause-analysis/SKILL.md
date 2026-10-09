---
name: root-cause-analysis
description: Diagnose the real cause of a defect from evidence instead of guesswork; use when a bug, hang, crash, leak, race, latency spike, or intermittent failure is unexplained and you need a proven root cause before writing any fix.
metadata:
  owner: Sherlock
  domain: debugging
---

# Root Cause Analysis

The procedure skill. It owns the hypothesis loop, nothing else. It defers how to measure to
`profiling` and how to read production artifacts to `production-signal-analysis`.

## When to use
- A defect is reported with no known cause: wrong output, hang, crash, corruption.
- A fix was applied and the symptom returned, or moved somewhere else.
- Two engineers disagree on the cause and the disagreement is about evidence, not taste.

## Name the three things separately
- **Symptom** — what was observed: verbatim, with timestamp, identifier, and environment.
- **Trigger** — the action or condition that started it, such as "first request after deploy".
- **Cause** — the mechanism that turns that trigger into that symptom.

"Memory grows to 4 GB" is a symptom. "Unbounded cache with no eviction" is a cause.

## Procedure
1. Write the observation down before theorizing: exact symptom, exact time, exact identifier,
   exact environment. If a stranger could not check it, you are not ready to investigate.
2. Inventory every data point, and mark which remain unexplained. An unexplained data point is
   the strongest lead you have; do not file it as noise.
3. State one falsifiable hypothesis: "if X is the cause, we will observe Y."
4. Name, before looking, the observation that would refute it. A hypothesis that cannot be
   refuted is a belief, not a hypothesis.
5. Go get exactly that observation, using the cheapest method that can produce it.
6. If refuted, discard the hypothesis whole and return to step 3. Never bend it to fit data.
7. If confirmed, ask what else that cause must also explain, and follow those consequences.
8. Reduce with a fault tree: symptom at the top, candidate causes below, OR/AND gates
   expanded only where evidence exists. 5 Whys is a prompt for this, not the method itself.
9. Fix at the cause, then run step 10. Do not reorder these.

## Verify — you have the cause when all three hold
- (a) The explanation accounts for every observed data point, **including the surprising ones**.
- (b) The explanation predicts an unobserved consequence, and you go confirm it is there.
- (c) The fix removes the symptom, and re-introducing the cause brings the symptom back.

Re-introduction is the proof. If you cannot re-break it on demand, you have a correlation.

## Anti-patterns
- Not a retry, a sleep, or a null check unless the cause is already identified.
- Not a patch at the point the symptom appears when the mechanism sits upstream.
- Not "works on my machine" — record the environment difference as a clue to explain.
- Not two hypotheses in flight at once; then neither is actually being tested.
- Not a rewrite of the component hoping the bug vanishes; you will not learn which change did it.

## Prevention
Close the blind spot that let this arrive unexplained: `observability`.
Prevent the class, not the instance: `correctness-errors`, `concurrency-resources`, `resilience`.
Make it fail loudly next time: `testing-strategy`.
