---
name: rented-cpu-slow-for-this-workload
description: 2026-09-20 measured — many-core x86 rental is ~3x SLOWER in total throughput than the Mac for the toy lookup training (memory-bandwidth bound); don't rent CPU for it
metadata:
  type: project
---

On 2026-09-20 a whole AMD EPYC 7763 (64 cores, vast.ai, $0.376/h, torch 2.8 MKL) ran the grow-blind lookup training at ~2.2 updates/s per seed with 48 seeds in parallel vs ~18 on the Mac (same phase). Micro-benchmark of a batched attention forward/backward: Mac 6.7 s; box idle 22 s; box with 48 jobs 170 s. Plain Python was only 1.8x slower. So the workload is memory-bandwidth bound and collapses under many-process contention; total throughput of the box was about a third of the Mac running 6 jobs. Wave aborted (infrastructure failure, nothing scored), evidence in `W/artifacts/fable-operator-reliability-grow-blind-20260920/remote-wave-1-ABORTED/`, box destroyed, cost ≈ $0.12.

**Why:** Ben gave a standing OK for rented CPU when it significantly speeds things up ([[rented-cpu-standing-ok]]); for this workload it does not.

**How to apply:** run many-seed waves of this toy on the Mac (6 at a time, ~12 min per batch). Before any future CPU rental, run `bench.py`-style contention test at full parallelism for 1 minute BEFORE launching registered seeds. If speed-up is needed, test BensPC's GPU with several processes first (free) rather than renting CPU.
