---
name: refactoring-technique
description: Keep refactors separate from behavior changes and keep every step small, green, and reversible; Use when cleaning up code you are about to change, when a change has grown past reviewable size, when renaming across call sites, when tempted to rewrite rather than edit, or when sequencing a multi-step refactor.
metadata:
  owner: Jeff
  domain: implementation
---

# Refactoring Technique

## When to use
- The ticket is a cleanup, or a behavior change has grown a cleanup around it.
- A rename or signature change crosses many call sites.
- You are choosing between editing and rewriting a unit.

## Rules
- **Never mix a refactor with a behavior change.** Two separate steps, two separate diffs, each reviewable on its own. A reviewer must be able to approve one without accepting the other's risk.
- **Extract before inlining.** Moving a named block out is safe and provably behavior-preserving; inlining first is a rewrite disguised as cleanup.
- **Delete before rewriting.** Removal is provably safe when the suite is green and the symbol has no callers; a rewrite is not.
- **Change and rename are separate steps.** Introduce the new name alongside the old, migrate call sites, then remove the old — one step each, never a single sweeping rename.
- **No drive-by reformatting of untouched lines.** The formatter's own diff belongs in its own change or nowhere. A diff that mixes reflow with logic cannot be reviewed line by line.
- **Sequence a multi-step refactor so the suite is green after every step**: one mechanical step, tests green, then the next. Never leave a "step 1 of 4" state red. If a step cannot be made green alone, split it differently.
- **A rewrite is sometimes genuinely cheaper** than an incremental edit — a small unit with tangled assumptions, a dead abstraction to delete. When that is true, say so, cite the estimate, and escalate (`escalation-rules`). Do not smuggle a rewrite inside a feature diff.
- Keep matching existing conventions while refactoring; a refactor is not permission to introduce a pattern (`codebase-conventions`).
- **Behavior-preserving means exactly that.** If a refactor changes an observable output, it is a behavior change.

## Verify
- Each step is green: run the suite per commit, or state which step is deliberately intermediate.
- The diff contains no line changed only for formatting.
- A rename shows old and new coexisting in an intermediate state, then the old name removed.
- The final diff of a refactor ticket is mechanical and describable in one sentence.

## Anti-patterns
- Not "I cleaned it up while I was in there".
- Not one commit doing rename, behavior change, and reformat together.
- Not a large rewrite presented as a small diff because the file count is low.
- Not leaving the tree red between refactor steps.
- Not deleting a test to make a refactor green — that is a behavior change in disguise.