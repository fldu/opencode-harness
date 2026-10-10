#!/usr/bin/env python3
"""Tier 2: behavioural evals. Real model calls, non-deterministic, opt-in only.

This tier is NOT a gate and does not pretend to be one. Every case is a real
model call, so the runner reports a pass RATE over N runs and prints every
individual run's outcome, because a single binary verdict on a non-deterministic
judgement would manufacture confidence that the measurement cannot support.

Three rules keep it from lying:

  1. Three outcomes, never two. PASS / FAIL / ERROR. An ERROR (a run that did
     not reach the state the case is about -- typically no dispatch happened)
     is excluded from the numerator rather than counted as a pass.
  2. A weak signal is never promoted. Cases asserting `text_names` get their own
     outcome bucket and are reported separately from real dispatches.
  3. Opt-in plus cost warning. Nothing runs without EVAL_CONFIRM=1, and the
     estimate is printed before that confirmation is even honoured.

Exit status: 0 only when every case met EVAL_MIN_PASS. Because the tier is
non-deterministic, treat a red run as evidence to investigate, not as a
regression to bisect.

Usage:
  eval_behavior.py [--repo PATH] [--case ID] [--runs N] [--keep]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from harness import (  # noqa: E402
    IsolationError,
    eprint,
    fingerprint,
    make_sandbox,
    opencode_bin,
)

# Measured on this repo with this model: a Dispatcher run costs roughly 19k
# tokens end to end and the provider reports $0 for opencode/space-bunny-free.
# Both are estimates for the pre-flight warning only; the real numbers are
# printed per run from the stream's own step_finish events.
TOKENS_PER_RUN_ESTIMATE = 20_000
COST_USD_PER_RUN_ESTIMATE = 0.0

RUN_TIMEOUT = 420

PASS = "PASS"
FAIL = "FAIL"
ERROR = "ERROR"
WEAK = "WEAK"  # right agent named, nothing actually dispatched


class RunResult:
    def __init__(self, index: int) -> None:
        self.index = index
        self.outcome = ERROR
        self.reasons: list[str] = []
        self.tools: list[str] = []
        self.dispatched: list[str] = []
        self.tokens = 0
        self.cost = 0.0
        self.seconds = 0.0
        self.text = ""

    def line(self, case_id: str) -> str:
        detail = "; ".join(self.reasons) if self.reasons else ""
        return (
            f"    {case_id} run {self.index}: {self.outcome:<5} "
            f"tools=[{','.join(self.tools) or '-'}] "
            f"dispatched=[{','.join(self.dispatched) or '-'}] "
            f"{self.tokens}tok ${self.cost:.4f} {self.seconds:.1f}s"
            + (f" -- {detail}" if detail else "")
        )


def parse_stream(raw: str) -> tuple[list[str], list[str], str, int, float]:
    """Pull tools, dispatched subagents, prose and cost out of --format json.

    The event stream is newline-delimited JSON. `tool_use` carries the tool name
    and its input; a `task` input carries `subagent_type`, which is the only
    non-prose evidence of which agent actually ran.
    """
    tools: list[str] = []
    dispatched: list[str] = []
    texts: list[str] = []
    tokens = 0
    cost = 0.0
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        part = event.get("part") or {}
        if kind == "tool_use":
            tool = part.get("tool")
            if tool:
                tools.append(tool)
            if tool == "task":
                subagent = (part.get("state") or {}).get("input", {}).get(
                    "subagent_type"
                )
                if subagent:
                    dispatched.append(subagent)
        elif kind == "text" and part.get("text"):
            texts.append(part["text"])
        elif kind == "step_finish":
            info = part.get("tokens") or {}
            tokens = max(tokens, info.get("total") or 0)
            cost += part.get("cost") or 0.0
    return tools, dispatched, "\n".join(texts), tokens, cost


def evaluate(case: dict, result: RunResult) -> None:
    """Apply one case's assertion to one run. Sets result.outcome."""
    spec = case.get("assert", {})
    mode = spec.get("mode")
    expected = spec.get("expected_agents", [])

    # Forbidden tools are checked in every mode: an agent reaching for a tool it
    # does not have is a failure regardless of what else it said.
    forbidden = set(spec.get("forbidden_tools", []))
    used_forbidden = [t for t in result.tools if t in forbidden]
    if used_forbidden:
        result.outcome = FAIL
        result.reasons.append(
            f"called forbidden tool(s) {sorted(set(used_forbidden))}"
        )
        return

    # `require_dispatch` means the property under test lives inside the subagent.
    # If no subagent ran, the reply proves nothing about it, and scoring the
    # assertion anyway is the vacuous pass this suite is supposed to be immune
    # to: "Sherlock did not claim to edit" is trivially true when Sherlock was
    # never invoked. Checked here, before the mode dispatch, so it applies to
    # every assertion mode rather than only to dispatch_to.
    if case.get("require_dispatch") and not result.dispatched and mode != "dispatch_to":
        result.outcome = ERROR
        result.reasons.append(
            "no dispatch happened, so the subagent never ran and the assertion "
            "would be vacuous; case inconclusive"
        )
        return

    if mode == "no_forbidden_tool":
        # `task` in `forbidden_tools` already means "must never dispatch"; a
        # case whose only real assertion is text still gets checked here.
        for pattern in spec.get("text_all", []):
            if not re.search(pattern, result.text):
                result.outcome = FAIL
                result.reasons.append(f"reply does not match {pattern!r}")
                return
        for pattern in spec.get("text_none", []):
            if re.search(pattern, result.text):
                result.outcome = FAIL
                result.reasons.append(f"reply matches forbidden {pattern!r}")
                return
        result.outcome = PASS
        result.reasons.append("no forbidden tool; required phrases present")
        return

    if mode == "text_all":
        missing = [p for p in spec.get("text_all", []) if not re.search(p, result.text)]
        bad = [p for p in spec.get("text_none", []) if re.search(p, result.text)]
        if bad:
            result.outcome = FAIL
            result.reasons.append(f"reply matches forbidden {bad[0]!r}")
        elif missing:
            result.outcome = FAIL
            result.reasons.append(f"reply does not match {missing[0]!r}")
        else:
            result.outcome = PASS
            result.reasons.append("asked rather than guessed")
        return

    if mode == "text_none":
        bad = [p for p in spec.get("text_none", []) if re.search(p, result.text)]
        missing = [p for p in spec.get("text_all", []) if not re.search(p, result.text)]
        if bad:
            result.outcome = FAIL
            result.reasons.append(f"reply matches forbidden {bad[0]!r}")
        elif missing:
            result.outcome = FAIL
            result.reasons.append(f"reply does not match {missing[0]!r}")
        else:
            result.outcome = PASS
            result.reasons.append("no overclaim; failure reported")
        return

    if mode == "dispatch_to":
        hit = [d for d in result.dispatched if d in expected]
        if hit:
            result.outcome = PASS
            result.reasons.append(f"dispatched to {hit[0]}")
        elif result.dispatched:
            result.outcome = FAIL
            result.reasons.append(
                f"dispatched to {result.dispatched[0]}, expected one of {expected}"
            )
        elif case.get("require_dispatch"):
            result.outcome = ERROR
            result.reasons.append("no dispatch happened; case inconclusive")
        else:
            result.outcome = WEAK
            result.reasons.append(
                f"named {'/'.join(expected)} in prose but dispatched nothing"
            )
        return

    if mode == "text_names":
        named = [a for a in expected if re.search(rf"\b{a}\b", result.text)]
        hit = [d for d in result.dispatched if d in expected]
        if hit:
            result.outcome = PASS
            result.reasons.append(f"dispatched to {hit[0]}")
        elif named:
            result.outcome = WEAK
            result.reasons.append(
                f"mentions {named[0]} in prose only -- not evidence of routing"
            )
        else:
            result.outcome = FAIL
            result.reasons.append(
                f"never mentioned or dispatched {expected}; this is a real routing miss"
            )
        return

    result.outcome = ERROR
    result.reasons.append(f"unknown assert mode {mode!r}")


