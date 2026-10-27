# Hypothesis queue (ranked; full cards with sources in notes.md section 2)

Rules for every card: one change; shared code paths so plain gets any change it can use; no maze-specific hand-written
priors (so no dihedral augmentation: it tells the net a fact about mazes the designer knows); no kind labels.
Status: untried / trial id / kept / discarded / retired.

| id | card | phase | arms | source | status |
|---|---|---|---|---|---|
| H1 | Full-budget loss: 0.99 x loss after 16 rounds (gradient through all 16) + 0.01 x current random-round loss | maze | loop | Bansal 2202.05826 Alg.1 (mazes wanted alpha 0.01) | t1 discard (-0.044 seed 0; ahead at 4k-32k, fell at 64k 0.41 vs 0.715, 11x11 0.23 vs 0.50; 3.4x compute) |
| H2 | Deep supervision with carried state: several detached supervision steps per handed batch | maze | loop | TRM 2510.04871, HRM 2506.21734 | t3 KEPT (+0.106 screen, +0.110 fresh seeds; 64k: 0.955-0.975 vs 0.715; 2.5x compute) |
| H3 | Carry over only practised attention (fresh MLPs + embeddings) | maze init | both | Shinnick 2505.22308 (attn-only 99.0 vs full 18.8) | untried |
| H4 | LP-FT: train embeddings + head + stop head first, then everything at lr/10 | maze | both | Kumar 2202.10054 | untried |
| H5 | New maze tokens start at the mean of practised token rows | maze init | both | Hewitt 2021 note (via notes) | untried |
| H6 | EMA of weights (decay ~0.99 for ~1k steps) used for answering | maze | both | TRM (no EMA 79.9 vs 87.4) | untried |
| H7 | Label smoothing 0.3 on the maze loss | maze | both | DART 2609.05988 | untried |
| H8 | Practise less (lower practice lr or shorter schedule) | practice | both | Hu 2502.19249 (optimal pre-pretraining length) | untried |
| H9 | Weight decay toward the practised weights (L2-SP) instead of toward zero | maze | both | L2-SP (Li et al. 2018; not read, mark suggested) | untried |
| H10 | Shrink-and-perturb practised weights before mazes (x0.8 + small noise) | maze init | both | Ash & Adams 2020 (not read, mark suggested) | untried |
| H11 | Higher maze-phase lr (tune: 2e-3) / lower (5e-4) | maze | both | tune | t2 lr 2e-3 discard (-0.041 seed 0; slower to 32k, better at 64k 0.84 vs 0.715) |
| H12 | Train with 1-24 rounds in the maze phase (longer paths need more rounds) | maze | loop | Bansal (m = 30 on mazes) | untried |
| H13 | Stop head off in maze training (halt weight 0), fixed 32 rounds at answer time | maze | loop | TRM finding that ACT extras hurt; simplify | t4 KEPT as simplify: drop stop-head loss in maze deep supervision (+0.045 screen, +0.054 fresh seeds) |
| H14 | Practice with the full-budget loss too (H1 applied to practice) | practice | loop | Bansal | untried |
| H15 | Carry over attention + MLP of block 1 only / block 2 only (which layer transfers) | maze init | both | Shinnick (MLP-only sometimes helps) | untried |
| H16 | Round-count curriculum in practice (rounds grow with training) so the loop learns an iterative procedure | practice | loop | Deep Thinking (suggested) | untried |
| R1 | Dihedral augmentation of handed mazes | - | - | TRM | retired: designer prior |
