# NOTES: real-transition world-model harness (toy shape)

## What was run

Environment: system `python3` (3.14) had no numpy/torch/crafter, so I made a throwaway
venv from `python3.12` with numpy 1.26.4, torch 2.2.2 and crafter, and ran everything
there. `premonition_core_v2/` was not edited.

1. `python record.py --out data`
   - train: 160 worlds (0-159), 20,000 transitions, 20,175 frames, 175 episodes,
     moved-frame share 0.823
   - heldout: 16 worlds (1000-1015), 5,008 transitions, 5,042 frames, 34 episodes,
     moved-frame share 0.876
   - extra episodes (175 > 160, 34 > 32) are early deaths; each restart uses
     `seed = world*1000 + episode_idx` in the same world. Episodes are capped at 250
     steps and also at the remaining transition budget for that world.
2. `python wm_fit.py --smoke --device cpu --out smoke` (20 steps, 200 synthetic train
   windows, 80 synthetic heldout windows): runs end to end and writes
   `smoke/score.json`, `smoke/forecasts.npz`, `smoke/wm.pt`. Cells: total 83,952,
   expert 36,864, active 65,520; whole model 349,744 params.
3. `python wm_fit.py --device cpu --out run_literal` (full protocol: 1,500 steps,
   batch 64, Adam 3e-4, seed 42, ~0.16 s/step, about 4 minutes): final checkpoint
   scored on heldout and written to `run_literal/`.

## Full-run result (literal TASK recipe)

| k | E_k | B_k | E_k/B_k | moved E/B | windows |
|---|---|---|---|---|---|
| 1 | 17387.1 | 16474.3 | 1.0554 | 1.0661 | 5008 (4381 moved) |
| 3 | 40735.0 | 35720.4 | 1.1404 | 1.1547 | 4940 (4316 moved) |
| 5 | 55832.6 | 46358.0 | 1.2044 | 1.2127 | 4874 (4252 moved) |

- real-board decode ceiling (k=1): E/B = 1.0554 (> 0.95 -> pre-gate fails, moot)
- shuffle: pooled moved-window error ratio 1.0000 (k=1), 0.99999 (k=5);
  0/16 worlds met either per-world mark (>=1.25 k=1, >=1.10 k=5)
- collapse: first-action std ratios 0.006-0.121 (mark 0.25-2 -> fail);
  PCs for 90% variance: predicted 98, real 111 (98 >= 0.5*111 -> pass)
- PROVES_WRONG flag: false (E1/B1 is not <= 0.80)
- verdict: **WRONG**

## Why the literal recipe diverged (diagnosis, not a code fix)

The k=1 row loss is specified against the board after the model "continues that
state and reads frame t+1", i.e. two more `run_tick`s after the two ticks used to
read frame t. In this cell the fast rows move by the full delta every tick, so that
detached target grows simply with tick count even before any training: with an
untrained cell the mean |row| over 64 real frames was 0.40 at init, 0.52 after 4
ticks, 0.64 after 6 and 0.74 after 8 (slow rows stayed ~0.43). The stop-gradient
target therefore moves away from `next_rows` faster than a one-imagine-step
prediction can follow, and the row MSE runs away: training loss went 0.017 at step 0
to 3,291 at step 1,499. Because the row term dominates, the decoder never learns
either (its copy-baseline error stays flat), so E_k/B_k ends above 1 and the
imagined board, when fed back at k=3/5, drifts further.

Short 150-step diagnostics on the same data (not shipped as the result): the row
loss alone with this continued target diverges; the same loss against a fresh
`read(init_state, enc_{t+1})` target, or restricted to the 3 slow rows, converges
(l2 -> ~0 and rows stay ~0.4). I kept the task-literal target. That instability is
the likely reason the run fails the pre-gate; a retry would need to change the
target rule, not the code mechanics.

## API assumptions

- `read(state, enc)` = two `cell.run_tick(state, enc, noise=False)` calls. Board t =
  `init_state(B, k=1)` then `read(enc_t)`; `rows_real_next` = `read(board_t, enc_{t+1})`
  (continued state, two more ticks). `noise=False` was chosen so reads are
  deterministic and the target is well defined.
- Frame reader: 16 spatial tokens, each a 4x4 block of 4x4x3 pixels -> 48 values;
  `Linear(48, D)` + learned [16, D] position embedding, then `rms_level` (unit RMS
  per row). Context uses `Source.SIGHT`, mask all True, support all 1, age_s/epoch/
  q_hash 0.
- `cell.imagine(state_t, enc_t, action_emb, wm_grad=True)` per step; every imagined
  step uses `enc_t` (frame t context); `next_rows` is fed back with
  `dataclasses.replace(state, rows=...)`. Actions are `nn.Embedding(17, D)`.
- Decode head reads only flattened `next_rows` [B, R*D] -> 256 -> 768 (zero-init last
  layer), reshaped to [16,16,3] as a predicted change; predictions are not clamped.
- Loss = mean MSE(head(next_rows), x_{t+1}-x_t) + mean MSE(next_rows,
  rows_real_next.detach()) + mean MSE(head(rows_real_next), x_{t+1}-x_t) +
  0.01 * imagine.aux_loss. `world_model_loss` is not used (weight 0).
- Moved window = mean((x_{t+1}-x_t)^2) > 1e-6. Blends fit `a` on train windows of the
  same k; B_k is the better of copy and blend on heldout (or the moved subset).
- Shuffle permutes action values across all heldout transitions of each world with
  `np.random.default_rng(43)`, preserving marginals; true and shuffled rollouts use
  the same windows/contexts.
- Action-group std is the global std of flattened predicted/real one-step changes per
  first-action group. PC counts are from the eigendecomposition of the per-pixel
  covariance of centered changes.
- Training windows are drawn with replacement (numpy rng seed 42) from all valid k=1
  train windows; the first 20 steps' seconds/step are printed; `--max-minutes`
  (default 15) cuts steps; only the final checkpoint is scored. `--smoke` builds tiny
  synthetic splits in memory.
