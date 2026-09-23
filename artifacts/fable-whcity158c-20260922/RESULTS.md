# RESULTS — Exp 158c: wh-city question rewriter on loop158b (Muse)

One change only: `scripts/fable_loop158c_agent.py` subclasses the frozen
loop158b agent (`Loop158cEars(Loop158bEars)`). When the base returns
all-clarify, five closed shapes rewrite to 158b's "Where does X live?"
path: "What/Which city does X live in?", "What/Which city is X in?",
"What town does X live in?" (X = name or possessive chain, gated by
loop158b's own entity resolver). The four director look-alikes match no
shape. Questions never write (teach/correct/forget2 in the second pass
are discarded). No loop158b file was edited.

## Marks (all counts integer, every seed/case reported)

| mark | bar | result |
|---|---|---|
| T1 probe (46 cases: 22 shapes incl. 7 length-2 chains, 12 look-alikes, 12 other) | 22/22 exact, 24/24 byte-identical | 22/22 exact, 24/24 identical, 4.4 s |
| T2 writes/exactness | 0 question writes | 0 writes, 22/22 exact |
| G1 bench121 (4 splits, per-item vs loop158b rows) | 0 new wrong, every move listed | 0 moves, 0 new wrong (correct/abstain/wrong: 196/2/2, 150/50/0, 194/2/4, 198/2/0), 41.1 s |
| G2 marks123 (p2/p3/p4/rt110/q1/bench/rt81/sleep/soak+q4, per-case vs marks158b) | identical except predicted sleep filename | 0 moves, 1 allowed (sleep SKIP reason names new file), q4 leaks [] vs [], n_replies 481/481 |
| G3 redteam136/redteam143/sessions152 + cases150/cases139b/f1 | 0 new WRONG/junk writes, every move listed | 0 moves everywhere (rt136: 135 OK/3 MISSED/7 WRONG-WRITE; rt143: 106 OK/7 MISSED/11 WRONG-ANSWER; sessions 0 reply diffs; f1 45 OK + 1 pre-existing WRONG-WRITE on both arms), 7.2 s |
| G4 time | each run < 1500 s Mac CPU, OMP/MKL=1 | max ≈ 437 s (marks total); daemon accepts idle_seconds |

SCORE: PASS (T1/T2/G1–G4). All six ledger predictions TRUE.

## What it means

The two declining shapes now answer exactly ("What city does Sue live
in?" → "Sue's city is Leeds."), chains included, with zero behaviour
change anywhere else: bench, all nine marks suites, junk/redteam and
sessions are per-case identical to loop158b.

## What it does not mean

Not a general city-question fix: "What's ...", "Which town is ...",
and unknown-X shapes still clarify, and town shapes answer through the
city path ("Bob's city is Rome.") — inherited base behaviour, unchanged.

## Deviations

A previous agent sealed PASSMARKS (seal re-verified OK after all runs)
and finished probe/bench/redteam plus marks p2/p3/p4 before cutoff. I
ran only the remaining marks suites (rt110/q1/bench/rt81/sleep/soak)
one at a time with the stock runner, same agent/config/out dir, then
the sealed driver's own `compare()` (no sealed file touched). Base
rt81 `pass=false` (60 ok/0 bug/14 unclear) and p3 `pass=false` are
identical on both arms — 0 moves. No code edits after the seal; no
re-runs (no flakes seen).

## Reproduce (Mac CPU, offline)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix158c_probe.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix158c_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix158c_redteam.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix158c_marks.py
