---
name: scalability-design
description: Reason about capacity and failure before building by stating current numbers with their sources, naming the resource that saturates first, identifying whether the bottleneck is CPU, IO, lock, or coordination bound, choosing scale up, scale out, or partition deliberately, pricing the design at ten times today's load, and writing down the trigger number that would force a rethink; Use when a design must survive growth in traffic, data volume, team size, or cardinality, when a capacity or cost question determines the architecture, or when someone claims a design "scales".
metadata:
  owner: Daedalus
  domain: architecture
---

# Scalability Design

## When to use
- A design must survive growth in traffic, data volume, team size, or key cardinality.
- A capacity, latency, or cost question is what is actually deciding the architecture.
- Someone has claimed a design "scales" and the claim needs arithmetic behind it.

## Rules

**1. State the current numbers honestly:** requests, payload sizes, data volume, growth, and the growth **rate** — with the source of each number. Every later calculation inherits that uncertainty, so the source matters as much as the figure.

**2. Derive the requirement from the growth curve, not the average.** Find the dominant resource — CPU, memory, IOPS, network, or a human bottleneck — and name which one saturates **first**. A system is limited by its scarcest resource, not by its average behaviour.

**3. Find the ceiling and the unit cost:** the maximum throughput, and what one unit of work costs in memory, IO, and money.

**4. Name the bottleneck's nature** — CPU-bound, IO-bound, lock-bound, or coordination-bound. The remedy differs entirely, and optimising the wrong one is wasted work.

**5. Choose the growth strategy deliberately:**
- **Scale up** — a bigger machine. Simplest, and has a hard ceiling.
- **Scale out** — stateless replicas. Requires removing shared mutable state first (`concurrency-resources`).
- **Partition** — shard by tenant or key. Buys total capacity, and introduces cross-shard queries, rebalancing, and hotspot risk.

**6. Design for the predictable consequences of scale:** hot keys and skew, cache stampede on expiry, thundering herd on reconnect, retry amplification, and the coordination cost that grows **superlinearly** as component count grows. Replicas are not free independence.

**7. Name the architectural trigger and its number.** At the scale where a single machine, a single database, or a single team cannot hold, the architecture must change — that threshold is a written number with a date it will be hit, not a feeling.

**8. State the cost consequence:** what this design costs per request at ten times current load, in the currency that is actually paid.

Bounded queues, pools, and batch sizes are not designed here — the bounding mechanism belongs to `concurrency-resources`; this skill sets the number it must respect.

## Verify
- Every capacity claim carries its arithmetic **and** its input numbers, each traceable to a source.
- The first-saturating resource is named, with the measurement that identified it (`profiling`).
- The scale-out strategy states the shared state that must be removed for it to work, and that state is removed or the strategy is not scale-out.
- At least one trigger number is recorded, with the date it will be reached.
- The ten-times-load cost is computed from the stated unit cost, not estimated.

## Anti-patterns
- Not optimising an abundant resource while the scarce one saturates.
- Not "just add a cache" without a hit-rate target, an invalidation strategy, and a stampede plan.
- Not sharding before measuring skew — sharding an already-skewed key makes the hot key hotter.
- Not scaling out while shared mutable state remains and becomes the new bottleneck.
- Not "it scales" with no dimension, no number, and no date.
- Not quoting an average where the growth curve is the thing that matters.
