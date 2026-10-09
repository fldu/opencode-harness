---
name: slo-and-alerting
description: Turn reliability into numbers and pages worth waking someone for — user-facing SLIs, a defensible SLO, an error budget with stated consequences, and burn-rate alerting; Use when defining or reviewing an SLO, deciding what an exhausted error budget changes, tuning alert thresholds or severity, or when a page fires on CPU, memory, or queue depth instead of a user-visible symptom.
metadata:
  owner: Jozef
  domain: infrastructure
---

# SLOs and Alerting

> Scope — what to promise and what pages. What the code emits is `observability`; whether the pipeline carries it is `observability-stack`; running the response is `incident-response`.

## When to use
- Choosing or changing an SLI, an SLO, or an error-budget policy.
- An alert fired and nobody could say what to do about it, or nobody was paged at all.
- Deciding whether work may ship while reliability is degraded.

## Rules

**SLIs that reflect the user**
- Pick per service from availability (good/total), latency (share of requests under a stated threshold), correctness (valid results/total, machine-checkable), freshness (age of the newest data), durability (loss found by audit, not by absence of complaints).
- Measure at the boundary the user touches — the edge, not the internal hop. An internal call returning 200 while the user sees an error is a green dashboard.
- Write down every excluded event (health check, synthetic, batch, cache hit). Silent exclusions are how an SLI becomes flattering.
- A mean is not an SLI. Use share-over-threshold, or a percentile with a stated window.

**SLOs that can be defended**
- The target comes from a user expectation you can name, not from today's measurement. 100% is not a target, it is the absence of one — it forbids an error budget and guarantees a miss, so the team learns to ignore it.
- Bound the target by what you control; a third party's outage is not your SLO.
- State the window (28 days rolling is a common default) and the exclusions. An SLO without a window is not a number.
- Derive the first target from measured history, set it slightly above, then tighten deliberately. Do not invent 99.99% on day one.
- One SLO per user journey. A pile of component SLOs nobody can map to a journey cannot be traded off.

**Error budget — what exhaustion actually changes**
- Budget = (1 − target) × good events in the window. Publish it as a number and a trend, not as a colour.
- Write the policy while calm, in the same document as the SLO, with the person who can grant each consequence named.
- Consequences in increasing order of pain: raise review and test depth → shrink rollout (canary share, staged release) → freeze non-essential feature work → freeze releases. All pre-agreed, none improvised during an incident.
- An exhausted budget never blocks an incident fix; it needs an explicit exception path, or the rule is overridden the first time it matters.

**Multi-window, multi-burn-rate alerting**
- One alert per SLO, on burn rate = observed bad rate ÷ allowed bad rate. "14× burn" means the budget is gone 14× faster than sustainable.
- Two windows per severity — short (e.g. 5m) to page, long (e.g. 1h) to confirm. Page only when both agree, so a one-minute blip wakes nobody.
- Page on the fast burn, ticket on the slow one. The common starting pair is 14.4× over 1h+5m (page) and 6× over 6h+30m (ticket); recalibrate against your own window and budget, and write down the pair you chose.
- Also alert on imminent exhaustion — a burn that would consume a whole budget inside the window — even when nothing is paging.
- Page on symptoms: error rate, latency share, freshness, availability. Resource metrics (CPU, memory, disk, queue depth, pool use) are dashboard or ticket signals unless one has been *measured* as a leading indicator of a user-visible symptom.
- Every alert carries the SLO it protects, its query, an owner, and a runbook link (`runbook-authoring`).

**Alert quality**
- Every page is actionable now, owned, and has a tested runbook. Unowned is noise; not actionable is a ticket.
- Route by severity — page wakes someone, ticket waits for working hours, dashboard tells nobody.
- Alert on a change in the user-visible symptom, not on a value that is always high.
- Measure the pager honestly, in pages per on-call shift. More than roughly one means the alerts are wrong, not the responders.
- Delete or retune alerts nobody trusts; each has a stated false-positive tolerance and a review cadence.

## Verify
- For each SLO, quote from the store: the SLI query, the window, the exclusions, the current value, and the burn rate.
- Confirm the budget policy names a consequence and a decision-maker in writing, before it is needed.
- Inject a synthetic error and a synthetic latency breach; record which alert fires, in which window, and how long after.
- Walk the paging list — every row has an owner, an action, and a runbook link that resolves, or it is deleted.
- List every paging rule with the user-visible signal behind it; nothing pages on a resource metric alone.

## Anti-patterns
- Not 100%, and not an invented 99.99% — a defensible target beats an unreachable one.
- Not a mean latency as an SLI, and not an SLI measured at an internal hop.
- Not paging on CPU, memory, or queue depth alone — page on the user-visible symptom.
- Not a single-window alert — the short window pages, the long window confirms.
- Not an error budget with no consequence, and no exception path for the fix during an incident.
- Not an alert with no owner, no action, or no runbook link.
