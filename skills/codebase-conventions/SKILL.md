---
name: codebase-conventions
description: Mimic the surrounding code before writing any of it — structure, naming, error model, logging, dependency wiring, and test style; Use when making the first edit in an unfamiliar area, when tempted to introduce a pattern that does not exist yet, or when a change is technically correct but does not look like the code around it.
metadata:
  owner: Jeff
  domain: shared
---

# Codebase Conventions

## When to use
- Before the first edit in an area you do not know.
- When your instinct is "that is not how I would write this".
- When deciding whether to add a pattern the codebase does not have yet.

## Rules
Mimic before you write. Read in the target directory, or the nearest comparable one, until you could predict the next line of code:

- **Structure** — where this kind of thing lives; module boundaries, layer direction, dependency flow.
- **Naming** — files, types, functions, constants, and test names: the exact prefix, suffix, and case used here.
- **Error model** — returned values, exceptions, typed error unions or enums, wrapping and context. Reuse this project's shape, not the ecosystem's default (`correctness-errors`).
- **Logging** — the project's logger, its call shape, its level vocabulary, its field names (`observability`).
- **Dependency wiring** — how components are constructed and injected; never add a second construction path.
- **Dependency direction** — who may import whom; do not invert it for convenience.
- **Test style** — the same assertion library, fixture and helper conventions, and layout.
- **Comment and doc voice** — how this repo expresses *why* comments and file headers.

- **Consistency beats preference.** Match the existing pattern even if you would write it differently. Disagreement goes in the report, not the diff.
- **Do not introduce a new pattern**: not a second logging library, not a second error style, not a new test helper, not a new directory layout. If the existing pattern cannot express the change, escalate (`escalation-rules`) instead of smuggling a parallel style in beside it.
- **One exception is allowed**: an existing pattern that is genuinely unsafe and that you must not copy. Fix it separately and say so.

## Verify
- `git diff` shows no file touched only to reformat, rename, or reorder untouched lines (`refactoring-technique`).
- Every new symbol follows local naming and placement; a stranger could find it by search.
- The diff introduces no new library, logger, or helper that duplicates an existing one.

## Anti-patterns
- Not "cleaner" — a local change that reads like its neighbours beats a better pattern.
- Not a helper "for reuse" that has one call site.
- Not a drive-by reformat of a file you had to open.
- Not a parallel abstraction beside an existing one instead of reusing it.
- Not copying a pattern the codebase has already outgrown — that is an escalation, not a default.