---
name: profiling
description: Measure where time, memory, and input-output actually go before changing code; use when something is slow, spins a core, allocates heavily, grows memory, blocks on input-output or locks, or regressed in latency and you need a number with stated uncertainty.
metadata:
  owner: Sherlock
  domain: debugging
---

# Profiling

Measure first, hypothesize second. Turn the result into a hypothesis for `root-cause-analysis`.

## When to use
- Something is slower or hotter than it should be, and nobody knows where the cost sits.
- Memory grows, or allocation rate looks like the problem.
- A thread is blocked, not busy: a CPU profile will show nothing, because the cost is off-CPU.

## Pick the method
- **Sampling** — cheap, always-on-able, gives proportions not counts. Right when the hot path
  runs continuously. Tools: `perf` and `async-profiler` or JFR, Go `pprof`, `py-spy`,
  `samply` or `cargo-flamegraph`, `rbspy` or `stackprof`, `dotnet-trace`, Erlang `prof`.
- **Instrumenting** — exact counts and timings on chosen points, high overhead, distorts the
  thing it measures. Right when you need a precise count, not a proportion.
- **Counting** — allocations, syscalls, I/O bytes, lock acquisitions, query counts. Right when
  the hypothesis is about volume rather than time.

## Reading the output
- Split inclusive from self time: the frame that dominates inclusive time may only be a router.
- Distinguish a hot path (executed constantly, cheap each time) from a hot loop (rarely entered,
  expensive) from allocation-driven cost.
- A self-heavy stack is CPU work. An idle-looking profile on a slow request means off-CPU.
- Allocation profiles come in two flavors: churn, meaning bytes allocated per operation, and
  retention, meaning live bytes that never drop. Only retention is a leak; see
  `resource-leak-hunting`.
- Allocation profiling: heap dumps plus dominator trees, `pprof -alloc_space` versus
  `-inuse_space`, `tracemalloc` or `memray`, JFR allocation profiling, LeakSanitizer or
  Valgrind, and language heap profilers such as `dhat`.
- Off-CPU and wait time: eBPF off-CPU or sched profilers, `strace -c`, blocked and mutex
  profiles in Go, thread dumps and `jstack`, and language-native scheduler dump commands.
  Attribute the wait to the thing being waited on: socket, lock, timer, or child process.
- Input-output and syscalls: `strace` or `dtruss`, per-process IO counters, and database or
  broker-side query stats. Volume and latency of round trips is a first-class cost.

## Flame-graph traps
- Inlined frames collapse into their caller, hiding cost or mislabelling it.
- Sampling skew and too-short runs produce beautiful, wrong pictures.
- Lost or truncated frames at recursion and deep stacks; check the resolver.
- Differential comparison beats a single picture: profile before and after, diff the two.

## Procedure
Profile, change one thing, re-profile the same workload, compare. Stop when the target metric moves
more than the measured noise, or when the remaining cost is inherent to the work.

## Verify
Establish warmup, then run enough repetitions to see variance, on an environment resembling
production. Record CPU, memory limits, thread and process count, and the input as a baseline.
Always report the measurement with its uncertainty: a 12 percent change inside a 15 percent
run-to-run spread is not a finding.

## Anti-patterns
- Not optimizing the frame that merely sits on top of the inclusive-time tree.
- Not trusting a profile captured before warmup, or from a workload unlike production.
- Not treating a CPU profile as evidence about a thread that was blocked the whole time.
- Not calling a guess a finding without a before-and-after measurement on one workload.
- Not leaving sampling on in production at a rate that costs what you were optimizing for.

## Prevention
Make the cost visible before it surprises you: `observability`. Bound the work that consumes
these resources: `concurrency-resources`. Guard the budget in CI: `testing-strategy`.
