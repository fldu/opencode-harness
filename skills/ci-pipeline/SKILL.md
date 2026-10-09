---
name: ci-pipeline
description: Design and repair CI as a fast, hermetic, least-privilege job graph whose green run is the definition of truth; Use when adding or reordering jobs, wiring caching or artifacts between jobs, choosing a matrix, granting CI credentials, setting required status checks, or when a red pipeline must be impossible to ignore.
metadata:
  owner: Jozef
  domain: infrastructure
---

# CI Pipeline

## When to use
- Adding, reordering, splitting, or deleting a job — a pipeline is a graph, not a list.
- A pipeline is slow, flaky, or fails on CI but not locally.
- Granting a job a credential, cache, artifact, or network permission.
- Deciding what blocks a merge (`testing-strategy` owns what the tests must prove; this skill owns the graph around them).

## Rules

**Job graph, ordering, and matrix**
- Order by information value and cost: static checks (lint, format, types) → build → unit → integration → contract → security scans → e2e. Fast, cheap, decisive signals first.
- Declare dependencies explicitly (GitHub Actions `needs:`, GitLab `needs:`, Jenkins `stages`, Circle `requires:`, or plain Make targets) — never implicitly, through side effects on a shared runner.
- Independent jobs run in parallel; two jobs with no edge between them that run sequentially are a defect. Fail fast: no `continue-on-error` on a gate job, only on non-blocking jobs that still report visibly.
- A matrix multiplies cost by cell count plus queue time: fan out only across dimensions that change behaviour (OS, arch, runtime major), always include the cell production actually runs, exclude impossible cells explicitly, and use `fail-fast: false` only when you need the whole matrix.

**The pipeline is the definition of truth**
- The canonical build+test command lives in the repo (Makefile, taskfile, justfile, package script), not in CI YAML. CI invokes it and never re-implements the steps, so a CI failure reproduces locally in one command.
- Required status checks are set on the protected branch and list every gate job; adding a gate means adding its check name in the same change, or the check is decorative. A job that cannot fail is a bug — prove each gate can go red on a scratch branch.

**Caching**
- Key on the **hash of the lockfile/manifest**, never on the branch name — `<toolchain>-<lockfile-hash>-<target>` (illustrative: `actions/cache` with `key: ${{ hashFiles('**/lock.json') }}`).
- A cache hit must be a speedup, never an assumption: every job passes cold, so prove it by clearing caches and running once.
- Never cache a directory the job also writes without a key covering the write dimension, never outside the keyed path, and treat every shared cache as a shared secret store — it holds credentials and source.

**Artifacts**
- Pass build outputs as artifacts, never by re-building; name them with the commit sha so a stale download is detectable.
- Publish logs, reports, and coverage even when a later job fails — evidence is needed for triage (`flaky-test-triage`, `root-cause-analysis`).
- Keep artifacts small and bounded: strip debug symbols where unneeded, compress, never ship a dependency tree between jobs. Check your CI vendor's current storage limits before raising them; they are vendor-set and change.

**Credentials and secrets**
- Least privilege per job, not per pipeline: a format job needs no publish token, only the publish job gets one (illustrative: per-job `permissions:` block, scoped `id-token` only where federation happens).
- Never one shared token across jobs; prefer short-lived OIDC-style federation so there is nothing to rotate.
- Scope each credential to the minimum repositories, packages, environments, and paths. Write-everything is a supply-chain hole (`supply-chain-scanning`).
- Secrets are never echoed, never passed as build arguments that appear in a process listing or a printed build line, and never written into generated files that get uploaded — mask in the log layer *and* keep them out of the command echo.

**Determinism**
- Pin the toolchain by exact version (`.tool-versions`, `rust-toolchain.toml`, `.nvmrc`, `go` directive, `.python-version`), installed from a lock, never "latest".
- No network at test time — provision dependencies in a setup step and let tests run hermetically (`testing-strategy`). Pin the seed, sort glob expansion, fix timezone and locale, pin parallelism where it affects output.
- Two runs of one commit producing different artifacts is a stop-the-line defect: it invalidates every downstream comparison (`release-automation`, `performance-regression-gates`).

**Duration honesty, and a red run nobody can ignore**
- Track p50 and p95 duration. A pipeline nobody waits on is a pipeline nobody watches; a required check belongs in minutes, not tens of minutes. Push slow non-gating work (full e2e, cross-OS matrix) to a scheduled or post-merge run and say so in the check name.
- Flakiness is a latency bug: a retry loop costs more wall time than the flake and trains people to re-run.
- Branch protection with required checks, required review, no direct push and no force-push to the protected branch. Notify on failure (chat, mail, issue) — a red run nobody is told about is a green pipeline.
- No skip, no expected-failure, no long-lived red. If a check is knowingly broken, disable it in the same change that records why.

## Verify
- `ls` the graph: every edge declared, and independent jobs demonstrably overlap in start time.
- Run the canonical build+test command locally from a clean checkout and quote the output.
- Delete every cache for the branch and run the pipeline once — it must pass cold.
- Revoke each CI credential in turn and confirm only the jobs that need it fail, and for the right reason.
- Confirm the required-check list equals the gate set, and that each gate can be made red on a scratch branch.
- Report p50/p95 pipeline duration before and after.

## Anti-patterns
- Not "CI-only steps" — the repo's build command is what runs, so a local run reproduces CI.
- Not caching on branch name — key on the lockfile hash.
- Not one token for every job — scope per job, prefer short-lived federation.
- Not a secret in a build argument or a printed command line — it lands in the log.
- Not a required check that cannot fail, or a gate missing from the required list.
- Not a 40-minute blocking pipeline, a flaky retry loop, or a red run discovered a day later — split it, fix the flake (`flaky-test-triage`), and notify on failure.
