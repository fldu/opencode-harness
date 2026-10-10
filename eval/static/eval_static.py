#!/usr/bin/env python3
"""Tier 1: static / config-derived assertions. Deterministic, offline, free.

This tier answers one question -- *what does V1 actually resolve* -- and answers
it against the runtime rather than against our own reading of the source files.
Every assertion here is derived from `opencode debug agent <Name>`, which is
the same resolution the behavioural tier will run under.

`make check` is a prerequisite of the target that runs this, and it is not
weakened or duplicated: A1-A6 compare text in the repo, this tier checks the
merged rule array. The overlap is stated case by case in the README rather
than hidden.

Exit status is 0 only when every assertion passes. Exit 1 otherwise.

Usage:  eval_static.py [--repo PATH] [--keep]
"""

from __future__ import annotations

import argparse
import filecmp
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from harness import (  # noqa: E402
    AGENT_FILES,
    AGENT_NAMES,
    MIN_INSTALLED_SKILLS,
    MIN_RESOLVED_RULES,
    VERIFIED_VERSION,
    IsolationError,
    Report,
    debug_agent,
    eprint,
    fingerprint,
    installed_skills,
    last_matching_index,
    make_sandbox,
    opencode_bin,
    opencode_version,
    resolve,
)

MIRRORING_AGENTS = ["Jeff", "Jozef", "Sherlock"]

# Commands the deny-list exists to stop, and the benign ones that must keep
# working. Asserting both directions matters: a deny-list that accidentally
# denies `ls` is a broken harness, and a test that only probes the dangerous
# commands cannot tell "correctly denied" from "bash is dead everywhere".
DANGEROUS_BASH = [
    "git push origin main",
    "git push origin master",
    "git push origin release",
    "kubectl apply -f deploy.yaml",
    "kubectl delete pod api",
    "kubectl exec -it api -- sh",
    "helm upgrade api ./chart",
    "helm install api ./chart",
    "terraform apply -auto-approve",
    "terraform destroy -auto-approve",
    "docker push registry.example/app:latest",
    "cargo publish",
    "npm publish",
    "curl http://169.254.169.254/latest/meta-data/iam/security-credentials/",
    "curl http://metadata.google.internal/computeMetadata/v1/",
]

BENIGN_BASH = [
    "git status --porcelain",
    "git diff --stat",
    "ls -la",
    "make check",
]

# Credential paths every agent must keep denied. Probed HOME-EXPANDED against
# the sandbox, because that is the only spelling the runtime can ask about:
# `opencode debug agent` shows every credential rule in the resolved array with
# `~` already expanded against the process HOME, so a value written with a
# literal tilde could not match a credential rule at all. See S5 for what
# happens to the literal spelling now that ordinary external paths ask.
CREDENTIAL_PATHS = [
    "~/.ssh/id_rsa",
    "~/.aws/credentials",
    "~/.config/gcloud/application_default_credentials.json",
    "~/.kube/config",
    "~/.gnupg/secring.gpg",
]

# Filesystem tools per agent, and the resolution each must produce. This is the
# shape of the guarantee Dispatcher's Non-negotiables rest on: it never writes
# a file and never runs a command itself.
#
# `write` is expected to resolve to deny for EVERY agent, including the two
# that may edit. `write` is not a V1 permission key at all -- `edit` is what
# covers write/edit/apply_patch (this is A5's whole point) -- so a lookup for
# it falls through to the agent's `"*": deny` catch-all. Asserting deny here is
# deliberate: it is what proves no agent can be talked into permitting file
# modification by adding a `write:` key, and it would fail loudly if one ever
# started resolving to allow.
TOOL_EXPECTATIONS = {
    "Dispatcher": {"bash": "deny", "edit": "deny", "write": "deny", "read": "allow"},
    "Daedalus": {"bash": "deny", "edit": "deny", "write": "deny", "read": "allow"},
    "Michal": {"bash": "deny", "edit": "deny", "write": "deny", "read": "allow"},
    "Sherlock": {"bash": None, "edit": "deny", "write": "deny", "read": "allow"},
    "Jeff": {"bash": None, "edit": "allow", "write": "deny", "read": "allow"},
    "Jozef": {"bash": None, "edit": "allow", "write": "deny", "read": "allow"},
}


