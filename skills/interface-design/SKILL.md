---
name: interface-design
description: Design a contract other code depends on by specifying shape, semantics, and failure modes together — idempotency, timeouts, rate limits, cursor pagination, an error taxonomy a caller can act on, versioning, and field sizing — so retries, queues, and old clients stay correct; Use when defining or changing a public API, service interface, event or queue schema, RPC or CLI surface, webhook, or any boundary crossing a process or a team.
metadata:
  owner: Daedalus
  domain: architecture
---

# Interface Design

## When to use
- Defining or changing a public API, service interface, event or queue schema, RPC or CLI surface, or webhook.
- Any boundary crossing a process or a team, where another party codes against what you write.
- A consumer is about to be told an error changed, or a field is about to be removed.

## Rules

**An interface is a promise: specify shape, semantics, and failure modes.** Most designs specify only shape, and the consumer then guesses the rest.

**Every operation states:**
- **Idempotency** — safe to retry? Does it carry an idempotency key, and for how long is that key honoured?
- **Timeout expectation** — what a caller should wait, and what happens server-side after it passes.
- **Rate limits** — the number, the window, and the response shape when exceeded.
- **Pagination** — cursor-based for anything that can grow. Never offset pagination on a mutating or large collection: rows shift underneath the offset.
- **Error taxonomy** — distinguish invalid-request, unauthenticated, unauthorized, not-found, conflict, rate-limited, and transient-dependency-failure. **A caller cannot build correct retry behaviour from an undifferentiated error.**
- **Partial-failure behaviour** — what is committed when a multi-step operation fails halfway.

**Retry, timeout, breaker, and backpressure mechanics are not designed here.** State the contract each operation needs and defer the mechanism to `resilience`. Likewise load and queue bounding belong to `concurrency-resources`. Design the promise; those skills implement it.

**Determinism and idempotency are what make retries, queues, and replication safe.** Treat any operation whose result changes on retry as a defect, not a caveat.

**Envelopes** carry a correlation identifier, a timestamp, and a schema version. The correlation identifier is what makes one request traceable across producers and consumers (`observability`).

**Data types**
- Prefer explicit and closed over open; size every field and every collection. An unbounded collection in a contract is an unbounded queue in production.
- An added enum value must not break an existing consumer: enums travel with an explicit *unknown* branch, or stay open with documented handling.

**Versioning**
- Additive changes are compatible; removals and semantic changes are not. Default to additive, with a deprecation window and a stated removal version.
- A breaking change requires a new major version **and** a migration path — never a coordinated deploy across teams.

**Consistency.** Naming and shape must match the existing surface; where it cannot, say why in the specification. Errors must not leak internals, stack traces, or the existence of resources the caller may not see.

## Verify
- A caller written against only this specification can retry **every** operation safely, or the spec says which ones it cannot.
- Every error tells the caller whether to retry, back off, or stop — read the taxonomy as a stranger would.
- Every collection is paginated with a cursor, and every field has a stated maximum size.
- Adding an enum value and adding a field were both checked against an old consumer (`data-compatibility`).
- Every breaking change has a version bump, a deprecation window, and a migration path.
- No error body reveals a stack trace, an internal host, or the existence of another tenant's object.

## Anti-patterns
- Not a field list — a field list has no idempotency, no failure modes, and no retry contract.
- Not `errors: 500`; that tells the caller nothing it can branch on.
- Not a breaking rename inside a minor version.
- Not an unbounded list, and not offset pagination on data that changes.
- Not an enum that crashes an old consumer the day a new value ships.
- Not an error message that confirms a resource the caller was never allowed to know about.
