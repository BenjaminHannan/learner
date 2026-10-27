# PASSMARKS — Exp 158b: relation-word question rewriter on loop138b (Muse)

Sealed before any registered run. Predictions P158b.1–6 are in
artifacts/fable-predictions-ledger.md (appended before the seal).
Base: loop138b (scripts/fable_loop138b_agent.py,
artifacts/fable-agent138b-20260922/loop138b-config.json).
Agent: scripts/fable_loop158b_agent.py (Loop158bEars subclass of
Loop138bEars; no loop138b file edited).
Relation tables = the loop's own notebook triple relation set
(scripts/fable_loop90_agent.py:101 notebook_triples), keys normalised by
FakeEars._relation (scripts/fable_agent_loop.py:151); the only static
table is PERSON_RELATIONS (scripts/fable_agent_loop.py:91).
Fallback = FakeEars clarify (scripts/fable_agent_loop.py:148) via
AgentLoop._act (scripts/fable_agent_loop.py:350) and the frozen loop138
decline rule (scripts/fable_loop138_agent.py:81); the 158b stage runs
before it and never alters it.

## Marks

| mark | bar | prediction |
|---|---|---|
| T1 probe (scripts/fable_fix158b_probe.py, artifacts/fable-whrel158b-20260922/cases158b.json: 40 exact shapes (a)–(d) incl. 1- and 2-hop X across color/birthday/age/city/job/school/team/hometown/home, both cases, with/without "?"; 12 unknown-X/relation; 12 look-alikes) | 40/40 exact, 24/24 byte-identical to loop138b | P158b.1: 64/64, 0.75 |
| T2 writes/exactness | 0 writes on every question; >= 95 % of must-cases exact | P158b.2: 0 writes, 40/40, 0.80 |
| G1 bench (scripts/fable_fix158b_bench.py reuses artifacts/fable-agent138b-20260922/fable_loop138b_bench121.py by import; per-item vs fable_bench121_loop138b_*_rows.jsonl, 4 splits) | 0 new wrong, every move listed | P158b.3: 0 moves, 0 new wrong, 0.70 |
| G2 marks123 (scripts/fable_fix158b_marks.py runs scripts/fable_marks123_all.py suites p2/p3/p4/rt110/q1/bench/rt81/sleep/soak+q4; per-case vs marks138b) | per-case identical except predicted sleep-reason agent filename | P158b.4: identical + filename line only, 0.65 (rt110 flake -> one open re-run, both reported) |
| G3 junk+redteam+sessions (scripts/fable_fix158b_redteam.py reuses sealed judges by import; vs loop138b frozen redteam136-loop138b.json, probe150-loop138b.json, f1-loop138b.json, probe139b-loop138b.json, redteam143-loop138b.json, sessions152-loop138b.json) | 0 new WRONG/WRONG-WRITE, 0 new junk writes, every move listed | P158b.5: 0 moves, 0.70 |
| G4 time | each run < 1500 s Mac CPU, OMP/MKL=1 | P158b.6: all < 1500 s, 0.90 |

Known base limits (not claimed): 2-hop chains through non-person
relations (e.g. "What is Tom's dog's color?") abstain on the base itself
("not someone I can look up"), so no pre-fallback rewriter can fix them;
(b)-shaped 2-hop ("What is the age of Tom's mother?") is pre-parsed by
the base into a wrong ask on both arms; "What's Ann's age?" (contraction)
fails on the base and is out of the four shapes.

## Reproduce (Mac CPU, offline; only after this seal)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix158b_probe.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix158b_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix158b_redteam.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix158b_marks.py

A FAIL is recorded as FAIL with one diagnosis note; no silent re-runs.
Any code edit after the seal (including scorer/driver scripts) is
reported and the affected marks re-run in the open.
