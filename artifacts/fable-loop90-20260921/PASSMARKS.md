# Exp 90 pass marks — INTEGRATED loop (sealed before the registered wave)

Marks Z1..Z5. Every seed/case reported, never averaged. A registered FAIL is
recorded as FAIL, never re-run into a pass. Claims never exceed evidence.

- Z1: 60-turn acceptance file `data/open/turns84/turns.jsonl` through the
  Loop90 mailbox (Loop90Daemon): 0 wrong writes AND 60/60 turn statuses match
  the contract (per-turn records scored from the daemon log).
- Z2: Fable-Edit-200 English arm through the loop notebook (bench73 ears over
  the loop's notebook, Reasoner77): 200/200 items in their expected cell
  (correct / abstain_ok), 0 WRONG, 0 WRITE_FAULT, 0 pending stalls.
- Z3: 69 red-team core cases + 56 web cases re-run by import (output to the
  exp-90 dir): verdicts identical to the sealed baselines (67: 64 OK / 3 BUG /
  2 UNCLEAR; 79: 53 OK / 1 BUG / 2 UNCLEAR, same ids), 0 new BUGs, 0 changed
  verdicts; plus 8/8 doctrinal checks against the actual loop90
  notebook/thinker pass.
- Z4: daemon74 selftest D2 (kill -9 mid-write + restart) against the Loop90
  daemon, seeds 1/2/3 reported separately: per seed correct == 200,
  wrong == 0, dupes == 0, chain_ok-or-torn_reported.
- Z5: `--config` JSON documents all 6 plug points (ears, notebook, reasoner,
  mouth, thinker, sleeper) each with its current stand-in and the file that
  will replace it; a loop built from that file answers the smoke turn and
  satisfies every AgentLoop Protocol.

Environment: Mac CPU, offline, OMP_NUM_THREADS=1 MKL_NUM_THREADS=1,
`uv run --offline --no-project --python 3.12 --with torch --with numpy
python -B scripts/fable_loop90_marks.py --mark all`.
tau-hat is read at run time from
`artifacts/fable-abstain76-20260921/ltt_summary.json` (tape 0.088756), never
hard-coded.
