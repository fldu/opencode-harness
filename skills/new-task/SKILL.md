---
name: new-task
description: Triage a piece of work the operator hands over and route it to the specialist whose skill actually covers the work, after establishing impact, reproducibility, the real source of any deadline, and an honest size; Use when new work arrives, when its scope or priority is unclear, when the operator asks what it will take and who should work on it, or when one piece of work has quietly become two objectives.
metadata:
  owner: Dispatcher
  domain: orchestration
---

# New Task

The entry point for a piece of work the operator hands over. It triages and
routes; it does not implement.

## Rules / Procedure

1. **Triage first.** Load `issue-triage`. Impact sets priority, not the wording
   the work arrived with. Reproducibility is classified before anything is
   dispatched.
2. **Route second.** Load `delegation-router`. It picks the agent and the sequence,
   and it is the only place the agent domains are written down.
3. **Ask the operator** which piece of work to take when triage leaves it
   genuinely open — that choice is theirs, not an inference from an asserted date.
4. **Get approval before dispatching.** `delegation-gate` requires explicit approval
   immediately before each dispatch, and prefers loading a skill over delegating at all.
5. **Plan before building.** When the work needs a design, `Daedalus` drafts the plan
   (read-only), then a writer implements it. Record the outcome in `handoff-report`.

## Anti-patterns
- Dispatching before triage, so the wrong agent does the impact analysis.
- Treating an undated "urgent" as urgent.
- One dispatch carrying two objectives; split it first.
