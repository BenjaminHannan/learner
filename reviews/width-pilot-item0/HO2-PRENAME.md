# Second HO cell (HO2): seed and procedure named BEFORE generation (coordinator ruling Q50, 10-17)

Written and committed before any HO2 row is drawn.

- **Seed:** `HO2_SEED = 93703`. That is L5_EVAL_SEED (93702) + 1; no build in `domain/far/learn_probe.py` uses it.
- **Cell:** 420 rows, layout `(K)*(J)` on the L3 **training** kind pairs (`pair_split()`, asserted equal to `pair-split-l3.json`), drawn with the shipped `draw_joined(rng, train_pairs, '(K)*(J)', 420, 'HO2', 'l5b', exclude, seen, help_prompts)` and `rng = random.Random(93703)`.
- **Disjointness:** `seen` starts as every prompt in `train-rows-l5.jsonl` plus every prompt in `eval-rows-l5.jsonl` (all five cells: S5, S, HP, HO, HPO). `exclude` is the L5 build's own exclusion set.
  - Caveat: as in the verified L5 regeneration, `train-rows-mode.jsonl` and `train-rows-l4r1.jsonl` need the fleet parent and are empty here.
  - Those are earlier experiments' training files, not data for this pilot. Pilot parents train on the 200k-row skills build; the join phase trains on L5 rows only.
- **Frozen outputs (both hashes):**
  - HO1: the existing HO cell, sha256 `3aba6de17b8a2bb596414004fef2b2d673b0f740701642d703a167e883698b8e` (420 rows of `eval-rows-l5.jsonl`);
  - HO2: sha256 of `eval-rows-ho2.jsonl`, recorded in the next commit together with the file.
- **Use:** final checkpoint only, all runs, never a tuning target (spec §4).
- **Rule:** if the draw comes up short of 420, it is reported and **not** redrawn with another seed.
