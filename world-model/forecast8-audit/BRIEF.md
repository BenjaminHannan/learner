# Task: determinism audit of the Problem 7 pilot-2 conv world model (no new ideas, diagnostic only)

Code to read (do NOT edit): ../forecast8-pilot2/{train_v7.py, model_v7.py, scorer.py, pilot_driver.py, PILOT2-PLAN.md}.
Write ONLY inside this folder (forecast8-audit/). The script will be copied to another Mac where the pilot-2 folder
layout is identical (runs/s7_uniform/model.pt, runs/s{7,8}_{uniform,relper_u75}/{model.pt, forecasts_dev_reencode.npz,
score_dev_reencode.json, score_dev.json, sampler_log.jsonl}, pilot_data/). Take the pilot-2 folder path as --root.
Never read or open any sealed data path (train_v7.py has is_sealed_path/guard_sealed_path: reuse them and refuse).

Write audit.py with three stages; each prints a clear PASS/DIFF line and writes audit.json:
1. Score replay without the model: take runs/s7_uniform's saved predictions (forecasts_dev_reencode.npz or whatever
   file the pilot scored wall from — find out from the code), run the exact same wall scoring (score_block_open with
   the same inputs the pilot used) twice in two fresh subprocesses. Compare per-window open/blocked calls and the
   integer confusion counts (open->blocked, blocked->open, totals), and compare to the saved score json's wall numbers.
2. Model replay without training: load runs/s7_uniform/model.pt (with buffers), eval mode, regenerate the k1
   predictions on the same pilot eval windows twice (two fresh subprocesses, same device), hash the prediction arrays,
   compare wall calls per window, and compare against the saved predictions from stage 1. Do this for s8_uniform too.
3. Short training replay: twice, from the same seed (7) and the same initial state, run the first 20 uniform-sampler
   minibatches of the real pilot training path (reuse train_v7's functions; do not reimplement the loss). At every step
   record sha256 of: sampled indices, batch tensors, loss value, gradient vector, updated weights. Report the first
   step and quantity that differs, if any. Run on --device (default mps; also allow cpu).
Total wall time must be under 10 minutes. Add --stages to run a subset.
Also write PROOF.md: commands run on this Mac (e.g. syntax check, a --help run, any tiny CPU self-test on synthetic
data if you add one), exit codes, sha256 of audit.py. You cannot run the real stages here (no pilot runs on this Mac),
so say so; do NOT fabricate results.
Non-goals: no training beyond the 20-step replay, no changes to marks, no reading private files or any key/secret file.
