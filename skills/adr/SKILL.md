---
name: adr
description: Record an architecture decision with its context, at least two real options including the status quo, the decision, its consequences, and the observable conditions that would reverse it, superseding rather than rewriting a reversed record; Use when choosing a technology or service, a data model, a boundary, a protocol, a dependency, adopting a pattern, or removing one — any choice with lasting consequence that a reasonable engineer would not make identically without asking.
metadata:
  owner: Daedalus
  domain: architecture
---

# Architecture Decision Records

## When to use
- **Use for:** a technology or service choice, a data model, a boundary, a protocol, a dependency, a pattern adoption, a removal.
- **Not for:** a routine change a reasonable engineer would make identically without asking. Volume is not the goal; an ADR nobody reads is worse than none.
- The decision is being made now, not recalled afterwards.

## Rules

**Format — every ADR has these six fields:**
- **Title** — a short noun phrase naming the decision, not the document.
- **Status** — proposed, accepted, superseded by ADR-XXXX, or deprecated. The status field is what makes a superseded decision findable; a missing one is a defect.
- **Context** — the forces at play, the constraints, and the deadline or scale that actually matters. Facts and numbers, not narrative.
- **Options considered** — at least two real ones, and the set **must include the status quo and doing nothing**. An ADR with one option is not a decision record; it is an announcement.
- **Decision** — what was chosen, stated plainly enough to act on.
- **Consequences** — what becomes easy, what becomes hard, what new obligation this creates, and what it forecloses. The negatives are the useful half.
- **Revisit triggers** — the *specific observable condition* that would make this decision wrong: a load threshold, a dependency's licence change, a team size, a deadline, a vendor's deprecation notice.

**Timing and history**
- Record the decision and its reasoning **at the moment of making it**. An ADR written afterwards from memory is a justification, not a record.
- A reversed decision gets a **new ADR that supersedes the old one** — never an edit in place. The old record is the evidence that the reasoning changed, and deleting it destroys the audit trail.
- Never write an ADR as a justification for a decision already made and presented as inevitable.
- Outcome records what actually happened, and never rewrites the original reasoning.

## Verify
- A reader who was not present can explain why this team chose this over the obvious alternative.
- That reader can name the trigger that would make the team reconsider, and it is observable rather than a feeling.
- The options list contains the status quo and doing nothing, each argued in good faith.
- Every ADR has a status, and every `superseded by` reference resolves to a record that exists.
- The date is recorded; anything older than the assumptions it rests on is re-read, not assumed current.

## Anti-patterns
- Not a design doc — an ADR records one decision, not a system description.
- Not written after the fact from memory, and not written to justify a fait accompli.
- Not "we chose X because X is better"; the rejected option gets a real argument.
- Not editing a superseded ADR in place — supersede it, keep the history.
- Not a revisit trigger like "if it becomes a problem"; a trigger has a number or an observable event.
- Not an ADR for a change nobody would question.
