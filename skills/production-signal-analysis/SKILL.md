---
name: production-signal-analysis
description: Turn production logs, metrics, and traces into one defensible timeline and tell signal from noise; use when a problem shows up only in field data, such as prod-only intermittent failures, latency spikes, error-rate drift, or regional or per-customer anomalies.
metadata:
  owner: Sherlock
  domain: debugging
---

# Production Signal Analysis

Reading artifacts, not theorizing. Once you have a candidate cause, take it to `root-cause-analysis`.

## When to use
- The failure is real but not reproducible locally, or only reproduces at production volume.
- Logs, metrics, and traces tell apparently contradictory stories.
- You must state what happened, and when, for an incident or a bug report.

## Establish the clock first
- A log timestamp is not an event timestamp: it is emission time, plus buffer flush, plus
  collector ingestion lag, plus export batching. Measure the lag before trusting any ordering.
- Check clock skew between hosts, timezone and daylight-saving handling, and monotonic versus
  wall clock. Skew of a few hundred ms will invent or hide an ordering you care about.
- Align traces, metrics, and logs to one reference clock, then state the residual uncertainty
  in the timeline itself rather than pretending to second-level precision you do not have.

## Procedure
1. Fix the scope: which service, version, region, tenant, and time window. Confirm the data
   covers it; dashboards routinely aggregate away the exact failure domain.
2. Pick one reference series and normalize all others to it before comparing anything.
3. Build a single timeline: deploys, config and feature-flag changes, traffic shape, alerts,
   saturation, and the first user-visible error. Order matters more than density.
4. Establish the baseline for this population before calling anything anomalous: same service,
   same customer or region, same time of day, same load. A value abnormal globally may be
   normal for a heavy tenant on a batch schedule.
5. Work the misleading-signal catalogue below; assume at least one of these is active.
6. Pivot on the axes the failure could hide on: by region, version, instance, tenant, error
   type, and payload shape. The signal that appears everywhere is often the least specific.
7. Extract the minimal reproduction from the field data: the smallest input, the single request
   or job, and the precondition that made it special. Hand that to `root-cause-analysis`.

## Misleading-signal catalogue
- Averages hide tails; the p99 incident looks fine when the mean is fine.
- Sampled or head-based data can miss the spike entirely.
- Percentiles over a rolling window lag the event by the window length.
- Dashboards aggregate away the failure domain: one shard, one tenant, one node pool.
- Retry storms inflate success counts and depress apparent error rate while latency explodes.
- Successful cache hits mask the slow path the user actually felt.
- Cardinality explosion silently drops or samples the metrics you are trying to read.
- Debug logging added during the incident changes volume, cost, and sometimes timing.

## Cost discipline while debugging in production
Every new log line, trace attribute, and metric label costs money, ingest, and latency. Prefer
high-cardinality diagnosis in a narrow window over permanent broad instrumentation, and remove
what the incident added once it is understood.

## Verify
The timeline must survive the clock check, be corroborated by two independent signals, and
reproduce an observation nobody told you about. If it explains only the reported symptom, it is a
story, not a timeline.

## Anti-patterns
- Not a story assembled from one graph; require at least two independent signals to agree.
- Not a timeline reconstructed from memory; record it contemporaneously.
- Not treating every flat line as healthy without checking ingestion is still flowing.
- Not sampling more data at higher cardinality than the bill and the pipeline can take.
- Not drilling into code before the timeline pins the change that introduced the symptom.

## Prevention
Make the artifacts trustworthy and cheap: `observability`. Make degradation visible and bounded
up front: `resilience`. Capture the reproduction as a test: `testing-strategy`.
