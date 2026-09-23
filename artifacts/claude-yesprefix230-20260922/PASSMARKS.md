# Exp 230 pass marks — "YES." ONLY ON YES/NO QUESTIONS (sealed before the registered runs)

Base: loop219 (scripts/fable_loop219_agent.py, config
artifacts/fable-selfname219-20260922/loop219-config.json), wrapped read-only.
Problem: 219's grounded D8 reply "Yes. Your name is X." also lands on
wh-questions and requests ("What am I called?", "Remind me what my name
is?"). One change (scripts/claude_loop230_agent.py): after the 219 turn runs
verbatim, a reply line starting "Yes. Your name is " loses "Yes. " unless the
turn is a yes/no question = its first word is an auxiliary (do does did can
could will would is are am was were have has had shall should may might
must, or a negative contraction: don't doesn't didn't can't couldn't won't
wouldn't isn't aren't wasn't weren't haven't hasn't hadn't shouldn't
mustn't). Reply-only, never writes.

Mac CPU, offline, OMP/MKL=1, fresh temp notebook per session, fictional
names only, one suite at a time, each run < 25 min, `uptime` checked before
each registered run. Every case reported. Any change to a sealed file after
the seal = FAIL.

Expected 230 reply for every turn (driver scripts/claude_yesprefix230_marks.py):
from the live 219 reply, strip "Yes. " from a "Yes. Your name is " line iff
the turn is not yes/no; otherwise byte-identical. Notebooks identical to 219.

- M1 (219's own cases: 20 taught sessions x 5 probes, 5 untaught x 5, 20
  Mira-age sessions x 2; 45 sessions, 195 turns incl. teach turns),
  `--m1`. PASS iff 45/45 sessions match the expected rule, notebooks
  identical, and 0 yes/no turns move. Predicted moves: exactly the 20
  "What's my name again?" rows in M1 ("Yes. Your name is X." -> "Your name
  is X."). 219's yes/no probes ("Do you remember / Did I tell you / Have I
  told you my name?") unchanged.
- M2 (fresh cases, m2-cases.json: 25 WH, 31 IMP, 14 YN; each run taught
  "My name is <fictional>." + question, and untaught), `--m2`. PASS iff every
  WH and IMP case: 219 taught reply "Yes. Your name is X." and 230 "Your
  name is X."; every YN case: taught reply byte-identical to 219; every
  untaught reply byte-identical to 219; 0 question-turn writes; notebooks
  identical to 219. (Registered bar: WH 25/25, IMP 31/31, YN 14/14.)
- M3 frozen suites, scripts/fable_suitediff218.py: sessions152, bench,
  marks123 with --base-dir artifacts/fable-selfname219-20260922 (219's saved
  rows); rt136, rt143 with --base 138i (219's folder has no rows file the
  218 lookup finds for these; 219 was 0 moves vs 138i on both). PASS iff
  0 moves and GATE clean. Predicted moves: none. Known flake rule applies
  (the bench pilot showed 1 flake-type move, bench103-s2fresh-4hop-119
  correct->abstain; this change cannot produce an abstain, but a registered
  move still counts against the mark and is then run alone 5 times).
- M4 sleep smoke: scripts/fable_sleepsmoke206.py on loop230 (seed 1, idle 30)
  matches 219's smoke219.json: sleeps=1 installed=1 episodes=20 probes=5/5
  wrong=0 broken=abstain taught=50/50 ow=0.

Verdict PASS iff M1-M4 all pass. Pilots (pre-seal, final code): M1 45/45
sessions, 195/195 turns, 20 moves (all predicted), 0 yes/no moves; M2 WH
25/25, IMP 31/31, YN 14/14; rt136/rt143 0 moves; sessions152 0, marks123 0,
bench 1 flake-type move (above); smoke identical to 219.