def documented_skills(agent_file: Path) -> set[str]:
    """Skill names backticked in the agent's "## Load these skills" table.

    Only the first table column is read, so prose in the "When to load it"
    column (Jeff's row legitimately reads "`definition-of-done`, then
    `handoff-report`") cannot inject a name. Same shape-driven approach as
    `make check` A6: not a general Markdown parser, and an unrecognised shape
    yields an empty set which the caller's floor rejects.
    """
    names: set[str] = set()
    in_table = False
    for line in agent_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("## Load these skills"):
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if not in_table or not line.strip().startswith("|"):
            continue
        columns = line.split("|")
        if len(columns) < 2:
            continue
        first = columns[1]
        for chunk in first.split("`")[1::2]:
            if chunk.strip():
                names.add(chunk.strip())
    return names


def check_s7_name_resolution(report: Report, sandbox) -> None:
    """S7: an agent resolves by frontmatter `name:`, never by filename.

    `Dispatcher` resolves and `dispatcher` does not. That asymmetry is a
    documented V1 trap and nothing in A1-A6 looks at the `name:` key at all, so
    a renamed agent could pass the whole existing suite and still be
    unaddressable by `--agent`.
    """
    for name, filename in AGENT_FILES.items():
        path = sandbox.config / "agent" / filename
        stem = Path(filename).stem
        declared = None
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("name:"):
                declared = line.split(":", 1)[1].strip()
                break
        if declared != name:
            report.fail(
                "S7",
                f"agent/{filename} declares frontmatter name: {declared!r}, "
                f"expected {name!r}",
                "opencode addresses agents by frontmatter name, not filename",
            )
            continue
        # The lowercase spelling must NOT resolve. If it ever does, something
        # else has started matching on filename and this tier is looking at the
        # wrong array.
        proc = subprocess.run(
            [opencode_bin(), "debug", "agent", stem],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(sandbox.repo),
            env=sandbox.child_env(),
            check=False,
        )
        try:
            payload = json.loads(proc.stdout)
            resolved = isinstance(payload, dict) and bool(payload.get("permission"))
        except json.JSONDecodeError:
            resolved = False
        if resolved:
            report.fail(
                "S7",
                f"`opencode debug agent {stem}` (the filename spelling) resolved, "
                f"so agent/{filename} is addressable two ways",
            )
        else:
            report.ok("S7", f"{name} resolves by name; filename spelling does not")


