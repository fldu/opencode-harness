"""Shared plumbing for the opencode-harness eval suite.

Two rules govern everything in this file.

1. ISOLATION BY CONSTRUCTION. Every opencode invocation runs against a
   throwaway HOME under the system temp directory. The operator's live
   ~/.config/opencode is never read and never written: this module snapshots it
   before and after so the caller can prove that rather than assert it.

2. NO NETWORK, NO MODEL, NO SECRET for tier 1. The static tier only shells out
   to `opencode debug agent`, which resolves configuration and prints it. It
   makes no model call, so it is deterministic and free.

Stdlib only. No third-party imports: the Makefile's zero-new-dependency rule
applies here too, and python3 appears only because the task permits it inside
eval scripts invoked from the Makefile -- `make check` never reaches it.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

# The only runtime this suite's V1 assumptions were verified against. See the
# README: the assertions are derived from whatever the binary actually
# resolves, but the *ordering* assumption (last match wins, global before
# agent) was checked by hand on this version only.
VERIFIED_VERSION = "1.18.35"

# V2 renamed the permission actions `bash` -> `shell` and `task` -> `subagent`
# (and merged `write`/`patch` into `edit`). `debug_agent` maps them back so the
# assertions below, which are written against the V1 names, keep their meaning.
V2_ACTION_TO_V1 = {"shell": "bash", "subagent": "task"}

# Agent IDs are the frontmatter `name:`, never the filename. This is the exact
# set `opencode debug agents` must resolve. V2 lowercases them, so
# `debug_agent` matches case-insensitively.
AGENT_NAMES = ["Dispatcher", "Michal", "Sherlock", "Jeff", "Daedalus", "Jozef"]

# Frontmatter name -> file basename. The two are spelled differently on
# purpose (dispatcher.md holds `name: Dispatcher`), which is exactly the trap
# S7 pins down.
AGENT_FILES = {
    "Dispatcher": "dispatcher.md",
    "Michal": "michal.md",
    "Sherlock": "sherlock.md",
    "Jeff": "jeff.md",
    "Daedalus": "daedalus.md",
    "Jozef": "jozef.md",
}

# A bash allowlist that resolves nothing would make every "resolves to allow"
# assertion vacuously true. Floor guards against a config that parses to zero.
MIN_RESOLVED_RULES = 40
MIN_INSTALLED_SKILLS = 20

# V2's background service answers `debug agents` with an empty list until it has
# finished booting a cold sandbox. Retry a bounded number of times before
# calling an agent unresolvable.
SERVICE_BOOT_ATTEMPTS = 6
SERVICE_BOOT_RETRY_SECONDS = 2.0


# --------------------------------------------------------------------------
# Wildcard matching
# --------------------------------------------------------------------------
# Mirrors opencode's `Wildcard.match(value, rulePattern)`: the value under test
# is matched against the rule's pattern, `*` is "any run of characters",
# `?` is "any single character", and the match is whole-string. Only the
# argument order matters for correctness here and it is deliberately the
# reversed-looking one -- see resolve().
#
# This is NOT a general glob implementation. It is the subset the config in
# this repo actually uses (`*` and `**`, never `[]` or `{}`). A pattern using
# an unmodelled metacharacter is escaped and therefore matched literally,
# which fails closed: it cannot invent an allow that the runtime would not
# also produce for these shapes.
_regex_cache: dict[str, re.Pattern[str]] = {}


def _to_regex(pattern: str) -> re.Pattern[str]:
    cached = _regex_cache.get(pattern)
    if cached is None:
        out = []
        for ch in pattern:
            if ch == "*":
                out.append(".*")
            elif ch == "?":
                out.append(".")
            else:
                out.append(re.escape(ch))
        cached = re.compile("^" + "".join(out) + "$", re.DOTALL)
        _regex_cache[pattern] = cached
    return cached


def wildcard_match(value: str, pattern: str) -> bool:
    return _to_regex(pattern).match(value) is not None


def resolve(rules: list[dict], permission: str, value: str) -> str | None:
    """Resolve one tool call the way V1 does.

    The runtime matcher is
    `rules.flat().findLast(z => Wildcard.match(permission, z.permission)
                             && Wildcard.match(pattern, z.pattern))`
    -- one flat array, LAST match wins, and the value under test is the first
    argument to Wildcard.match in both positions. This is a literal
    transcription, not an approximation.

    Returns the winning action, or None when no rule matches.
    """
    for rule in reversed(rules):
        rule_permission = rule.get("permission", "*")
        rule_pattern = rule.get("pattern", "*")
        if wildcard_match(permission, rule_permission) and wildcard_match(
            value, rule_pattern
        ):
            return rule.get("action")
    return None


def last_matching_index(rules: list[dict], permission: str, value: str) -> int:
    """Index of the winning rule, for assertions about ordering."""
    for index in range(len(rules) - 1, -1, -1):
        rule = rules[index]
        if wildcard_match(permission, rule.get("permission", "*")) and wildcard_match(
            value, rule.get("pattern", "*")
        ):
            return index
    return -1


# --------------------------------------------------------------------------
# Sandbox
# --------------------------------------------------------------------------


class IsolationError(RuntimeError):
    """Raised when the sandbox cannot be shown to be safe. Never worked around."""


@dataclass
class Sandbox:
    root: Path
    home: Path
    config: Path
    repo: Path
    real_home: Path
    real_config: Path
    _fingerprint_before: dict[str, tuple] = field(default_factory=dict)

    def child_env(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """Environment for every opencode child process.

        HOME points into the sandbox and so do all four XDG roots, so no
        lookup can escape to the operator's real profile. OPENCODE and
        OPENCODE_PID are dropped: they mark a nested opencode process and
        letting them through is how a child could reattach to its parent
        instead of resolving its own config.

        Everything else is inherited deliberately. The model provider may need
        an environment entry to authenticate, and stripping it would make the
        behavioral tier fail for a reason that has nothing to do with the agent
        under test. Nothing from this dict is ever printed -- it is passed to
        execve, not to a log line.
        """
        env = dict(os.environ)
        env.pop("OPENCODE", None)
        env.pop("OPENCODE_PID", None)
        env["HOME"] = str(self.home)
        env["XDG_CONFIG_HOME"] = str(self.home / ".config")
        env["XDG_DATA_HOME"] = str(self.home / ".local" / "share")
        env["XDG_STATE_HOME"] = str(self.home / ".local" / "state")
        env["XDG_CACHE_HOME"] = str(self.home / ".cache")
        env["TMPDIR"] = str(self.root / "tmp")
        # Pinned so output ordering and any date rendering inside the agent are
        # reproducible between runs and between machines.
        env["LANG"] = "C.UTF-8"
        env["LC_ALL"] = "C.UTF-8"
        env["TZ"] = "UTC"
        env["SHELL"] = "/bin/zsh"
        if extra:
            env.update(extra)
        return env


def fingerprint(path: Path) -> dict[str, tuple]:
    """Content + mtime of every file under `path`.

    Used to prove the operator's real config dir was not written to. A read
    does not change mtime, so this is a write-proof, not a read-proof; the
    read side is covered by the sentinel in the static tier plus the child
    environment, which the README states plainly rather than overclaiming.
    """
    out: dict[str, tuple] = {}
    if not path.exists():
        return out
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames.sort()
        for name in sorted(filenames):
            full = Path(dirpath) / name
            try:
                rel = str(full.relative_to(path))
                stat = full.stat()
                digest = hashlib.sha256(full.read_bytes()).hexdigest()[:16]
                out[rel] = (stat.st_size, stat.st_mtime_ns, digest)
            except OSError as exc:  # unreadable entry: record, do not crash
                out[rel] = (-1, -1, f"unreadable:{exc.errno}")
    return out


def _guard(sandbox_root: Path, real_home: Path) -> None:
    """Refuse to build a sandbox that could touch the operator's environment."""
    resolved = sandbox_root.resolve()
    real_home = real_home.resolve()
    tmp = Path(tempfile.gettempdir()).resolve()

    if resolved == real_home or real_home.is_relative_to(resolved):
        raise IsolationError(
            f"sandbox {resolved} contains the operator's HOME {real_home}; refusing"
        )
    if not resolved.is_relative_to(tmp):
        raise IsolationError(
            f"sandbox {resolved} is not under the temp dir {tmp}; refusing to "
            "build a sandbox outside /tmp"
        )
    if str(resolved) == str(tmp):
        raise IsolationError(f"sandbox must not be the temp dir itself ({tmp})")


