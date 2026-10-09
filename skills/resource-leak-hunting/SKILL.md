---
name: resource-leak-hunting
description: Tell a true leak apart from retention, high-water-mark, and expected growth, then attribute it to a code path; use when file descriptors, sockets, connections, goroutines, tasks, threads, timers, memory, cursors, or child processes grow monotonically, hit a limit, or exhaust a long-lived process.
metadata:
  owner: Sherlock
  domain: debugging
---

# Resource Leak Hunting

## When to use
- A long-lived process eventually fails on out-of-memory, too-many-open-files, or thread limits.
- Handle counts, task counts, memory, or log and buffer sizes grow and never come back down.
- Throughput decays over hours while per-request cost looks flat.

## Classify before hunting
- **Leak** — unreachable and never reclaimed; the count grows past the peak working set.
- **Retention** — no longer needed but still referenced; fix the retainer, not the allocator.
- **High-water-mark** — pools, caches, arenas, buffers holding the maximum ever seen; flat.
- **Expected growth** — a set that legitimately grows, such as a per-tenant map; bound it.
Do not call it a leak until growth continues past the peak working set.

## What leaks
Descriptors, sockets and connections in pooled and non-pooled paths, tasks, goroutines, threads, timers
and cancellation sources, native allocations, temp files, child processes, database cursors, and log,
metric, and buffer growth. Unreleased resources usually hide on the error path, not the happy path.

## Procedure
1. Baseline the count and footprint at steady state, not at startup.
2. Delta: run the workload N times, or for T, with the process otherwise idle.
3. Rate per iteration or request: a delta that never returns to baseline is the leak, a slope that flattens is a high-water-mark.
4. Attribute to a code path: take a handle or memory dump and group by identity, name, stack, or caller. The dominant group is the suspect.
5. Separate allocators from retainers. The allocation site says where it was made, the retaining path
   says why it is still alive. Only the retainer explains the leak.
6. Count what is live, not what is open: enumerate handles per process, dump tasks and threads, read in-use allocation profiles.
7. Confirm deterministically, per Verify below, then hand the cause to `root-cause-analysis`.

## Tools, by resource
- Handles: per-process descriptor listings, `lsof`, open and close syscall tracing, socket state listings.
- Tasks and threads: task and thread dumps, scheduler dump commands, leaked-task detectors such as
  LeakSanitizer in C and C++ and the equivalents elsewhere.
- Memory and retainers: heap dumps with dominator trees, retained-size reports, in-use versus
  allocated-space profiles, native allocation trackers, LeakSanitizer or Valgrind.
- Downstream: database session and cursor stats, pool metrics, broker consumer state. A
  server-side leak shows up as your own client count growing.

## Verify
Never prove a leak by running out of memory. Run the workload K times, assert the count returns to
baseline after each cycle, then re-introduce the leak and confirm the assertion fails.

## Anti-patterns
- Not treating growth that plateaus as a leak; that is a high-water-mark.
- Not blaming the allocator when a stale reference is the retainer.
- Not counting allocations instead of live objects; churn is performance, not a leak.
- Not ignoring pooled resources; a pool missing an error-path return leaks silently.
- Not assuming a leaked descriptor is a network problem; check for a file, pipe, or device.

## Review checklist for pooled resources
- Returned on every exit path: success, error, throw, cancel, panic, and early return.
- Returned by a scope guard, `defer`, `finally`, or an RAII wrapper, so no path can forget it.
- Unbounded growth impossible: pools, caches, and queues have caps and eviction.
- Leaked-handle and descriptor-count assertions already exist in the suite.

## Prevention
Ownership and scope-bound release: `concurrency-resources`. Caps and eviction: `resilience`.
Counters, limits, and saturation alerts: `observability`. Leak assertions and soak tests:
`testing-strategy`. Correct free and error handling: `correctness-errors`. Using a handle after
return is a race, so hand that hazard to `concurrency-debugging`.
