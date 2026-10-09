---
name: runbook-authoring
description: Write the document that must work at 3am — preconditions, an ordered diagnosis path with commands and expected output, mitigations ordered by risk, escalation with a timeout, verification, and cleanup; Use when writing or updating a runbook for an alert, when an alert has no runbook, when a mitigation lives only in someone's head, or when a runbook written after an incident has never been followed end to end.
metadata:
  owner: Jozef
  domain: infrastructure
---

# Runbook Authoring

> Scope — the document. Deciding what to do during a live incident is `incident-response`; producing the timeline from artifacts is `production-signal-analysis`.

## When to use
- An alert can page, and has no runbook, or its runbook link does not resolve.
- A mitigation is known but lives in one person's shell history or memory.
- After an incident whose response depended on undocumented knowledge.
- Before a rotation starts, for anything that rotation can be paged for.

## Rules

**Structure — these sections, in this order, every time**
1. **What this alert means** — the user-visible symptom in user terms, plus the alert's query and threshold. Not the internal detail that raised it.
2. **Impact and severity** — who is affected, how badly, and what happens if it is not acted on. Include "no user impact, investigate in working hours" as a valid answer.
3. **Preconditions** — access required (role, account, cluster, namespace), tools that must be installed, and **how to confirm you are in the right place and the right incident**: the exact commands that print the current version, region, and failing signal, with the output a healthy system prints.
4. **Diagnosis** — an ordered decision path, not a list of things to check. Each step carries the exact command or query, the expected output, how to read it, and the branch it leads to. "Check the logs" is not a step; the query and its two possible readings are.
5. **Mitigation** — options ordered by risk and reversibility, lowest risk first (`incident-response` holds that order). Each with the exact command, its expected effect, its blast radius, and whether it loses data or state.
6. **Escalation** — who, through which channel, and after how long without improvement. A rota link plus a timeout, never "escalate if needed".
7. **Verification** — the command or query that proves the mitigation worked, and the window to watch before declaring it over — long enough to clear the tail.
8. **Cleanup and rollback** — the step people forget: revert the temporary change, remove the flag override, cancel the scale-out, drain the queue, revoke the temporary access grant, and confirm the system is back to its declared state.

**Quality bar**
- Every command is copy-pasteable, placeholders visibly marked (`<region>`, `$SERVICE`), and no secret inline.
- Every step states its expected output. A step whose output the reader cannot interpret forces them to guess, which is the failure mode this document exists to remove.
- Write for the reader who is awake, tired, and new to the service. No "as usual", "as before", or "see above".
- Keep it in the repository, reviewable like code, and link it from the alert itself. A runbook in a wiki nobody can reach from the page is not a runbook.
- One alert, one runbook. If the runbook is a general service document, the alert links to the exact section anchor.
- A runbook is tested by following it — run it on staging or against a deliberately degraded environment, with a colleague who did not write it, and record the date and what broke. An untested runbook is fiction.
- Correct it the day it is used. An incident that followed the runbook and still went wrong is a runbook bug, and the fix is part of the incident, not a follow-up.

## Verify
- Someone other than the author follows it end to end and reports where they got stuck; the fixes land in the same change.
- Every command has been executed as written, in the environment the runbook names, and the output is pasted next to it.
- Every alert in the paging rotation links to a runbook that exists and resolves.
- Every mitigation step states its expected effect and whether it is reversible; destructive ones are labelled as such.
- The cleanup section names the exact command that returns the system to its declared state.

## Anti-patterns
- Not "check the dashboards" — the query, the expected output, and the branch it leads to.
- Not a mitigation with no command, or a command with no expected effect.
- Not escalation without a timeout — "if it has not improved in 15 minutes, page <role>".
- Not written only after the incident and never updated — correct it the day it is used.
- Not tested only by its author, and not tested at all in a degraded state.
- Not omitting cleanup — a mitigated incident that leaves a flag flipped is a second incident.
