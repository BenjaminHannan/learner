# Inner-state work for Think-3 (thread "Improve the thinking loop's inner state")

- `ARMS.md`: the proposed addendum arms with pass marks, the free CPU checks' results, and two implementation defaults.
- `research/A-H`: 2025-2026 literature sweeps (Haiku helpers); `F-factcheck.md` checks the key numbers against the papers.
- Free CPU checks on base K2-Horizon-3.7B (no GPU, no training; village validation shard 0 only):
  `python3 make_rows.py WORK` builds `WORK/vrows.json` and `WORK/ev_rows.json`; download IFM/K2-Horizon-3.7B to `WORK/k2`,
  set `D` at the top of `probe.py` / `probe2.py` to `WORK/`, then run them (about 2-4 min per row on 4 CPU cores, 11 GB RAM).
  Outputs: `probe_out.json` (12 rows), `probe2_out.json` (24 rows; the first 4 rows lack `top1pct_share`).
