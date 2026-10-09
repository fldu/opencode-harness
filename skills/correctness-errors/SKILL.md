---
name: correctness-errors
description: Handle every error path explicitly so no failure is ignored or misrepresented; Use when writing or reviewing code that can fail — parsing, I/O, network, allocation, locking, cancellation — and when you see an empty catch, an unwrap or panic on input-reachable input, a discarded error return, or a loop or retry with no termination argument.
metadata:
  owner: Jeff
  domain: implementation
---

# Correctness & Errors

## When to use
- Any function that can fail for a reason a caller or operator could act on.
- Reviewing a diff that introduces a failure mode: a new call, parse, branch, or retry loop.
- Whenever an error is "handled" without appearing in a return value, a log, or a metric.

## Rules
- **Every failure path is explicit.** No empty catch, no ignored return value, no `unwrap`/`panic`/abort on any input-reachable failure. A panicking path must be provably unreachable from untrusted input — say why in a comment.
- **Never swallow silently.** If an error is genuinely non-actionable, record it once at `warn` or `debug`, including the reason it is non-actionable, and count it. Never at `error` (that level must mean a human acts), never nowhere.
- **Errors carry actionable context**: operation, resource, identifiers, and the cause chain preserved. Never secrets, tokens, raw request or response bodies, or personal data (`security-implementation`).
- **Classify failures in the type or API surface**, not in each caller's guesswork: *transient* (retryable — timeout, connection reset, contention, temporary unavailability, server-side failure, some rate limits) versus *permanent* (fail fast — malformed input, not found, denied, unsupported, most client errors). Add a class only deliberately; `resilience` consumes this classification and must not redefine it.
- **Fail closed on security-relevant checks.** Fail open only when the failure mode is documented, recoverable, and observed.
- **Make invalid states unrepresentable**: validate and normalize at the boundary, then let types and invariants carry validity downstream instead of re-checking.
- **Termination argument for every loop, recursion, and retry**: a bound that decreases, a counter that caps, or a deadline. No unbounded retry-until-success, no recursion without a depth bound.
- **Timeout on every blocking call, await, and lock acquisition** — including the ones that are "always fast". Derive it from the caller's remaining budget, never a fresh constant (`resilience`).
- **Cleanup on every exit path**, including cancellation, error, and early return: release locks, close handles, roll back partial writes. Prefer scoped, RAII, or with-statement forms where the language offers them.
- **Partial work is atomic.** Choose temp-then-rename, a transaction, or idempotency with a documented key — pick one on purpose. Never a read-modify-write a crash can interleave.
- **Monotonic clock for durations**; wall clock only where a human reads it. Never derive an interval by subtracting two wall-clock reads.

## Verify
- Every `catch`/`except`/`unwrap`/`panic` in the diff is handled, re-raised with context, or justified in a comment.
- Grep the diff for discarded returns and bare `catch`/`except`; account for each hit by name.
- Inject one failure per new error path (test double, closed port, exhausted quota, cancellation) and assert the observable outcome (`testing-strategy`).
- Confirm cleanup and atomicity on the error path, not only on success.

## Anti-patterns
- Not "log and continue" — log once with the reason, or propagate with context.
- Not `catch (e) {}` — an empty handler hides the failure the metric should count.
- Not an error message built from user input or a raw provider payload.
- Not a retry loop with no cap and no classification.
- Not a "best effort" write with no atomicity story and no idempotency key.