---
name: handoff-report
description: Produce the one standard report every agent hands off with — what changed, verification with literal output, decisions and rejected alternatives, residual risk and what was not done; Use when finishing any task, when reporting work that could not be fully verified, when a measurement must be stated, or when a reviewer needs to know what was skipped and why.
metadata:
  owner: Jeff
  domain: shared
---

# Handoff Report

## When to use
- Every completed task, every partial task, and every hand-back when blocked (`escalation-rules`).
- When verification was done by someone else's gate (CI, another agent) rather than by you.
- Whenever a number, a log line, or a command is being cited as evidence.

## Rules
Four sections, in this order, under these headings. Nothing else.

1. **What changed** — one line per file: path, then the one-line reason it changed. A file not listed here is a defect. New or changed public surface is called out explicitly.
2. **Verification** — the exact commands run and their literal output, or the exact line they failed on.
   - Never present untested work as verified. A gate that was not run is written as "not run: `<command>`" plus why.
   - Performance or cost claims carry before/after numbers and the method, or the literal words "no measurable change" (`performance-measurement`).
   - Anything unverified is labeled unverified. "Should work" is not a result.
3. **Decisions & rejected alternatives** — one line per decision: what was chosen, what was rejected, why. Include the option that was cheapest and not taken.
4. **Residual risk & not done** — explicit: known defects, unhandled cases, deferred work, and anything that belongs to another owner.

## Verify
- Every claim of verification carries a command someone else can paste and run.
- `git status --short` and the file list under "What changed" agree exactly.
- Every deferral names an owner and a trigger, not "later".
- No adjective stands where a number belongs.

## Anti-patterns
- Not "tests pass" — the command and the count of tests run.
- Not "follow-up ticket" with no id, no owner, and no trigger.
- Not hiding a partial write under "mostly done" — say which part is unverified.
- Not omitting a measurement because it is inconvenient — "no measurable change" is a valid result.
- Not per-agent report formats; this single format replaces them.