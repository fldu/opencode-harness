---
name: observability
description: Make a subsystem legible after the fact through structured logs, bounded-cardinality metrics, and propagated traces; Use when adding or changing a path that crosses a process or machine boundary, when an operator must debug it from evidence alone, when choosing a log level or a metric label, or when deciding what to emit so that cardinality, cost, and noise stay bounded.
metadata:
  owner: Jeff
  domain: implementation
---

# Observability (logs, metrics, traces)

## When to use
- Any path that crosses a process, machine, or network boundary, or that an operator will debug from evidence alone.
- Adding or moving an instrumentation point, renaming an event, or adding a metric label.
- Deciding what is enough to answer "did it work, and why not" without reading the code.

## Rules

**Logs**
- One event per line, machine-parseable (structured key-value or JSON). Never a prose sentence with interpolated values.
- Mandatory fields on every event: UTC timestamp with milliseconds, severity, a stable dot-namespaced event name (`ratelimit.exceeded`), trace and span id, correlation or request id, actor, target resource, duration in ms.
- Event names are a contract: lowercase, dot-namespaced, past-tense, stable. Never reuse a name for a new meaning, and never build a name from input.
- Severity is a budget: `error` = a human must act; `warn` = degraded but handled; `info` = lifecycle or significant state change; `debug` = diagnostic. Choose the lowest level that answers the question. An `error` with no matching metric is a defect.
- **Redaction happens in the logger, not at call sites**: a configured redactor for credentials, tokens, cookies, keys, and personal data applied to every string field and message body. Never log full request or response bodies, or raw provider payloads.
- Log volume is bounded by design: no logging inside per-item loops; aggregate and emit once per window with a count.

**Metrics**
- Minimum set per subsystem: operation **count**, **error count**, **latency histogram**, and a **saturation gauge** (queue depth, pool utilization, in-flight). Names and units match the metrics already in the repo.
- **Label cardinality is a budget.** Never use an unbounded value as a label — user id, URL, path, raw error text, request id, message content, timestamp. Log the detail, count the aggregate. Prefer a small enumerated label (outcome, reason, endpoint from an allowlist).

**Traces**
- Propagate context across every async hop and every cross-process hop: enqueue, batch, scheduled job, sub-request, callback. A span started and never propagated is worse than none.
- One span per meaningful operation, not per line. Span attributes use the same field names as logs so a trace and a log line join.
- **Log↔metric parity**: every error metric has a matching event name, and every `error` log increments a matching counter. Unmatched pairs are defects.

Event names, metric names, and log keys are also compatibility surface (`data-compatibility`).

## Verify
- Trigger the path and paste the raw emitted lines in `handoff-report`; they must parse as structured records.
- List every new label with its cardinality source; anything derived from input is removed or bucketed.
- Grep the diff for new log calls; each carries the mandatory fields or inherits them from an established helper.
- Confirm trace context reaches the far side — the correlation id appears in the downstream log or metric.

## Anti-patterns
- Not `log("request failed: " + err)` — structured fields and a stable event name.
- Not a per-item log in a loop — one aggregate line per window.
- Not `error` for "expected and handled" — that trains people to ignore `error`.
- Not a user id, URL, or raw error string as a metric label.
- Not redacting at the call site "just this once" — configure the logger.
- Not a span per function call — spans cost money and hide the shape of the request.