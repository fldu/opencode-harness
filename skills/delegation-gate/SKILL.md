---
name: delegation-gate
description: Obtain the operator's explicit approval immediately before every subagent dispatch, and prefer loading a skill over delegating the work at all; Use when the task tool is about to be called, when a skill already covers the work, when one approval is being stretched to cover a second dispatch, when a read-only agent produced content that must now be written by someone else, or when blocked with a choice between guessing and asking.
metadata:
  owner: Dispatcher
  domain: orchestration
---

# Delegation Gate (operator override)

The operator's standing instruction. It outranks every routing heuristic, every
decision matrix, and every urgency signal in every other skill.

## When to use
- Every single time `task` is about to be called. There is no dispatch too small to gate.
- A skill already covers the work and a subagent is being weighed against it anyway.
- One dispatch was approved and the next one is being treated as covered by it.
- A read-only agent (Sherlock, Daedalus, Michal) produced content that must become a change.
- You are blocked, and the options are guessing or going back to the operator.

## Rules

**1. Ask before every dispatch.**
- State four things in one short block: which agent, the objective, why that agent, the expected deliverable. Then stop and wait for a reply. Do not call `task` in the same turn as the question.
- No exception for an obvious route, a one-line edit, a re-dispatch to the same agent, or a ticket that clearly belongs to one specialist. Approval for one dispatch is not approval for the next.
- Approval does not persist across turns. A new turn reopens the gate.

**2. Skills first.**
- If a skill covers the work, load it and work through it yourself with the tools you hold. Dispatching an agent to execute a skill is pure indirection: you already hold the skill, and the subagent would have to load the same one before doing anything.
- Your own reach stops at `read`, `grep`, `glob`, `skill`, and `task`. Anything that changes a file or runs a command is a dispatch by definition, not something you can do.
- Loading a skill is not a dispatch and needs no approval.

**3. An approved dispatch is scoped, not pre-executed.**
- Name the skills the subagent should load. Do not load them on its behalf, and do not paste skill text into the prompt — the subagent can read the file, and a pasted copy goes stale the moment the skill changes.
- Supply context, deliverable, and constraints in the prompt; a subagent starts with no memory of this conversation.

**4. Read-only producers still need a writer.**
- Sherlock, Daedalus, and Michal cannot change files. They can still be exactly right for producing content: a root cause, a design, a threat model, a verification verdict.
- Turning that content into a change is a separate dispatch to Jeff or Jozef, and that dispatch needs its own approval.
- Never dispatch a write objective to a read-only agent.

**5. Batch, but never bundle.**
- Fold related steps of one objective into a single approved dispatch instead of asking repeatedly.
- Never merge unrelated objectives to spend one approval. Two unrelated objectives is two dispatches.

**6. Blocked means hand back.**
- Report the evidence gathered, the decision you cannot make, and the owner you recommend (`escalation-rules`).
- Do not stall silently, and do not quietly pick the most likely option.

**7. Report state honestly.**
- State what was skipped, deferred, left uncertain, or never verified. Do not present partial work as finished.

## Verify
- Before each `task` call, the operator's approval for that specific dispatch appears earlier in the conversation.
- No prompt contains text copied out of a `skills/*/SKILL.md`; it names the skill instead.
- Every dispatch whose result must change a file targets Jeff or Jozef, never a read-only agent.
- The closing summary names what was not done.

## Anti-patterns
- Not "the route is obvious, I will just dispatch" — obvious is a routing opinion, not an approval.
- Not "same agent as last time" — the gate is per-dispatch.
- Not dispatching an agent to run a skill you could load yourself.
- Not pasting skill content into a prompt — name it and let the subagent read it.
- Not asking once and spending that answer on five dispatches.
- Not reporting a dispatch as complete when its result was never collected.
