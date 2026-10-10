#!/usr/bin/env python3
"""Prove the static tier can fail. A gate that has never gone red is decoration.

Seven defects are seeded into a scratch COPY of the repository -- never the
working tree -- and the tier that owns each one must catch it. Three go through
eval-static, which prints the tier's own output so the failure message is the
evidence, not this script's summary of it. The last four go through `make
check`, because A7 (the assertion that owns `task` scoping), A8 (the
`external_directory` credential block) and A9 (the `read` `.env` block) live
there and not in this tier; see CHECK_MUTATIONS for why that is not a
workaround.

  M1  drop one bash deny from agent/sherlock.md
      The removed pattern's command then falls through to the agent's own
      `"*": allow`, because agent rules are appended after the global ones. Both
      `make check` and eval-static go red; eval-static additionally names the
      file and the command that resolved to allow.

  M2  add a skill to agent/michal.md's `skill:` block that its table does not list
      eval-static resolves every installed skill and reports the undocumented
      capability. `make check`'s A6 catches the same drift by diffing text; this
      is the resolution-level view of the same fact.

  M3  append a shadowing allow for one denied pattern, in opencode.json AND in
      all three mirroring agents
      This is the one that matters. The deny-lists stay byte-identical and stay
      at 19 entries, so A1, A2, A3 and A4 all stay green and `make check` passes
      on a config where `terraform destroy` resolves to allow -- because the
      appended allow sits AFTER the deny and V1 takes the last match. Only the
      resolved-array assertion catches it. If this case ever stops failing, the
      tier has been weakened into decoration.

  M4  replace agent/michal.md's `task:` block with a bare `task: allow`
      The defect A7 exists for. A bare scalar becomes one wildcard rule appended
      after the global ones, so it reaches every agent -- Dispatcher included.
      A1-A6 inspect `bash`, `skill`, `write` and ordering and never `task`,
      which is why this shape survived in two agents for as long as it did.

  M5  misspell the Sherlock task allow in agent/michal.md as `sherlock`
      The silent half of the same defect. Agent IDs are the frontmatter `name:`
      and are case-sensitive, so this rule can never match anything: the agent
      becomes undispatchable to Sherlock, and every human-facing surface -- the
      frontmatter, the "Tool Constraints" prose, the table of agents -- still
      reads as if it were reachable. Nothing reports an error anywhere.

  M6  drop the `~/.aws/**` deny from agent/sherlock.md's external_directory block
      The defect A8 exists for. The other four credential denies stay, so the
      block still *looks* like a credential deny-list, but `~/.aws/**` now falls
      through to the agent's own `"*": ask` wildcard and the operator gets a
      clickable prompt on an AWS credentials file instead of a hard block.

  M7  move the `*.env.example` allow above `*.env.*: deny` in agent/jeff.md's
      read block
      The defect A9 exists for, and the half that is invisible in review.
      `*.env.*` matches `.env.example`, so under last-match-wins the deny wins
      and the allow becomes an inert rule. The `.env` denies are both still
      present and still correctly ordered relative to the wildcard, so a check
      that only looked for the two `*.env` rules would call this tree clean.

Exit 0 only if all seven were caught.

Usage:  eval_selftest.py [--repo PATH]
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static" / "eval_static.py"

# M1: a deny whose removal flips a genuinely destructive command to allow.
DROP_LINE = '    "terraform destroy*": deny\n'

# M3: rather than flipping the deny (which also removes it from the list and so
# trips `check`'s MIN_DENY floor), APPEND a second entry for the same pattern.
# Both deny-lists stay identical and stay at 19, so every text-level assertion
# in `check` stays green while the runtime resolves the command to allow.
#
# The new line goes immediately after the terraform-destroy deny, never after
# the last entry of the block: a trailing comma on the final line makes the
# agent frontmatter unparseable and also defeats `check`'s shape-driven
# extractor, which compares the action token literally and would read `deny,` as
# something other than `deny`. That is a limitation of a text parser, not a
# property worth demonstrating here.
#
# The shadow pattern is `terraform*`, NOT a second `terraform destroy*`. A
# duplicate key in one YAML mapping makes the whole frontmatter fail to parse,
# which would take every agent offline and prove nothing about resolution. A
# broad pattern placed after the denies is the realistic form of this defect
# anyway: someone widens an allowlist without noticing they put it downstream.
ANCHOR = {
    "opencode.json": '      "terraform destroy*": "deny",\n',
    "agent/jeff.md": '    "terraform destroy*": deny\n',
    "agent/jozef.md": '    "terraform destroy*": deny\n',
    "agent/sherlock.md": '    "terraform destroy*": deny\n',
}
SHADOW = {
    "opencode.json": '      "terraform*": "allow",\n',
    "agent/jeff.md": '    "terraform*": allow\n',
    "agent/jozef.md": '    "terraform*": allow\n',
    "agent/sherlock.md": '    "terraform*": allow\n',
}


def drop_sherlock_deny(repo: Path) -> None:
    target = repo / "agent" / "sherlock.md"
    text = target.read_text(encoding="utf-8")
    if DROP_LINE not in text:
        raise SystemExit("M1: expected deny line not found in agent/sherlock.md")
    target.write_text(text.replace(DROP_LINE, "", 1), encoding="utf-8")


def add_michal_skill(repo: Path) -> None:
    target = repo / "agent" / "michal.md"
    text = target.read_text(encoding="utf-8")
    anchor = '    "escalation-rules": allow\n'
    if anchor not in text:
        raise SystemExit("M2: expected skill anchor not found in agent/michal.md")
    target.write_text(text.replace(anchor, anchor + '    "adr": allow\n', 1), encoding="utf-8")


def shadow_deny_with_allow(repo: Path) -> None:
    """Insert `terraform destroy*: allow` directly after its deny, in all four.

    The deny-lists that A3 diffs are untouched -- the new line is an allow, and
    both A3 and its extraction only ever look at entries whose action is deny --
    so A1, A2, A3 and A4 all stay green. Under last-match-wins the inserted
    allow is the winner.
    """
    for rel, anchor in ANCHOR.items():
        path = repo / rel
        text = path.read_text(encoding="utf-8")
        if anchor not in text:
            raise SystemExit(f"M3: anchor {anchor!r} not found in {rel}")
        path.write_text(text.replace(anchor, anchor + SHADOW[rel], 1), encoding="utf-8")


# M4: the block A7 replaced. Matched whole, INCLUDING the opening `task: {` and
# the closing `  }`, so the replacement cannot leave a half-block behind -- a
# partial edit would still be a defect, just a different one, and the seed would
# stop testing what it claims to test. The block-mapping spelling this used to
# match no longer exists anywhere in agent/: all six agents now write `task:` as
# a flow mapping, so matching the old spelling would make this seed raise
# SystemExit on a clean tree rather than on a defective one.
MICHAL_TASK_BLOCK = (
    '  task: {\n'
    '    "*": deny,\n'
    '    "Sherlock": allow,\n'
    '    "Daedalus": allow,\n'
    '  }\n'
)
BARE_TASK = "  task: allow\n"


def bare_task_allow(repo: Path) -> None:
    """Put agent/michal.md's `task:` block back to the bare scalar it used to be."""
    target = repo / "agent" / "michal.md"
    text = target.read_text(encoding="utf-8")
    if MICHAL_TASK_BLOCK not in text:
        raise SystemExit("M4: expected michal.md task block not found")
    target.write_text(text.replace(MICHAL_TASK_BLOCK, BARE_TASK, 1), encoding="utf-8")


