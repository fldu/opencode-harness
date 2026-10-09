---
name: release-automation
description: Version, changelog, tag, sign, gate, and roll back releases from the change set rather than by hand; Use when cutting a version, deciding whether a change is major or minor, writing or fixing a changelog entry, setting up a release gate, or when a rollback path must exist before it is needed.
metadata:
  owner: Jozef
  domain: infrastructure
---

# Release Automation

## When to use
- Cutting any version that leaves the team — tag, publish, announce.
- Debating whether a change is major, minor, or patch.
- A release needs a changelog, a tag, a signature, or a checksum.
- A published artifact must be attributable to a commit, or a bad release must be undoable.

## Rules

**Semantic versioning, applied honestly**
- A **breaking** change to a public contract — removed or renamed API, changed default, changed wire or storage format, changed error semantics, tightened validation — is a **major** bump. "It is still beta/internal" is a reason to have no version contract at all, not to smuggle a break into a minor.
- A **bug fix** that changes no contract is a **patch**, not a minor. A new backward-compatible capability is a **minor**. Pre-release (`-rc.N`) is a label, not permission to break compatibility silently; while the project is pre-1.0 a minor may break, but the changelog must say so every time.
- Version strings in files, images, and registries are generated from one source of truth. Hand-editing a version in three places is a defect.

**Derive, do not author**
- The version comes from the change set and the changelog is generated from it. Nobody types a version into a file to make a release happen.
- Tooling is illustrative and interchangeable — `git-cliff`/`conventional-changelog`/`release-please`/`semantic-release` (JS), `git-chglog`/`towncrier`/`scriv` (Python), `release-it`/`cargo-release`/`goreleaser` (polyglot). The properties required:
  1. commits or PR labels classify each change (Conventional Commits, or PR labels where commits are not trusted);
  2. the highest breaking change forces the major bump; `feat:` forces minor, `fix:` forces patch, `perf:`/`refactor:`/`chore:` stay silent unless they cross a documented contract;
  3. anything unparseable **fails the release** rather than being silently dropped or guessed;
  4. the generated file is committed, so a release is a reviewable diff.
- **Version bump, changelog, and tag come from one commit**, produced by one command. A release is not three hand-run steps.

**Changelog**
- Stated format: `Breaking / Added / Fixed / Changed / Deprecated / Security`, ordered by severity, with the version and date.
- One entry per user-visible change, phrased as the change and its effect, not as the commit subject.
- **Keep the "why" from the PR body** — the commit subject says what, only the PR body says why. Pull a short rationale and any migration note into the entry.
- Breaking entries carry exact migration steps; a breaking entry without them is an incomplete release. Security entries disclose without exploit detail and cross-link the advisory. Never edit a released version's changelog — corrections go into the next release as `Changed`.

**Tag, sign, attest**
- Annotated tag, not lightweight — the message and tagger identity are the record. Signed where the ecosystem supports it (`git tag -s`, GPG/SSH key, or a keyless Sigstore-style attestation flow).
- Tag exactly the released commit, and never move or re-create a published tag: a moved tag is indistinguishable from tampering.
- Publish a checksum and, for images and binaries, an SBOM next to every artifact, and record provenance — builder identity, source commit, workflow id, toolchain versions (`supply-chain-scanning` for attestation and verification, `containerization` for image provenance).

**The release gate**
- The required CI checks for the tagged commit are green and actually required (`ci-pipeline`).
- The full suite for that exact commit passed, including integration and e2e (`testing-strategy` owns what those tests must prove).
- No open blocking finding at or above the enforced threshold (`supply-chain-scanning`).
- The working tree is clean, this version's changelog is committed, and migration and rollback notes exist for anything breaking.
- The artifact built from the tagged commit is the artifact published — build once, promote that exact artifact, never rebuild at deploy time.

**Rollback, tested before it is needed**
- Every release states its rollback: previous tag, previous artifact digest, and whether it is a redeploy, a migration revert, or a forward fix. "Forward fix" must be an explicit, acceptable answer; "rollback impossible" is a release-gate escalation, not a footnote.
- Data migrations must be expand/contract or otherwise backward compatible across exactly one release, so the previous binary runs against the new schema. A destructive migration shipped alongside the code that needs it removes the option to roll back.
- **Rehearse the rollback before the incident** — on staging, from the real artifacts, timed. An untested rollback plan is a hypothesis, and the elapsed time sets incident expectations.

## Verify
- `git tag --points-at HEAD`, `git cat-file -t <tag>`, and the ecosystem's signature check (`git tag -v`, `cosign verify`) — output quoted.
- Show the version-bump commit's diff: one commit containing version files, changelog, and lockfile bumps only.
- Rebuild from the tagged commit in a clean environment and compare checksums with the published artifact — they must match.
- Demonstrate the rollback on staging from the real artifacts, and time it.
- Read every breaking changelog entry against the diff and confirm each has migration steps; confirm the gate fails when one condition is violated (scratch tag).

## Anti-patterns
- Not "minor because I added something" when a public API was removed or renamed — that is major.
- Not hand-editing a version string in a file, a manifest, and a registry — derive it.
- Not a changelog of commit subjects with no rationale, and no migration steps for a break.
- Not re-creating or moving a published tag, or publishing an artifact rebuilt after the tag.
- Not a rollback plan written during the incident — rehearse it on staging first.
- Not a destructive data migration shipped with the code that requires it — that removes rollback.
- Not a release that went out while a required check was red or skipped.
