# rsn-358e3 run note (sleep research thread)

- Started: 2026-09-26 22:45:56 UTC (process start times; the launcher also wrote 22:45 from date -u). This note was written at 23:50 UTC, an hour late.
- Where: this session's cloud container (hostname "vm"), CPU, 1 thread per run, torch 2.14.0. $0.
- Batch 1 (graded arm + control), PIDs 24323-24326: moe-grow-replay s1, s2 and dense-replay s1, s2.
- Batch 2 (report only) starts when batch 1 ends: moe-grow-eq s1, s2 and moe-grow-eq-replay s1, s2.
- Steps per run: 2,500 grids + 2,500 sums (250 of them grids replay) + 1,500 mazes, batch 64, sealed code 8ba72fe39, marks 963833138.
- State at 23:50 UTC (from the training logs, loss only): moe-grow-replay at mazes step 1,250 of 1,500; dense-replay at sums step 2,250 of 2,500.
- Expected: batch 1 done around 00:00-00:30 UTC, batch 2 about 1 h after that (estimates). Logs and result.json are committed only after each run ends.