def wrong_case_task_name(repo: Path) -> None:
    """Lowercase the Sherlock task allow, so the rule can never match anything."""
    target = repo / "agent" / "michal.md"
    text = target.read_text(encoding="utf-8")
    anchor = '    "Sherlock": allow,\n'
    if anchor not in text:
        raise SystemExit("M5: expected Sherlock allow not found in agent/michal.md")
    target.write_text(text.replace(anchor, '    "sherlock": allow,\n', 1), encoding="utf-8")


# M6: remove one credential deny from an agent's own external_directory block.
# The agent keeps its `"*": ask` wildcard, so the path stops resolving to deny
# and starts resolving to ask -- a prompt on ~/.aws/** rather than a block. The
# line is removed whole, exactly as M1 removes a bash deny, because a leftover
# trailing comma would make the frontmatter unparseable and would then prove
# something about YAML rather than about A8.
M6_DENY_LINE = '    "~/.aws/**": deny,\n'


def drop_credential_deny(repo: Path) -> None:
    target = repo / "agent" / "sherlock.md"
    text = target.read_text(encoding="utf-8")
    if M6_DENY_LINE not in text:
        raise SystemExit("M6: expected ~/.aws/** deny not found in agent/sherlock.md")
    target.write_text(text.replace(M6_DENY_LINE, "", 1), encoding="utf-8")


