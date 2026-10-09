---
name: concurrency-debugging
description: Find races, deadlocks, livelocks, lost updates, and use-after-free from evidence rather than intuition; use when failures are intermittent, timing or load dependent, appear only under concurrency or only in CI, hang without crashing, or corrupt shared state.
metadata:
  owner: Sherlock
  domain: debugging
---

# Concurrency Debugging

Intermittent means unobserved, not absent. Get a reproduction before theorizing.

## When to use
- The failure is timing, load, ordering, or environment dependent, or is CI-only.
- A program hangs, spins without progress, or blocks forever with no crash.
- Values are corrupted, lost, or seen twice; objects are used after they should be gone.
- Production only. Concurrency bugs hide in the field because field interleavings are richer
  than any test you wrote, so treat "works in CI" as a scheduling clue naming the missing
  interleaving, not as an excuse.

## Procedure
1. Reproduce under load with concurrency turned up, not a single-threaded sequential run.
2. Loop the suspect operation many times with a fixed seed where randomness is involved.
3. Inject deliberate delays and yields at every shared-state access point: that is where it hides.
4. Randomize interleavings deliberately, or exhaustively if the state space is small.
5. Compare against the deterministic scheduler: single-threaded, one worker, one core pinned.
   A bug that disappears when serialized is a concurrency bug until proven otherwise.
6. If tooling is unavailable, record every shared location, enumerate the orderings that break an
   invariant, and reason about happens-before explicitly.

## Tools ladder, pick the cheapest that answers the question
- Race detector: `-race` in Go, `-fsanitize=thread` for ThreadSanitizer in Clang, GCC, Android
  NDK and Rust nightly, and TSan ports used by other JVM and managed-runtime ecosystems. TSan cannot be
  combined with ASan in one build, so run separate builds.
- Exhaustive interleaving search: `loom` in Rust, `herd7` in OCaml, Jepsen or the Shepherd
  style histories for distributed systems, `jcstress` for Java.
- Dynamic analysis: stress loops, delayed injection, and running under the race detector in
  the test suite rather than only locally.
- Lock-order and deadlock detection: ThreadSanitizer reports lock-order inversion, Helgrind and
  DRD under Valgrind, thread dumps such as `jstack` for blocked monitors, Go mutex and block
  profiles, and analyzer passes that build a lock graph.
- With only a dump, read every thread's state: what it holds, what it waits for. A cycle in the
  wait-for graph is the deadlock, and the dump is the proof.

## Hazard patterns to grep for
- Shared counters and maps mutated without a lock or atomics, including in fast paths.
- Check-then-act across an await, yield, or callback: read, then decide later.
- Time-of-check to time-of-use on a path, file, key, or handle that another actor can change.
- ABA: a value returns to its old state between compare and swap, so identity is not enough.
- Callbacks, observers, and listeners outliving their owner or its dependencies.
- Cancellation and early-return paths that skip cleanup, unlock, or drain.
- Unbounded fan-out of tasks or futures with no cap and no backpressure.
- A high-priority or interactive task waiting on a low-priority holder: priority inversion.
- Unbounded retries with no jitter, which converts a stall into a livelock.

## Verify
The interleaving must fail on demand before your fix and not after: N runs, every thread count, and
under race detection, plus one re-introduced bug that fails again. A race you cannot provoke is unproven.

## Anti-patterns
- Not a fix based on adding a lock because it looked racy; name the invariant first.
- Not a sleep to "let the race settle"; sleeps hide bugs and add latency everywhere.
- Not a global lock or a queue where a clear ownership invariant was the real answer.
- Not trusting a passing single-threaded run; concurrency bugs are order-dependent.
- Not closing over mutable state shared across invocations without a per-invocation boundary.

## Prevention
Design ownership so the invariant is structural: `concurrency-resources`. Bound fan-out,
retries, and queues: `resilience`. Keep concurrency under continuous race detection:
`testing-strategy`. Surface the stalled state in production: `observability`.
