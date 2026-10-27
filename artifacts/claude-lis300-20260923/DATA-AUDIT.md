# lis-300 training-data audit (2026-09-23)

Three Opus writers hand-wrote 1,500 turns with frames: w1 (casual statements), w2 (no-save turns and questions) and w3 (our/we, pronouns, corrections, short answers). Names start with A to M; the panel's names start with N to Z. Three more Opus agents relabelled each file blind, without seeing the frames. A row is kept only when both labels give the same saved facts, the same whose-ask, the same act and the same ask (`scripts/claude_lis300_agree.py`).

| file | rows | agreed | main disagreement |
|---|---|---|---|
| w1 | 500 | 465 | writes 27 (casual tells, "negate + correct" mixes, rambles) |
| w2 | 500 | 477 | act 15 (mostly "forget" requests, which the spec has no act for) |
| w3 | 500 | 450 | writes 30, act 16, whose 10 (our/we, pronouns, corrections) |
| total | 1,500 | 1,392 | |

Disagreeing rows are dropped, not adjudicated.

Practice-generator rows come from own-O0b: 3,000 per family across 9 families (27,000 rows). The binding family is dropped because its pronoun labels are wrong or rest on a guessed gender.

Built set: 32,012 training rows (27,000 O0b + 1,253 agreed Opus rows × 4) and 867 dev rows (428 O0b L2, 139 Opus, 300 fresh own-O0a2 turns). Training rows average 97 tokens (max 225), about 3.1M tokens per epoch.
