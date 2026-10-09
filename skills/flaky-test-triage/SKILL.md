---
name: flaky-test-triage
description: Triage a test that fails intermittently and fix it at its root rather than papering over it; use when a test passes locally but fails in CI, passes on rerun, depends on order, timing, ports, clock, locale, or random seed, or a red suite has destroyed trust in the whole build.
metadata:
  owner: Sherlock
  domain: debugging
---

# Flaky Test Triage

A red suite is worse than no suite: it teaches everyone to rerun, and it hides real failures.

## When to use
- A test fails intermittently, in CI only, in parallel runs, or only on some machines.
- A suite is being rerun or retried in CI, or green builds turn red without a code change.
- A test fails only when run after or before a specific other test.

## Stop the bleeding first
1. Quarantine the flaky test immediately so the suite goes green again. Do this before the deep
   investigation, because every hour of red trains people to ignore the suite.
2. Quarantine is not a fix and is never permanent. Every quarantined test gets a named owner
   and a written deadline, and it is tracked as a visible debt item.
3. Then investigate. The quarantine keeps the signal alive; it does not replace the work.

## Classify before fixing
- Real intermittent bug in product code — the most valuable and the most common.
- Test isolation defect: shared state, files, ports, global fixtures, or a singleton surviving
  a test.
- Environment dependency: port already bound, real clock, real network, filesystem limits,
  locale, timezone, available memory, CPU count, or container versus host differences.
- Ordering or shared-fixture coupling: depends on another test, or on its absence.
- Race: see `concurrency-debugging`.
- External service: a flaky third party. Mock or contract-test it, and if it cannot be, decide
  explicitly whether it belongs in this suite at all.
- Resource exhaustion: ports, file descriptors, connections, or threads not returned. See
  `resource-leak-hunting`.
- Random seed or time dependence: nondeterminism in the test itself.

## Procedure
1. Loop the single test many times with a fixed seed and one thread, then with all threads:
   `go test -count` and `-race`, pytest repetition plugins, `cargo test` with repeat flags,
   Jest with `--runInBand` versus parallel, and equivalents in other stacks.
2. Run it under race and sanitizer modes, not only in the normal build.
3. Run it with the whole suite, and with the suite split, to expose fixture and port coupling.
4. Bisect by disabling tests in halves until the failure follows a specific pair. Ordering bugs
   hide only in combination.
5. Capture the complete output, environment, seed, thread count, and machine on every failure.
   A report without the environment cannot be reproduced later.
6. Then hand the reproduction to `root-cause-analysis` and fix at the root.

## Verify
The test fails on demand before your fix and passes deterministically after: N consecutive runs,
in random order, in parallel, and under race detection, plus one full-suite run. Fix the root and
remove the quarantine. Do not leave a retry in place to hide a defect you have not found.

## Anti-patterns
- Not a retry, a rerun, or a longer timeout without first naming which class the failure is.
- Not an unconditional sleep; sleep is only legitimate when waiting for a real external event
  with a bounded condition, never as a guess at timing.
- Not a fixed port, a wall-clock time, or a locale-dependent assertion.
- Not shared mutable fixtures between tests, and not a singleton the suite forgets to reset.
- Not asserting on log text or map iteration or set ordering that is not guaranteed.
- Not re-quarantining a test that already failed once; that is how a suite dies.

## Prevention
Isolated, deterministic, order-independent tests: `testing-strategy`. Remove the shared state
and the race: `correctness-errors` and `concurrency-resources`. Bound the external dependencies:
`resilience`. Per-test and per-suite telemetry so flakes are attributed: `observability`.
