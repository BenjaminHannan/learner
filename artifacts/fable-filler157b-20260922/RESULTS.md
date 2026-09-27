# Exp 157b RESULTS — capitalised/stacked filler strip on loop157 (Muse)

## Result: PASS on all marks (T1, T2, G1, G2, G3, G4)

Loop157b (loop157 + one mixin: strip up to two leading capitalised fillers
only when the remainder parses as a complete base frame) fixes the director
probe failures with zero measured regressions against loop157.

## Marks table (integer counts, every seed/case reported, never averaged)

| mark | bar | got |
|---|---|---|
| T1 probe (scripts/fable_fix157b_probe.py, sealed cases157b.json, 60 cases) | 34/34 cap-filler == bare twin; 13/13 titles == loop157, 0 stripped writes; 13/13 garbage/correction == loop157 | 60/60 OK (34 cap, 13 title, 13 same157) PASS |
| T2 | >= 33/34 must-cases, 0 wrong writes | 34/34, 0 wrong writes PASS |
| G1 bench (scripts/fable_fix157b_bench.py, 600 items: new_121_4hop 200 + old_s2fresh_4hop 200 + edit200 200) | per-item verdicts AND replies identical to sealed loop157 rows, 0 new wrong | 0 verdict moves, 0 reply moves, 0 new wrong (split correct: 136/157/150; wrong: 1/0/0 identical to base) PASS |
| G2 marks123 (scripts/fable_marks123_all.py, --workers 4) | per-case verdict identical to sealed marks157; only allowed text diff: sleep SKIP reason filename | identical: p2 64/64, p4 30/30, rt110 62/62, q1 f5/m5 + replies, rt81 74/74, p3 all sub-marks + l5z2 200/200 + l4 3/3, bench 400/400 rows, soak counters, q4 leaks 7/7; sleep reason differs by filename only. ONE cosmetic diff: p3/l6 replied_before_kill counts (verdicts identical, pass true both arms; timing metadata, same class as the known 139c L6 note) PASS |
| G3 sessions (scripts/fable_fix157b_session152.py, 6 phone sessions) | every reply identical to sealed loop157 runs, 0 new WRONG, 0 new writes | 0 reply moves, 0 new wrong, 0 new writes (S4's 2 WRONG are base behaviour, identical) PASS |
| G4 time | each run < 1500 s Mac CPU, OMP=1 MKL=1, daemon idle_seconds | probe 4.8 s, bench 67.1 s, sessions 7.6 s, rt110 177.3 s, soak 150.5 s, marks suites (p2 11.8, p3 77.9, p4 4.9, q1 3.5, rt81 4.6, bench 50.9, sleep 0.0) PASS |

Step 1 (pre-seal): 157's title rule is scripts/fable_fix157_filler.py:67-101
(strip_one_filler157; capitalised block lines 92-96).

## What it means

Phone-style sentences ("Btw Tom's sister is Jo.", "Oh and Tom's mother is
Rita.", "So Tom's boss is Bob.", stacked "Oh and btw ...") now save and
answer exactly like their bare twins, while titles ("Hey Jude", "Also
Sprach Zarathustra", "So Far Away", "Well Played") and garbage/hedges
behave byte-identically to loop157.

## What it does not mean

It does not mean the assistant understands titles or fixes any other
refusal class: anything whose remainder is not already a complete base
frame ("X's R is V", "who is X's R?", other base question forms) behaves
exactly as on loop157, by construction of the parse gate.

## Deviations / post-seal notes (reported, per rules)

1. Prior agent was cut off mid-marks-run (rt110/soak/q4 missing). I resumed
in the open: ran ONLY the missing single suites (--suite rt110, --suite
soak) into the same out dir; completed suites were not re-run. q4-report
derived via the runner's own suite_q4/collect_replies. G2 compared with new
read-only helper scripts/fable_fix157b_markscompare.py (analysis only).
2. scripts/fable_loop157b_agent.py carries mtime 05:10, after the 04:27
seal. Contents match the sealed design (thin wrapper; rule code in
scripts/fable_fix157b_capfiller.py, mtime 04:19 pre-seal, untouched; sealed
config verified in use). No behaviour impact is measurable: 0 verdict moves
across probe, 600 bench items, sessions, and all marks suites. No rule
changes after the seal.
3. No FAILs, no silent re-runs, no rt110/soak flakes (both passed first
try, no re-run needed).

## Reproduce (from worktree root, after seal verify)

shasum -a 256 -c artifacts/fable-filler157b-20260922/SEAL.sha256.txt
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157b_probe.py --out artifacts/fable-filler157b-20260922/probe157b-loop157b.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157b_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop157b_agent.py --config artifacts/fable-filler157b-20260922/loop157b-config.json --out artifacts/fable-filler157b-20260922/marks157b --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157b_session152.py
