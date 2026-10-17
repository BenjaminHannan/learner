# Item 0(h) validation slice (VAL): seed and procedure named BEFORE generation (2026-10-17)

The playbook's Item 0(h) asks for "a validation slice disjoint from the 420-item HO cell (generated, hashed, named) — the only permitted tuning/selection target for Item 6". This file is committed before any VAL row is drawn. The slice is a **draft for the coordinator to freeze**, made with the procedure approved for HO2 (ruling Q50).

- **Seed:** `VAL_SEED = 93704` (HO2_SEED + 1; no build uses it).
- **Cell:** 420 rows, layout `(K)*(J)` on the L3 training pairs, drawn with the shipped `draw_joined(rng, train_pairs, '(K)*(J)', 420, 'VAL', 'l5v', exclude, seen, help_prompts)` and `rng = random.Random(93704)`.
- **Disjointness:** `seen` starts as every prompt in `train-rows-l5.jsonl`, `eval-rows-l5.jsonl` (all five cells) and `eval-rows-ho2.jsonl`. `exclude` is as for HO2.
- **Rules:** no redraw if short; the hash is recorded in the next commit with the file; never scored against HO.
