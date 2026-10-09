---
name: supply-chain-scanning
description: Scan and attest what enters a build — dependency vulnerabilities against an enforced severity threshold, lockfile and checksum integrity, typosquatting and dependency-confusion risk, secret scanning across git history, and artifact provenance; Use when wiring or tuning a scanner, when a scan must pass or be formally accepted, when a package name or registry could be hijacked, or when an artifact's origin must be provable by a consumer.
metadata:
  owner: Jozef
  domain: infrastructure
---

# Supply Chain Scanning

> Scope — detection and enforcement. Whether to add the dependency at all is `dependency-management`; what runs in the build is `ci-pipeline`; image scanning of a shipped artifact is `containerization`.

## When to use
- Adding, upgrading, mirroring, or vendoring anything that executes during the build.
- A scan is red, or a scan has been "allowed" so often it is decoration.
- Publishing an artifact whose origin a consumer must be able to verify.
- A secret may exist in history, in a fixture, in an artifact, or in an image layer.

## Rules

**Vulnerability scanning that is actually enforced**
- Scan direct **and transitive** dependencies in the real resolved tree, in the mode production resolves — not the developer's loose tree. Tools are illustrative and interchangeable (language-native audit/OSV-class scanners, image scanners, IaC and secret scanners); what matters is which tree is read, the threshold, and that it blocks.
- Set one severity threshold that **fails the build**, plus an explicit written policy below it.
- **Most transitive CVEs are unfixable without a major upgrade.** That is why the policy needs an accept-and-document path rather than an ignored scan: every accepted finding carries the advisory id, the reason (no fix available / fix requires a breaking upgrade / mitigated by isolation), an owner, and a revisit date, in a file a human reviews (an ignore entry with a required comment, an exception register, a ticket). An exception with no expiry is a permanent silent hole.
- Never blanket-ignore a package, a path, or the whole scan to reach green — that disables the scanner with extra steps.
- Scan the full transitive tree and newly published advisories on a schedule, not only at change time; today's CVE is in no report written yesterday.

**Lockfile and integrity**
- Commit the lockfile and verify integrity hashes on every install (frozen/locked/ci install modes). An install that re-resolves in CI is not reproducible (`ci-pipeline`).
- A checksum change with no matching version change is an incident — stop and investigate, do not accept the new hash because the build asked nicely.
- Fetch through authenticated, integrity-checked transports; no plain tarball from an arbitrary URL inside a build script.

**Typosquatting and dependency confusion**
- Every install resolves from explicitly configured registries, one per scope. Silent fallback to a public registry is the dependency-confusion hole — an internal scope name can be claimed publicly and your install starts pulling someone else's package.
- Reserve internal names in public namespaces where the registry allows it; keep scopes explicit; never rely on an unstated default registry.
- Check new dependency names for near-misses with popular packages (single-character and homoglyph edits) at diff time, not in a postmortem.
- Do not install by URL, branch, or commit from an unmirrored third-party repo in a release build; mirror what the build needs instead.
- Pin by immutable digest wherever the ecosystem supports it — image tags, action refs, download URLs. A floating reference is a decision nobody made.

**Provenance and attestation**
- For every published artifact record the source commit, the builder identity, the workflow/run id, and a signature over the artifact. Use the ecosystem's native mechanism — keyless OIDC signing (Sigstore/cosign class), in-toto/SLSA-class attestations, registry or package-registry provenance — and verify with the matching verify command.
- Publish an SBOM retrievable by digest, and check that secret scanning covers image layers and build artifacts, not just the working tree.
- Verification must be runnable **by a consumer**, not only by you: the verify command and its expected result belong in the release notes (`release-automation`).
- Where the ecosystem has no signing, achieve the property instead — immutable digest pins, checksum verification on install — and state the residual gap rather than claiming provenance.

**Secrets and updates**
- Scan the working tree **and the full history**, plus CI logs, artifacts, and image layers — a deleted secret is still in every clone and every published image.
- Every finding is rotate first, remove second. Deleting the line without rotating the credential leaves it live.
- Known-pattern matching is necessary and insufficient; add entropy and provider-specific checks, and treat a first run with zero findings as information about the scanner, not about the repository.
- Automated dependency-update changes are expected: each runs the full gate, each is read by a human, and a mass-update change is never merged unread.

## Verify
- Show the scan output for the resolved tree, the threshold, and the exit status the build saw.
- Show the accept register — every exception with id, reason, owner, and expiry — and its trend over time.
- Corrupt a checksum or digest in the lockfile on a scratch branch and confirm the install fails closed.
- Run provenance verification as a consumer would, from the published artifact, and quote the result.
- Rotate one scanned secret and show the finding only clears after rotation, with the old value confirmed dead.
- Confirm every scope has an explicit registry and that no install can fall back to a default.

## Anti-patterns
- Not a scan that reports but does not block — no threshold, no gate, no signal.
- Not a blanket ignore to reach green, and not an exception with no owner or expiry.
- Not a lockfile install that re-resolves, and not accepting a changed checksum to make a build pass.
- Not public-registry fallback for a private scope, and not installing by URL or branch in a release build.
- Not scanning only the working tree when the secret is in history or in a published layer.
- Not deleting a leaked secret without rotating it.
- Not publishing an artifact with no signature, no SBOM, and no consumer-runnable verify command.
