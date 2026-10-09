---
name: parallel-delegation
description: Run multiple approved dispatches concurrently only when they share no dependency, no file, and no contended resource, then reconcile the results yourself; Use when two or more tasks are independent, when a read-only investigation can run beside a write task, when partitioning work by file or directory, or when one parallel task failed and every sibling's status must be checked individually.
metadata:
  owner: Dispatcher
  domain: orchestration
---

# Parallel Delegation

Concurrency is a claim about the work, not a wish. If the claim is wrong, the
damage is silent.

## When to use
- Two or more objectives are ready and nothing about one depends on the other.
- A read-only investigation can run while a write task proceeds elsewhere.
- Work can be partitioned cleanly by file or by directory.
- A parallel batch came back and the results must be combined.

## Rules / Procedure

**1. Parallelise only what is truly independent.**
- If B's prompt depends on A's output, it is sequential, regardless of how unrelated the wording looks.
- Overlapping file writes are a race: two agents editing one file corrupt it. When in doubt, partition by file.

**2. Batch by domain and by blast radius.**
- A read-only investigation plus a write task elsewhere: safe.
- Two tasks on disjoint directories: safe.
- Two tasks on the same package, module, or config file: sequential.

**3. Every parallel prompt is complete and self-contained.**
- A subagent cannot see the other tasks, this conversation, or your reasoning. Restate the shared context in every prompt.
- "Same as the other task" is not context. Assume zero shared state.

**4. Dispatch in one message with multiple tool calls.**
- Sequential messages serialise the batch and waste the concurrency you set out to buy.
- One batch is still one set of dispatches: the approval gate applies to each of them (`delegation-gate`).

**5. Do not parallelise tasks that share a contended resource.**
- The same checkout, build directory, lock file, generated manifest, single config file, or a rate-limited external service.
- Two agents touching one Makefile is a lost update, not a merge conflict someone will notice.

**6. Verify write access before dispatching.**
- A read-only agent asked to produce a change will report a blocker, or produce a plan and stop, and both look like progress until you read them.
- Check the target agent can actually write before the dispatch, not after the silence.

**7. Collect and reconcile the results yourself.**
- You own the combined outcome. Two individually correct reports can still contradict each other.
- Where they conflict, resolve it explicitly and say which one you accepted and why.

**8. Check every sibling when one fails.**
- A failed task tells you nothing about the others' status. Check each one individually; do not infer success and do not infer failure.

## Verify
- For each pair of parallel tasks: no shared dependency, no overlapping file, no shared contended resource.
- Every prompt stands alone: issue id, state, deliverable, and constraints all restated.
- Every task requiring a change targets an agent with write access.
- Each task's result was read, not assumed, and conflicts between results are resolved in the report.
- Every sibling of a failed task has its own recorded outcome.

## Anti-patterns
- Not parallelising dependent work because the wording looks unrelated.
- Not parallelising two writes to the same file.
- Not assuming a failed sibling means the others failed, or that silence means success.
- Not under-specifying prompts on the theory that "they can see the context" — they cannot.
- Not parallelising around a shared build directory or rate-limited service.
- Not merging two results without reconciling them.
