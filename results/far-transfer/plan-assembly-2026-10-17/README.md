# Plan-assembly bracket test: probe scripts and tables (Oct 17, 2026)

These are the $0 probes behind `domain/far/RESULTS-plan-assembly-bracket-2026-10-17.md`. Nothing was trained. They are drafts until the coordinator reviews them.

Layout the scripts expect, relative to the repo root:

- `ck/<run>/checkpoint.pt` and `scores.jsonl`: from `results/far-transfer/learn/<run>/` on branch `claude/launch-bound-solve`.
  The runs are `L13-LBsoft10` and `L14-LBnk30`; the sha256s are in that branch's MANIFEST.md.
- `inputs/far/{train-rows-l5,eval-rows-l5,sheet-probe}.jsonl`: from `inputs/far-transfer/` on branch `claude/far-transfer-inputs`.
- `out/`: copy these scripts there. The per-item dumps go to `out/items-<run>.jsonl`. They are about 1.5 MB each, deterministic, and not committed.

Steps:

1. Make the per-item dumps (about 5 min per run on 2 threads):
   `python -m domain.far.dump_items --ckpt ck/<run>/checkpoint.pt --scores ck/<run>/scores.jsonl --step 4000 --train-rows inputs/far/train-rows-l5.jsonl --eval-rows inputs/far/eval-rows-l5.jsonl --probe inputs/far/sheet-probe.jsonl --cells l5 --out out/items-<run>.jsonl`
   The hit counts must equal `scores.jsonl` at step 4000.
2. Run the probes:

| script | what it gives |
|---|---|
| `strata.py out/items-<run>.jsonl HO` | hit rate and role of the first wrong call by (steps, cells); reproduces 0/106 |
| `r0.py`, `ca.py`, `ca_err.py` | round-0 accuracy by K-piece shape, cell-arithmetic counts by layout, and the error classes of the cell-arithmetic `mul` call |
| `bracket.py --ckpt ... --items ... --tag L13` | the bracket test: teacher-forced per-round accuracy by role, the determinism check and the product check (`bracket-L13/L14.{txt,json}`, 29 s each) |
| `tf_join.py <run>`, `tf_caj.py <run>` | what the model writes at the join call and the cell-arithmetic calls under teacher forcing |
| `cf_join.py <run>` | the join-operator counterfactual `(K)*(J)` → `(K)+(J)` |
| `bracket_blind.py <run>` | single formulas `(c1+c2)*N` vs `c1+c2*N` |
