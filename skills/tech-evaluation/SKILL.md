---
name: tech-evaluation
description: Choose a library, framework, datastore, queue, runtime, or managed service by writing testable requirements first and evaluating candidates against them, including doing nothing and the boring incumbent, with operational and exit cost as first-class criteria and the risky assumption prototyped; Use when selecting a dependency, revisiting an existing choice, or when someone proposes a rewrite, a migration, or a new platform and the proposal needs evidence rather than enthusiasm.
metadata:
  owner: Daedalus
  domain: architecture
---

# Tech Evaluation

## When to use
- Selecting a library, framework, datastore, queue, runtime, or managed service.
- Revisiting an existing choice, or fielding a proposal to replace one.
- A rewrite, a migration, or a new platform is proposed and must be judged on stated dimensions.

## Rules

**1. Requirements before candidates.** Write testable constraints *before* looking at anything: workloads, latency and durability targets, the consistency model, and the operational constraints — who runs it, what skills exist, what the budget is, what the deadline is. Then the non-negotiables.

**2. Real candidates include doing nothing and the boring incumbent.** A rewrite must beat a working system **on a stated dimension**. If it cannot be named, it is not a proposal.

**3. Evaluate against the requirements, not a feature checklist.** Feature parity is table stakes and carries no information. Score each candidate against numbered requirement 1, 2, 3 — including where it fails.

**4. Operational and lifecycle cost, honestly:** who maintains it, how upgrades happen, what happens when it is abandoned, what a breaking upgrade costs, how large the dependency tree is, and the real migration path off it.

**5. Exit cost is a first-class criterion, not a tiebreaker.** How hard is it to remove in a year? Name what data, code, and knowledge would have to move. A choice you cannot leave has no downside recorded.

**6. Prefer the boring, widely-adopted, reversible choice** unless a requirement genuinely forces the interesting one. Novelty is a cost, and it is paid immediately and continuously.

**7. Prototype the risky assumption only** — the single assumption that would invalidate the choice if false — and timebox it. Do not build a prototype to compare features.

**8. Record the outcome via `adr`**, naming the rejected alternatives and the reason.

**Evidence rules**
- A benchmark from the vendor's own marketing is not evidence. Run it yourself, on your workload, and record the method (`performance-measurement`).
- Popularity is weak evidence about maintenance and strong evidence about hiring.
- "We might need it later" is not a requirement. If it is genuinely required, it is numbered and testable.

## Verify
- Every recommendation traces to a numbered requirement; any candidate that traces to none is dropped.
- At least one criterion in the comparison is exit cost.
- The do-nothing option was genuinely evaluated, with its costs, not dismissed.
- The reversible option was preferred, unless a numbered requirement forced the irreversible one.
- The prototype tested the riskiest assumption and nothing else; its result and timebox are recorded.
- The `adr` exists and lists the rejected alternatives.

## Anti-patterns
- Not a feature-matrix bake-off; that measures table stakes and rewards whichever checklist is longest.
- Not "it scales better" without the workload, the number, and the method behind it.
- Not a prototype built to compare features — that is a second implementation, not evidence.
- Not ignoring operational cost because the demo was clean.
- Not a vendor benchmark quoted without reproduction.
- Not choosing for a hypothetical future requirement nobody has written down.
