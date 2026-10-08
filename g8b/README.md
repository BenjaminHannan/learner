# 8b: does B2 grow with an EmbeddingGemma input? (2026-10-08)

Spec, diagnosis and marks (written before any 8b run): `design/8b-gemma-growth-2026-10-08.md`.

- `analysis/free_ablations.py`: the diagnosis tables from the saved 8a results (no new runs); output in `analysis/free_ablations.txt`.
- `overlay/custom_io/g8a/caps.py`: the 8a caps with one fix: `apply()` imports the Ledger (and the other lazily built modules) before
  patching them. Without it every 8a B2 run kept 9 register tokens and cut GEN targets to 8 letters (design doc, addendum B).
- `overlay/custom_io/models/ledger.py`: the 8a Ledger plus `gen_ar` (Fix 3: the thinker writes GEN answers letter by letter with its own
  blocks). `gen_ar=False` is the 8a Ledger exactly (`tests/test_gen_ar.py`, check 8).
- `tests/test_gen_ar.py`: 8 CPU checks of `gen_ar` (parameter parity, loss and gradient, causality, teacher forcing = greedy decoding,
  every lesion, and identity with the pinned Ledger when off). Run from a checkout of the pinned code with the overlay copied in.
- `analysis/screen_readout.py`: the screen's go / stop readout, mechanically from the pre-registered rules.
- `overlay/custom_io/g8a/configs.py`: `train_args` checks the size band on the thinker's shape too (the first 3M launch, on dba17e6, refused
  to start: the adapter put EGE-3M 7.3% over the 3M band). The EmbeddingGemma adapter is counted and reported, not banded.
- `overlay/custom_io/g8a/job.py`: the 8a job (build branch `claude/project-thread-f1to6a` at 50ee171632) with one change: `eg_embed` is
  allowed for B2-only jobs, the size band is checked on the thinker's shape, and the trained count includes the 198,400-param adapter.
- `box-g8b.sh`: the 8a probe box script plus the overlay, EmbeddingGemma 2 (transformers 5.19.0, pinned revision, probe check),
  boolean B2X values, and no checkpoint printing by default.
- `vast8b.py`: `custom_io/box/vast.py` pointed at `box-g8b.sh` and `results/8b`.

Launch (one rung x seed per box, B2 arm only):
`python g8b/vast8b.py create --offer ID --label 8b-EGA36-3M-s400 --env "OVL=<commit> RUNG=3M SEED=400 ARMS=B2 B2X=eg_embed:true,gen_ar:true MAXH=6 JOBH=5.5 DPH=0.6"`
(EGE36: `B2X=eg_embed:true`), then `collect --id ID --out results/8b/EGA36` and `destroy --id ID`.
