# M0: old-skill re-scoring of the far checkpoints (2026-10-16, measurement only)

Nothing was trained. CPU greedy scoring through custom_io `evaluate` + `is_hit` (the `domain/harm.py` `in_dist_hits` path).
Pre-registration written before scoring: `PREREG-M0.md` (P1 parent = 1227 and P2 L13/L14 reproduce: both held).

- DEV: rebuilt with `python -m skills_curriculum.build --out OUT --train 200000 --dev-per-cell 40 --seed 1` from branch
  `claude/project-thread-y0sxwe`; all 7 files match `FULL-BUILD-MANIFEST-200k-seed1.json` (in_dist sha256 f975d9fb...).
  Big DEV: same command with `--dev-per-cell 200` (6,800 in_dist rows; same train.jsonl hash; the 1,360 rows are its per-family prefix).
- Checkpoints (`checkpoints.sha256`): parent = `claude/far-transfer-inputs:inputs/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt`;
  children = `claude/project-thread-yha868:results/far-transfer/learn/{L12-LA64,L12-LB,L13-LBsoft10,L14-LBnk30}/step_4000/checkpoint.pt`
  (L12 is QUARANTINED for far-transfer claims; used only as a forgetting specimen).
- `hits.json`: per checkpoint x split, the per-row hit string ('1'/'0' in DEV file order), n, exact, and sha256 of the id list.
  Keys `<ckpt>.<split>` for the 1,360-row splits (in_dist, frame, variant, answer, vocab, family) and `<ckpt>.big_in_dist` (6,800).
- `M0-analysis.txt`, `M0-big-analysis.txt`: paired tables (b, c, item SE, z), lost-set overlaps, family tables.
  NOTE: the "by #calc steps" table in M0-analysis.txt buckets by the text `steps` field and its p^k reading is WITHDRAWN
  (family-mix artifact; see FORGETTING-SOLVE-2026-10-16.md section 2).
- `trace/`: free-run call traces and the loss decomposition (overrun / overrun-from-0 / op / operand / readout), from the
  adversarial review; totals reproduce the hit counts exactly (parent 1227, L12-LB 451, L13 1221).
- `score_m0.py`, `score_dev.py`: the scoring scripts (paths are this session's; adapt).
