---
name: escalation-rules
description: Route a decision to its owner before implementing it, and hand back with evidence instead of stalling; Use when the work crosses a service boundary, involves technology selection or a public API contract, needs root-cause analysis or profiling, touches security or data loss, requires CI/CD, dashboards, alerting or deployment, or when requirements are ambiguous or broader than the ticket.
metadata:
  owner: Jeff
  domain: shared
---

# Escalation Rules

## When to use
- The ticket names something you are not the owner of, or you are about to make a decision you cannot justify alone.
- You are blocked and the next step needs authority you do not have.

## Rules
When a trigger row matches, the decision belongs to the named owner. Consult **before** implementing, not after.

| Trigger | Owner |
|---|---|
| Cross-service design, technology selection, public API contract | Daedalus |
| Root-cause analysis, profiling, unexplained failure | Sherlock |
| Vulnerability assessment, threat model, crypto or auth choice | Michal |
| CI/CD, dashboards, alerting, deployment | Jozef |
| Ambiguous requirements, or scope beyond the ticket | Requester / Dispatcher |

- **Escalate before implementing** any decision affecting security posture or data loss: authentication, authorization, crypto, secrets, personal data, destructive migration, deletion, permission or network-reach change. Implement after the answer, never in parallel with it.
- **Escalate findings that are implementation-shaped too.** A root cause you cannot explain is Sherlock's even if you can patch the symptom; a new public field or cross-service shape is Daedalus's even if you can write it today.
- **When blocked, hand back with evidence**: what you tried, the exact evidence (command plus output, log line, failing test), the decision you need, and a recommended owner. Never stall silently, never poll waiting for input that will not come, never mark a blocked task in progress (`handoff-report`).
- **Partial progress is allowed and must be labeled**: ship the part you own, keep the diff separable, state the blocked part and its owner.
- **You cannot delegate upward mid-diff.** If the design is undecided, asking is the honest move; a speculative implementation is not faster than a question.

## Verify
- Every decision you implemented alone matches no trigger row.
- Security- or data-loss-relevant changes carry a named owner's answer recorded in the handoff before merge.
- Every hand-back contains reproducible evidence, not a status update.

## Anti-patterns
- Not "I'll patch it and flag the design issue" — escalate first for contracts and security.
- Not "escalate everything" — a local bug fix inside one component is yours to do.
- Not a hand-back without evidence — "it doesn't work" is not a hand-back.
- Not a silent stall — a blocked task reported as in progress is worse than not started.