---
name: definition-of-done
description: The pre-handoff checklist that turns the practice skills into pass/fail conditions before work is reported done; Use when finishing any implementation task, before writing the handoff report, when deciding whether something is complete, or when self-reviewing a diff for readiness to merge.
metadata:
  owner: Jeff
  domain: implementation
---

# Definition of Done

## When to use
- Every implementation task, immediately before the handoff, not at merge time.
- Self-review of your own diff before asking for review.
- Deciding whether "mostly done" counts as done.

## Rules
Each box is true only when its condition holds. The parenthetical names the skill that defines the practice — load that skill whenever a box is in doubt; the rules are not restated here.

- [ ] Build, lint, format, type-check, and the full test suite pass, with the exact commands and their literal output in the report (`stack-discovery`, `handoff-report`).
- [ ] The new behavior has a success-path test and at least one failure-path test (`testing-strategy`).
- [ ] Every new external call has a timeout derived from a propagated deadline, an explicit retry policy, and an error classified transient or permanent (`resilience`, `correctness-errors`).
- [ ] The new subsystem emits structured logs and count / error / latency / saturation metrics, with stable, paired event and metric names (`observability`).
- [ ] Every new async or cross-process path propagates trace context to the far side (`observability`).
- [ ] No secret, personal datum, or unbounded value is reachable in any new log line or metric label — established by reading an actually emitted line and the full label list, not by intent (`security-implementation`, `observability`).
- [ ] All growth introduced is bounded: every queue, pool, buffer, retry, and log volume has a stated cap and overload policy (`concurrency-resources`, `resilience`).
- [ ] Existing interfaces, wire formats, log keys, metric names, and config keys are preserved, or the break is versioned with a migration plan (`data-compatibility`).
- [ ] Every new dependency has a stated need, a rejected alternative, and a lockfile consistent with CI (`dependency-management`).
- [ ] Untrusted input is validated and normalized at its boundary, and no new shell, query, or path construction interpolates data (`security-implementation`).
- [ ] Performance claims carry before/after numbers with method and input size; otherwise the report says "no measurable change" (`performance-measurement`).
- [ ] Surrounding conventions are matched and the diff is minimal: no unrelated reformatting, no refactor mixed with a behavior change (`codebase-conventions`, `refactoring-technique`).
- [ ] Comments explain *why*, and no comment is left false by the change.
- [ ] Anything not done, deferred, or uncertain is stated explicitly with an owner (`handoff-report`, `escalation-rules`).
- [ ] Every significant choice is nameable against a principle, and the change stayed inside the ticket (`engineering-principles`, `scope-control`).

## Verify
- Walk the list top to bottom; every box is either true with evidence, or the report says it is not.
- A box that cannot be evaluated is a finding, not a pass.
- `git status --short` and `git diff --stat` match exactly what the report claims.

## Anti-patterns
- Not writing the report around unchecked boxes — an open box is reported, not hidden.
- Not treating "tests pass" as the whole list; a passing suite says nothing about bounds or compatibility.
- Not marking a box true from intent rather than from observed output.
- Not deferring a box silently to the next task.