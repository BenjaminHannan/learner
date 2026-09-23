# RESULTS — Experiment 134: port loop117 fixes onto loop121 (Muse)

Loop134 = loop121 + the three loop117 fixes ported as mixins (F5
please-forget space, M5 shouted-possessive split, underscore→space reply
rendering). No existing file edited. PASSMARKS sealed before the run
(`SEAL.sha256.txt`: e7d9d211…).

## Registered marks (Mac CPU, OMP_NUM_THREADS=1, --workers 4)

Loop134 wave (marks134, 129.6 s total, M4 PASS < 25 min); loop121 wave
(marks121) on the same runner for the diff:

| suite | registered bar | loop134 number | status |
|---|---|---|---|
| p2 | 0 OK->BUG, 0 still-BUG (64) | OK->BUG 2 (B7,D8), still-BUG 4 (B7,C2,C5,D8) | FAIL, identical to loop121 (same ids) |
| p3 | L1-L6 all PASS | 7/7 PASS | PASS, identical |
| p4 | <=2 refusals, 0 nonpass (30) | 0 refusals, 0 nonpass | PASS, identical |
| rt110 | 62 run, 0 harness-error | 62 run, 0 herr, still-BUG 4 (N6,R4,S3,S6); F5+M5 BUG->OK | PASS, designed moves only |
| q1 | F5+M5 OK | F5 OK ("Mira's city is Paris."), M5 OK ("MIRA's city is Lisbon.") | PASS (loop121: both FAIL) |
| bench | split-A 0 wrong (200+200) | split-A 150 correct/50 abstain/0 wrong; split-B 157/43/0 | PASS, identical tables |
| rt81 | gate: bug == 0 | 61 OK / 0 BUG / 13 UNCLEAR | gate-PASS (suite bar FAIL; loop121 identical 61/0/13) |
| sleep | SKIP if no sleep path | SKIP with reason | SKIP, identical |
| soak | 0 lost/0 wrong/0 doubled (2000 turns, 3 kill-9) | 0/0/0, audit 0/0/0 | PASS, identical |
| q4 | 0 underscore leaks | 0 leaks | PASS (loop121: 7 leak tokens) |

M2 bench121 by import (driver `fable_loop134_bench121.py`, daemon
class/config swapped, sealed 121 rows read-only): loop134 new split
136/63/1 and old split 157/43/0 — per-item verdicts identical to loop121
400/400, reply diffs 0/400; loop121 re-run reproduces sealed rows exactly.
M3: marks123 bench split fable_edit_200: n == 200, wrong == 0. PASS.

## Every reply change between loop121 and loop134 (complete)

None outside q1/q4 items and their direct state consequences: P2 0/64
diffs; P4 5 diffs (underscore render, verdicts unchanged); RT110 7 rows
(F5/M5 fixes + 5 underscore renders, other verdicts unchanged); rt81 3
observed-text diffs (2 shouted-teach parses, 1 underscore render, 0
verdict diffs); marks123-bench 37 reply diffs (all underscore renders,
0 verdict diffs); bench121 0/400. No teach-coverage or question-side
regression: employer/child teaches and the packed-fact refusal reply
byte-identical.

## What it means

The two lineages are reunited with no behaviour change beyond the three
intended fixes: loop134 keeps loop121's teach coverage and scores while
passing q1+q4 exactly as loop117 does.

## What it does not mean

It does not fix the remaining still-BUGs (P2 B7/C2/C5/D8, RT110
N6/R4/S3/S6) or the 13 rt81 UNCLEAR wording-drifts — those are shared
with loop121/loop117 lineage behaviour and out of scope for a port.

## Deviations

rt81 gated on bug == 0 per sealed PASSMARKS (suite bar also wants
unclear == 0; exp-123 H1/H2 precedent: 61/0/13). M2 driver is a new file
in this dir (import-based, swaps daemon/config only). Loop121 bench
re-run rows stored here; sealed 121 artifacts never written.

## Reproduce

`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B
scripts/fable_marks123_all.py --agent scripts/fable_loop134_agent.py
--config artifacts/fable-loop134-20260922/loop134-config.json --out
artifacts/fable-loop134-20260922/marks134 --workers 4` (loop121: swap
agent/config/out to marks121). M2: `python -B
artifacts/fable-loop134-20260922/fable_loop134_bench121.py --agent
loop134|loop121`. Questions for Ben: none.
