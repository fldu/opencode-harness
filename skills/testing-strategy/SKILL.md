---
name: testing-strategy
description: Choose test levels deliberately, keep tests hermetic and deterministic, and exercise failure paths rather than happy ones; Use when deciding what to test for a change, when a test is flaky or order-dependent, when a bug fix needs a regression test, when parsers or boundary code need property or fuzz coverage, or when throttling, queue, and concurrency behavior must be exercised under load.
metadata:
  owner: Jeff
  domain: implementation
---

# Testing Strategy

## When to use
- Before writing tests for a change, to pick the level.
- When a test flakes, hangs, or passes only in a particular order.
- Whenever a bug is fixed, or a limit, timeout, or retry policy is introduced.

## Rules
- **Test failure paths first**: timeout, retry exhaustion, breaker open, partial write, cancellation mid-operation, malformed input, duplicate delivery, limit exceeded, dependency unavailable. Each gets a test asserting the observable outcome (`correctness-errors` defines the outcomes).
- **Mix levels deliberately**:
  - unit — pure logic, no I/O;
  - integration — real wiring and real adapters, still hermetic;
  - contract — an interface you do not own, pinned to a recorded or published contract;
  - property / fuzz — parsers, decoders, canonicalization, and other boundary code (`security-implementation`);
  - load — throttling, queue depth, and backpressure behavior under increasing concurrency.
- **Hermetic and deterministic**: no network; inject the clock, the randomness source, and the id generator; no shared mutable global state; no ordering assumptions between tests; no dependence on wall-clock delays or on today's date.
- **Concurrency coverage runs under the ecosystem's race or sanitizer mode** (`-race`, `-fsanitize=thread`, `loom`, `miri`, …). If no such mode exists, or you cannot run it, say so explicitly — never imply it passed.
- **A flaky test is fixed or deleted, never retried into passing.** Re-running until green hides the defect it was reporting.
- **Every bug fix ships a regression test that fails without the fix.** Verify it by reverting the fix locally and watching it fail.
- **Assert operator-visible behavior and error messages**, not incidental formatting, unless that format is a documented contract.
- **Keep the suite runnable**: if a test needs a real dependency to be meaningful, gate it explicitly rather than letting it flake in the default run. Results go to `handoff-report`.

## Verify
- The suite passes deterministically: run it repeatedly, or with shuffled order or a random seed, and quote the results.
- Each failure mode introduced by the diff has a named failing-path test.
- Each fixed bug has a test observed to fail before the fix.
- The race or sanitizer command used is quoted, or the explicit statement that none was available.

## Anti-patterns
- Not a happy-path-only suite for a change that adds timeouts and retries.
- Not `sleep` to wait for async work — await a signal or inject a clock.
- Not a shared fixture mutated across tests.
- Not asserting an exact log line's formatting when only the message matters.
- Not a test that passes only because retries made it pass.