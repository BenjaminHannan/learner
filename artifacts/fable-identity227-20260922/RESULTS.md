# Exp 227 RESULTS — questions about the assistant get an answer about the assistant

Problem (director-verified on loop138i, fresh notebook): "What is your name?"
and "Who made you?" both got the user-name reply "You never told me your
name, so I do not know it." — an answer about the user to a question about
the assistant. One change: a fixed identity sheet
(scripts/fable_identity227.py) served inside the notebook-miss branch when a
"?" turn has a second-person word and exactly matches a sealed template (38
templates, scripts/fable_identity227_templates.json). Nothing else changes;
notebook answers always win; the gate never writes.

## Marks (all counts are exact per-seed/per-case rows, never averaged)

| mark | result |
|---|---|
| M1 identity sheet (36 cases, 6/intent, 12 taught-first) | 36/36 sheet answer, 0 question-turn writes — PASS |
| M2 byte-identical to 138i (32 cases w/ and w/o taught name) | 32/32 reply + facts identical — PASS |
| M3 suitediff vs 138i rt136 / rt143 / sessions152 / bench | 0 moves everywhere (rt143 124 rows; bench 4 splits, 0 new wrong) — PASS |
| M4 sleep smoke 227 vs 138i | identical (sleeps=1 installed=1 probes=5/5 wrong=0 taught=50/50 ow=0 broken=abstain) — PASS |
| M5 0 new wrong writes (marks123 0 moves; bench 0 new wrong) | PASS |

Registered verdict: PASS. Seal 9/9 OK post-runs; no post-seal edits. Slowest
registered run 96.7 s (bench), Mac CPU, OMP/MKL=1, one suite at a time.

Census note: "What is my name?"/"Do you know my name?" still hit the notebook
namecheck after teaching; "Do you remember my name?" keeps today's D8 route
(exp 219's piece). Fictional names only throughout.

What it means: identity questions now get short honest answers, and nothing
else moved — every frozen suite is byte-identical to the base.
What it does not mean: the assistant still has no name, age, or home, and it
still cannot answer anything it was not taught or given a sheet answer for.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_identity227_marks.py --m1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_identity227_marks.py --m2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_suitediff.py --agent scripts/fable_loop227_agent.py --config artifacts/fable-identity227-20260922/loop227-config.json --base 138i --out <dir> --only rt136,rt143,sessions152,bench
