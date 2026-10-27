# PASSMARKS — Exp 158c: wh-city question rewriter on loop158b (Muse)

Sealed before any registered run. Predictions P158c.1–6 are in
artifacts/fable-predictions-ledger.md (appended before the seal).
Base: loop158b (scripts/fable_loop158b_agent.py,
artifacts/fable-whrel158b-20260922/loop158b-config.json).
Agent: scripts/fable_loop158c_agent.py (Loop158cEars subclass of
Loop158bEars; no loop158b file edited).
Entity gate = loop158b's own `_ctx` / `_resolve_x` / `chain_split`
(imported, not copied). Fallback = FakeEars clarify
(scripts/fable_agent_loop.py:148) via AgentLoop._act
(scripts/fable_agent_loop.py:350) and the frozen loop138 decline rule
(scripts/fable_loop138_agent.py:81); the 158c stage runs before it and
never alters it.

## Marks

| mark | bar | prediction |
|---|---|---|
| T1 probe (scripts/fable_fix158c_probe.py, artifacts/fable-whcity158c-20260922/cases158c.json: 22 exact shapes (e1)–(e5) incl. 7 chains of length 2, both cases, with/without "?"; 12 look-alikes incl. the 4 director shapes; 12 other questions/teaches) | 22/22 exact, 24/24 byte-identical to loop158b | P158c.1: 46/46, 0.75 |
| T2 writes/exactness | 0 writes on every question; >= 95 % of must-cases exact | P158c.2: 0 question writes, 22/22, 0.80 |
| G1 bench (scripts/fable_fix158c_bench.py reuses artifacts/fable-agent138b-20260922/fable_loop138b_bench121.py by import; per-item vs fable_bench121_loop158b_*_rows.jsonl in artifacts/fable-whrel158b-20260922/, 4 splits) | 0 new wrong, every move listed | P158c.3: 0 moves, 0 new wrong, 0.70 |
| G2 marks123 (scripts/fable_fix158c_marks.py runs scripts/fable_marks123_all.py suites p2/p3/p4/rt110/q1/bench/rt81/sleep/soak+q4 into marks158c; per-case vs marks158b) | per-case identical except predicted sleep-reason agent filename | P158c.4: identical + filename line only, 0.65 (rt110/soak flake -> one open re-run, both reported) |
| G3 junk+redteam+sessions (scripts/fable_fix158c_redteam.py reuses sealed judges by import; vs loop158b frozen redteam136-loop158b.json, probe150-loop158b.json, f1-loop158b.json, probe139b-loop158b.json, redteam143-loop158b.json, sessions152-loop158b.json) | 0 new WRONG/WRONG-WRITE, 0 new junk writes, every move listed | P158c.5: 0 moves, 0.70 |
| G4 time | each run < 1500 s Mac CPU, OMP/MKL=1 | P158c.6: all < 1500 s, 0.90 |

Known base behaviour (not claimed): town shapes answer through the city
path ("What town does Bob live in?" -> "Bob's city is Rome."); unknown-X
shapes ("What city is Zzz in?") clarify on both arms; "What's ..." and
"Which town is ..." are outside the five closed shapes.

## Reproduce (Mac CPU, offline; only after this seal)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix158c_probe.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix158c_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix158c_redteam.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix158c_marks.py

A FAIL is recorded as FAIL with one diagnosis note; no silent re-runs.
Any code edit after the seal (including scorer/driver scripts) is
reported and the affected marks re-run in the open.
