# Stage 0 report (SC-1, ruling Q22)

**Status: NO RESULT YET.** The Stage 0 script is filed for the coordinator's review (Q129) and must not run until
that review passes. The reviewed-script run will be the Stage 0 result.

## Attempt 1: unreviewed script, stopped, does not count
- Script: `scripts/span_stage0.py` at a3b145ee8 (sha256 c4a9a5082cfe1320...0191), before Q129. It ran **without
  the coordinator's review** of the script; Q129 says such a readout is provisional and does not count.
- Box: Vast instance 56561820, label `claude-spancards-stage0`, on-demand (not interruptible), 1x RTX 3090,
  Ryzen 9 7950X, 30 GB disk, $0.264/h all-in. Created 13:49:28Z; destroyed by me at 14:07:16Z, as soon as Q129
  arrived (17.8 min). Image `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime` with torch 2.11.0 cu128 installed.
- Readout: **none.** A log snapshot was requested at destroy time but was never uploaded (the log store
  answered AccessDenied), so no line of the run was recovered. Nothing is known about how far it got.
- Spend: **$0.089** (account credit 32.749 before to 32.661 after; it may move by a cent when billing settles).

## Budget for the reviewed run
Hard stop $0.50 across all attempts: **$0.411 left.** Planned rerun: the same box class (about $0.265/h plus
about $0.03 of downloads), expected to take under 60 min (about $0.30), with a watchdog that destroys the
instance at 75 min (worst case about $0.36, so $0.45 in total). If no offer of that class fits inside the
remaining budget with that margin, I stop and come back to the coordinator instead of renting.

## Ledger line (suggested; the ledger lives on the Mac)
2026-10-18 | spancards-stage0 attempt 1 (unreviewed script, stopped on Q129) | vast 56561820 | RTX 3090 |
0.30 h | $0.264/h | $0.089 | no readout, does not count
