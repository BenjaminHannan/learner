# lis-312: our 1B reader plugged into 292t, scored on the sealed conversation benchmark F0

Written by the listener thread (Opus) on 2026-09-23, before any lis-312 run and before lis-301's result.

## The one change

The reader wrapper (`install_turn310`, from lis-310/311, read-only) is installed outermost on **292t**, the verified talking-layer join on 292 and the candidate main base. Nothing else changes. `scripts/claude_lis312_f0.py` runs the arms. It uses a fresh agent per dialog, runs each dialog once, and scores with `claude_convf0_score.py`'s own mechanical rules (imported).

| Arm | System |
|---|---|
| A | 292t alone (in-run baseline) |
| B | 292t + lis-300 reader, T = 0.995 (sealed lis-300 threshold) |
| C | 292t + lis-301 reader at lis-301's sealed THRESHOLD.txt (registered arm) |

Benchmark: `artifacts/claude-convbench-f0-20260923` (sealed; 40 dialogs, 286 turns: teach 84, ask 84, smalltalk 68, other 40, correct 10). It was written for the talking line and never used for training or tuning here. Its user turns are never printed.

## Marks (arm C vs arm A, same run)

| Mark | Bar |
|---|---|
| P312.1 unexpected-save turns (new triples on smalltalk / ask / other turns) | C ≤ A + 1 |
| P312.2 teach turns whose gold triple is stored | C ≥ A + 15 (of 84) |
| P312.3 clarify / not-understood replies (F0 markers) | C ≤ A − 15 (of 286) |
| P312.4 ask turns answered right | C ≥ A |

- **Report only:**
  - every count for arms A, B and C;
  - new triples on teach turns that are not the gold, listed as triples, so the listener thread can audit them as possible wrong saves;
  - smalltalk clarify counts;
  - ms median and max.
- **Proved wrong if** arm C's teach matches ≤ arm A's. That would mean the reader does not raise what Premonition understands in real conversation, whatever the panels say.
- **Expected limit (stated now):** the reader labels small talk CHAT and passes it down, so small-talk replies still come from 292t. A small-talk gap that stays open is the mouth's job, not a reader failure.

A CPU cloud smoke run of arm A, and of arm C with a fake always-CHAT reader, completed without errors on 2026-09-23. The router was stubbed, so its numbers are not results.
