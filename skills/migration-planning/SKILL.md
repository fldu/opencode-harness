---
name: migration-planning
description: Change a live schema, protocol, storage engine, service boundary, or contract by expanding, migrating, then contracting — every step independently reversible and written down before it ships, old and new versions running concurrently, backfills bounded, resumable, throttled and observable, and contraction gated on proven non-use; Use when any deployed code depends on what is being changed, when adding or removing a column, field, endpoint, or message shape, or when planning a cutover, dual-write, or data backfill against production.
metadata:
  owner: Daedalus
  domain: architecture
---

# Migration Planning

## When to use
- Changing a schema, protocol, storage engine, service boundary, or any contract a deployed version depends on.
- Adding, renaming, or removing a column, field, endpoint, topic, or message shape.
- Planning any cutover, dual-write, or backfill against production data.

## Rules

**The core rule is EXPAND, MIGRATE, CONTRACT.** Add the new alongside the old, backfill and dual-write, move readers, then remove the old only after a stated soak proving nothing reads it. Additive-first shape changes belong to `data-compatibility`; this skill is the sequencing and rollback discipline around them.

**1. Every step is independently reversible, and the reversal is written down before the step ships.** A migration you cannot roll back is an outage waiting for a trigger.

**2. Old and new must run concurrently.** A rolling deploy means both versions are live at once — that is the normal case, not the exception. If the two versions cannot coexist, the deploy is not rolling and the plan is wrong.

**3. Schema changes are additive first:** add the nullable column or the new table → deploy code that writes both → backfill → switch reads → drop the old. Each arrow is a separate, reversible step.

**4. Backfills run in bounded, resumable, throttled batches against production** — never one unbounded UPDATE, never during peak, and always with a kill switch. Record progress so a resume does not redo work and does not skip rows (`correctness-errors` for the failure paths).

**5. CONTRACT is a separate, later change**, gated on a stated verification that nothing still references the old artefact: a code search, a query-log check, and a soak period measured in **real traffic**, not minutes.

**6. The rollback path is tested, not assumed**, and a destructive step is never in the same release as the change that enables it.

**7. Dual-write is a compatibility tool with a real cost** — two writes per operation, and divergence is possible. State how divergence is detected, how it is reconciled, and when dual-writing stops. "We write both" is not a plan; it is a second source of truth.

**8. Budget for old code staying alive.** Instances running the old version exist for the entire rollout, plus the soak. That duration is the migration's real schedule, and the rollback window must outlast it.

## Verify
- Each step lists its reversal, and the reversals were exercised — not merely written.
- The concurrency assumption is stated and true: old and new code were run against the same data at the same time.
- The backfill is bounded per batch, resumable from a recorded point, throttled, observable, and has a kill switch.
- The contract step has a stated "nothing reads this" check and a soak duration in real traffic.
- No destructive change shares a release with the code that enables it.
- Divergence under dual-write has a detection method and a reconciliation owner.
- Field and shape compatibility was checked against old and new readers (`data-compatibility`).

## Anti-patterns
- Not a big-bang cutover on a single deploy.
- Not a backfill without a kill switch, without a resume point, or without a rate limit.
- Not dropping a column in the same deploy that stops writing it.
- Not calling a migration done when the script exits; it is done when the soak proves non-use.
- Not a rollback plan written after the failure, in the incident channel.
- Not assuming instances run the new code the moment the deploy starts.
