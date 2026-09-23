# Exp 227b pass marks — THE ASSISTANT IS NAMED PREMONITION (sealed before the registered runs)

Base: loop227 (scripts/fable_loop227_agent.py, config
artifacts/fable-identity227-20260922/loop227-config.json), wrapped read-only.
One change: the identity-sheet NAME answer "I don't have a name yet."
becomes "My name is Premonition." (name decided by Ben). The NAME line is the
only sheet line saying the assistant has no name (MAKER/WHAT/LEARN/AGE/HOME
never mention a name), so it is the only line replaced. Implementation:
scripts/claude_loop227b_agent.py runs the 227 turn verbatim and swaps the
reply text only when that turn was served by the identity sheet with intent
NAME. Same gate, same 38 templates, same routing, reply-only, 0 writes.
The fable_identity227.SHEET dict is not mutated.

Mac CPU, offline, OMP/MKL=1, isolated temp dirs, fictional names only, one
suite at a time, each run < 25 min. Every case reported. Any change to a
sealed file after the seal = FAIL.

- M1 (all 227 cases, 68 = 227 m1-cases 36 + m2-cases 32, run on both 227b
  and 227 in fresh dirs): `python -B scripts/claude_name227b_marks.py --m1`.
  PASS iff each of the 6 NAME cases gives "My name is Premonition." on 227b
  where 227 gives "I don't have a name yet." (earlier turns identical), and
  each of the other 62 cases is byte-identical to 227 (all replies); final
  notebook snapshot identical to 227 for all 68; 0 writes on every
  identity question (36 M1 cases).
- M2 (7 sessions, m2-cases.json here): user teaches "My name is <X>." (X
  fictional: Juno, Tavi, Orla, Brix, Nell, Quill), asks an identity NAME
  question, "What is my name?", "What is your name?", "What is my name?"
  (J02 asks "What is your name?" before teaching). `--m2`. PASS iff every
  user-name question contains X, not "Premonition", with 0 writes; every
  assistant-name question = "My name is Premonition." with 0 writes; the
  notebook's only USER name triple is X and nothing mentions Premonition.
- M3 frozen suites, scripts/fable_suitediff218.py: sessions152, bench,
  marks123 with --base-dir artifacts/fable-identity227-20260922 (227's saved
  rows); rt136, rt143 with --base 138i (227's folder has no rows file the
  218 lookup finds for these two; 227 was 0 moves vs 138i on both, so 138i
  rows = 227 rows). PASS iff 0 moves on all five and GATE clean. Predicted
  moves: none (no frozen suite item in the pilots hit the identity NAME
  templates). Known flake rule applies (reported, counts against the mark,
  then the item is run alone 5 times).
- M4: 0 writes from identity questions (from M1 + M2) and 0 new WRONG /
  WRONG-WRITE / junk writes in M3.

Verdict PASS iff M1-M4 all pass. Pilots (pre-seal, final code): M1 68/68,
M2 7/7, suitediff rt136/rt143 (vs 138i) 0 moves, sessions152/bench/marks123
(vs 227 dir) 0 moves, GATE clean. Sleep smoke not part of this registration
(the change is reply text inside a reply-only branch; not requested).
