# RESULTS — Exp 164b: fresh registration of the 164 "about" feature on loop138h — PASS

Base: `scripts/fable_loop138h_agent.py` + `artifacts/fable-agent138h-20260922/loop138h-config.json`.
Agent: `scripts/fable_loop164b_agent.py` (new file; 138h/164 files read-only, never edited).
Resumed session: pilot files (agent, cases, drivers, pre-seal outputs) existed from a cut-off
agent; inspected, kept, wrote PASSMARKS.md + ledger P164b.1–7, sealed 7/7, re-ran everything.

## What changed (one change)
Read-only about-stage checked first in `hear()`: P0 summary + P1–P4
about-shapes over active taught facts (subject then value, max 8 + "and N
more.", unknown-X -> existing reply, 0 writes). Two sealed deltas: 138h USER
templates (Your/you) and about-me -> USER facts. All else delegates
byte-identical to 138h.

## Marks table (integer counts, every case reported, never averaged)

| mark | result |
|---|---|
| A1 probe (50 dialogues) | 50/50 OK (A 25, B 8, C 5, D 12); 0 writes on every about/summary turn; 1.7 s |
| A2 junk (rt136/cases150/f1/cases139b) | 145+57+46+101 cases, 0 moves, 0 new wrong/write |
| A2 rt143 (124) | 107 OK / 7 MISSED / 10 WRONG-ANSWER, 0 moves |
| A2 sessions152 (180 turns) | 166 OK / 14 UNHELPFUL, 0 moves, 0 new writes |
| bench 4x200 | 194/2/4, 198/2/0, 150/50/0, 196/3/1; 0 verdict/reply moves, 0 new wrong |
| A3 marks123 (11 reports) | 0 case-moves (1 diag-only log race rt110-U4); p3-l5z1/p4-1-nonpass/rt81 FAILs inherited byte-identical; 278.5 s |
| seal | 7/7 OK post-run; no post-seal edits |

Registered verdict: PASS (P164b.1–7 all TRUE). Max run 278.5 s < 1500 s.

## What it means
"Tell me about Kim." now lists Kim's stored facts instead of saying it knows
nothing, with zero change to anything else.

## What it does not mean
Only exact full-turn shapes fire; nearby phrasings still take the old path.

## Deviations
None. Repo-root notebook/ untouched. Outputs kept small; own reg-*.json scratch deleted.

## Questions for Ben
None.

## Reproduce
`shasum -a 256 -c artifacts/fable-about164b-20260922/SEAL.sha256.txt`, then the seven
commands in `artifacts/fable-about164b-20260922/PASSMARKS.md`, one suite at a time:
`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12
--with torch --with numpy python -B …`.
