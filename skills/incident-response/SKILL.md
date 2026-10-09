---
name: incident-response
description: Stabilize, triage, communicate, and learn from a live production incident; use when users are impacted or an outage is declared and you must mitigate before diagnosing, assess severity from user impact, preserve evidence, keep a contemporaneous timeline, and run a blameless postmortem.
metadata:
  owner: Sherlock
  domain: debugging
---

# Incident Response

Restore service first, understand it second. Diagnosis under pressure is how evidence gets lost.

## When to use
- Users, revenue, or data are impacted, or an outage is declared or imminent.
- A service is degraded, erroring, slow, or unavailable in production.
- A postmortem is owed after an incident is resolved.

## Procedure
1. Confirm impact and declare. Severity from user-visible impact: who is affected, how many,
   how badly, and since when. A frightening stack trace with no user impact is a low-severity
   event; a bland log line with total unavailability is a high-severity one. Do not let the
   drama of the artifact set the severity.
2. Stabilize before diagnosing. Prefer the most reversible, lowest-risk mitigation that stops
   the bleeding. Ordered roughly by reversibility: roll back or redeploy the last known-good
   version, disable the offending feature flag, shed or rate-limit load, degrade to a fallback
   or cached response, then only then make a code change.
3. Assign roles explicitly: incident commander, communications, and operations. One person
   coordinates; the comms role never also edits production.
4. Communicate on a fixed cadence whether or not there is news. Silence reads as absence of a
   plan. State impact, current action, and next update time, even when the answer is "no
   change". Say what you do not yet know rather than speculating on cause.
5. Preserve evidence before restarting, redeploying, or rolling back. Capture the state that
   exists now: metrics, logs, traces, thread and task dumps, heap or handle dumps, config and
   deployment state, and the exact version and time. This is the single step most often skipped,
   and skipping it permanently loses the incident.
6. Diagnose with the artifacts you saved, using `production-signal-analysis` for the timeline
   and `root-cause-analysis` for the cause.
7. Write the timeline contemporaneously as you work, from artifacts and not memory. Reconstructed
   timelines are wrong about times and about what was known when, which is exactly what a
   postmortem needs.
8. Mitigate, verify recovery from user-visible metrics, and watch long enough to see the tail.
9. Schedule the blameless postmortem within a few days while memory is fresh.

## Postmortem format
Impact in user terms and numbers, timeline, contributing factors, root cause, what went well,
detection and response gaps, and action items each with a named owner and a deadline. Action
items that say "add more logging", "add better dashboards", or "be more careful" are not action
items; they are the absence of one. Ask instead: why did this take this long to detect, why was
the blast radius this wide, which control would have limited it, and which assumption was
believed before it was checked.

## Verify
Recovery is user-visible metrics back inside target for long enough to clear the tail, not a
green deploy. Close the incident only once the follow-up has a named owner and a deadline.

## Anti-patterns
- Not debugging while users are down; mitigation is the deliverable during impact.
- Not a fix under pressure without a rollback path and a way to detect it made things worse.
- Not restarting or redeploying before capturing state, and not "just bouncing it" as a first move.
- Not a single channel, or one person's direct messages, as the incident's communication plan.
- Not one person incident-commanding, writing updates, and editing production simultaneously.
- Not a blame-oriented review; a named person's name in a cause list guarantees the next
  incident is under-reported.

## Prevention
Detection and blast-radius controls: `observability`. Engineering that prevents the failure
class: `correctness-errors`, `concurrency-resources`. Limits, degradation, and recovery:
`resilience`. Regression coverage: `testing-strategy`.
