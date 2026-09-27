# Exp 230b pass marks — a name check must compare the name (sealed before the registered runs)

Base: loop230 (scripts/claude_loop230_agent.py, config
artifacts/claude-yesprefix230-20260922/loop230-config.json), wrapped read-only.
Bug (verifier, artifacts/claude-verify-20260922/227bc230/out-p2-230.txt item 09):
after "My name is Ottilie.", "Is my name Quenby?" -> "Yes. Your name is Ottilie."

One change (scripts/claude_loop230b_agent.py): only when the 230 turn already
produced a line starting "Yes. Your name is " (the D8 user-name path on a
yes/no turn), and asked_name(turn) finds a specific name (patterns: "Is my
name [really] X", "Is X my name", "Am I [called|named] X", "Did/Have I
say/tell you my name is/was X", "Do/Did you know/remember/have my name
is/as X", "Do you have me down as X"; 1-3 name words, no stop-words, no
"or", capitalised unless the whole turn is lower case), compare X with the
stored user name, case-insensitive, whole name. Different -> "No. Your name
is <stored>."; same -> unchanged. No stored name -> the line never exists,
reply unchanged. Nothing outside a "Yes. Your name is " line is touched, so
routing is not widened. Reply-only; never writes. The 228 guard is installed
(install_srcguard228() at import; SrcGuardMixin228 first in Loop230bDaemon).

Mac CPU, offline, OMP/MKL=1, fresh temp notebook per session, fictional
names only, one run at a time, `uptime` checked before each registered run
(wait while 1-min load > 60). Any change to a sealed file after the seal = FAIL.

Expected 230b reply for every turn (driver scripts/claude_namecheck230b_marks.py,
function expected()): from the live 230 reply on the same turns, a "Yes. Your
name is " line becomes "No. Your name is <stored>." iff asked_name finds a
name, a name is stored, and they differ; otherwise byte-identical.

- **M1 blind panel** (artifacts/claude-namecheckpanel230b-20260922/panel.jsonl +
  base230.jsonl; seal checked from the repo root first; run ONCE:
  `marks.py --panel` then `score.py --panel`). PASS iff ALL of:
  (a) false_yes = 0 (230b reply starts "Yes" when the item's expect is NO,
      or no name is stored, or asked_name differs from the stored name);
  (b) every NO item whose base230 reply starts "Yes. Your name is " now is
      exactly "No. Your name is <stored>." (NO_fixed = NO_base_yes);
  (c) every YES item still starts "Yes" (YES_kept = YES_total);
  (d) every UNCHANGED item byte-identical to its base230.jsonl reply
      (UNCHANGED_identical = UNCHANGED_total);
  (e) question_writes = 0.
  Items with other labels are reported, not scored. If a panel item is not
  readable by the driver's generic loader, that is a driver-only fix,
  reported with its diff. Predicted moves: only NO items (base "Yes. Your
  name is ..." -> "No. Your name is ..."); ids unknown before the run (blind).
  Risk named in advance: a NO phrasing my asked_name patterns do not cover
  would stay "Yes" and fail (a).
- **M2 dev cases** (artifacts/claude-namecheck230b-20260922/dev-cases.json, 31
  cases: 11 NO, 6 YES, 9 SAME, 5 UNTAUGHT; `marks.py --dev`). PASS iff
  NO 11/11 = "No. Your name is <stored>.", YES 6/6 = "Yes. Your name is
  <stored>.", SAME 9/9 and UNTAUGHT 5/5 byte-identical to live 230 (UNTAUGHT
  never "Yes"), every turn follows expected(), notebooks identical to 230,
  false_yes = 0, question writes = 0. Predicted moves by id: exactly d01-d11.
  Known and accepted (not a move): d23 "Is my name Quenby or Ottilie?" keeps
  230's "Yes. Your name is Ottilie." (choice question, not handled).
- **M3 frozen suites** (scripts/fable_suitediff218.py): sessions152, bench,
  marks123 with --base-dir artifacts/claude-yesprefix230-20260922 (230's saved
  rows); rt136, rt143 with --base 138i (the 218 lookup does not find 230's
  rt rows by name) PLUS score.py --rt comparing reply/verdict/stored by id
  against 230's saved suitediff-rt rows. PASS iff 0 new WRONG, WRONG-WRITE or
  junk, GATE clean, and every move predicted by id. Predicted moves: none
  (0 on all five suites, 0 vs 230's rt rows). Flake rule: an unpredicted flip
  to an abstain or "Was that a question?" counts against the mark and is run
  alone 5 times (guard installed).
- **M4 sleep smoke**: scripts/fable_sleepsmoke206.py (seed 1, idle 30) report
  identical to smoke230.json on every key except agent/config/label/seconds
  (`score.py --smoke`).
- **M5 time**: median over dev question turns of (230b turn time - 230 turn
  time) <= +5 ms (from `marks.py --dev`, median_added_ms).

Verdict PASS iff M1-M5 all pass. Pilots (pre-seal, final agent code): M2
31/31, moves d01-d11 only, false_yes 0, writes 0, median added -0.04 ms;
M3 sessions152/bench/marks123 0 moves vs 230 rows, rt136/rt143 0 moves vs
138i and 0 vs 230 rows, GATE clean; M4 identical. M1 not piloted (blind).
