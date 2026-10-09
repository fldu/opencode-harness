---
name: data-compatibility
description: Change schemas, wire formats, and configuration additively so old and new code can run side by side; Use when adding or renaming a field, column, endpoint, parameter, event, log key, metric name, or config key, when removing anything a deployed version might read, when writing or ordering a migration, or when a value could be consumed by a version that is still running.
metadata:
  owner: Jeff
  domain: implementation
---

# Data & Compatibility

## When to use
- Any change to a stored or transmitted shape: schema, API, event, queue message, file format, config key.
- Renaming or removing anything a deployed version might read or write.
- Writing, ordering, or reversing a data migration.

## Rules
- **Additive and backward compatible by default**: new fields optional with a default an old reader can survive; new endpoints alongside old ones; new columns nullable.
- **A breaking change requires all three**: a version bump, a migration plan, and a dual-read or dual-write window so both versions work throughout the rollout.
- **Migrations are reversible, online, and separate from the code deploy** where possible: small forward steps, backward compatible at every step, no table lock or full-table rewrite on a hot path, and a tested undo.
- **Never change the meaning of an existing field, log key, metric name, or config key.** Deprecate loudly (a warning at the boundary plus a dated removal), read both during the window, then remove after the stated window. A rename is delete plus add, never a reinterpretation.
- **Parse defensively**: unknown fields are ignored, not rejected. A newer producer must never break an older consumer.
- **No config value may silently change behavior.** A new key gets a safe, documented default; changing an existing default is a breaking change with a release note. Validate config at startup and fail naming the offending key.
- **No field becomes required without a version gate.**
- **Irreversible data actions** (drop, truncate, backfill) are staged: dry-run, report the count, then require explicit confirmation. Split them out if they exceed the ticket (`scope-control`).

## Verify
- Grep the diff for removed or renamed identifiers; each has a deprecation path and a stated removal window.
- Test an old-payload/new-reader pair and a new-payload/old-reader pair; both succeed.
- Run the migration forward and backward against production-shaped data; record row counts and duration.
- Every new config key has a documented default and appears in the repository's reference or sample config.

## Anti-patterns
- Not a rename that changes meaning in place.
- Not "reject unknown fields" on a public or versioned format.
- Not a migration in the same deploy as the code requiring it, with no rollback.
- Not changing a default value and filing it as a bug fix.
- Not a mandatory new field with no version gate.