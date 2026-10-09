---
name: delegation-router
description: Choose and sequence the agent whose skill actually covers the task, respecting read-only agents and the approval gate, and split any task carrying two objectives; Use when selecting between Jeff, Sherlock, Daedalus, Michal, and Jozef, when ordering a multi-agent sequence, when deciding who verifies a security fix, or when a task must be split before it is dispatched.
metadata:
  owner: Dispatcher
  domain: orchestration
---

# Delegation Router

## When to use
- A triaged ticket needs an owner and a sequence.
- Two agents look plausible and the deciding evidence is which skill the work needs.
- A task has quietly grown a second objective.
- A change is about to be dispatched to an agent that cannot write.

## Rules / Procedure

**Agent domains**
- `Jeff` — implementation, refactoring, testing, code quality, observability, resilience. The only agent that changes application code by default.
- `Sherlock` — root cause, profiling, incident response, performance debugging. Read-only on files.
- `Daedalus` — architecture, technology selection, system design. Read-only on files.
- `Michal` — threat modeling, security review, vulnerability assessment. Read-only on files.
- `Jozef` — CI/CD, deployment, monitoring, dashboards, scaling. Writes infrastructure and pipeline files.

**1. Route by the skill required, not the keyword in the title.**
- "Refactor the parser" needs `codebase-conventions` and `refactoring-technique`, so it is Jeff's. A ticket mentioning "database" is not automatically Daedalus's.

**2. Sequence by dependency, and state the order out loud.**
- Design before implementation: Daedalus → Jeff.
- Root cause before fix: Sherlock → Jeff.
- Security: Michal → Jeff → Michal. Threat model first, fix second, independent verification last.
- Pipeline and dashboards after the feature exists: Jeff → Jozef.

**3. Security work always gets a second look.**
- Michal triages and states the finding, Jeff implements it, Michal re-verifies the fix.
- The implementer does not sign off their own security fix. That step is not optional and not batchable away.

**4. Respect the read-only agents.**
- Sherlock, Daedalus, and Michal cannot write. Any objective that must change a file ends with Jeff or Jozef.
- Never dispatch a write objective to a read-only agent; it will return a plan, or a blocker, and the work will stall.

**5. One task, one owner.**
- A subagent given two unrelated objectives will do the more interesting one and leave the other quietly undone.
- Split into two dispatches instead. Related steps of one objective stay together.

**6. Give every subagent its three inputs.**
- Context (issue id, links, current state), deliverable (the artifact you expect back), constraints (tools, scope, what not to touch).
- A subagent starts with no memory of this conversation, so anything you leave out is lost, not inferred.

**7. Do not delegate work a skill already covers.**
- If you can do it by loading a skill, load the skill.

**8. Get approval before dispatching.**
- Every dispatch requires the operator's approval. The gate and its rules are `delegation-gate`; apply them there rather than re-deriving them here.

## Verify
- The chosen agent's domain matches the skill the work actually needs, and you can name that skill.
- The sequence is written down, and each step's output is named as the next step's input.
- Every task that must change a file has a write-capable agent last in its sequence.
- Every prompt carries context, deliverable, and constraints, and each dispatch carries an approval `delegation-gate` accepts.

## Anti-patterns
- Not routing on title keywords — route on the required skill.
- Not skipping the verification pass after a security fix.
- Not dispatching a write objective to Sherlock, Daedalus, or Michal.
- Not bundling two unrelated objectives into one task.
- Not re-delegating finished work, and not sending a prompt that assumes the subagent remembers this conversation.
- Not proceeding past a blocked decision instead of handing back (`escalation-rules`, `scope-control`).
