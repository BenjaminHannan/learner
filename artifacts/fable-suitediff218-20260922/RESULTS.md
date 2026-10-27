# Exp 218 RESULTS — SUITE-DIFF CLASSES + ANY BASE (Muse)

Tool: `scripts/fable_suitediff218.py` (new file; imports
`scripts/fable_suitediff.py` read-only, reuses its runners; 214 files
untouched). Seal `SEAL.sha256.txt` verified OK after all runs (no
post-seal edits). One-line usage future pieces will copy:
`python -B scripts/fable_suitediff218.py --agent <agent.py> --config <cfg> --base 138i --out <dir>`
(or `--base-dir <sealed agent folder>`).

## Marks table (integer counts)

| mark | bar | got | verdict |
|---|---|---|---|
| C1 classifier table | 12/12 | 12/12 (`--check-table`) | PASS |
| C2 plant rt136 | 6 moves: C002/C105/C118 lost OK, C075/C096/C121 reply-only | exactly that | PASS |
| C2 plant sessions152 | 0 moves | 0 | PASS |
| C2 GATE | NOT clean (lost OK 3) | NOT clean (lost OK 3) | PASS |
| C3 `--base 138i` rt136/rt143/sessions152 | 0 moves each | 0/0/0 | PASS |
| C3 `--base 138i` bench | 0 moves | 1 (s2fresh-173 correct→abstain) | FAIL |
| C3 `--base-dir` rt136/rt143/sessions152/bench | 0 moves, 0 skipped | 0/0/0/1 (bench132-188 correct→abstain), 0 skipped | FAIL |
| C3 GATE both ways | clean | clean both ways | PASS |
| C4 time | each C3 run < 900 s | 68.1 s, 102.9 s | PASS |

Registered verdict: **FAIL** (C3), with one diagnosis note (below). No
re-runs, no re-seal. C4 passes; every suite ran one at a time on Mac
CPU with OMP_NUM_THREADS=1 MKL_NUM_THREADS=1.

## Diagnosis note (the single C3 miss)

Both C3 arms surfaced exactly one bench move, a *different* item each
time (s2fresh-173, then bench132-188), each correct→abstain with
byte-identical teach replies to the sealed base row; the flip is on the
final question turn (base `ears_stage=loop138b-rewrite`, new run `none`).
An ad-hoc re-run of the s2fresh split gave 0 moves, and 10/10 isolated
probes of item 173 answered correctly: loop138i's question side is
nondeterministic run-to-run on 4-hop items despite a fresh daemon per
item. The harness behaved as designed — it caught a real reply move the
old reply-only bucket would also have caught, but now with verdict
context. Not a systematic regression (GATE clean both ways; frozen
suites 0 moves everywhere).

## Known tool limitation (found post-seal, not fixed — seal is sealed)

Bench verdicts (`correct/abstain/wrong`) are not OK-based, so a
verdict-changing bench move with no stored triples falls through
classes 1–6 to the `reply-only move` fallback, whose name understates a
verdict change. The move is still listed and counted (never silent);
only the label is weak. Suggested follow-up (new exp, not this one):
add an explicit `answer change` class before the fallback.

## What it means

The 218 classifier puts the director's plant where a merge reader can
see it: OK→MISSED save-losses are now `lost OK` (gate-blocking), pure
rewordings stay `reply-only move`, and `--base-dir` diffs any sealed
base (138j/139-ready). The plant reads `lost OK=3, GATE NOT clean`
instead of a harmless `reply-only=6`.

## What it does not mean

It does not prove loop138i is deterministic — C3 caught real
run-to-run flips on 4-hop bench items, so future merges must expect
occasional single-item bench noise and confirm it by the GATE + frozen
suites, not by demanding 0 moves.

## Deviations

None from the brief. Pilots ran before the seal; pilots' scratch dirs
deleted. No-tune sets never opened. Exact reproduce commands are the C2
and C3 commands above with `--out` under
`artifacts/fable-suitediff218-20260922/runs/`.