# M7: swap two adjacent lines inside jeff.md's read block so the template allow
# precedes the `*.env.*` deny it is shadowed by. Both rules stay present and the
# wildcard stays first, so this is invisible to any check that only looks for the
# presence of the two `.env` denies.
M7_BEFORE = '    "*.env.*": deny,\n    "*.env.example": allow,\n'
M7_AFTER = '    "*.env.example": allow,\n    "*.env.*": deny,\n'


def invert_env_template_order(repo: Path) -> None:
    target = repo / "agent" / "jeff.md"
    text = target.read_text(encoding="utf-8")
    if M7_BEFORE not in text:
        raise SystemExit("M7: expected *.env.* deny / *.env.example allow pair not found")
    target.write_text(text.replace(M7_BEFORE, M7_AFTER, 1), encoding="utf-8")


# Each mutation: (id, description, apply_fn, substrings the tier must print)
MUTATIONS = [
    (
        "M1",
        "remove one bash deny from agent/sherlock.md",
        "drop_sherlock_deny",
        ["agent/sherlock.md", "terraform destroy"],
    ),
    (
        "M2",
        "add an unlisted skill to agent/michal.md's skill block",
        "add_michal_skill",
        ["Michal", "adr"],
    ),
    (
        "M3",
        "insert a broad 'terraform*' allow after the terraform denies in "
        "opencode.json and all three mirroring agents",
        "shadow_deny_with_allow",
        ["terraform destroy", "terraform apply"],
    ),
]

# A7, A8 and A9 are `make check` assertions, so their seeds are driven through
# `make check`. This is not a demotion. The static tier's S4 was written while
# agent/*.md was frozen and deliberately reports task scoping WITHOUT gating it
# -- `report.finding` and `report.ok` never set an exit code -- so a seeded task
# defect leaves eval-static at exit 0 by design, and seeding it there would
# produce a selftest that is red on arrival for the wrong reason. The same holds
# for the block SHAPES A8 and A9 assert: they are text properties of one file,
# which is `check`'s whole remit; what the static tier adds is the resolved-array
# view of the same rules (S5), not a second opinion on their spelling. The gate
# has to be shown capable of going red by the thing that actually asserts it, and
# the M3 cross-check below already calls run_check() for exactly this reason.
CHECK_MUTATIONS = [
    (
        "M4",
        "replace agent/michal.md's task block with a bare `task: allow`",
        "bare_task_allow",
        ["agent/michal.md", "bare-scalar"],
    ),
    (
        "M5",
        "misspell the Sherlock task allow as `sherlock` in agent/michal.md",
        "wrong_case_task_name",
        ["agent/michal.md", "sherlock"],
    ),
    (
        "M6",
        "drop the `~/.aws/**` credential deny from agent/sherlock.md's "
        "external_directory block",
        "drop_credential_deny",
        ["agent/sherlock.md", "~/.aws/**"],
    ),
    (
        "M7",
        "move the `*.env.example` allow above `*.env.*: deny` in agent/jeff.md's "
        "read block",
        "invert_env_template_order",
        ["agent/jeff.md", "*.env.example", "*.env.*"],
    ),
]


def run_static(repo: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(STATIC), "--repo", str(repo)],
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    return proc.returncode, proc.stdout + proc.stderr