def _pin_service_port(config: Path) -> int:
    """Give the sandbox's background service a port nothing else is using.

    Binds port 0 to let the kernel pick, reads the port back, closes it, and
    writes it to the sandbox's own `service.json`. The window between closing
    the probe socket and the child binding it is a TOCTOU race in principle; it
    is not a security boundary here because the port only decides which
    loopback socket the disposable child listens on, and a lost race would fail
    the run loudly with an "address already in use" rather than pass quietly.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    (config / "service.json").write_text(
        json.dumps({"port": port}), encoding="utf-8"
    )
    return port


def make_sandbox(repo_root: Path, keep: bool = False) -> Sandbox:
    """Build an isolated HOME plus a disposable copy of the repository.

    The repo is copied whole, .git included, so `git status` inside the copy
    can prove the evaluated agents changed nothing. The live repo is never a
    working directory for an evaluated agent.
    """
    repo_root = Path(repo_root).resolve()
    real_home = Path(os.path.expanduser("~")).resolve()
    real_config = real_home / ".config" / "opencode"

    root = Path(tempfile.mkdtemp(prefix="opencode-eval."))
    _guard(root, real_home)

    home = root / "home"
    config = home / ".config" / "opencode"
    repo = root / "repo"
    (root / "tmp").mkdir(parents=True, exist_ok=True)
    config.mkdir(parents=True, exist_ok=True)
    home.mkdir(parents=True, exist_ok=True)

    shutil.copytree(repo_root, repo, symlinks=True)

    # Mirror of the Makefile's COPY_CMDS, byte for byte in effect:
    #   agent/*.md -> agent/,  skills/. -> skills/,  opencode.json -> .
    (config / "agent").mkdir(parents=True, exist_ok=True)
    for md in sorted((repo_root / "agent").glob("*.md")):
        shutil.copy2(md, config / "agent" / md.name)
    shutil.copytree(repo_root / "skills", config / "skills", symlinks=True)
    shutil.copy2(repo_root / "opencode.json", config / "opencode.json")

    # V2 runs a background service, and a sandboxed child defaults to the same
    # port the operator's own service already holds. The child then fails to
    # start and every assertion reports an opencode crash instead of a
    # permission result. Pin a free port in the sandbox's own config so the two
    # never collide.
    #
    # This is written directly rather than via `opencode service set port`,
    # which restarts the service -- and that would take out the operator's own
    # session, including the one running this suite.
    _pin_service_port(config)

    sandbox = Sandbox(
        root=root,
        home=home,
        config=config,
        repo=repo,
        real_home=real_home,
        real_config=real_config,
    )
    sandbox._fingerprint_before = fingerprint(real_config)
    if not keep:
        # Registered for cleanup on normal exit; the caller may still inspect
        # the tree while the process is alive if it asked to keep it.
        import atexit

        atexit.register(shutil.rmtree, root, ignore_errors=True)
    return sandbox


def installed_skills(sandbox: Sandbox) -> list[str]:
    """Skill directories that really carry a SKILL.md.

    opencode scans `{skill,skills}/**/SKILL.md`, so a directory without one is
    not a loadable skill and must not count as one in a scope assertion.
    """
    skills_root = sandbox.config / "skills"
    if not skills_root.is_dir():
        return []
    return sorted(
        d.name
        for d in skills_root.iterdir()
        if d.is_dir() and (d / "SKILL.md").is_file()
    )


# --------------------------------------------------------------------------
# opencode invocation
# --------------------------------------------------------------------------


def opencode_bin() -> str:
    return os.environ.get("EVAL_OPENCODE_BIN") or shutil.which("opencode") or ""


def opencode_version(binary: str) -> str:
    try:
        proc = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return (proc.stdout or proc.stderr).strip().splitlines()[0] if (
        proc.stdout or proc.stderr
    ) else "unknown"


def debug_agents(sandbox: Sandbox) -> list[dict]:
    """Every agent the runtime resolves, retried until the list is non-empty.

    V2's first `debug agents` against a cold sandbox returns an empty array
    while the background service is still booting, and the second returns the
    full set. Reading that first empty array as "these agents do not exist"
    turns a startup race into a red tier, so retry until the service answers.

    Bounded by SERVICE_BOOT_ATTEMPTS rather than retried forever: an agent that
    genuinely fails to load must surface as a failure, not hang the suite.
    """
    binary = opencode_bin()
    if not binary:
        raise IsolationError(
            "opencode is not on PATH. Set EVAL_OPENCODE_BIN to run the static tier."
        )
    last_error = "no output"
    for attempt in range(SERVICE_BOOT_ATTEMPTS):
        proc = subprocess.run(
            [binary, "debug", "agents"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(sandbox.repo),
            env=sandbox.child_env(),
            check=False,
        )
        if proc.returncode != 0:
            last_error = f"exited {proc.returncode}: {proc.stderr.strip()[:400]}"
        else:
            try:
                agents = json.loads(proc.stdout)
            except json.JSONDecodeError as exc:
                last_error = f"invalid JSON: {exc}"
            else:
                if agents:
                    return agents
                last_error = "returned an empty agent list (service still starting)"
        if attempt + 1 < SERVICE_BOOT_ATTEMPTS:
            time.sleep(SERVICE_BOOT_RETRY_SECONDS)
    raise RuntimeError(f"`opencode debug agents` {last_error}")


def debug_agent(sandbox: Sandbox, name: str) -> list[dict]:
    """The fully resolved rule array for one agent.

    `opencode debug agents` is the only supported way to see what the runtime
    actually merged: global config rules first, then the agent's frontmatter,
    last match wins. Asserting on the source files instead would be asserting
    on our intent rather than on the runtime's behaviour, which is the whole
    point of this tier.

    V1 exposed `opencode debug agent <Name>` returning `{permission: [...]}`
    with `bash`/`task` action names. V2 removed that subcommand in favour of
    `debug agents`, which lists every agent as `{id, permissions: [...]}` with
    `{action, resource, effect}` rules and `shell`/`subagent` action names.

    The resolved rules are normalised back into the V1
    `{permission, pattern, action}` shape here, so `resolve()` and
    `last_matching_index()` — and every assertion built on them — keep their
    existing contract. `shell` maps back to `bash` and `subagent` back to
    `task`, which is exactly the mapping the V2 migration guide documents.

    cwd is the disposable repo copy so the run sees exactly the tree the
    behavioral tier will see, project config included.
    """
    agents = debug_agents(sandbox)

    # Agent IDs are the lowercased frontmatter name, so the frontmatter
    # spelling (`Sherlock`) never matches an id (`sherlock`) literally.
    wanted = name.strip().lower()
    entry = next(
        (a for a in agents if str(a.get("id", "")).lower() == wanted), None
    )
    if entry is None:
        raise RuntimeError(
            f"`opencode debug agents` has no agent named {name!r}; "
            "refusing to assert against an empty rule set"
        )

    rules = entry.get("permissions")
    if not isinstance(rules, list) or not rules:
        raise RuntimeError(
            f"agent {name!r} resolved to no permission array; "
            "refusing to assert against an empty rule set"
        )
    return [
        {
            "permission": V2_ACTION_TO_V1.get(rule.get("action", ""), rule.get("action", "")),
            "pattern": rule.get("resource", "*"),
            "action": rule.get("effect", ""),
        }
        for rule in rules
    ]


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


class Report:
    """Collects pass/fail results and renders them deterministically.

    Findings are separate from failures on purpose: a finding is a true
    observation about the harness that a human should look at, and folding it
    into the exit code would either hide a real defect behind an unfixable
    gate or redden the suite on a frozen input.
    """

    def __init__(self, title: str) -> None:
        self.title = title
        self.passed: list[str] = []
        self.failed: list[tuple[str, list[str]]] = []
        self.findings: list[str] = []
        self.warnings: list[str] = []

    def ok(self, check_id: str, detail: str = "") -> None:
        self.passed.append(f"{check_id}{': ' + detail if detail else ''}")

    def fail(self, check_id: str, *detail: str) -> None:
        self.failed.append((check_id, list(detail)))

    def finding(self, text: str) -> None:
        self.findings.append(text)

    def warn(self, text: str) -> None:
        self.warnings.append(text)

    def emit(self) -> int:
        width = max((len(c) for c in self.passed), default=0)
        for line in self.passed:
            print(f"  PASS  {line:<{width}}")
        for check_id, detail in self.failed:
            print(f"  FAIL  {check_id}")
            for line in detail:
                print(f"        {line}")
        for text in self.findings:
            print(f"  NOTE  {text}")
        for text in self.warnings:
            print(f"  WARN  {text}")
        print()
        total = len(self.passed) + len(self.failed)
        if self.failed:
            print(
                f"{self.title}: FAILED -- {len(self.failed)} of {total} "
                f"assertion(s) failed"
            )
            return 1
        print(f"{self.title}: OK -- {total} assertion(s) passed")
        return 0


def rel(path: Path, root: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(Path(root).resolve()))
    except ValueError:
        return str(path)


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)
