# PASSMARKS — Exp 95 diagnosis of the registered exp-47 FAIL (rung-2 ears)

Written and hashed BEFORE any exp-95 model run. Diagnose only: no retraining,
no edits to any exp-47 file (sealed). All inference is read-only on the Mac CPU.

Date: 2026-09-22 · artifact dir: `artifacts/fable-diag95-20260921/`
Checkpoints: `artifacts/fable-ears47-20260921/runs/c-470{1,2,3}/ear.pt` (read-only).
Snapshot: `/Users/ben-hannan/.cache/huggingface/hub/models--allenai--scibert_scivocab_uncased/snapshots/24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1`
Panels: `artifacts/fable-ears47-20260921/panels/*.json` (read-only).

## 1. Registered analysis plan (fixed)

- D95-WEB: count pool composition WITHOUT rebuilding the pool: (a) synth pool
  family draw rule from `fable_ears47_data.py` (`POOL_SEED 47100`, `_pick_family`
  over train frames + 10% hearsay augmentation of STATE rows); (b) WebRED train
  rows reachable (81,517 − 614 dropped = 80,903) + 60,000 synth = 140,903;
  (c) wpos relation classes vs train classes (direct JSON count, no model);
  (d) CPU inference on wpos rows 1–10 only: per-seed top act/rel/conf.
- D95-EXEC: CPU inference on ALL rows of cal, t_seen, t_new, t_far, t_trap,
  t_hard, wneg, wpos, wclosed, wnewrel × 3 seeds (batch 64, `use_temp=True`,
  sealed scorer decode/verdict functions imported read-only). Histogram bins
  (ensemble conf, fixed): [0,.3) [.3,.5) [.5,.65) [.65,.75) [.75,.85)
  [.85,.8766) [.8766,1] for SEEN/NEW STATE-gold rows not EXECUTEd.
  Per-seed disagreement = fraction of those rows where the 3 raw frames are
  not identical. LTT candidate grid (exp-76 style, CAL only): candidate =
  ensemble verdict EXECUTE at tau=0 (all brakes except confidence pass, 3-way
  agree); G=15 acceptance counts linspace(max(114,N_cand), N_cand, 15) — if
  N_cand < 114, grid = single point N_cand and NO certificate is claimed;
  alpha=0.02, delta=0.10 pooled, fixed-sequence most→least conservative, exact
  binomial tail P(X<=k|m,alpha)<=delta; tau-hat = last accepted tau. Count new
  silent wrong writes at tau-hat on every test panel (integer each, per panel).
- D95-SAFE: the 2 trap rows (t_trap #259, #751): per-seed frame/conf/ok4/ok5/
  forced_echo + flags; why brake 4 (leftover-[UNK]) and brake 5 (validator)
  did not fire (code-path reading, no edits).
- D95-TAU: per-seed tau0 items (which CAL rows set the worst wrong-write conf
  per seed + ensemble); ECE per seed on CAL write-candidates, 10 equal-width
  bins over ensemble... no — per-seed conf vs frame-correct, 10 equal-width
  bins, reported per seed (never averaged); temps quoted from meta.json.
- D95-RANK: rank single changes for a registered 47b by expected effect on the
  failing marks (SAFE, SEEN-exec, NEW-exec, WEB) with SAFE held at 0. Rank by
  evidence from D95-WEB/EXEC/SAFE/TAU only; no new training.

## 2. Predictions (P95.1–P95.6, appended to ledger before the run)

See ledger block. Falsified by the integer counts in `fable_diag95_report.json`.

## 3. Reproduce

`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B scripts/fable_diag95_infer.py
--out artifacts/fable-diag95-20260921/fable_diag95_report.json`
then `... python -B scripts/fable_diag95_analyze.py` (numpy only) for tables.
