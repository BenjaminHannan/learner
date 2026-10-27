# Exp 227b RESULTS — the assistant is named Premonition

**Verdict: PASS** (M1-M4 all pass; seal 5/5 OK after the runs; no post-seal edits).

One change on loop227: the identity-sheet NAME answer "I don't have a name
yet." became "My name is Premonition." (Ben's choice of name). No other
sheet line said the assistant has no name, so nothing else changed. Agent:
scripts/claude_loop227b_agent.py (wraps loop227 read-only; swaps the reply
only when the 227 identity gate served the NAME intent).

## Marks table

| mark | result |
|---|---|
| M1 all 68 loop227 cases (36 identity + 32 user/other) vs live loop227 | 68/68: 6/6 NAME cases now "My name is Premonition." (227: "I don't have a name yet."); 62/62 others byte-identical; 68/68 notebooks identical; 36/36 identity questions 0 writes — PASS |
| M2 same-session user name vs assistant name (7 sessions, 6 fictional user names) | 7/7: every "What is my name?" gives the user's name (e.g. "Your name is Juno."), every "What is your name?"-type turn gives "My name is Premonition.", all question turns 0 writes, only USER name triple stored, Premonition never stored — PASS |
| M3 frozen suites (fable_suitediff218) | rt136 0 moves, rt143 0 moves (vs 138i); sessions152 0, bench 0 (4 splits x 200), marks123 0 (vs 227 rows); GATE clean — PASS |
| M4 0 writes / 0 new wrong | 0 identity-question writes (49 turns: 36 in M1 + 13 in M2); 0 new WRONG / WRONG-WRITE / junk — PASS |

Moves: the 6 predicted NAME replies (I01-I06) only. No frozen-suite moves.
Run times: every run under 1 minute (slowest: sessions152+bench+marks123 51 s).

## Deviations
- rt136/rt143 compared against 138i rows, not 227's folder: the 218 lookup
  finds no redteam136/143 rows file in artifacts/fable-identity227-20260922.
  227 was 0 moves vs 138i on both, so this is the same comparison. Declared
  in PASSMARKS before the run.
- My first registered launch line failed before running anything (shell
  quoting: "command not found", rc=127, no agent started). Re-launched with
  a shell function; the logs in this folder are from that run. No file was
  edited between the two.
- Sleep smoke not run (not in this registration).

## What it means
When someone asks the assistant its name, it now says "My name is
Premonition." It still keeps the user's own name separate: after "My name is
Juno.", "What is my name?" still answers Juno, and the assistant's name is
never written into the notebook. Everything else behaves exactly as before.

## What it doesn't mean
It only recognises the same 6 fixed ways of asking for its name that 227
knew (for example, "What's your name?" with a contraction is still not
recognised — that is exp 227c's job). The assistant did not learn its name;
it is a fixed line on a hand-written sheet.

## Reproduce
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; R="uv run --offline --no-project --python 3.12 --with torch --with numpy python -B"
$R scripts/claude_name227b_marks.py --m1 ; $R scripts/claude_name227b_marks.py --m2
$R scripts/fable_suitediff218.py --agent scripts/claude_loop227b_agent.py --config artifacts/claude-name227b-20260922/loop227b-config.json --base 138i --out <dir> --only rt136,rt143
$R scripts/fable_suitediff218.py --agent scripts/claude_loop227b_agent.py --config artifacts/claude-name227b-20260922/loop227b-config.json --base-dir artifacts/fable-identity227-20260922 --out <dir> --only sessions152,bench,marks123
