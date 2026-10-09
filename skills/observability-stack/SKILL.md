---
name: observability-stack
description: Build and operate the telemetry pipeline that collects, ships, stores, samples, and retains logs, metrics, and traces; Use when choosing a collector or agent, fixing backpressure or dropped logs, blowing a metric cardinality or storage budget, choosing a trace sampling strategy, or when a silently broken exporter must be told apart from a healthy quiet system.
metadata:
  owner: Jozef
  domain: infrastructure
---

# Observability Stack (shipping and storing telemetry)

> Scope boundary: this skill covers the pipeline **after** emission — collection, transport, sampling, storage, retention. What the code *emits* (log fields, metric names and labels, span structure) is `observability`. Do not merge them: that skill is the producer contract, this one is the transport and storage contract. For what to query during an incident, see `production-signal-analysis`.

## When to use
- Standing up or changing the agent → collector → store path, or debugging telemetry that "is not showing up".
- Logs, metrics, or traces are being dropped, lagging, or arriving out of order.
- Metric storage cost, series count, or query latency is growing faster than traffic.
- Choosing a sampling rate, a retention period, or a cost tier.

## Rules

**Pipeline shape**
- Agent on the host or sidecar → collector → store. The collector is the buffer and the filter: it batches, retries, drops deliberately, and reshapes. The application must never talk to a store directly.
- Every stage has a health endpoint and an internal metric for its own state. **A silently broken exporter looks exactly like a healthy system with no traffic** — this is the single most expensive failure mode in telemetry.
- Monitor the telemetry pipeline as a service: end-to-end synthetic canary (a known event emitted on a timer, asserted present downstream within a bounded latency), plus dropped-event counters, queue depth, and export latency per stage.
- Buffer and retry with bounded queues. Unbounded retry is a memory leak that takes the host down during the incident you were trying to see.

**Logs: backpressure must be decided, not inherited**
- Logging is never on the request's critical path. Emit is non-blocking; the failure mode is drop, not stall.
- Decide explicitly, per signal, which of: **drop newest**, **drop oldest**, **block with a short timeout**, **sample**, **buffer to disk**. State the choice and the bound.
- Every drop is counted (`logs_dropped_total{reason}`) and the counter is alerted on. Silent dropping is the anti-pattern; the pipeline must be honest about losing data.
- Buffer to disk only with a size cap and a disk-space guard, and never on the same filesystem as the app's data.
- Structured transport, not plain lines: keep the structured record intact end to end. If you must parse free text at ingest, you have lost fields and lost the ability to drop by level cheaply.

**Metrics: cardinality is a storage-layer budget**
- Storage, not just the code, decides cost: each unique **series** is a time series with its own on-disk chunks and index entries. Series count, not sample count, drives the bill.
- Budget series per metric and per team. The expensive combinations are the ones that multiply: `service × route × status × region × instance`. State which combinations are affordable and hold them to it.
- Unbounded labels — user id, request id, full URL, raw path, error text, timestamp, build sha at unbounded cardinality — are rejected **at ingest**, not trusted to be absent from the code. Enforce a max-labels-per-series and a max label-value length in the store or collector config, and route violations to a reject metric.
- High-cardinality labels destroy two things at once: storage/query cost and **query latency**, because the index stops pruning. A single `user_id` label can make every dashboard query unusable.
- If per-detail data is needed, send it as logs or traces and correlate — do not put it in a label. Detail belongs in a queryable log store, not a metrics index.
- Guardrails that must exist: series limit per metric, cardinality-growth alert on top-N label values, and a documented ingest-rate limit per team.

**Traces: sampling strategy**
- **Head-based** (decide at the client, cheap, loses traces you did not choose): acceptable only for low-value, high-volume traces. Fine for a local dev sample.
- **Probability sampling** with a parent-consistent decision: every span of a trace shares the trace's sample flag, so a sampled trace is never a fragment.
- **Tail-based** (decide at the collector, after the trace completes): lets you sample on the *outcome* — keep all errors and all slow traces, drop boring successes. This is the right default for production traces, at the cost of collector memory and buffer-hold latency.
- **Sample preferentially, never uniformly**: retain 100% of errors and slow/error-adjacent traces, a small baseline of successes for baseline shape, and a tail-based rule for anything anomalous.
- Sampling decisions must be recorded on the trace itself (`sampled` flag, and the priority) so a partial trace is never mistaken for a complete one.
- Enforce per-tenant and global trace-rate ceilings; tail sampling with no memory bound is an OOM.

**Retention and cost tiers**
- Set retention per signal explicitly, from the question you must answer: hot (hours–days, full resolution), warm (weeks, downsampled), cold (months, aggregated) — drop what no one queries.
- Downsample or roll up old metrics before they age out; a 90-day retention of 1-second resolution is paid for and never read. Logs are volume-driven — sample `info` from healthy nodes, keep `warn`/`error` at full rate.
- Know the unit cost and current quota of your backend and set a spend alert before the bill arrives.

## Verify
- Kill the collector or block the store, drive traffic, and observe: requests still succeed, `*_dropped_total` rises, no unbounded memory growth, and the app's own latency is unaffected.
- Emit the canary event and assert it is queryable downstream within the stated bound; alert on canary absence.
- Enumerate the top series counts per metric and per label combination; anything not on the affordability list is removed or relocated to logs.
- Confirm a single sampled trace is complete (no orphan spans) and that errors and slow traces survive the sampling decision.
- Attempt an oversized or over-cardinality label and confirm the store rejects it and increments the reject counter.
- State the retention and cost tier per signal, and show the spend/usage alert exists.

## Anti-patterns
- Not "the dashboard is empty" and concluding there was no traffic — check the canary first.
- Not unbounded queues and retries in front of a downed store.
- Not blocking a request on a slow log write.
- Not a `user_id`, URL, or request-id label on a metric — that is the bill and the query latency.
- Not uniform 1% trace sampling that throws away every error you needed.
- Not 90 days of 1-second-resolution metrics nobody queries.
- Not trusting the code to keep cardinality low instead of enforcing it at ingest.
