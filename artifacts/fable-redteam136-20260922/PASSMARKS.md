# Exp 136 PASSMARKS (Muse) — sealed BEFORE the registered run

Target: loop129b (`scripts/fable_loop129b_agent.py` +
`artifacts/fable-fix129-20260922/loop129b-config.json`).
Cases: `cases136.json` (145 fresh cases, expectations frozen, sealed in
`SEAL.sha256.txt`). One message per case through a fresh daemon dir via
`fable_fix129_common.new_daemon129b` + mailbox `process_file`; stored facts
read via `fable_loop90_agent.notebook_triples`. Every case reported, never
averaged.

- M1 (completeness): 145/145 cases get a verdict in
  {OK, WRONG-WRITE, MISSED, HARNESS-ERROR}, with HARNESS-ERROR = 0.
- M2 (knowns reproduce): C124 WRONG-WRITE (officeholder junk), C125 MISSED
  (two-word possessive), C126 WRONG-WRITE (closing-quote value leak).
- M3 (diagnosis): every WRONG-WRITE case is assigned to a root-cause class,
  each class cites the responsible pattern (file:line) and one proposed
  single-change fix; classes ranked by normal-user likelihood.
- M4 (budget): whole sealed wave < 1500 s wall-clock, Mac CPU,
  `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`, `uv run --offline`.

Verdict rules (frozen): expect "nowrite" + empty store = OK, else
WRONG-WRITE; expect triple T + store == [T] = OK, empty = MISSED, else
WRONG-WRITE. A registered M2 MISS stays a MISS (never re-run into a pass).

Reproduce:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_redteam136_cases.py
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_redteam136_run.py
