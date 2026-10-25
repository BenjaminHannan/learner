# Dopamine-2: does single-try learning move at all with a 10x learning rate? (fixed 2026-10-25, before any run)

Dopamine-1 (RESULTS-dopamine1.md): no arm's training reward rose at lr 1e-5, so the comparison of baselines had
no power. This test makes one change: lr 1e-4. Everything else is the same as Dopamine-1 (seed 0, 20 x 16 single
tries, checks-only reward, the same 100 held-out tasks). The base score is reused (25/100).

Arms: d_none and d_value. Command: `LR=1e-4 bash rlaif/run_dopamine1_lane.sh OUT none` (and `value`).

- Q1 learning moves: d_none >= 30, or its training reward over steps 16-20 is at least 0.05 above steps 1-5.
- Q2 dopamine helps once learning moves: d_value >= d_none + 5, with the paired McNemar p reported.
- Proved wrong: if Q1 fails, single-try RL at this scale doesn't learn, and the nightly update moves to
  correction pairs (DPO/KTO) instead. If Q1 passes and d_value <= d_none again, the per-type baseline is
  dropped for single tries.
- Harm alarm: either arm <= 20, which would mean lr 1e-4 breaks the model.
