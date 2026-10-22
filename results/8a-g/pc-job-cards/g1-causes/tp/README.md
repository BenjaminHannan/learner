# T-P package: self-found programs (3M s400)

Test T-P of `G1-OTHER-CAUSES-RANKED-2026-10-12.md` section 3 (cause 3: the calculator is used only by imitation). One change on G1's 3M B2:
on training rows with no parsed program, mode GEN and a canonical integer answer, the NOOP op target gets weight 0 and each update samples K = 8
programs per row from the model's own op/operand heads (temperature 1), runs them on the exact executor and trains on the shortest one that
reproduces the gold answer (NUM mode, answer = its last result slot, no GEN target). Rows with no hit keep their GEN target.

Files
- `ledger.py`: G1's `models/ledger.py` plus `self_prog=0` (K; 0 = exactly G1) and `self_prog_t=1.0` (stored only, no new module: 3,544,913 trained, every weight inits as G1's);
  `run(rep=1, sample_t=None)`; the pure `pick_hits()`; `Ledger.self_programs()`; aux `sp_cand`, `sp_hit`, `sp_len` (only with self_prog > 0).
- `8aTP-pc.txt`: queue (data line as WIDE, then `g8a: 8aTP-3M-s400 --rung 3M --seed 400 --arms B2 --b2-extra '{"eg_embed": true, "self_prog": 8}' --accum B2=4`).
  `--b2-extra` goes job.py -> `configs.sizes` -> `b2_cfg` (merged into the cfg) -> `train.py --cfg`; the size/band check counts the same 3,544,913; the pool key is `p10-rung30-s400-a64` (G1's, reused).
- `tpcheck.py`: CPU check (no EmbeddingGemma weights, no GPU). `TP CPU CHECK OK` at the end.
- `install_tp.ps1`: copies src-8ag to src-tp, swaps in ledger.py, runs tpcheck, writes `WORK\insert\46-tp.txt`. Deletes nothing, never touches G1's results, pools or checkpoints. Not parse-checked (no PowerShell here).
- `tp.template.md`: the card (marks verbatim, cost, readout).
- `tp_read.py`: read-only readout and verdict.

Install: copy this folder to the PC, run `install_tp.ps1` from it (PowerShell 5.1).

Marks (sealed): pass = four families >= 38.4% (G1 219/720 = 30.4%) AND pooled-5 >= 72.5 AND chain-5 >= 99; proved wrong = four families <= 32.4%; between -> s401.

Known limits (see the build report): candidate rows with small integer answers can be hit by chance programs; the share of candidate rows in the real pool is unmeasured here.
