---
name: concurrency-resources
description: Give every piece of shared mutable state one owner, keep locks narrow, and cap every collection, pool, and queue; Use when code runs on more than one thread, task, or coroutine, when adding a cache, pool, queue, or worker, when a handler must tolerate duplicate delivery, or when you see unsynchronized lazy init, a lock held across I/O, or an unbounded buffer.
metadata:
  owner: Jeff
  domain: implementation
---

# Concurrency & Resources

## When to use
- Any code with threads, tasks, coroutines, callbacks, signals, or shared mutable state.
- Adding a cache, connection pool, worker pool, queue, buffer, or semaphore.
- A handler that may receive the same message twice, or a cleanup path that must free on every exit.

## Rules
- **One documented owner** for every piece of shared mutable state: a single writer thread or task, an actor, or a named lock. "Probably safe" is not a design — write the ownership down where the state is declared.
- **Locks are narrow** and cover pure computation only. **Never hold a lock across I/O, an await, or a callback into code you do not own** — that is a deadlock waiting on a slow dependency.
- **State a lock ordering rule** when more than one lock exists, document it at the declaration, and confirm no cycle; add an assertion if the language allows.
- **No unsynchronized lazy initialization.** Build the value before the state is shared: eager init, a once-style primitive, or an immutable value constructed at construction time.
- **Every collection is bounded**, with the overload policy stated in one word at the declaration: *block*, *reject*, *shed*, or *sample*. A library default is not a decision.
- **Pools are capped and return on every path.** Every acquire has a matching release on success, error, cancellation, and unwind; use scoped or RAII forms where available.
- **Batch the work**: group reads and writes, avoid N+1 access, coalesce events over a flush window. Document the window and its latency cost.
- **Allocation discipline in hot paths**: reuse buffers explicitly, avoid per-item allocation in a loop, and never log inside a per-item loop (`observability`).
- **Cancellation is part of the contract**: every cancellable operation checks for cancellation at a bounded interval and propagates it to its children.
- **Consumers are idempotent.** At-least-once delivery means the handler tolerates duplicates — `data-compatibility` for the durable-key pattern, `resilience` for who retries.

## Verify
- Run the concurrency tests under the ecosystem's race or sanitizer mode (`-race`, `-fsanitize=thread`, `loom`, `miri`, …) and quote the command; if none exists, say so explicitly instead of implying a pass.
- Grep the diff for lock acquisition and confirm none spans an I/O or await point.
- Every added collection shows a literal cap and a named overload policy at its declaration.
- A test asserts the pool returns to its initial size after a run that injects errors and cancellation.

## Anti-patterns
- Not a lock held "just for the log call".
- Not `if cache is None: cache = build()` on a shared path.
- Not a queue with a default size you did not choose.
- Not an unbounded map used as a cache in a long-lived process.
- Not the same work retried in two places at once — one owner retries (`resilience`).