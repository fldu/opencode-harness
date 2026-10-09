---
name: threat-modeling
description: Derive security findings by applying STRIDE per trust boundary rather than per component, starting from the assets and what an attacker wants from this specific system; Use when designing a new feature, service, or external surface before it is built, when data will cross a process, network, privilege, tenant, or user-supplied boundary, when adding an endpoint, message consumer, file path, or third-party integration, or when re-examining a boundary that a change has altered.
metadata:
  owner: Michal
  domain: security
---

# Threat Modeling

## When to use
- A new feature, service, or externally reachable surface is being designed, before it is built.
- Data crosses a process, network, privilege, tenant, or user-supplied boundary.
- A change moved a boundary — re-run the model for that boundary only (`fix-verification` step 7).

## Rules

**1. Assets first.** Name what is worth protecting *in this system* — which records, whose credentials, what money, what availability, what reputation — and what an attacker would actually want from *this* system. No asset named, no finding: stop and ask what the thing is for.

**2. Flows, not components.** Enumerate each flow as `source → transform → sink` and name the actor at each end. A component is not a flow and cannot be threat-modelled alone.

**3. Mark every boundary each flow crosses:** process, network, privilege, tenant, user-supplied.

**4. For each boundary-crossing flow, ask all six questions:**
- *Spoofing* — is the actor authenticated as claimed, at this boundary, right now?
- *Tampering* — can the flow be altered in transit or at rest by someone who does not own it?
- *Repudiation* — can the actor deny the action afterwards, with no durable record?
- *Information disclosure* — what leaves this boundary, and to whom?
- *Denial of service* — what here is unbounded, amplifiable, or cheap for the attacker?
- *Elevation of privilege* — can this flow reach a capability it must not reach?

**5. State each flow's assumptions** — authenticated? as which principal? from which network position? **An unstated assumption is the finding.** Assumptions are what an attacker reads first.

**6. Abuse legitimate functionality,** not only injection: replay, enumeration, races, exhaustion, misbound tenant ids, order-dependent state changes, unbounded export.

**7. Rate, then discard.** likelihood × impact *for this system*. Anything with no concrete path is discarded, and each discard gets one line saying what and why, so the decision stays auditable.

**Deliverable:** boundary map / findings (id, STRIDE category, CWE, flow id, likelihood, impact) / mitigation stated as the required **property**, never as a patch / verification check / discarded-and-why. Findings go to `vulnerability-assessment` for reachability and scoring.

**Stop** when findings are ranked, each with a mitigation property and a verification criterion. Do not write the implementation — `security-implementation` does that; the final risk call is `escalation-rules`.

## Verify
- Every finding names a flow id and a boundary it crosses; a finding with no flow was discarded, not ranked.
- Every assumption is written in words; none is carried only by a diagram.
- Every mitigation is a property ("the resolved path lies inside the base directory after canonicalisation"), not an action ("sanitise the input").
- Every discard has a one-line reason, and no discarded item reappears in `vulnerability-assessment`.

## Anti-patterns
- Not STRIDE per component — that produces noise; per boundary it produces findings.
- Not a model with no assets, or a risk score with no path.
- Not mitigations written as patches before the model is agreed.
- Not assumptions left implicit in a diagram.
- Not stopping at the injection classes — abuse of legitimate function is where the loss is.
