# SECURITY.md — known limitations of the opencode agent harness

This file records **measured** behaviour of this harness on OpenCode **V1
1.18.35**, including one limitation that is **accepted rather than fixed**. It is
not a claim that the harness is secure. It is a record of what was tested, what
was observed, and what was deliberately left alone so the next reader does not
have to rediscover it — or, worse, cite a "clean run" that was never an
enforcement.

Everything below was observed on Linux with `opencode/space-bunny-free`. The V1
permission model was not re-verified on any other version; see
[Scope](#scope-what-this-file-does-not-cover).

---

## What the configuration *does* enforce

`make check` compares **text**; `make eval-static` asks the runtime **what it
resolved**. The third column is deliberately not uniform — two of these rows are
gated at both levels and two are gated at the text level only, and saying
otherwise would be the exact kind of overclaim this file exists to avoid.

| Property | Text gate | Resolved-level gate |
|---|---|---|
| Each agent's `bash` deny-list is byte-identical to `opencode.json` and in the same order | `check` A1–A3 | `eval-static` **S2** — 15 dangerous commands resolve to `deny` |
| `task` is scoped to named agents; an unknown or miscased name is an inert rule | `check` A7 | `eval-static` **S4** reports it and sets no exit code; `check` A7 is the only gate |
| Credential paths (`~/.ssh`, `~/.aws`, `~/.config/gcloud`, `~/.kube`, `~/.gnupg`) resolve to `deny` **through the agent's own named rule**, not through the `"*": deny` catch-all | `check` A8 | `eval-static` **S5** — gated, and it asserts the *winner is a named rule* |
| Ordinary source files resolve to `read: allow` | `check` A9 | `eval-static` **S3** — probes `/tmp/probe.txt` |
| `read` of `*.env` resolves to `deny` via a named rule, and `.env.example` resolves to `allow` | `check` A9 | **not gated.** S3 probes one ordinary path only. Verified by hand on 1.18.35 (resolved rule index 95 `read/*.env/deny`, 97 `read/*.env.example/allow`, against the `"*"` wildcard at 94); no committed assertion re-checks it |
| Ordinary external paths (sibling repos, `/etc`, `$HOME` outside the project) resolve to **`ask`** | `check` A8 | **not gated.** S5 probes the credential paths only. Verified by hand on 1.18.35 (winner `external_directory/*/ask` at index 121 for Dispatcher); no committed assertion re-checks it |

Note what is *not* in that table: **no row about `bash` and credentials.** The
next section is that row.

The two "not gated" rows are the honest gap in this change. Adding `.env` and
`/etc` probes to `eval_static.py` would close it; that file was out of scope
here, so it is a named follow-up rather than something smuggled in.

---

## ACCEPTED: `bash` can read credential files regardless of `external_directory`

**Status: accepted by decision, not fixed. Not fixable at config level in V1.**

### What happens

An agent that holds `bash: allow` can read a credential file through `bash`.
`external_directory` does not mediate it.

### Measured facts, and how they were measured

**Method.** The classifier's own resolution was inspected with
`opencode debug agent <Name>` against an isolated `HOME`, and the command forms
were issued through the harness with the agent's `bash` permitted. The probe
set was the same list of command verbs below, each pointed at a file inside one
of the five protected directories above. "Fires" below means
`external_directory` was asked at all for that command; "resolved to" is the
winning rule read out of the resolved array.

**1. `external_directory` fires for roughly three command verbs, and no others.**

| Fires | Does **not** fire |
|---|---|
| `cat`, `cp`, `mv` | `head`, `tail`, `sed`, `awk`, `strings`, `nl`, `tac`, `more`, `grep`, `dd`, `xxd`, `od`, `base64`, `python3 -c`, `sh -c`, `bash -c`, `find -exec`, `tar` |

**2. With `bash: allow`, the non-firing forms resolve to `bash allow` and
returned credential-file contents.** Not "would have" — the probe returned the
bytes of the protected file.

**3. This is a classifier gap, not shadowing.** The bare `"*": deny` was removed
from the agent's `permission` block, making the credential rule the true winner
for `external_directory`, and the outcome did **not** change. **No reordering of
`external_directory` rules fixes it**, because the command is never classified
as an external-directory access in the first place. This is why the fix for this
ticket was scoped to `read` and to the `external_directory` *policy*, and left
this path alone.

**4. Exactly three of the six agents are not exposed by this path: Dispatcher,
Michal and Daedalus** — precisely the three that declare `bash: deny`. The
exposure is a property of holding `bash`, not of any agent's identity.

**5. Model self-restraint is not a control.** In testing, the model refused to
run `sed`, `awk` and `base64` against a file named `credentials`, and ran the
identical commands against a neutrally-named file in the same protected
directory. Earlier "clean" runs were **judgement, not enforcement**, and must
not be cited as a mitigation. Do not add an agent non-negotiable that says "I
will not read credentials with `bash`" — the harness would then be relying on
the one component that has already been measured to be inconsistent with itself.

### The accepted mitigation is OS-level

Filesystem permissions, a separate unprivileged uid, or containerisation. None of
these is in scope for a config file, and none is implemented by this repository.
An operator who needs the credential paths to be unreachable from an agent that
holds `bash` must put the boundary at that layer.

### Why `bash` stays permitted

Sherlock (`root-cause-analysis`, `profiling`, `resource-leak-hunting`,
`flaky-test-triage`, `incident-response`) and Jozef (`ci-pipeline`,
`release-automation`, `observability-stack`, `slo-and-alerting`,
`runbook-authoring`) cannot do their work without a shell; Jeff needs one to
build and test. Narrowing `bash` was considered and rejected for that reason.
This is recorded here so the trade-off is visible rather than inferred from a
list of allowed tools.

### Where this is enforced, and where it is not

- Enforced **now**, as of this file: `check` A8 (every agent declares the
  credential denies after its `external_directory` wildcard) and A9 (every agent
  re-declares `*.env` after its `read` wildcard). Seeds **M6** and **M7** in
  `make eval-selftest` prove those gates go red on an inverted ordering.
- **Not** enforced anywhere, and not enforcible here: the `bash` path above.

---

## Scope: what this file does not cover

- **One runtime.** V1 **1.18.35** only. `eval-static` prints a loud `NOTE` on a
  different version rather than failing, because the ordering assumption these
  conclusions rest on was confirmed by hand on 1.18.35 and nowhere else.
- **One platform.** Linux. Nothing here was tested on macOS or Windows, where
  the accepted OS-level mitigation has different properties.
- **One model.** `opencode/space-bunny-free`, for the self-restraint observation.
  A different model may restrain more or less; that is not a control either way.
- **No threat model, no severity rating.** Those belong to Michal's
  `threat-modeling` and `vulnerability-assessment` skills. This file records
  observations; it does not score them, and it is not a risk acceptance signed
  off in advance of one.
- **The measurements above were not re-run for this change.** They are carried
  forward from the investigation that produced them. The config-level results in
  the first table *were* re-run and are the literal output of `make check`,
  `make eval-static` and `make eval-selftest`.
- **One carried-forward claim was partially re-verified.** The mechanism behind
  "`.env` files are readable" was re-observed directly: before the `read` block
  change, `read` of `<repo>/.env` resolved to `allow` through the agent's own
  `"*"` wildcard (resolved rule index ~94), overriding the built-in `*.env` rule
  at index ~57. The specific secret canary that was read out of a `.env` during
  the original investigation was **not** reproduced here — no credential file
  was opened as part of this change.