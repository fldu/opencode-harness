---
name: fix-verification
description: Close a security finding only by reproducing it first, then checking the fix for pattern coverage, correct layer, whole input class, new failure modes, a regression test that fails when reverted, a re-run threat model, and an honest residual-risk statement; Use when a vulnerability report is claimed fixed, when reviewing a security patch or pull request, when deciding whether a finding can be closed or must go back, or when a scan comes back clean and someone wants to know whether the problem is actually gone.
metadata:
  owner: Michal
  domain: security
---

# Fix Verification

## When to use
- A finding is claimed fixed and must be closed, or sent back.
- Reviewing a security patch before merge.
- Deciding whether a clean scan means the problem is gone.

## Rules

**1. Restate and reproduce first — before reading the fix.** Restate the finding in the nine fields defined by `vulnerability-assessment` (consume that format; never redefine it). Reproduce it on the unfixed revision. If you cannot reproduce it, you cannot verify the fix: the finding is wrong or already mitigated — **send it back**, do not close it.

**2. Pattern or instance.** Grep for the **class** of vulnerable pattern, not the string quoted in the report. One escaped quote fixed while the concatenation remains is not a fix.

**3. Right layer.** Validation belongs at the boundary, not escaped at each sink. Authorization belongs on the route or the policy, not inside one handler. Path containment belongs in the resolver, not at each call site. A fix at the owning layer is inherited by every current and future caller; a fix at a call site is not.

**4. Whole input class.** Alternate encodings and encodings-of-encodings, wrong types, boundary sizes, alternate entry points (CLI, job, import, webhook, a second API version), and second-order flows (`injection-and-input-hardening` owns the flow mechanics).

**5. New failure modes.** Confirm the fix fails **closed**, and that closed is **correct**: it must not deny legitimate traffic, lock out real users, or leak the reason through an error message, a status code, or a timing difference. Exercise the error path deliberately, not just the accept path.

**6. Regression test** that fails without the fix and passes with it, placed where it keeps running — the unit or integration suite, not a scratch script. Assert the **rejection or denial**, not the absence of an exception (`testing-strategy`).

**7. Re-run the threat model** for the boundary that changed (`threat-modeling`). Did the diff move data across a boundary, change a default, or change a serialized format — and did it open a new one?

**8. Residual risk, stated honestly.** What remains unverified, what you could not test, what depends on configuration or deployment, what is deferred. "Probably fine" is not a residual-risk statement.

## Verify
- The reproduction fails on the unfixed revision and is rejected on the fixed one — both observed, not assumed.
- The regression test **fails when the fix is reverted** (that is what proves it bites) and passes with the fix.
- You can name the single function or policy now enforcing the property, and grep for remaining bypasses of it.
- The error path was exercised: legitimate traffic still succeeds, and the rejection leaks nothing.
- The relevant scan was re-run and recorded as **one input among many** — a clean scan is never the verification.
- A residual-risk paragraph exists and contains no "probably" and no "should be fine".

## Anti-patterns
- Not closing on the author's test alone; a test written alongside the fix encodes the fix's assumptions.
- Not a scan-clean ticket with no reproduction and no named enforcing function.
- Not "the escape was added" as evidence the class is closed.
- Not an error message that tells the attacker which check failed.
- Not verifying the happy path only — a fix that rejects everything also passes a smoke test.
