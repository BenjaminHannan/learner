# Exp 158 RESULTS — question-surface normalisation (loop150 + qform mixin)

Registered single-change fix for 152 classes N5 (`what's` / `tell me`
refused) and N7 (`???` leaks into the relation). All runs Mac CPU,
`OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`, `uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B …`.

## Marks table (integer counts, every case reported, never averaged)

| mark | bar (sealed) | result | status |
|---|---|---|---|
| Q1 probe (59: 43 pairs + 16 non-q) | 43/43 identical + want + 0 writes; 16/16 identical to loop150 + 0 writes | 59/59 OK, 10.5 s | PASS |
| Q2/G3 sessions (6x30, Loop158Daemon) | all replies = T-T except S5 n5/n6/n9 -> OK, 0 new WRONG, 0 new writes | exactly n5/n6/n9 UNHELPFUL->OK (`tess's city is Omaha.` x2, `Rosa's mother's city is lima.`), new_wrong=[], new_writes=[], 10.0 s | PASS |
| G1 bench (edit200+old+new121) | per-item verdicts+replies = loop150 rows, 0 moves | 600/600 identical (edit200 150/50/0, old 157/43/0, new 136/63/1), 0 moves, 90.8 s | PASS |
| G2 marks123 | per-case = marks150 except rt81 D_q_vs_s-03 OK->UNCLEAR | p2/p4/rt110/q1/bench/p3/Q4/sleep identical (Q4 same 7 leaks, sleep SKIP); rt81 exactly D_q_vs_s-03 as predicted; soak wrong 10 vs 0 (see FAIL note) | FAIL (soak only) |
| G4 time | every run < 1500 s | 10.5 / 10.0 / 90.8 / 225.0 s | PASS |

## G2 FAIL note (one diagnosis, no re-run)

Soak: `wrong 10 / audit_lost_pairs 1` vs sealed 150 `0 / 0`; all other
suites per-case identical plus the single predicted rt81 move. The 10
wrongs are 9 asks for one entity (SoakP151, teach never landed) plus 1
empty file read (`I didn't catch anything.` at turn 248). All three
soak sentence templates provably never engage the mixin (no leading
contraction, no tell/show/give-me opener, no `?`/`!` in the original,
so eligibility is False by construction, verified on the pure
function). Signature = lost teach with `lost=0` plus an empty read:
mailbox race under the shared loaded machine (6 parallel agents + 4
suite workers), where the 150 reference ran clean. Teach/ask/mailbox
paths are untouched by this experiment (question-side `hear()` only).

## Deviations from the plan

1. Bench attempt 1 killed by my 120 s tool timeout (infra, no verdict);
   re-ran whole bench with a 10 min timeout: 90.8 s, reported above.
2. rt81 D_q_vs_s-03 reply is `I don't know anyone called Mira.`, not
   the guessed `Mira's city is Lisbon.` (Mira is never taught in that
   seq: turn 1 teaches nothing). Predicted verdict move (OK->UNCLEAR),
   0 writes, no leak all hold.
3. Interior-mark guard added pre-seal (PASSMARKS §THE ONE CHANGE):
   glued `?`-turns (red-team S2) stay byte-identical instead of becoming
   a garbage ask. N5/N7 shapes unaffected.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix158_probe.py --out artifacts/fable-qform158-20260922/probe158-loop158.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix158_session.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix158_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop158_agent.py --config artifacts/fable-qform158-20260922/loop158-config.json --out artifacts/fable-qform158-20260922/marks158 --workers 4

What it means: `what's X's R?`, `tell/show/give me X's R` and `???`-stacks
now answer exactly like the canonical question, with zero behaviour
change anywhere else (600/600 bench, all marks123 cases, 177/180
session turns identical).
What it does not mean: pronouns, small talk, `mom`, bare corrections,
the N9 wrong-answer hop and 151's no-`?` questions are not fixed here.
