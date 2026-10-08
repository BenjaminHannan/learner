# 8a shape probe (spec addendum J, section 20 of design/8a-bigger-is-better-2026-10-07.md)

Two seeds (400, 401), B2 only, 10M band, same pool, caps, recipe and 24,000 updates as the 10M rung, one rented RTX 5090
per arm and seed, code 50ee17163276061255e76b1a0039951b5de223b5 (build branch claude/project-thread-f1to6a).

- `R/`: `RUNG=10M ARMS=B2 B2X=reader_layers:23,blocks:2 LRS=1.0` (10,243,921 trained params)
- `W/`: `RUNG=10M ARMS=B2 B2X=d:384,n_heads:6,mlp:4.8,blocks:3 LRS=0.66667` (9,892,562 trained params)
- `box-probe.sh`: the box script these ran with (the 8a box script plus ARMS / B2X / LRS).
- `readout.json`: the readout fixed before the runs, applied to these results and to `results/8a-ladder/` (3M B2 and
  the deep 10M B2 of the same seeds). R: flat. W: unclear. "Size sits in the wrong place" is not proved wrong.

Write-up: `results/8a-ladder/8A-10M-RESULT-2026-10-08.md`. Checkpoints: `/mnt/project-files/checkpoints/8a-probe/{R,W}/`.