def check_s8_deploy_equivalence(report: Report, sandbox) -> None:
    """S8: the tree this tier judged is the tree `make deploy` installs.

    The sandbox is populated by harness.make_sandbox, which mirrors the
    Makefile's COPY_CMDS. If the two ever drift, every other assertion here
    would still pass while describing a config the operator never installs --
    the worst possible failure mode for a gate. So it is checked, not assumed.

    Only the three paths COPY_CMDS manages are compared. Running opencode
    against a config dir makes opencode drop its own bookkeeping into it
    (`.gitignore`, and an `opencode.jsonc` alongside `opencode.json`); those
    are the runtime's artefacts, not part of what this repo installs, and
    comparing them would make this check fail on contact.
    """
    managed = ["agent", "skills", "opencode.json"]
    make = shutil.which("make")
    if not make:
        report.warn("S8 skipped: make is not on PATH, cannot verify deploy equivalence")
        return
    deploy_root = Path(tempfile.mkdtemp(prefix="opencode-eval-deploy."))
    try:
        dest = deploy_root / "opencode"
        proc = subprocess.run(
            [make, "-C", str(sandbox.repo), f"DEST={dest}", "deploy"],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if proc.returncode != 0:
            # `make deploy` runs `check` first, so a tree that `check` rejects
            # cannot reach the comparison. That is not an S8 finding -- it is
            # `check` doing its job, and it is already the target's
            # prerequisite -- so report it as a skip rather than a failure.
            # Failing here too would double-count one defect and bury whichever
            # assertion actually diagnosed it.
            report.warn(
                f"S8 skipped: `make DEST={dest} deploy` exited {proc.returncode}, so "
                "the tree did not install. `check` is the target's prerequisite and "
                "has already reported this; S8 is only reached when deploy succeeds."
            )
            return
        diffs: list[str] = []
        for entry in managed:
            mine = sandbox.config / entry
            theirs = dest / entry
            if not mine.exists() or not theirs.exists():
                diffs.append(f"{entry}: present in sandbox={mine.exists()} deploy={theirs.exists()}")
                continue
            if mine.is_file():
                if not filecmp.cmp(mine, theirs, shallow=False):
                    diffs.append(f"{entry}: differs")
                continue
            comparison = filecmp.dircmp(str(mine), str(theirs))

            def walk(node: filecmp.dircmp, prefix: str = "") -> None:
                diffs.extend(f"{entry}/{prefix}{n}: only in sandbox" for n in node.left_only)
                diffs.extend(f"{entry}/{prefix}{n}: only in deploy" for n in node.right_only)
                diffs.extend(f"{entry}/{prefix}{n}: differs" for n in node.diff_files)
                for name, sub in node.subdirs.items():
                    walk(sub, f"{prefix}{name}/")

            walk(comparison)
        if diffs:
            report.fail(
                "S8",
                f"the config this tier judged differs from what `make deploy` "
                f"installs ({len(diffs)} difference(s))",
                *sorted(diffs)[:10],
            )
        else:
            report.ok(
                "S8",
                f"agent/, skills/ and opencode.json are byte-identical to "
                "`make deploy` output",
            )
    finally:
        shutil.rmtree(deploy_root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--keep", action="store_true", help="keep the sandbox")
    args = parser.parse_args()

    repo_root = Path(args.repo).resolve()
    binary = opencode_bin()
    if not binary:
        eprint("eval-static: FAILED -- opencode is not on PATH.")
        eprint("eval-static: set EVAL_OPENCODE_BIN to the opencode binary.")
        return 1

    version = opencode_version(binary)
    print("eval-static: tier 1 -- config-derived assertions")
    print(f"  repo     {repo_root}")
    print(f"  opencode {binary} ({version})")
    if version != VERIFIED_VERSION:
        print(
            f"  NOTE  V1 semantics were verified against {VERIFIED_VERSION}; this "
            f"run observed {version}."
        )
        print(
            "        The assertions read whatever this binary resolves, but the "
            "ordering assumption they encode was confirmed by hand on "
            f"{VERIFIED_VERSION} only. A failure here after a runtime upgrade is "
            "a signal to re-verify, not automatically a regression."
        )

    try:
        sandbox = make_sandbox(repo_root, keep=args.keep)
    except IsolationError as exc:
        eprint(f"eval-static: FAILED -- {exc}")
        return 1

    print(f"  sandbox  {sandbox.root}")
    print(f"  HOME     {sandbox.home}  (the operator's {sandbox.real_home} is never used)")

    report = Report("eval-static")

    try:
        # ---- resolve every agent once, and refuse a vacuous rule set ----
        rules: dict[str, list[dict]] = {}
        for name in AGENT_NAMES:
            try:
                rules[name] = debug_agent(sandbox, name)
            except (RuntimeError, IsolationError) as exc:
                report.fail("S0", f"could not resolve agent {name}: {exc}")
        if not rules:
            report.emit()
            return 1

        missing_agents = [n for n in AGENT_NAMES if n not in rules]
        thin = [n for n, r in rules.items() if len(r) < MIN_RESOLVED_RULES]
        if missing_agents:
            report.fail(
                "S0",
                f"agent(s) did not resolve at all: {', '.join(missing_agents)}",
                "opencode could not read them. An agent whose frontmatter does not "
                "parse is an agent nothing can address with --agent, and every "
                "assertion below would silently skip it.",
            )
        if thin:
            report.fail(
                "S0",
                f"resolved rule array(s) below the {MIN_RESOLVED_RULES}-rule floor "
                f"for {', '.join(sorted(thin))}",
                "refusing to assert against a rule set this small; it would pass "
                "vacuously",
            )
        if not missing_agents and not thin:
            total = sum(len(r) for r in rules.values())
            report.ok(
                "S0",
                f"resolved {len(rules)} agents, {total} rules "
                f"({', '.join(f'{n}={len(rules[n])}' for n in AGENT_NAMES)})",
            )

        skills = installed_skills(sandbox)
        if len(skills) < MIN_INSTALLED_SKILLS:
            report.fail(
                "S6",
                f"only {len(skills)} installed skill(s) with a SKILL.md, expected at "
                f"least {MIN_INSTALLED_SKILLS}",
                "a skill scope assertion over an almost-empty set would pass "
                "vacuously",
            )
        else:
            report.ok("S6", f"probe universe: {len(skills)} installed skills")

        # ---- S1: skill scope, resolved ----
        # For each agent, resolve EVERY installed skill and require the allow
        # set to equal the declared allowlist and the documented table. Probing
        # all of them, rather than only the listed ones, is the part A6 cannot
        # do: A6 diffs two name lists in one file and never asks the runtime.
        for name in AGENT_NAMES:
            agent_rules = rules.get(name)
            if not agent_rules:
                continue
            agent_file = sandbox.config / "agent" / AGENT_FILES[name]
            documented = documented_skills(agent_file)
            resolved_allow = {
                s for s in skills if resolve(agent_rules, "skill", s) == "allow"
            }
            resolved_deny = {
                s for s in skills if resolve(agent_rules, "skill", s) == "deny"
            }
            unlisted = sorted(resolved_allow - documented)
            missing = sorted(documented - resolved_allow)
            other = sorted(s for s in skills if s not in resolved_allow and s not in resolved_deny)

            if unlisted:
                report.fail(
                    "S1",
                    f"{name} resolves `skill: allow` for {len(unlisted)} skill(s) it "
                    "does not document: " + ", ".join(unlisted[:6]),
                    "an undocumented capability -- the agent can load a skill no "
                    "table entry authorises",
                )
            if missing:
                report.fail(
                    "S1",
                    f"{name} documents {len(missing)} skill(s) that do not resolve to "
                    "allow: " + ", ".join(missing[:6]),
                    "the agent is told to load a skill the runtime will refuse",
                )
            if other:
                report.fail(
                    "S1",
                    f"{name} leaves {len(other)} installed skill(s) resolving to "
                    f"{resolve(agent_rules, 'skill', other[0])!r} rather than a "
                    "clean allow/deny: " + ", ".join(other[:6]),
                )
            if not unlisted and not missing and not other:
                report.ok(
                    "S1",
                    f"{name}: {len(resolved_allow)} allow / {len(resolved_deny)} deny "
                    "over all installed skills",
                )

        # ---- S2: the bash deny-list, resolved ----
        # This is the assertion that would have caught the original defect. A
        # bare `bash: allow` in an agent appended AFTER the global rules makes
        # every one of these commands resolve to allow; the file-level checks
        # were written afterwards, this one is what proves the runtime agrees.
        for name in MIRRORING_AGENTS:
            agent_rules = rules.get(name)
            if not agent_rules:
                continue
            wrongly_allowed = [
                cmd
                for cmd in DANGEROUS_BASH
                if resolve(agent_rules, "bash", cmd) != "deny"
            ]
            wrongly_denied = [
                cmd for cmd in BENIGN_BASH if resolve(agent_rules, "bash", cmd) != "allow"
            ]
            if wrongly_allowed:
                agent_rel = f"agent/{AGENT_FILES[name]}"
                report.fail(
                    "S2",
                    f"{name}: {len(wrongly_allowed)}/{len(DANGEROUS_BASH)} denied "
                    f"command(s) resolve to something other than deny",
                    *(
                        f"{agent_rel}: {cmd!r} resolves to "
                        f"{resolve(agent_rules, 'bash', cmd)!r}, expected 'deny'"
                        for cmd in wrongly_allowed
                    ),
                    "the agent's own `bash` block is missing the matching deny "
                    "pattern, or a wildcard allow was ordered after it",
                )
            if wrongly_denied:
                report.fail(
                    "S2",
                    f"{name}: benign command(s) blocked: "
                    + ", ".join(repr(c) for c in wrongly_denied),
                    "a deny-list that breaks `git status` is a broken harness",
                )
            if not wrongly_allowed and not wrongly_denied:
                report.ok(
                    "S2",
                    f"{name}: {len(DANGEROUS_BASH)} denied, {len(BENIGN_BASH)} allowed",
                )

        # ---- S3: non-bash tool gating ----
        for name, expectations in TOOL_EXPECTATIONS.items():
            agent_rules = rules.get(name)
            if not agent_rules:
                continue
            bad = []
            for tool, expected in expectations.items():
                if expected is None:
                    continue
                probe = {"bash": "ls -la"}.get(tool, "/tmp/probe.txt")
                actual = resolve(agent_rules, tool, probe)
                if actual != expected:
                    bad.append(f"{tool} resolves to {actual!r}, expected {expected!r}")
            if bad:
                report.fail(
                    "S3",
                    f"agent/{AGENT_FILES[name]}: " + "; ".join(bad),
                )
            else:
                report.ok(
                    "S3",
                    f"{name}: "
                    + ", ".join(f"{t}={e}" for t, e in expectations.items() if e),
                )

        # ---- S4: task scoping (reported, not gated) ----
        # `agent/*.md` is frozen this round, so a defect found here must be
        # reported rather than asserted -- otherwise the gate would sit red on
        # arrival with nothing anyone is permitted to fix.
        for name in AGENT_NAMES:
            agent_rules = rules.get(name)
            if not agent_rules:
                continue
            reachable = [
                target
                for target in AGENT_NAMES + ["NotAnAgent"]
                if resolve(agent_rules, "task", target) == "allow"
            ]
            if reachable == AGENT_NAMES + ["NotAnAgent"]:
                report.finding(
                    f"{name}: bare `task: allow` -- reaches every agent including "
                    "names that do not exist. `make check` A1-A6 inspect `bash`, "
                    "`skill`, `write` and permission ordering, but never `task`, so "
                    "this shape is unchecked. It may be intentional; it is not "
                    "documented anywhere. Reported, not gated, because "
                    "agent/*.md is frozen this round."
                )
            elif reachable:
                report.ok("S4", f"{name}: task -> {', '.join(reachable)}")

        # ---- S5: credential paths stay denied, via the agent's OWN rule ----
        #
        # Two properties, and the second is strictly stronger than what this
        # assertion used to check.
        #
        # 1. The HOME-expanded path resolves to `deny`. This is the spelling the
        #    runtime asks about -- see CREDENTIAL_PATHS -- and it is the only
        #    one that can match a credential rule at all.
        #
        # 2. The WINNER is the agent's own named credential pattern, not its
        #    `"*": deny` catch-all. Every agent now declares its own
        #    `external_directory` block (A8), and the whole point of that block
        #    is that the credential paths stop being resolved by a catch-all:
        #    under the old shape the catch-all (rule ~93) denied them, the five
        #    global credential denies at rules 87-91 were shadowed in every case
        #    and contributed nothing, and A4's comment described that as if it
        #    were intended. Checking `!= deny` alone would let a tree go back to
        #    that shape with every assertion in this file still green.
        expanded = [
            str(sandbox.home / path.lstrip("~/"))
            for path in CREDENTIAL_PATHS
        ]
        literal_asks: list[str] = []
        for name in AGENT_NAMES:
            agent_rules = rules.get(name)
            if not agent_rules:
                continue
            leaks = [
                path
                for path in expanded
                if resolve(agent_rules, "external_directory", path) != "deny"
            ]
            catchall = []
            for path in expanded:
                index = last_matching_index(agent_rules, "external_directory", path)
                winner = agent_rules[index] if index >= 0 else {}
                if winner.get("pattern") == "*":
                    catchall.append(path)
            literal_asks.extend(
                path
                for path in CREDENTIAL_PATHS
                if resolve(agent_rules, "external_directory", path) == "ask"
            )
            if leaks or catchall:
                detail = []
                if leaks:
                    detail.append(
                        "not denied: " + ", ".join(repr(p) for p in leaks)
                    )
                if catchall:
                    detail.append(
                        "resolved by the `\"*\"` catch-all rather than a named "
                        "credential rule: " + ", ".join(repr(p) for p in catchall)
                    )
                report.fail("S5", f"{name}: credential path(s) — " + "; ".join(detail))
            else:
                report.ok(
                    "S5",
                    f"{name}: {len(expanded)} credential path(s) denied by the "
                    "agent's own named rule",
                )
        # The literal-tilde spelling resolves to `ask` now, because every agent
        # ends its external_directory block with `"*": ask` and that is the last
        # rule a literal-tilde value can match. That is the deliberate
        # consequence of Change 1 -- ordinary external reads must reach the
        # operator -- and it is reported rather than gated: no probe in this
        # repo hands the runtime a literal-tilde path, so gating it would gate a
        # value the runtime never produces and would go red again the moment
        # anything honest about the expansion were written.
        if literal_asks:
            report.finding(
                f"the literal `~/...` spelling of {len(set(literal_asks))} "
                "credential path(s) now resolves to 'ask' rather than 'deny' for "
                "every agent (reported, not gated: opencode expands `~` in rule "
                "patterns against the process HOME, so the value the runtime "
                "actually asks about is the absolute path that IS gated above). "
                "The enforcement this leaves in place is the OS: filesystem "
                "permissions, a separate uid, or a container -- see SECURITY.md."
            )

        # ---- S6: no dead allows ----
        dead: list[str] = []
        for name in AGENT_NAMES:
            agent_rules = rules.get(name)
            agent_file = sandbox.config / "agent" / AGENT_FILES[name]
            for skill in sorted(documented_skills(agent_file)):
                if skill not in skills:
                    dead.append(f"agent/{AGENT_FILES[name]}: {skill!r} is allowed but "
                                f"no skills/{skill}/SKILL.md exists")
        if dead:
            report.fail("S6", *dead)
        else:
            report.ok(
                "S6",
                f"every documented skill in all {len(AGENT_NAMES)} agents exists on disk",
            )

        check_s7_name_resolution(report, sandbox)
        check_s8_deploy_equivalence(report, sandbox)

        # ---- isolation proof ----
        after = fingerprint(sandbox.real_config)
        before = sandbox._fingerprint_before
        if before == after:
            print(
                f"  ISO    operator config {sandbox.real_config}: "
                f"{len(after)} file(s) unchanged (content hash + mtime)"
            )
        else:
            changed = sorted(set(before) ^ set(after)) + sorted(
                k for k in set(before) & set(after) if before[k] != after[k]
            )
            report.fail(
                "ISO",
                f"the harness modified the operator's live config "
                f"({len(changed)} path(s)): " + ", ".join(changed[:5]),
            )

        # Read-isolation sentinel. A write leaves an mtime; a read leaves
        # nothing. The proof that the live config was not the one consulted is
        # behavioural: the live config is stale and still carries a bare
        # `skill: allow`, so a tier that read it would resolve every skill to
        # allow. It resolves them to deny, so it read the sandbox.
        dispatcher = rules.get("Dispatcher", [])
        sentinel = resolve(dispatcher, "skill", "adr") if dispatcher else None
        if sentinel == "deny":
            print(
                "  ISO    read-isolation sentinel: Dispatcher resolves an "
                "unlisted skill to 'deny' (the live config's bare `skill: allow` "
                "would yield 'allow')"
            )
        else:
            report.fail(
                "ISO",
                f"Dispatcher resolves an unlisted skill to {sentinel!r}; the tier "
                "may be reading the operator's stale live config instead of the "
                "sandbox",
            )

        print()
        return report.emit()
    finally:
        if args.keep:
            print(f"eval-static: sandbox kept at {sandbox.root}")
        else:
            shutil.rmtree(sandbox.root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
