# Stiffness test v1: has the skills-trained core lost the ability to learn new skills?

Written 2026-10-04 14:10 UTC, before any training. Fast lane (exploratory, simple held-out split). Idea source: J. F. Hernandez Garcia, *Selective Reinitialization Algorithms for Preventing Plasticity Loss*, PhD thesis, Alberta 2026 (plain summary: https://claude.ai/artifact/1Ltwx44nCCx5DeW7LsLJ75).

## Question
All skills runs stall at 65-72/100. The thesis shows networks trained on a long, changing stream lose plasticity (they learn new things more slowly than a fresh copy). Our skills runs are that setup: a trained parent, then 50,000 rows easy-to-hard. Test: does the skills-trained core learn two never-seen skills more slowly than the same core before skills training?

## Arms (one change: the starting checkpoint)
- **A** = skills main2 checkpoint (copy path, constant lr, in_dist 72): `<PKG>/artifacts/skills/main2/final-checkpoint.pt` (60.7 MB, update counter 55120, loaded with `--parent-path`; the file is only read).
- **B** = the pinned seed-0 parent that main2 started from (the script's default parent; no `--parent-path`).
Everything else identical: frozen LFM, contextual reader features, `--copy-path`, constant lr 1e-3, each arm continues its own Adam state, batch 1, same rows in the same order.

## Data (committed here, built by `scripts/cap256_launch/make_stiffness_data_v1.py` from PR #32 @ 57c45293f)
- Families `clock_date` and `string_transform`: held-out families of the curriculum, so neither A nor B trained on them.
- `data/seed{1..6}/train.jsonl`: 4000 practice rows per seed (2000 per family, shuffled), different rows per seed.
- `data/seed{s}/dev/in_dist.jsonl`: the same fixed 200 test rows (100 per family) for every seed. No test prompt is in any practice set or in the curriculum's dev/family file (checked: 0 overlaps).

## Run (12 runs, interleaved A1 B1 A2 B2 ... A6 B6; ~15 min each, ~3 h total; no checkpoints written)
```
python scripts/cap256_launch/skills_pretrain_v1.py --root <PKG> --data <REPO>/artifacts/stiffness-test-v1/data/seed<s> --out artifacts/stiffness/A<s> --updates 4000 --eval-every 1000 --dev-n 200 --minutes 40 --copy-path --eval-at-start --no-checkpoint --parent-path <PKG>/artifacts/skills/main2/final-checkpoint.pt
python scripts/cap256_launch/skills_pretrain_v1.py --root <PKG> --data <REPO>/artifacts/stiffness-test-v1/data/seed<s> --out artifacts/stiffness/B<s> --updates 4000 --eval-every 1000 --dev-n 200 --minutes 40 --copy-path --eval-at-start --no-checkpoint
```
`<PKG>` = the same `--root` used for skmain2. The script holds `C:\Users\benja\GPU-BUSY.txt` itself and refuses to start if it exists, so start only after the English queue has finished and released it. Then: `python scripts/cap256_launch/score_stiffness_v1.py <PKG>`.

## Marks (fixed now)
Score = exact-match accuracy on the 200 test rows after 4000 updates. D = A - B in points, per seed.
- **STIFF**: mean D <= -5 and A behind B on at least 5 of 6 seeds. Then Test 2 (selective weight reinitialization inside the skills run) is worth running.
- **NOT STIFF**: mean D >= 0. The 72 stall has another cause; replanting is parked until the continual-learning (Minecraft / sleep) work.
- **INCONCLUSIVE**: anything in between.
- **VOID**: both arms average under 10% (the skills were not learnable in 4000 updates); no claim either way.
Reported, no mark: accuracy at update 0 (transfer before practice), the curve at 1k/2k/3k, and gain = final - start per arm.

Reading: A has 50,000 more updates of related practice, so if anything it should start ahead. A finishing behind B is therefore strong evidence of stiffness; A ahead does not rule out mild stiffness hidden by transfer.

## Limits
One parent seed (0); two families; 4000 updates; batch-1 Adam. Says nothing about the vision or village models.
