---
name: dependency-management
description: Add, pin, upgrade, and vendor dependencies without moving supply-chain risk; Use when adding a library, bumping a version, hitting a lockfile or integrity error, deciding whether to vendor, or when a major version arrives and the upgrade looks like a bump but is actually a migration.
metadata:
  owner: Jeff
  domain: implementation
---

# Dependency Management

## When to use
- Any change to a manifest or a lockfile.
- A build that behaves differently on your machine than in CI.
- Deciding whether a problem needs a new library at all.

## Rules
- **Prefer standard library and platform-provided primitives** when they meet the need. A dependency is a permanent contract with someone else's release schedule.
- **Every new dependency needs a stated need plus the rejected alternative** (a built-in primitive, a few lines here, a platform API), recorded in `handoff-report`. "It is the standard choice" is not a need.
- **Respect the lockfile**: commit it, never hand-edit it, never resolve differently in CI than locally. Integrity checksums are verified — a checksum change without an intended version change is an incident, not a fix.
- **Pin exact versions** for runtime and build dependencies that affect behavior. Do not float a range in a deployable artifact.
- **Check transitive risk before adding**: how many packages come with it, who maintains it, last release, open advisories, license compatibility, and whether it is abandoned or single-maintainer. A three-line utility is not worth four hundred transitive packages.
- **Prefer adding over replacing.** Do not swap an existing dependency as a side effect of a feature; that is its own change with its own risk.
- **A major version upgrade is a migration, not a bump**: read the release notes, enumerate breaking changes, do it as a dedicated step with the suite green before and after (`refactoring-technique`).
- **Vendoring** (checking dependencies into the repository) is a deliberate offline or reproducibility decision. Confirm it is what the build expects, and accept the update burden — confirm the direction via `escalation-rules` before introducing it.
- **Never upgrade opportunistically** inside a feature diff, so a regression stays attributable.

## Verify
- The lockfile changed only in the entries required, and the resolved tree matches CI's.
- The install and verify commands CI runs pass from a clean checkout, and the output is quoted.
- Each new dependency has its need and its rejected alternative in the report.
- The changelog breaking-change list for any version bump has been read and reconciled against the diff.

## Anti-patterns
- Not "add the library" with no alternative considered — dependency shape is a design decision (`escalation-rules` for the large ones).
- Not hand-editing a lockfile to make a build pass.
- Not mixing a major upgrade with a feature.
- Not floating versions in an artifact.
- Not dismissing a checksum or advisory warning as "probably fine".