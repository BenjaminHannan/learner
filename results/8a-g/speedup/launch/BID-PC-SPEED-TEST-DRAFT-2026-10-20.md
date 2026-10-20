# BID (DRAFT, not sent): PC speed test of the ported trainer, flag on vs off

**Status: draft. It goes to the coordinator only after the coordinator's code review of `launch/port/`. The port is parked after review round 2, waiting on a ruling (10-20).** Nothing here is booked, started or spent.

## What it buys
The one number the goal still lacks: **the measured time of a 24,000-update B3G2 3M accum-4 run in the production trainer, with `--speed-arms defer` against without, per host.** This uses the ported tree `src-b3g2ck-defer` (custom_io 74d6e92c75 + g2fa4 `train.py` + `launch/port/`), not the profiling harness.

GPU-RUN-4 measured the harness at 1.36× (box 2) and 1.51× (box 1, raw). That was not the production trainer and not the PC.

## The test (one change: the flag)
- **Host 1, Ben's PC (RTX 4090), via the g2fa4 supervisor pack's pattern.** Four fresh 300-update runs in the order **off, on, off, on**:
  - same seed (400), rows, caps and queue line as 8aB3G2A4;
  - each run under a NEW name (`8aB3G2D4-speed-*`), output folders apart, `--ckpt-every 0`, no resume;
  - the final eval skipped (or cut to its minimum), so only training time counts.
- **Timed window:** updates 51–300 of each run. The time is read from train.py's own `elapsed` on the `--log-every 1` train lines, and the first 50 updates are left out as warm-up.
- **The second host, for the per-host quote:** either a second PC-class machine if one exists, or one Vast RTX 4090 running the same four runs through a box script generated like `gpu_run_5_box.sh` (about 70 min, about $0.55 billed, hard cap $1.00). The coordinator chooses.

## Pass marks (to be sealed before any run, in a PREREG; numbers fixed here)
- **Speed** = median s/update of the two off runs ÷ median of the two on runs, per host. Hosts are never pooled.
- **Ships:** speed ≥ 1.25× on **every** host. This is the amended sheet's port-grade bar (PREREG-launch-defer.md mark 1 + P1).
  - **Quoted result:** the 24,000-update time on each host = its median s/update × 24,000, off and on.
  - Today's figure, about 15 h at 2.24 s/update, would fall to ≤ 12 h at 1.25×.
- **Same-arm noise (AA):** the two off runs must agree within 5% (mark 5's spirit), or that host is not read.
- **Proved wrong:** speed < 1.25× on any host with AA holding. Then `defer` is not adopted, and the next step is the §5 "no port" branch.
- **Not judged here:** numerics, already settled by GPU-RUN-5 under its sealed bars, and loss quality over 24k updates. That loss quality is the first `defer` fresh run's own registered checks (trace A and others, as for 8aB3G2A4).

## What it costs and displaces
- **PC:** about 4 × (300 updates × 1.6–2.3 s) ≈ 40 min of GPU, plus about 10 min of setup.
  - The PC's GPU must be otherwise idle during the timed runs. That **displaces about 50 min of the PC queue** (8aB3G2A8 or whatever is running then), or it waits for a gap between jobs.
  - I do not know the PC queue's state today; the coordinator does.
- **Vast (only if chosen as the second host):** about $0.55, hard cap $1.00, inside the $50/week cap.
- **Modal:** none.

## Needs before booking
1. The coordinator's code review of `launch/port/` (the round-2 findings either fixed in a third round or accepted).
2. A sealed PREREG with the marks above, and a CPU dry run of the exact PC and box scripts.
3. Ben's own approval for the PC time, and for any Vast rental.
