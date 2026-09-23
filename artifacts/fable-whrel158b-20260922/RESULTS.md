# RESULTS — Exp 158b: relation-word question rewriter on loop138b (Muse, 2026-09-22)

Result first: 6 of 6 marks PASS. The one change (a pre-fallback ears
stage mapping "What <R> is <X>?", "What is the <R> of <X>?", "<X>'s <R>?"
and When/How-old/Where shapes onto "What is <X>'s <R>?", base run
unchanged) fixes all 40 sealed must-cases with 0 writes, and moves
nothing anywhere else: bench 800 items, all marks123 suites, all junk /
redteam / session cases per-item identical to loop138b's frozen results.

## Marks (every seed/case reported)

| mark | bar | got | verdict |
|---|---|---|---|
| T1 probe (64 cases: 40 exact + 24 identical) | 40/40 exact, 24/24 identical | must 40/40, identical 24/24, fails [] (7.6 s) | PASS |
| T2 writes/exactness | 0 writes; >= 95 % exact | 0 writes on all 64 questions; 40/40 exact | PASS |
| G1 bench (4 x 200) | 0 new wrong, moves listed | new_121 194/2/4, s2fresh 198/2/0, edit200 150/50/0, bench132 196/2/2; 0 moves, 0 new wrong (79.0 s) | PASS |
| G2 marks123 | per-case = marks138b except predicted sleep line | 0 verdict/reply moves; 1 allowed (sleep SKIP reason names fable_loop158b_agent.py); p3 FAIL + rt81 FAIL labels inherited byte-identical; q4 leaks [] (481/481 replies); rt110 no flake, no re-run needed (1128.1 s total; max suite rt110 588.1 s) | PASS |
| G3 junk+redteam+sessions | 0 new WRONG/WW, moves listed | rt136 135 OK/7 WW/3 MISSED; cases150 57/57; f1 45 OK + t14-only write; cases139b 101/101; rt143 106 OK/7 MISSED/11 WRONG; sessions 0 moves, 0 reply diffs (20.9 s) | PASS |
| G4 time | each run < 1500 s | 7.6 / 79.0 / 20.9 / 1128.1 s | PASS |

Ledger P158b.1–6: all TRUE (6/6). No code edit after the seal
(`shasum -c SEAL.sha256.txt`: all 8 OK); no deviations; no FAILs, no
re-runs. Mac CPU, offline, OMP/MKL=1, every seed/case reported.

## What it means

Relation-word questions ("What color is Rex?", "When is Ann's
birthday?", "How old is Tom's mother?", "Where does Sue live?",
"Tom's mother's birthday?") now answer exactly through the frozen
base, while unknown entities/relations and look-alikes ("What color is
the sky?", "What time is it?", "How old are you?") behave byte-for-byte
as loop138b. The rewrite only fires on base clarifies, only for taught
relations with resolving entity chains, and only keeps ask results, so
questions still never write.

## What it does not mean

Not every director-probe shape is fixed: 2-hop chains through
non-person relations ("What color is Tom's dog?") abstain inside the
base reasoner itself ("not someone I can look up"), (b)-shaped 2-hop
("What is the age of Tom's mother?") is pre-parsed by the base on both
arms, and the "What's Ann's age?" contraction is outside the four
shapes — all verified live on loop138b and documented, not claimed.

Reproduce: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run
--offline --no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_fix158b_probe.py` (then _bench, _redteam, _marks).
Questions for Ben: none.
