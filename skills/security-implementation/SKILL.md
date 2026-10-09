---
name: security-implementation
description: Write code that handles untrusted input safely and keeps secrets, permissions, and network reach minimal; Use when validating input from outside the trust boundary, when building file paths, queries, or command invocations from data, when adding serialization, temporary files, file modes, or network access, or when reviewing a change for injection, traversal, TOCTOU, or deserialization exposure.
metadata:
  owner: Jeff
  domain: implementation
---

# Security Implementation

## When to use
- Any code path reachable with input you did not create: HTTP, CLI arguments, files, environment, queues, headers.
- Building a path, a query, a template, or a shell command from data.
- Adding a secret, a permission, a file mode, or a network destination.

## Rules
- **Validate and normalize at the boundary**, once. Parse into a trusted value; downstream code works with the parsed value, not the raw string.
- **Allowlist over denylist.** Enumerate what is accepted. A denylist is a to-do list of bypasses.
- **Canonicalize before checking**: resolve `.` and `..`, normalize separators, percent-decode exactly once, resolve symlinks, then compare against the allowed root. Check the canonical path, not the input.
- **No secrets in source, tests, fixtures, snapshots, logs, or error messages.** Use the repository's existing secret mechanism and reference it; never invent a second. Fail at startup if a required secret is absent.
- **Use the safe or checked API**: checked arithmetic for sizes and offsets, parameterized queries, bounded allocations, length-prefixed or schema-validated deserialization, and no shell or string interpolation of external data — pass an argument vector, never a command string.
- **Least privilege**: new files get the narrowest workable mode, directories are not world-readable, network reach covers only what the feature needs. Nothing wide "just for debugging" — a debug allowance is tracked and expires.
- **TOCTOU**: never check a path, permission, or identity in one step and act on it in another. Use the atomic form the platform provides (open-with-flags, exclusive create, compare-and-swap) so the thing you checked is the thing you use.
- **Temp files**: create them in the destination directory with exclusive create, a fixed restrictive mode, and unlink on every exit path.
- **Untrusted deserialization is a parser, not a cast**: bound depth, size, element count, and recursion; reject types not expected; prefer data-only formats over ones that construct behavior.
- **Fail closed** whenever a security check itself errors (`correctness-errors`).
- Threat modeling, vulnerability rating, and severity scoring belong to Michal's `threat-modeling` and `vulnerability-assessment` skills. Escalate there rather than rating risk yourself; report anything you notice while implementing with location and reproduction steps.

## Verify
- Every input path has a boundary validation point; grep for parsers and confirm each has one.
- Test traversal and canonicalization with encoded, doubled, and symlinked variants.
- Grep the diff for shell invocation, string-built queries, and mode or permission arguments; each has a safe form.
- No secret-shaped literal exists in the diff, in fixtures, or in any new log or error string.

## Anti-patterns
- Not a denylist of extensions or characters.
- Not checking a path, then opening the original string.
- Not `run("sh", "-c", user_input)`.
- Not permissive modes "temporarily".
- Not hand-rolled crypto or an auth decision — that is Michal's call (`escalation-rules`).