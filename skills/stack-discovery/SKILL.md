---
name: stack-discovery
description: Discover the real build, test, lint, format, type-check and benchmark commands of an unfamiliar repository before writing code; Use when starting in an unknown project, when the README and the CI configuration disagree, when no test command appears to exist, or when tempted to assume a language, package manager, or toolchain the repository does not use.
metadata:
  owner: Jeff
  domain: shared
---

# Stack Discovery

## When to use
- First action in any repository you have not already worked in during this session.
- Before quoting a command in a plan, a report, or a ticket.
- Whenever a "quick check" depends on a tool you are not certain exists.

## Rules
Read before you run anything, in this order, stopping once the commands are pinned:

1. `README*`, `CONTRIBUTING*`, `docs/` — the claimed workflow and the pinned runtime version.
2. Task runners: `Makefile`, `justfile`, `Taskfile*`, `*.mk`, `scripts/`.
3. Manifests and lockfiles: `package.json` + its lockfile, `Cargo.toml`/`Cargo.lock`, `go.mod`/`go.sum`, `pyproject.toml` + lock or `requirements*.txt`, `*.csproj`, `pom.xml`, `build.gradle*`, `mix.exs`, `pubspec.yaml`, `Package.swift`, `*.cabal`, `composer.json`.
4. CI workflow files (`.github/workflows/*`, `.gitlab-ci.yml`, `.circleci/*`, `Jenkinsfile`, `.buildkite/*`) — **CI is truth**.
5. Linter, formatter, type-checker, and benchmark configuration; they name the exact invocations and flags.
6. The existing test layout: which kinds of tests exist and where, so you extend rather than invent.

- **Conflicting signals: CI wins.** If the README says one command and the workflow runs another, the workflow defines correctness. Fixing the README is a separate, explicit change.
- **No test command exists**: say so in `handoff-report`, then add the smallest thing the pinned ecosystem already provides (its own built-in test harness or runner). Do not introduce a framework, a package manager, or a CI change — that is Jozef's (`escalation-rules`).
- **Never assume a toolchain.** If a required tool is absent, report it as a blocker naming the version CI installs. Do not install it, do not substitute a near-equivalent command, and do not silently fall back to a weaker check.
- **Record the exact command set before the first edit**, so every later report quotes commands that exist.

## Verify
- Every command cited later in the session was found in a file, not remembered.
- Commands are run the way CI runs them: same working directory, flags, and environment.
- The pinned runtime version matches what CI installs.

## Anti-patterns
- Not "I know this stack" — a repository overrides your memory every time.
- Not substituting a familiar command for the repository's real one.
- Not adding a test framework because none was found — report it first.
- Not running a local check CI never runs and calling it verified.
- Not editing files before discovery; that is how conventions get broken (`codebase-conventions`).