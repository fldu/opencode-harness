---
name: issue-triage
description: Turn an incoming issue into a routing decision by establishing user impact, reproducibility, the real source of any deadline, the class of work, and an honest size before anyone is assigned; Use when a new ticket arrives, when a ticket's scope or priority is unclear, when an intermittent or unreproduced report must be classified, or when a ticket is too large for one sitting and has to become a parent plus independently verifiable sub-issues.
metadata:
  owner: Dispatcher
  domain: orchestration
---

# Issue Triage

Impact sets priority. Title severity does not.

## When to use
- A new ticket lands and nobody has decided who owns it.
- The scope is unclear, or the ticket says "broken" without saying what breaks.
- A bug report has no reproduction, or a field-only report needs to become a plan.
- The ticket looks bigger than one sitting and needs decomposing.

## Rules / Procedure

**1. Read the whole issue before judging it.**
- Body, reproduction, environment, affected version, labels, and every comment. The root cause is frequently already written in a comment by the person who hit it.

**2. Establish user impact.**
- Who is affected, how many, what breaks for them, whether data is lost or corrupted, and whether it is ongoing or intermittent.
- Record impact in one sentence before looking at any priority field. Priority derives from impact.

**3. Establish reproducibility.**
- Classify as: reproducible on demand, intermittent, environment-specific, or field-only only.
- An intermittent report is an evidence problem, not an implementation problem. Route it to `root-cause-analysis`, not to a fix.

**4. Establish the deadline and its source.**
- Name where the date comes from: a real external commitment, an internal guess, or nothing at all.
- An undated "urgent" is not urgent. Say so explicitly in the triage note.

**5. Classify the work before naming an owner.**
- One of: security, architecture, infrastructure, debugging, implementation — or an explicit mix.
- A single ticket often needs a sequence of specialists rather than one. State the sequence, not just the first name.

**6. Size it honestly, unknowns included.**
- Separate what is known from what is assumed.
- If the unknowns dominate the estimate, the first task is to reduce them, not to implement.

**7. Ask the operator when the ticket is ambiguous.**
- Two plausible readings, a deadline that conflicts with the effort, or a classification you are genuinely unsure of: ask rather than silently choosing (`scope-control`).
- If no amount of reading resolves it, hand back with the evidence and a recommended owner instead of guessing (`escalation-rules`).
- Do not resolve a scope ambiguity by picking the reading that is cheapest to be wrong about.

**8. Decompose anything larger than one sitting.**
- Produce a parent issue plus explicit sub-issues, each independently verifiable and ordered by dependency.
- A checklist inside one body does not create per-item status or per-item ownership.

## Verify
- The triage note states impact, reproducibility, classification, deadline plus its source, suggested owner, and dependencies.
- The specific questions still open are listed, not smoothed over.
- Every sub-issue can be verified on its own: it has its own observable pass condition.
- If the ticket was ambiguous, the operator's answer is quoted or referenced, not paraphrased into certainty.

## Anti-patterns
- Not routing on title keywords or label colour alone — read the body and the comments.
- Not treating "urgent" as a deadline; name the source or drop the claim.
- Not implementing an unreproduced bug report — get the reproduction or hand it to debugging.
- Not splitting into sub-issues that cannot each be verified alone.
- Not picking an owner while the classification is still a coin flip.
- Not reporting a confident size when the unknowns were never named.
