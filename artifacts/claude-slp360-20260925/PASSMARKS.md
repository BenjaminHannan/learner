# slp-360 pass marks (registered 2026-09-25, before any run)

Change (one): sleep's writes, and every `inferred` / `sleep-derived` row, go to a disposable scrap layer
(`<state_dir>/scrap360/scrap.jsonl`) instead of the main notebook (scripts/claude_slp360_scrap.py).
Twin: the same 0.1 base loop (292t, sleep_threshold 100000, one forced end-of-day sleep as in 336) without 360.
Card test, CPU, $0. World: the exp-104 sleep world (fable_sleep104_drive.build_turns, noise 0): 40 taught
facts, 20 grandmother questions, 15 fillers, then ONE forced sleep, then 5 new-people probes and 1 broken-chain
probe; then a restart from the same state dir and the 6 probes again. Seeds 1 and 2.

| Mark | Bar (each seed) |
|---|---|
| P360.1 derived rows in the MAIN notebook after sleep and after restart (arm P) | 0 |
| P360.2 main-notebook events written during the sleep tick (arm P) | 0 |
| P360.3 sleep still works (arm P): word installed; probes right | installed; probes right = twin's, and ≥ 4/5 |
| P360.4 wrong probe answers (arm P), before and after restart | 0 |
| P360.5 replies identical to the twin on every turn and probe | 80 + 6 + 6 of 92 identical |
| P360.6 taught facts intact (arm P) | 40/40 |
| P360.7 scrap layer holds sleep's report (arm P) | ≥ 1 sleep-derived row in scrap |
| P360.8 an `inferred` write from the thinking actor lands in scrap, not main (unit) | yes |

Report only: the twin's derived rows in main (expected ≥ 1, the 0.1 rule break this fixes).

Proved wrong if: any derived row or any sleep-written event lands in the main notebook, or any reply differs
from the twin.
