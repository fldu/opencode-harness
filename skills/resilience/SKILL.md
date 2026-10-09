---
name: resilience
description: Make every remote call survive a slow, flaky, or absent dependency without turning one failure into an outage; Use when adding or changing a network, queue, database, cache, or third-party call, when a timeout is missing or is a bare constant, when retries are unbounded or non-idempotent, when a dependency can be overloaded or down, or when load must be shed at a boundary.
metadata:
  owner: Jeff
  domain: implementation
---

# Resilience

## When to use
- Any call that leaves the process, or that waits on a resource another party controls.
- Adding or changing retry, timeout, breaker, bulkhead, throttle, or backpressure behavior.
- Symptoms: latency climbing under load, retry storms, a dependency outage taking down its callers, a queue growing without limit.

## Rules
- **Deadline first.** Every external call gets an explicit timeout, including the ones that are "always fast". Maintain **one end-to-end deadline** and propagate it downward: a child timeout never exceeds the caller's remaining budget, and a caller nearly out of budget issues no new calls.
- **Retry only when the operation is idempotent** or carries a documented idempotency key. Exponential backoff with **full jitter** (uniform over the whole window, not a fixed multiplier), capped attempts, capped delay, total retry time bounded by the deadline. Honor `Retry-After` when the server sends it.
- **Budget the retries.** A bounded percentage of requests may retry, enforced by a shared token budget rather than a per-request counter. Retry amplification is a second outage, not a mitigation.
- **Circuit breaker** per independently-failing dependency: closed until a failure-rate or latency threshold over a minimum volume, open to fail fast with no queueing, half-open with a small fixed number of probes, closed again after sustained success. While open, fail immediately — never queue work for a known-down dependency.
- **Bulkhead** per dependency: dedicated workers, threads, connections, or concurrency permits, so one slow dependency cannot starve the others.
- **Throttle at the boundary that owns the resource**, not at each caller: token or leaky bucket with a documented rate and burst size. Always return a retry hint (status plus a `Retry-After`-equivalent); never drop silently.
- **Backpressure propagates to the caller** instead of accumulating into unbounded memory: bounded queue plus explicit rejection, or blocking bounded by the deadline.
- **Degrade by design**: decide in advance what happens when overloaded — reject fast, serve a stale cache, sample, shed a feature — and make the degraded mode observable (`observability`).
- **Retries are not a fix for a slow dependency.** If p99 is dominated by one call, the answer is a deadline and a fallback, not more attempts.
- Failure classification (transient vs permanent) is defined in `correctness-errors`; this skill consumes it and must not redefine it.

## Verify
- Grep the diff for every new external call; each has a timeout derived from a propagated deadline.
- Test each mechanism in isolation with a controllable fake: breaker closed → open → half-open → closed, retry exhaustion at the cap, throttle rejection returning a retry hint.
- The deadline test asserts that child timeouts sum to less than the parent's remaining budget.
- Quote the retry-budget configuration and the amplification ratio it enforces.

## Anti-patterns
- Not a bare default timeout on every call — a deadline the caller controls.
- Not retrying a non-idempotent write without an idempotency key.
- Not fixed backoff — without full jitter you synchronize the herd.
- Not an open breaker that still queues requests.
- Not "we'll add the breaker when we see problems" — it ships with the call.
- Not a throttle that drops silently with no signal to the caller.