# Fix screen v1: which single change lets the model fit what it practises?

Written 2026-10-04 20:20 UTC, before any run. Fast lane (exploratory). Follows plateau diagnosis v1 (`../plateau-diag-v1/results/RESULT-v1.md`): main2 fits only 48% of 2,000 rows it practised 6 times; fair scaling (PR #18) showed a 4x core does not fit better.

## Setup (same as the diagnosis F arms, cut to 3 passes)
Start main2 (copy path). Worst-8 families: chain_ops, state_update, cipher_map, chain_story2, var_chain, seq_cycle, fewshot_number_rule, group_induct. 2,000 fixed rows (seeds 1-3, identical draws to F1-F3), 3 passes = 6,000 updates, batch 1. Scored at update 6,000 on 320 of the training rows ("fit") and the 320 held-out in_dist rows of the same families.

**Baseline** = F1-F3 of the diagnosis at update 6,000 (same seeds, same rows, same order, same code path): fit 50.6 / 52.5 / 46.3 (mean 49.8), held-out 34.4 / 37.2 / 36.9 (mean 36.1).

## Arms (one change each)
- **W (wider reader):** `--reader-hidden 256`. The reader's 2048->32->256 pipe becomes 2048->256->256. Function-preserving: old units copied, new units feed zero weights, so the start is exactly main2. Widened layers start fresh Adam state.
- **L (more rounds):** `--rounds 8` (shared weights, parent used 4).
- **O (calmer optimiser):** `--lr-mult 0.3` (lr 3e-4 instead of 1e-3).
- **P (allptr exit), added 20:24 UTC before it ran, at the coordinator's request:** `--pointer`. Adds the cloud recipe's 8 pointer vectors (Linear 256->8 on the core's final state, softmax over prompt positions, value = that prompt token's LM input embedding) between the 8 pooled vectors and the prompt embeddings the copy path already appends. New parameters, so its start is not exactly main2 (its update-0 score is reported). Runs on a second box.
Nothing else in the exit (StatePrefix, copy path) changes: other threads own talker changes.

## Marks (fixed now)
- An arm **FIXES FIT** if its mean fit is >= +15 points over baseline (>= 64.8) and all 3 seeds beat their paired baseline seed.
- It **HELPS** if mean fit gain is +5 to +15 with all 3 seeds positive.
- Otherwise **NO EFFECT** (or **HURTS** if mean fit gain <= -5).
- Held-out gain is reported for each arm; an arm that fixes fit but loses >= 5 held-out points is flagged MEMORISES.
- Wrong if: the winning arm's 6-seed confirmation (next step, its own marks written before it runs) does not reproduce the gain.

## Run
One Vast RTX 5090, 9 runs in waves of 5 and 4. Results copied back and sha256-checked before the box is destroyed. Scored locally from the copied SKILLS-RESULT.json files.
