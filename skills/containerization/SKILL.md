---
name: containerization
description: Build images that are small, reproducible, minimal-privilege, and correctly stoppable; Use when writing or repairing a Dockerfile or image build, choosing a base image, shrinking an image, fixing a container that ignores SIGTERM or takes 30s to die, or adding vulnerability and provenance scanning to the image build.
metadata:
  owner: Jozef
  domain: infrastructure
---

# Containerization

## When to use
- Writing, repairing, or reviewing any image build: Dockerfile, Containerfile, Buildpacks, Nix, `.img` definitions, CI image specs, Kubernetes pod specs.
- An image is too large, builds unreproducibly, or rebuilds from cache-less hell.
- A container in production ignores SIGTERM, is killed mid-request, or leaks state between runs.
- Choosing or bumping a base image.

## Rules

**Base image**
- Pin by digest, not a floating tag: `image@sha256:...`. A tag like `latest` or even `3.12` is a different image tomorrow, with no diff and no review. Record why the digest was bumped.
- Choose the smallest base that runs the app: a distroless/chroot-less static image, a slim runtime-only variant, or scratch for a static binary. Avoid a full distro with a shell and a package manager you do not need at runtime.
- Use a minimal non-root user (`USER`, or `USER 65532:65532`) created in the image. Never `root` at runtime, and never `chmod 777` to "fix" a permission error.
- Where the orchestrator allows, set a **read-only root filesystem** plus an explicit writable mount list; keep writable paths (`/tmp`, caches, state) as volumes, not as image content.

**Build**
- **Multi-stage**: a build stage with the toolchain and source, a runtime stage with only the artifact. The final stage must not contain compilers, headers, package managers, or the source tree.
- **Layer ordering for cache**: least-changing first. Copy the lockfile and install dependencies *before* copying source, so a source edit does not invalidate the dependency layer.
- Exclude everything irrelevant via `.dockerignore` before the first `COPY`: `.git`, `node_modules`, build outputs, test fixtures, docs, editor state, `.env`, credentials. A large build context is slow and leaks files into layers.
- Never bake credentials, tokens, `.env` files, or a full `.git` directory into any layer, including layers a later `RUN rm` would "remove". In a layered filesystem, a deleted file in a later layer still exists in the earlier one.
- **No package manager cache in the final layer**: clear the download cache in the *same* `RUN` that installed, so it is not a separate cached layer.
- Create the user, set ownership, and drop root *in the build*, before the artifact is copied, so no step in the final image runs as root.

**PID 1 and signal handling — the part people lose**
- Run the process **in exec form** (`CMD ["/app"]`, `ENTRYPOINT ["/app"]`), never shell form. Shell form makes the shell PID 1, the app PID 2, and **the app never receives SIGTERM** — it is killed at the orchestrator's grace period with no drain.
- PID 1 in a container has no default signal handlers and no parent to reap orphans. The process must: handle SIGTERM, handle SIGINT, ignore SIGHUP, reap children, and exit 0 on SIGTERM once drained. That may mean a tiny init (`tini`, `dumb-init`, `--init`) or explicit handlers in the app.
- **Graceful shutdown is where drain logic gets lost**: on SIGTERM, stop accepting new work, finish or hand off in-flight requests within the grace period, flush buffered telemetry, close listeners, then exit. The app's timeout must be shorter than the orchestrator's termination grace period, or the kill always wins.
- If the process legitimately cannot exit promptly, that is a design bug in the drain path, not a longer grace period.
- Do not depend on unmounting or file cleanup at exit; mount an explicit writable path and leave the container's own writes disposable.

**Reproducibility and supply chain**
- The same source digest must produce the same image digest. Pin base digest, pin toolchain version, fix timestamps and ordering where the ecosystem allows; do not embed the build time or a host path in a layer.
- Record provenance for the image: source commit, builder, workflow id, and base digests. Produce an SBOM and a signature/attestation where the platform supports it (`supply-chain-scanning`).
- Scan the **final** image — not just the source tree — against a stated severity threshold, and fail the build on it. Scanning the wrong stage reports the toolchain and not your risk.

## Verify
- `docker history <image>` (or the equivalent) inspected: no layer adds credentials, `.git`, a package cache, or a compiler to the final stage.
- Image size compared before and after; the runtime stage contains no build tool (`which cc`/`sh` absent unless required).
- Run the image and send SIGTERM (`docker stop`, `kubectl exec kill -TERM 1`); observe the app drains and exits 0 **well inside** the grace period, and the exit is not a SIGKILL.
- Rebuild the same commit twice and compare image digests; a mismatch is a reproducibility defect.
- Run the image as its declared non-root user with a read-only root filesystem; confirm it starts.
- Show the vulnerability scan output for the final image against the stated threshold.

## Anti-patterns
- Not `FROM x:latest` — pin the digest and review the bump.
- Not shell-form `CMD` — exec form, or the app never sees SIGTERM and drain never runs.
- Not a package cache, `.git`, or `.env` in the image; "it is removed later" is not removal.
- Not `USER root` in the final stage, nor a `chmod 777` to silence a permission error.
- Not a single-stage image shipping the compiler, source, and build cache to production.
- Not a `.dockerignore` that does not exist while the build context contains the whole repo.
- Not scanning the source tree and calling the image safe — scan the shipped artifact.
- Not copying source before the lockfile — that defeats the cache on every commit.
