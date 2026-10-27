# PASSMARKS — Experiment 142: port exp-128's speed fix onto loop134 (2026-09-22)

Port, not new science. New files only (prefix-owned, additive):
`scripts/fable_perf142_index.py` (128's index as mixins stacking on loop134:
index-backed "?" router, N-hop composer, compound-guard walk, loop121
teach-action; 128's notebook/reasoner/save/bookkeeping pieces reused by
import), `scripts/fable_loop142_agent.py` (loop142 = loop134 + mixins, with
`--daemon` entry), `scripts/fable_perf142_diag.py` (unregistered profile),
`scripts/fable_perf142_c1.py` (S1), `scripts/fable_perf142_c2.py` (S2),
`scripts/fable_perf142_bench121.py` (S4 driver). No existing file is edited.

Unregistered pre-seal evidence (not registered): 12-shape smoke + 400
seed-93 turns + multi-hop/forget/shouted shapes reply-identical loop142 vs
loop134; `diag134.json` profiles loop134 with 128's diag approach and names
every O(n)-per-turn scan with file:line (T1–T6 in
`scripts/fable_perf142_index.py`).

Registered runs (Mac CPU, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch
--with numpy python -B ...`):
  scripts/fable_perf142_c1.py --agent loop142 --out DIR/c1-142.json
  scripts/fable_perf142_c1.py --agent loop134 --out DIR/c1-134.json
  scripts/fable_perf142_c2.py --out DIR/c2.json
  scripts/fable_marks123_all.py --agent scripts/fable_loop142_agent.py
    --config artifacts/fable-perf142-20260922/loop142-config.json
    --out artifacts/fable-perf142-20260922/marks142 --workers 4
  same runner with --agent scripts/fable_loop134_agent.py
    --config artifacts/fable-loop134-20260922/loop134-config.json
    --out artifacts/fable-perf142-20260922/marks134 --workers 4
  scripts/fable_perf142_bench121.py --agent loop142  # then --agent loop134

| Mark | Pass condition |
|---|---|
| S1 per-turn CPU | process_time p50 at 15k facts ≤ 1.5× the 1k value for teach / correct / ask on loop142 (25 samples/kind; loop134 ratios reported too) |
| S2 identity | 5,000-turn reply byte-identity loop142 vs loop134 (128's C2 pattern, loop134 lineage): 5000/5000 |
| S3 marks | `fable_marks123_all.py --workers 4` verdicts identical loop142 vs loop134 on all suites (both waves run into this dir) |
| S4 bench121 | new + old splits per-item verdicts identical to loop134 (`artifacts/fable-loop134-20260922/` rows) |
| S5 time | S1+S2+S3+S4 registered wall-clock < 30 min Mac CPU total |

A registered FAIL is recorded as FAIL, never re-run into a pass. If S1 fails
on the first registered attempt, that FAIL stands; index coverage may then be
completed and re-run once, reported separately as unregistered. Every
seed/case is reported, never averaged. Claims never exceed evidence.
