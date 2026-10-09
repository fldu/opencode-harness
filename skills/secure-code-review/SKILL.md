---
name: secure-code-review
description: Review a diff or component in a fixed order — trust boundaries, new sinks, authorization, crypto and secrets, resource exhaustion, dependencies and config — holding it to boundary validation, allowlists, parameterised queries, bounded allocation, redaction by field name, least privilege, and fail-closed checks; Use when reviewing a pull request, a security-sensitive component, or a change that adds an endpoint, handler, job, or dependency, and when the diff is too large to review properly and must be reported as incomplete.
metadata:
  owner: Michal
  domain: security
---

# Secure Code Review

## When to use
- Any diff touching an endpoint, handler, job, queue consumer, admin path, or third-party call.
- A component that handles untrusted input, credentials, personal data, or file paths.
- Before merge on a change that crosses a trust boundary, even briefly.

## Rules

Review in this **fixed order**. Each step assumes the previous came back clean; do not reshuffle, because the steps are ordered by blast radius, not by convenience.

**1. Trust boundaries and privilege.** Does the diff move data across a process, network, privilege, tenant, or user-supplied boundary, or change *who may call what*? If yes, this is the review that matters — say so before reading a line of logic.

**2. Input sources and new sinks.** Query, shell, template, path, deserializer, HTTP client, log. For each new sink, name the source that reaches it (`injection-and-input-hardening` owns the flow analysis).

**3. Authorization on every new route, handler, job, and admin path** — including the ones with no UI and the ones behind a different verb (`authn-authz-review`).

**4. Crypto and secret handling.** Key/IV/nonce reuse; weak or hand-rolled algorithms; a non-cryptographic RNG for tokens or ids; non-constant-time secret comparison; secrets in source, fixtures, snapshots, logs, error strings, or URLs.

**5. Resource exhaustion.** Unbounded reads, allocations, loops, page sizes, decompression ratio, regex backtracking, connection and queue growth.

**6. Dependencies and config.** A new package; a changed default; a debug flag enabled; permissive CORS; disabled TLS verification; broadened IAM; an exposed admin port (`dependency-management`, `supply-chain-scanning`).

**Hold every line to these properties:**
- Validate and normalise at the boundary; reject a wrong type rather than coercing it.
- Allowlist over denylist, everywhere.
- Canonicalise a path before comparing, and verify containment **after** canonicalisation.
- Parameterised queries; no interpreter string built by concatenation or interpolation.
- Encoding matched to the output context, per sink.
- Bounded, checked allocation and checked arithmetic.
- Redact by field name, not by regex over a rendered message.
- Least privilege; fail closed when a security check itself errors.

**Scope.** Review what the diff changed **plus the two-hop neighbourhood it makes newly reachable**. Answer explicitly, even when the answer is no: did this diff change a trust boundary, a default, or a serialized format?

**When the diff is too large to review properly, say so.** Report the size, the fraction actually reviewed, and label the review incomplete. Request a split. Do not rubber-stamp.

**Emit findings in the nine-field format defined by `vulnerability-assessment`.** Do not restate or redefine that format here — it is a hard contract, and this skill only fills it in.

## Verify
- All six steps were walked in order, each with an explicit result.
- Every new sink has a named source or an explicit "no untrusted source".
- Every new route/handler/job has an authorization decision recorded, not assumed.
- Each finding carries all nine fields in order, and its CWE and OWASP category are both nameable.
- The completeness statement names the diff size and the fraction reviewed.

## Anti-patterns
- Not reviewing a diff larger than you can read carefully and calling it approved.
- Not spot-checking the changed lines while ignoring what they now make reachable.
- Not "no security issues found" without the six results behind it.
- Not fixing inline instead of reporting — a finding with a hidden patch is unreviewable.
- Not restating the nine-field format here; `vulnerability-assessment` owns it.
