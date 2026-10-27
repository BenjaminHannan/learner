# Exp 234 pass marks — one honest small-talk reply (sealed before registered runs)

Base: loop138i (scripts/fable_loop138i_agent.py, config
artifacts/fable-agent138i-20260922/loop138i-config.json), wrapped read-only.
Agent: scripts/claude_loop234_agent.py; config
artifacts/claude-smalltalk234-20260922/loop234-config.json (byte copy of the
138i config). One change: a whole turn that is (greeting +) a how-are-you
question about the assistant gets "I'm here and ready to learn. Tell me
something, or ask me about what you've told me." ("Hi! " first when the
turn opens with a greeting). Reply-only; everything else byte-identical.

Mac CPU, offline, OMP/MKL=1, fresh temp notebook per case per agent,
fictional names only, `uptime` checked before each registered run, each run
< 25 min. Every case reported. Any change to a sealed file after the seal =
FAIL.

Driver: scripts/claude_smalltalk234_marks.py (both agents in-process).

- M1 panel (blind, artifacts/claude-smalltalkpanel234-20260922/panel.jsonl,
  opened only after this seal), `--panel`. PASS iff: family wellbeing
  >= 90% of items reply exactly [FIXED] or ["Hi! " + FIXED]; 0 replies
  containing FIXED in any other family; every non-wellbeing test reply
  byte-identical to 138i; every setup reply byte-identical to 138i;
  notebook snapshot identical to 138i in every item; 0 writes on wellbeing
  test turns. (Also reported, not a bar: agreement with the panel's
  expect field.)
- M2 dev (artifacts/claude-smalltalk234-20260922/dev-cases.json, 84 cases:
  40 wellbeing, 8 people_wellbeing, 10 status, 6 greeting_plus_question,
  20 plain_questions), `--dev`. PASS iff >= 95% of cases ok (positives: the
  exact reply incl. correct "Hi! " form and 0 writes; others byte-identical
  to 138i with no FIXED; setups and notebooks identical).
- M3 frozen suites: scripts/fable_suitediff218.py --base 138i --only
  rt136,rt143,sessions152,bench,marks123. PASS iff 0 new WRONG /
  WRONG-WRITE / junk and GATE clean. Predicted moves: none (no suite turn is
  a whole-turn wellbeing question). Known flake rule applies.
- M4 sleep smoke: scripts/fable_sleepsmoke206.py (seed 1, idle 30) equals
  artifacts/fable-sleepsmoke206-20260922/s1-138i.json on every field except
  seconds/agent/config/label (sleeps=1 installed=1 episodes=20 probes=5/5
  wrong=0 broken=abstain taught=50/50 ow=0).
- M5 latency: paired per-test-turn wall time (234 minus 138i, order
  alternated, one untimed warm-up per agent) over the panel run and the dev
  run: median delta <= +5 ms in each. Mean reported (not a bar; load noise).

Verdict PASS iff M1-M5 all pass.
Pilots (pre-seal, final code): M2 84/84 (40/40 wellbeing moved to FIXED,
0 others moved); M5 dev median -0.15 ms, mean -0.35 ms; M3 all suites 0
moves, GATE clean; M4 identical to s1-138i except seconds.
Predictions: P234.1 M1 PASS; P234.2 M2 84/84; P234.3 M3 0 moves; P234.4 M4
identical; P234.5 median latency delta within +/-1 ms.
