# Exp 230 RESULTS — "Yes." only on yes/no questions

**Verdict: PASS** (M1-M4 all pass; seal 5/5 OK after the runs; no post-seal edits).

One change on loop219 (scripts/claude_loop230_agent.py, wraps 219
read-only): 219's "Yes. Your name is X." keeps "Yes. " only when the turn
starts with an auxiliary verb (do/does/did/can/could/will/would/is/are/am/
was/were/have/has/had/shall/should/may/might/must or a negative contraction
of one). Otherwise the reply is "Your name is X.". Reply-only; never writes.

## Marks table

| mark | result |
|---|---|
| M1 219's own cases vs live 219 (45 sessions, 195 turns) | 45/45 sessions, 195/195 turns follow the rule; 20 moves, all predicted ("What's my name again?" x 20 names: "Yes. Your name is X." -> "Your name is X."); 0 yes/no turns moved; notebooks identical — PASS |
| M2 fresh cases (taught + untaught each) | WH 25/25 lose "Yes."; IMP 31/31 lose "Yes."; YN 14/14 byte-identical to 219 (12 keep "Yes. Your name is X.", 2 were never name replies on 219 and stay as they were); 70/70 untaught identical; 0 question writes; notebooks identical — PASS |
| M3 frozen suites (fable_suitediff218) | rt136 0, rt143 0 (vs 138i); sessions152 0, bench 0 (4 x 200), marks123 0 (vs 219 rows); GATE clean — PASS |
| M4 sleep smoke (seed 1) | sleeps=1 installed=1 episodes=20 probes=5/5 wrong=0 broken=abstain taught=50/50 ow=0 — identical to 219's smoke219 — PASS |

Moves: only the 20 predicted M1 rows plus the 56 targeted fresh WH/IMP
cases. No frozen-suite moves in the registered run.
Slowest run: sleep smoke 167 s. All runs Mac CPU, OMP/MKL=1, one at a time.

## Deviations
- rt136/rt143 compared against 138i rows (219's folder has no rows file the
  218 lookup finds for them; 219 was 0 moves vs 138i). Declared before the run.
- The pre-seal bench pilot showed 1 flake-type move (bench103-s2fresh-4hop-119
  correct->abstain); the registered bench run had 0 moves, so the flake
  follow-up (5 solo reruns) was not triggered.
- Yes/no detection is by first word only, as asked. "Hey, do you remember my
  name?" or "So did I tell you my name?" would lose the "Yes." (not tested,
  not claimed).

## What it means
The assistant now only starts with "Yes." when you asked a yes-or-no
question. "Do you remember my name?" still gets "Yes. Your name is Juno.",
but "What am I called?" or "Remind me of my name." now get just "Your name
is Juno." Nothing else it says changed.

## What it doesn't mean
It does not understand grammar in general; it just looks at the first word.
It does not change which questions get routed to the name answer (some
requests like "Tell me my name." still get the "I do not know" refusal,
exactly as on 219).

## Reproduce
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; R="uv run --offline --no-project --python 3.12 --with torch --with numpy python -B"
$R scripts/claude_yesprefix230_marks.py --m1 ; $R scripts/claude_yesprefix230_marks.py --m2
$R scripts/fable_suitediff218.py --agent scripts/claude_loop230_agent.py --config artifacts/claude-yesprefix230-20260922/loop230-config.json --base 138i --out <dir> --only rt136,rt143
$R scripts/fable_suitediff218.py --agent scripts/claude_loop230_agent.py --config artifacts/claude-yesprefix230-20260922/loop230-config.json --base-dir artifacts/fable-selfname219-20260922 --out <dir> --only sessions152,bench,marks123
$R scripts/fable_sleepsmoke206.py --agent scripts/claude_loop230_agent.py --config artifacts/claude-yesprefix230-20260922/loop230-config.json --root <dir> --report <f> --label s1-230 --seed 1 --idle-seconds 30.0
