---
name: scope-control
description: Decide whether to proceed or ask, keep every change to the smallest diff that fully solves the stated problem, and refuse speculative work; Use when a request is ambiguous or underspecified, when you are tempted to add a config flag, an abstraction, or an extra feature "while we are here", when the ticket is larger than one reviewable sitting, or when finishing it would require touching unrelated code.
metadata:
  owner: Jeff
  domain: shared
---

# Scope Control

## When to use
- Before writing any code, and again the moment you notice yourself editing a file the ticket never named.
- The requirement is ambiguous, has two plausible readings, or names an outcome without a mechanism.
- The change would touch a second service, a public contract, or a shared data store.

## Rules
- **Proceed** when the ticket states the outcome, the affected code is unambiguous, and the change stays inside one component. Choose the smallest change that fully solves the stated problem; do not solve adjacent problems in the same diff.
- **Ask** when two readings lead to different code. Ask exactly one specific question, name the two candidate answers, and state which one you would default to if you get no reply. Never guess silently and never pick the more interesting reading.
- **Split** when the work exceeds one reviewable sitting or mixes a refactor with a behavior change. Ship the smallest independently useful slice, then state the remainder as a separate piece of work (`refactoring-technique` sequences the steps).
- **Refuse speculative generality**: no flag, interface, plugin point, or setting without a second caller inside the current ticket. "We may need it later" is not a use case.
- **Stop at the boundary.** A change to a public API contract, a wire format, or another service's data is a decision you do not own (`escalation-rules`).
- **Preserve the acceptance criteria.** If they cannot be met without widening scope, say which criterion moves and ask — do not silently relax one.

## Verify
- `git diff --stat` names only files the ticket implies.
- Every hunk traces to a stated requirement or to a defect the change fixes.
- Any question asked is recorded with both readings and the assumption you proceeded under (`handoff-report`).

## Anti-patterns
- Not "while I'm here" — unrelated cleanups become their own change.
- Not "I'll assume the obvious" — two readings mean ask one question.
- Not "a knob is cheap" — a knob without a caller is dead code plus a decision.
- Not "finish the refactor first" — a refactor and a behavior change never share a diff.
- Not "scope creep is fine if the tests pass" — passing tests do not make a large diff reviewable.