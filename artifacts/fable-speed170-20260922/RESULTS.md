# Exp 170 RESULTS — fast asks in the stacked agent

Base loop138d + one change: per-ask full-notebook scans (C1–C7) read the
incremental per-(subject, relation) index. No path, screen or rewriter
skipped or reordered. Seal 12/12 OK after all runs (no post-seal edits).

## Marks table (integers; every seed/case reported, never averaged)

| mark | bar | number | status |
|---|---|---|---|
| S1 M6 asks, 15k notebook | p50 < 50 ms, p99 < 200 ms, 25/25 identical | loop170 p50 28.45 ms, p99 64.35 ms (base p50 5760 ms); 0 reply diffs | PASS |
| S2 1000-turn replay, fresh + 15k | every reply + state identical | fresh 1000/1000, 15k 1000/1000, facts_sha + events equal both | PASS |
| S3 3000-turn 10-kill soak, seed 931 | exactly-once, K4 p99 <= 300 ms | K1/K2/K3/K4/K5 pass; 3000/3000 receipts clean; K4 p99 260.8 ms | PASS |
| G1 bench121 4 splits | 0 moves vs 138d, 0 new wrong vs 138b | 800 items: 194/4, 198/0, 150/50/0, 196/1; 0 moves, 0 new wrong | PASS |
| G2 marks123 all suites | per-case = 138d results | p2/p4/rt110/rt81 0 verdict/reply moves; p3/q1/bench/soak identical; sleep SKIP names new file only; l6 kill-timing counter only (below) | PASS |
| G3 redteam136/cases139b/redteam143/sessions152 | 0 new WRONG/WRONG-WRITE/junk vs 138b, moves listed | 0 moves vs 138d on all 4 suites (470 cases); 13 vs-138b moves all 138d-sealed inheritance (listed below), 0 new | PASS* |
| G4 time | every run < 25 min | S1 ~5.5, S2 ~17, G1 ~1, G3 ~4, G2 4.4, S3 2.7 min | PASS |

\*Deviation D1 (declared, not a rule change): the sealed G3 line said "0
moves" vs 138b, which even a null diff of 138d cannot meet (138d M4 sealed 7
WRONGs + improvements). Judged on the brief's regression bar — "0 NEW ...
every move predicted/listed" with 138d rows as baseline: 0 moves vs 138d,
all 13 vs-138b moves listed here. Ledger P170.6 scored FALSE on its literal
"0 moves" wording (forecast error, reported).

## G3 inherited moves (all byte-identical in 138d rows, 0 from this change)

redteam136: C124/C127/C129/C142 OK→WRONG-WRITE (inverted/shouted teaches),
C115 MISSED→OK (improvement); cases139b: C10/C21 OK→WRONG-WRITE (compound
inversions); redteam143: M3 OK→WRONG-ANSWER + J8/K9/O5/S4 WRONG-ANSWER→
MISSED/OK (improvements); sessions152: 36 moves, 0 new WRONG (the sealed
+36 OK gains). No new writes anywhere.

## Notes

- S1 deviation D2 (saves wall-clock only): arms boot on verbatim copies of
  the sealed 138d M6 doorway-built notebook instead of rebuilding (same FACT
  records); each arm in its own process so the 170 rebinding never touches
  the base arm. No flakes; no re-runs into passes.
- G2 l6 `replied_before_kill` counter (5 vs 9) is kill-timing volatile under
  load; verdicts (pass, 200 correct, 0 dupes) identical. rt110/p3 FAIL labels
  inherited from 138d per-case-identically.
- K4 p99 260.8 ms has modest margin over the 300 ms bar under load; growth
  with notebook size is now in teaches (index maintenance), not asks.
- Finished ~09:15 (past the 09:00 target; S2's 138d 15k arm alone took 15.8
  min on the loaded Mac). Deadline P170.10 FALSE; all other predictions in
  the ledger outcomes line.

## What it means

Asks are ~200× faster (5760 → 28 ms p50) with zero behaviour change across
2,159 S-replay turns, 800 bench items and all regression suites: the stack
now answers from the index at every leaf.

## What it does not mean

It does not fix 138d's M4 accept/answer boundary (inverted teaches,
ungrounded yes/no) — those are inherited byte-identically, still open.

## Questions for Ben

None — defaults taken (D1/D2 documented above).

## Reproduce (each < 25 min; `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`;
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`)

- `scripts/fable_fix170_speed.py --cases artifacts/fable-speed170-20260922/cases-s1-asks.json --src artifacts/fable-agent138d-20260922/work-speed2/nb138d --outdir artifacts/fable-speed170-20260922/s1`
- `scripts/fable_fix170_replay.py --agent loop170 --cases …/cases-s2-fresh.json --src empty …` (×2 arms ×2 notebooks)
- `scripts/fable_fix170_bench.py`; marks123_all.py with `--agent scripts/fable_loop170_agent.py`; `scripts/fable_fix170_soak.py`
