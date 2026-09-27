# R2 — mastered snapshot retention confirmation (prepared 2026-09-27)

**Status:** Registered when committed before any run. The parent must commit this exact file before any R2 benchmark or training run. `run_mastered.py` requires `--passmarks-sha` naming that commit and compares the committed bytes with this file before creating output. Preparing these files is not a run or a verdict.

## Distinct question and comparison

R1 seed 29 reached only **174/200 grids5 after A**, below its 190 mastery bar, so its functional isolation cannot establish mastered-skill retention. R1 remains separately graded under its own marks; R2 does not rescue or regrade it. R2 is a fresh confirmation with a longer, fixed A training budget. R1 seed 30 is not used to choose R2 seeds, thresholds, or checkpoints.

Within R2, the **only candidate/control difference is serving path** after the same sequential training trajectory: the candidate routes a known task ID to its immutable complete snapshot; the control serves the newest B-trained model for that old task. No classifier or learned switch is introduced. The typed `Item.env` is provided by the caller and fixed for the whole request. The old snapshot includes token/slot/environment embeddings, attention, MLP, normalization, answer and stopping heads. The B learner is a separately trainable *whole clone* of the A snapshot. Storage is two complete models, not a fixed-capacity solution.

## Fixed run and data

- Architecture: existing `claude_rsn358e_moe.py` **small dense** loop, 1,646,750 parameters per model. Existing generated/checkable grids4/5 then sums1–4; no replay, other task, new data author, or model download.
- **A grids: 6,000 steps; B sums: 2,500 steps**, batch 64 each. Same R1 `train_step`: AdamW lr 1e-3, weight decay 0.1, betas (0.9, 0.95), 100-step warmup and cosine schedule reset per phase, random recurrent-depth schedule, gradient clipping 1.0. The A budget is 3,500 steps greater than R1; report measured extra wall time. No early stopping, retry-selected checkpoint, or post-score hyperparameter adjustment.
- Fresh training seeds **31 and 32**, both run and reported without selection. For seed `s`, a 200-item grids5 and 200-item sums4 panel is generated with held-out seed `92000+s` (92031/92032). Reject and count exact training inputs matching either final panel. Panels are scored at phase boundaries only and never select a checkpoint. Do not print panel contents.
- Use R1's existing `new_net`, `train_step`, `heldout`, `score`, `exact_outcomes`, checkpoint and router helpers through a module import; do not invoke or alter R1's `run` or sealed files. R2 owns its phase loop and step constants. Choose CPU/MPS only by a post-registration local throughput benchmark, as R1 did. Save raw per-seed results/checkpoints only under `artifacts/codex-retention-20260927/r2/seed31` and `seed32`; never overwrite an existing seed directory.

## Fixed marks and required report

The primary score is exact correctness at the model's **own stop**; fixed16, any-round and mean-round fields are report-only. Each seed must satisfy **A grids5 >=190/200 after A** and **B sums4 >=190/200 after B**. If either seed misses either mastery gate, R2 is **INCONCLUSIVE for mastered retention**, even if exact snapshot isolation holds; report every observed count. A crashed or incomplete seed is **INCOMPLETE**, never a PASS.

**PASS** requires both seeds valid and, on each seed after B: routed grids5 score equals its A snapshot score and loses **zero** of the A snapshot's previously correct 200 items; every old checkpoint tensor and its hash is unchanged; all-round predicted tokens and stop probabilities on the fixed first 16 grid panel items are bit-identical before/after B and after reload; alternating grid/sum/grid calls preserve outputs; an unknown task ID is rejected. The same-device reload score and per-item outcomes must agree exactly. **FAIL** means both seeds meet mastery but any required preservation or routing check fails. **Proved wrong for the scoped isolation mechanism:** with identical input, software and device, training only B changes even one old routed prediction/stop probability or corrupts A's saved checkpoint. This says nothing about task-agnostic or equal-total-size continual learning.

Report the newest mutable B model's grids5 score and itemwise lost/gained count against A as the paired overwrite control. If it does not forget, mark **baseline forgetting not reproduced**; a passing isolation check then demonstrates correctness of the serving mechanism but no empirical advantage on that seed. Report A/B mastery, all preservation checks, unknown-ID check, per-seed checkpoint bytes, total two-model parameters/storage, device, Torch version, machine, UTC start/end, wall time, PASSMARKS commit and software HEAD. Run the predeclared seeds regardless of the first seed's outcome. No result from R2 changes R1 or any prior sealed verdict.

## Launch gate

Parent commits `PASSMARKS.md` before launch and supplies the commit SHA. A valid later command has the form `python -B artifacts/codex-retention-20260927/r2/run_mastered.py --seed 31 --out artifacts/codex-retention-20260927/r2/seed31 --passmarks-sha <committed-SHA>` (likewise seed 32). This document does **not** authorize launch before that commit. No PC, cloud, watcher, spending, download, keys, or sealed TEST-ONLY data are involved.
