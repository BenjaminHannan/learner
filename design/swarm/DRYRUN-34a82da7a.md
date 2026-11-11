# Dry run at the run-3 code commit 34a82da7a (2026-10-20)

**THIS IS A DRY RUN.** It uses the tiny preset, CPU and T = 120 s. Every number and verdict in it is meaningless. It
proves that the box kit runs end to end at 34a82da7a, the commit with C0's train-overhead probe in a fresh subprocess
and per-phase memory logging.

```
DRYRUN=1 PIN=34a82da7a8b85f3af7d448140c7d165b68e20dd7 OUT=.../dryrun-34a82da7a-seal bash scripts/premonition_swarm_box.sh
# clean tree, committed manifest (47 files) OK, HEAD == PIN; exit 0 after 1,657 s; 33 steps, every rc 0
```

- C0 wrote c0.json. Both train-overhead probes (S0 and D1) ran as fresh processes (`fresh_process: true`) and logged
  the phases start, calibration, step1, train, validation and save, in order (memory numbers exist only on CUDA).
- Trains: all 9 completed, `train_seconds` 120.0-120.2.
- All four readouts were computed. At `--min-items 100` both are INSUFFICIENT on tiny data (far_deep 62); at
  `--min-items 1` the full verdict paths ran.
- Archive packed, sha256 `0f26a8bbc46bbec0e82afbbc52ee6d76d37ad5263473ee549831d5c1b164a844`. Outputs are in
  `artifacts/claude-swarm-screen-20261018/dryrun-34a82da7a-seal/` (git-ignored).

## Steps (name, seconds, rc)

| step | seconds | rc |
|---|---|---|
| data | 6 | 0 |
| c0 | 213 | 0 |
| train-D1-s0 | 143 | 0 |
| train-S0-s0 | 142 | 0 |
| train-D1-s1 | 142 | 0 |
| train-S0-s1 | 141 | 0 |
| train-D1-s2 | 142 | 0 |
| train-S0-s2 | 140 | 0 |
| eval-D1-s0 | 8 | 0 |
| eval-S0-s0 | 8 | 0 |
| eval-D1-s1 | 8 | 0 |
| eval-S0-s1 | 9 | 0 |
| eval-D1-s2 | 8 | 0 |
| eval-S0-s2 | 9 | 0 |
| marks-S0 | 0 | 0 |
| marks-S0-minitems1 | 0 | 0 |
| train-S1-s0 | 142 | 0 |
| train-S1-s1 | 141 | 0 |
| train-S1-s2 | 142 | 0 |
| eval-S1-s0 | 8 | 0 |
| eval-S1-s0-board | 9 | 0 |
| eval-S1-s0-notes | 9 | 0 |
| eval-S1-s0-cards | 8 | 0 |
| eval-S1-s1 | 9 | 0 |
| eval-S1-s1-board | 9 | 0 |
| eval-S1-s1-notes | 9 | 0 |
| eval-S1-s1-cards | 8 | 0 |
| eval-S1-s2 | 9 | 0 |
| eval-S1-s2-board | 9 | 0 |
| eval-S1-s2-notes | 9 | 0 |
| eval-S1-s2-cards | 9 | 0 |
| marks-S1 | 0 | 0 |
| marks-S1-minitems1 | 0 | 0 |
