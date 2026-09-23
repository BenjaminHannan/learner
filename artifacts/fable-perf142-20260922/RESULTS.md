# RESULTS — Experiment 142: port exp-128's speed fix onto loop134 (Muse)

Result first: loop134's per-turn CPU grows 8–9x from 1k to 15k facts; the
index port removes that growth (unregistered re-run PASS 1.13/0.91/1.39)
with 5000/5000 identical replies and 400/400 identical bench rows. Two
registered FAILs stand (S1 ask 1.827 on attempt 1; S3 p3-crash + 1 rt81 move
from a latent 128 reasoner bug); both were fixed by completing the same
index coverage and re-run once as unregistered, per the sealed PASSMARKS.

## Marks (integer counts)

| mark | bar | result |
|---|---|---|
| S1 loop142 | 15k/1k CPU p50 ≤ 1.5x teach/correct/ask | attempt-1 FAIL: teach 0.815, correct 0.856, ask **1.827** (25/kind); loop134 ratios 8.412/8.541/9.438 (FAIL as expected) |
| S1 re-run (unregistered) | same bar, completed coverage | PASS: 1.134/0.908/1.394; p50 ms 1k 1.17/1.21/1.62 → 15k 1.33/1.10/2.26 |
| S2 | 5000/5000 replies identical loop142 vs loop134 | PASS registered (vA) + 5000/5000 unregistered on final code |
| S3 | all-suite verdicts identical (both waves in this dir) | attempt-1 FAIL: p3 harness crash (IndexError) + rt81 M_hops-06 UNCLEAR vs OK; p2/p4/rt110/q1/bench/q4/sleep/soak identical |
| S3 re-run (unregistered) | same bar, final code | identical: p2 64/64, p4 30/30, rt110 62/62, rt81 74/74 (61/0/13 both), bench 400/400 + 0 reply diffs, q1, q4 0 leaks, p3 7/7, soak 0/0/0, sleep SKIP |
| S4 | bench121 new+old per-item identical to loop134 rows | PASS 400/400 verdicts, 0/400 reply diffs (new 136/63/1, old 157/43/0) |
| S5 | S1x2+S2+S3x2+S4x2 registered wall < 1800 s | PASS: 51.3+332.2+65.2+137.1+143.2+46.1+47.3 = 822.4 s |

## Why attempt 1 failed (both fixed, same one-change theme)
- S1 ask: three O(E) mention scans per "?" turn (N-hop + 2-hop + fallback
  recompose). Fix: one shared span scan + per-turn fallback hint (same
  frames, `fable_perf142_index.py` only).
- S3: latent 128 bug inherited by reuse — `FastReasoner77._entry_for`
  indexes `facts[0]` with no empty guard. A drop-cache HIT for a
  (relation, subject) pair with no surviving rows (M_hops-06: Ana's city
  never taught, city's drop bit cached from an earlier turn at the same
  notebook version) crashed instead of returning None (-> MISSING_FACT, as
  the original does). Fix: `FastReasoner142` returns None on empty rows.
  128 never saw it (no repeated-relation missing-subject hop in its suites).

## Deviations
- DEV-1: S1 attempt-1 FAIL recorded; coverage completed; re-run once,
  unregistered, PASS (sealed PASSMARKS pre-authorised this path).
- DEV-2: S3 attempt-1 FAIL recorded (p3 crash + M_hops-06); same path:
  unregistered re-run, full identity.
- DEV-3: 15k tail synthesised (seed-93 plan holds ~14,003 taught FACTs;
  same as 128).
- DEV-4: S5 counts registered runs only; diag134 + unregistered re-runs
  excluded (stated here).

## Reproduce (Mac CPU, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`)
- `scripts/fable_perf142_diag.py --out DIR/diag134.json` (unregistered profile)
- `scripts/fable_perf142_c1.py --agent loop142|loop134 --out DIR/c1-X.json`
- `scripts/fable_perf142_c2.py --out DIR/c2.json`
- `scripts/fable_marks123_all.py --agent scripts/fable_loop142_agent.py --config DIR/loop142-config.json --out DIR/marks142 --workers 4` (loop134: swap agent/config/out)
- `scripts/fable_perf142_bench121.py --agent loop142` (then `loop134`)
- Seal: `shasum -a 256 artifacts/fable-perf142-20260922/PASSMARKS.md` =
  e9a6cc21… (SEAL.sha256.txt, before any registered run).

## What it means
Loop134 keeps its teach coverage, N-hop questions, and loop117 fixes, now
with flat per-turn CPU: ~1–2 ms at 15k facts, and every reply/verdict
checked identical (5000 turns, 400 bench rows, all marks suites).

## What it does not mean
The two registered FAILs stand as FAILs; the passes came from the allowed
single unregistered re-runs. Nothing here changes answers, storage format,
or sleep/thinking; wall-clock under load can still rise (mailbox + fsync).
Questions for Ben: none.