def run_case(case: dict, sandbox, runs: int) -> list[RunResult]:
    for spec in case.get("setup", []):
        target = sandbox.repo / spec["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(spec["content"], encoding="utf-8")
        if spec.get("mode"):
            target.chmod(int(spec["mode"], 8))

    cmd_base = [opencode_bin(), "run", "--dir", str(sandbox.repo), "--agent", case["agent"], "--format", "json"]
    if case.get("auto"):
        cmd_base.append("--auto")

    results: list[RunResult] = []
    for index in range(1, runs + 1):
        result = RunResult(index)
        started = time.monotonic()
        try:
            proc = subprocess.run(
                cmd_base + [case["prompt"]],
                capture_output=True,
                text=True,
                timeout=RUN_TIMEOUT,
                cwd=str(sandbox.repo),
                env=sandbox.child_env(),
                stdin=subprocess.DEVNULL,  # never block on a permission prompt
                check=False,
            )
        except subprocess.TimeoutExpired:
            result.outcome = ERROR
            result.reasons.append(f"timed out after {RUN_TIMEOUT}s")
            result.seconds = time.monotonic() - started
            results.append(result)
            print(result.line(case["id"]), flush=True)
            continue
        result.seconds = time.monotonic() - started
        if proc.returncode != 0:
            result.outcome = ERROR
            result.reasons.append(f"opencode exited {proc.returncode}")
            results.append(result)
            print(result.line(case["id"]), flush=True)
            continue
        tools, dispatched, text, tokens, cost = parse_stream(proc.stdout)
        result.tools = tools
        result.dispatched = dispatched
        result.text = text
        result.tokens = tokens
        result.cost = cost
        if not text.strip():
            result.outcome = ERROR
            result.reasons.append("empty reply")
        else:
            evaluate(case, result)
        results.append(result)
        print(result.line(case["id"]), flush=True)
    return results


def git_porcelain(repo: Path) -> set[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    return {line for line in proc.stdout.splitlines() if line.strip()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--case", action="append", help="only these case ids")
    parser.add_argument("--runs", type=int, default=int(os.environ.get("EVAL_RUNS", "3")))
    parser.add_argument("--keep", action="store_true")
    parser.add_argument(
        "--min-pass",
        type=int,
        default=int(os.environ.get("EVAL_MIN_PASS", "100")),
        help="required pass percentage per case (default 100)",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo).resolve()
    cases_path = Path(__file__).resolve().parent / "cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    if args.case:
        wanted = set(args.case)
        cases = [c for c in cases if c["id"] in wanted]
        missing = wanted - {c["id"] for c in cases}
        if missing:
            eprint(f"eval-behavior: unknown case id(s): {', '.join(sorted(missing))}")
            return 2
    if not cases:
        eprint("eval-behavior: no cases selected")
        return 2

    total_runs = args.runs * len(cases)
    print("eval-behavior: tier 2 -- behavioural evals (NON-DETERMINISTIC, opt-in)")
    print()
    print("  ESTIMATED COST -- read this before confirming")
    print(f"    cases            {len(cases)} x {args.runs} run(s) = {total_runs} model calls")
    print(f"    tokens           ~{total_runs * TOKENS_PER_RUN_ESTIMATE:,} "
          f"(~{TOKENS_PER_RUN_ESTIMATE:,}/run, measured)")
    print(f"    provider cost    ~${total_runs * COST_USD_PER_RUN_ESTIMATE:.2f} "
          "for opencode/space-bunny-free, which reports $0 today -- not a guarantee")
    print(f"    wall clock       ~{total_runs * 60 // 60}-{total_runs * 120 // 60} min "
          "(runs are sequential, deliberately: parallel calls would not reduce cost "
          "and would make the rate harder to read)")
    print(f"    required pass    {args.min_pass}% per case")
    print()
    print("  THIS TIER IS NOT A GATE. It reports a pass rate and every individual")
    print("  run so the flake rate is visible. A red run is a signal to read, not a")
    print("  regression to bisect. Do not add it to a required CI check.")
    print()

    if os.environ.get("EVAL_CONFIRM") != "1":
        # stdout is block-buffered when piped while stderr is not, so flush or
        # the cost estimate appears *after* the refusal that cites it.
        sys.stdout.flush()
        eprint("eval-behavior: refusing to run without explicit confirmation.")
        eprint(f"eval-behavior: re-run with EVAL_CONFIRM=1 to spend the "
               f"{total_runs} model call(s) estimated above.")
        return 3

    if not opencode_bin():
        eprint("eval-behavior: FAILED -- opencode is not on PATH.")
        return 1

    try:
        sandbox = make_sandbox(repo_root, keep=args.keep)
    except IsolationError as exc:
        eprint(f"eval-behavior: FAILED -- {exc}")
        return 1

    print(f"  sandbox  {sandbox.root}")
    print(f"  repo     {sandbox.repo}  (disposable copy; the live repo is never cwd)")
    print()

    baseline = fingerprint(sandbox.real_config)
    # Captured immediately after the copy, before any agent runs. The working
    # tree is often already dirty -- an uncommitted edit to agent/*.md or an
    # untracked eval/ would otherwise be reported as damage the agents did, and
    # a non-destructiveness check that cries wolf is a check nobody reads.
    git_baseline = git_porcelain(sandbox.repo)
    planted = {spec["path"] for c in cases for spec in c.get("setup", [])}
    all_results: dict[str, list[RunResult]] = {}
    try:
        for case in cases:
            print(f"  --- {case['id']}: {case['property']}")
            if case.get("note"):
                print(f"      note: {case['note']}")
            all_results[case["id"]] = run_case(case, sandbox, args.runs)
            print()

        # Non-destructiveness: the agents ran with this repo as their cwd, so
        # git is the authority on whether anything moved.
        dirt = git_porcelain(sandbox.repo)
        unexpected = sorted(
            line
            for line in dirt - git_baseline
            if not any(p in line for p in planted)
        )

        print("  === summary ===")
        header = f"  {'case':<26} {'pass':>7} {'rate':>7}  outcomes"
        print(header)
        print("  " + "-" * (len(header) - 2))
        failed_cases: list[str] = []
        grand_pass = grand_total = 0
        for case in cases:
            results = all_results[case["id"]]
            tally = {k: sum(1 for r in results if r.outcome == k)
                     for k in (PASS, FAIL, ERROR, WEAK)}
            # The denominator is EVERY run, including ERROR. An ERROR is a run
            # that failed to demonstrate the property -- a timeout, an empty
            # reply, or a dispatch that never happened -- so it is not evidence
            # of anything and must not quietly vanish from the arithmetic.
            # Reporting pass/(pass+fail) would let a case that passed 1 of 3
            # runs print "100%", which is precisely the manufactured confidence
            # this tier exists to avoid.
            total = len(results)
            rate = (tally[PASS] / total * 100) if total else 0.0
            grand_pass += tally[PASS]
            grand_total += total
            outcome_str = ", ".join(
                f"{k.lower()}={v}" for k, v in tally.items() if v
            )
            print(f"  {case['id']:<26} {tally[PASS]:>3}/{total:<3} "
                  f"{rate:>6.0f}%  {outcome_str}")
            if total and rate < args.min_pass:
                failed_cases.append(case["id"])

        print(f"  {'OVERALL':<26} {grand_pass:>3}/{grand_total:<3} "
              f"{grand_pass / grand_total * 100 if grand_total else 0:>6.0f}%")
        print()
        print("  rate = pass / every run, ERROR and WEAK included in the denominator.")
        print("  ERROR = the run never reached the state the case measures (timeout,")
        print("  empty reply, or no dispatch). It is not a pass and not a failure of")
        print("  the agent -- it is missing evidence, and it counts against the rate.")
        print()
        if unexpected:
            print(f"  DESTRUCTIVE: the evaluated agents modified the sandbox repo "
                  f"({len(unexpected)} path(s) beyond the "
                  f"{len(git_baseline)} already-dirty path(s) at copy time):")
            for line in unexpected[:10]:
                print(f"    {line}")
            failed_cases.append("non-destructive")
        else:
            print(
                f"  non-destructive: sandbox repo unchanged ({len(git_baseline)} "
                "path(s) were already dirty at copy time and none moved)"
            )

        after = fingerprint(sandbox.real_config)
        if baseline == after:
            print(f"  isolation: operator config {sandbox.real_config} unchanged "
                  f"({len(after)} files, content hash + mtime)")
        else:
            print("  isolation: FAILED -- operator's live config changed")
            failed_cases.append("isolation")

        print()
        if failed_cases:
            print(f"eval-behavior: FAILED -- below the {args.min_pass}% bar: "
                  + ", ".join(failed_cases))
            print("eval-behavior: remember this tier is non-deterministic; check "
                  "the per-run outcomes above before treating this as a defect.")
            return 1
        print(f"eval-behavior: OK -- every case met the {args.min_pass}% bar.")
        print("eval-behavior: this is a measurement, not a guarantee. Re-read the "
              "per-run outcomes before trusting it.")
        return 0
    finally:
        if args.keep:
            print(f"eval-behavior: sandbox kept at {sandbox.root}")
        else:
            shutil.rmtree(sandbox.root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