def run_check(repo: Path) -> tuple[int, str]:
    proc = subprocess.run(
        ["make", "-C", str(repo), "check"],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    return proc.returncode, proc.stdout + proc.stderr


def run_check_seeds(source: Path) -> list[str]:
    """Seed each CHECK_MUTATIONS defect and require `make check` to catch it.

    Same shape as the MUTATIONS loop above -- scratch copy, never the working
    tree -- with one difference: the verdict is printed only if the gate went
    red, and a non-zero exit with no FAIL line is reported as the gate itself
    breaking rather than as a silent miss. `check` prints its failures to stderr,
    so the FAIL lines and the indented detail beneath them are what is kept.
    """
    failures: list[str] = []
    for mut_id, description, apply_name, expected in CHECK_MUTATIONS:
        scratch = Path(tempfile.mkdtemp(prefix="opencode-eval-selftest."))
        repo = scratch / "repo"
        shutil.copytree(source, repo, symlinks=True)
        try:
            globals()[apply_name](repo)
            code, output = run_check(repo)

            print("=" * 72)
            print(f"{mut_id}: {description}   [`make check`]")
            print("-" * 72)
            kept = [
                line.strip()
                for line in output.splitlines()
                if line.strip().startswith("FAIL") or line.startswith("      ")
            ]
            if code != 0 and not any("FAIL " in line for line in kept):
                kept = ["<no assertion failure printed; tail of output>"] + output.splitlines()[-25:]
            for line in kept:
                print(f"  {line}")
            print(f"  -> `make check` exit code: {code}")

            if code == 0:
                failures.append(f"{mut_id} was NOT caught by `make check` (exit 0)")
                print(f"  VERDICT: NOT CAUGHT -- {mut_id} passed. A7 is decoration.")
            else:
                missing = [e for e in expected if e not in output]
                if missing:
                    failures.append(f"{mut_id} failed but the message did not name {missing}")
                    print(f"  VERDICT: failed, but the message did not name {missing}")
                else:
                    print(f"  VERDICT: caught, and the message names {expected}")
            print()
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[2]))
    args = parser.parse_args()
    source = Path(args.repo).resolve()

    print("eval-selftest: the static tier must FAIL on every seeded defect")
    print("               and `make check` must FAIL on every A7/A8/A9 seed")
    print(f"  source repo (read-only)  {source}")
    print()

    failures: list[str] = []
    for mut_id, description, apply_name, expected in MUTATIONS:
        scratch = Path(tempfile.mkdtemp(prefix="opencode-eval-selftest."))
        # A full copy including .git: the eval under test copies the repo itself,
        # and a half-copy would not exercise the same path the real target uses.
        repo = scratch / "repo"
        shutil.copytree(source, repo, symlinks=True)
        try:
            globals()[apply_name](repo)
            code, output = run_static(repo)

            print("=" * 72)
            print(f"{mut_id}: {description}")
            print("-" * 72)
            kept = [
                line for line in output.splitlines()
                if line.strip().startswith(("FAIL", "eval-static:", "NOTE", "WARN"))
                or line.strip().startswith("agent/")
                or "resolves to" in line
                # The 8-space indent is eval_static's detail indent, so these
                # are the lines explaining a FAIL. Dropping them would report
                # "caught" without ever showing what it said.
                or line.startswith("        ")
            ]
            if code != 0 and not any("FAIL " in line for line in kept):
                # A non-zero exit with no assertion failure means the tier itself
                # broke. Show the tail rather than a filtered view that would
                # hide the traceback and make this look like a silent miss.
                kept = [f"<no assertion failure printed; tail of output>"] + output.splitlines()[-25:]
            for line in kept:
                print(f"  {line.strip()}")
            print(f"  -> eval-static exit code: {code}")

            if code == 0:
                failures.append(f"{mut_id} was NOT caught (exit 0)")
                print(f"  VERDICT: NOT CAUGHT -- {mut_id} passed. The tier is decoration.")
            else:
                missing = [e for e in expected if e not in output]
                if missing:
                    failures.append(f"{mut_id} failed but did not name {missing}")
                    print(f"  VERDICT: failed, but the message did not name {missing}")
                else:
                    print(f"  VERDICT: caught, and the message names {expected}")
            print()
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    # A7/A8/A9 seeds run against `make check`, because that is where they live.
    failures.extend(run_check_seeds(source))

    # M3 is the load-bearing one: `make check` is expected to stay GREEN, which
    # is the whole argument for having a second tier at all.
    scratch = Path(tempfile.mkdtemp(prefix="opencode-eval-selftest."))
    repo = scratch / "repo"
    shutil.copytree(source, repo, symlinks=True)
    try:
        shadow_deny_with_allow(repo)
        code, _ = run_check(repo)
        print("=" * 72)
        print("M3 cross-check: does `make check` notice the same defect?")
        print("-" * 72)
        print(f"  `make check` exit code on the M3 tree: {code}")
        if code == 0:
            print("  GREEN, as expected. check diffs the four deny-lists against")
            print("  each other and only ever looks at entries whose action is")
            print("  deny, so an appended allow leaves all six assertions true.")
            print("  The command now resolves to 'allow' at runtime, and only the")
            print("  resolved-array assertion can see that.")
        else:
            failures.append(
                "M3 was also caught by `make check`, so the cross-check no longer "
                "demonstrates anything the static tier adds"
            )
            print("  UNEXPECTED: check rejected this tree too. The cross-check was")
            print("  meant to show a defect check cannot see; it no longer does.")
        print()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    if failures:
        print(f"eval-selftest: FAILED -- {len(failures)} problem(s):")
        for line in failures:
            print(f"  - {line}")
        return 1
    print("eval-selftest: OK -- all seeded defects were caught and named.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
