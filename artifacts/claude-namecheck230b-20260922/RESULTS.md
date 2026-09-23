# Exp 230b RESULTS — a name check must compare the name

**Verdict: FAIL (as sealed), on one sub-bar only: M1(c) YES items starting "Yes" = 10/11.**
The one miss, n230b-027 "My name's Sorrel, right?", was never "Yes" on 230:
230 replied "Your name is Sorrel." (230's first-word rule drops "Yes." on
non-auxiliary turns), and 230b is byte-identical to 230 there. The sealed
scorer counted every YES item, not only the ones that began with "Yes" on
230. Getting "Yes" there would have meant widening which turns count as
yes/no, and the brief forbids that. Everything else passed: 0 false "Yes"
anywhere, all 10 base-Yes NO items fixed, 0 writes, 0 suite moves, smoke
identical, no added time. Seal re-checked after all runs: 6/6 OK. No edits
after the seal. The 228 guard was installed.

One change on loop230 (scripts/claude_loop230b_agent.py, wraps 230 read-only).
A reply line that already starts "Yes. Your name is " on a turn that names a
specific name ("Is my name X?", "Is X my name?", "Am I [called] X?", "Did I
say my name was X?", ...) now has X compared with the stored user name
(case-insensitive, whole name). If they differ, the reply is "No. Your name is
<stored>.". Reply-only. It never writes.

## Marks table

| mark | bar | result |
|---|---|---|
| M1(a) false "Yes" (blind panel, 40 items) | 0 | 0 — pass |
| M1(b) NO items with base "Yes. Your name is …" now "No. Your name is <stored>." | 10/10 | 10/10 — pass |
| M1(c) YES items start "Yes" | 11/11 | **10/11 — FAIL** (n230b-027, unchanged from 230, see above) |
| M1(d) UNCHANGED items byte-identical to base230 | 8/8 | 8/8 — pass |
| M1(e) question writes | 0 | 0 — pass |
| M1 extra: every turn follows the sealed expected() rule; base230.jsonl = live 230 | — | 40/40; 0 mismatches |
| M2 dev cases (NO / YES / SAME / UNTAUGHT) | 11/6/9/5 | 11/11, 6/6, 9/9, 5/5; 0 false yes; 0 writes; notebooks identical — pass |
| M3 sessions152 / bench / marks123 vs 230 rows | 0 moves, GATE clean | 0 / 0 / 0, GATE clean — pass |
| M3 rt136 / rt143 vs 138i, and vs 230's saved rt rows | 0 moves | 0 / 0 (145 and 124 rows), 0 vs 230 — pass |
| M4 sleep smoke vs smoke230.json | identical | identical (sleeps 1, installed, 20 episodes, 5/5, wrong 0, Q99 abstain, 50/50, ow 0) — pass |
| M5 median added time per question (dev, 29 questions) | ≤ +5 ms | +0.035 ms — pass |

## Every move
- Blind panel, 10 (all NO items whose base was "Yes. Your name is …", all predicted by class):
  n230b-001 (Anna vs Ann), 002 (Mara/Maura), 003 (Lana/Lena), 004 (Toby/Tobin),
  005 (Jura/Juno), 006 (Kian/Kestrel), 008 (Bram/Wrenna), 009 (Isabel/Sabel),
  010 (Dace/Dacey), 012 (Corin Vask/Emlyn Vask): "Yes. Your name is S." -> "No. Your name is S."
- Dev, 11, exactly as predicted: d01-d11.
- Frozen suites: none.
- NO panel items that did not move, because 230 never said "Yes" on them (so they are not false yeses): 007, 011
  ("I do not know that ..." on 230), 029 "So my name is Idris?" (same), 030 and 032 (the "can't do 'not'" refusal).
- NOT_TOLD panel items (021-026): unchanged, none say "Yes".

## Deviations
- rt136/rt143 go through suitediff with --base 138i, since the 218 lookup does not find 230's rt rows by name. score.py --rt
  also compared them with 230's saved rows. Both were declared before the seal.
- Choice questions ("Is my name Quenby or Ottilie?", dev d23) still get 230's "Yes. Your name is Ottilie."
  This was declared in PASSMARKS and not handled.
- The driver was not changed after the seal. Its generic panel loader read the real panel without problems.
- No flake-type flips were seen, so no solo reruns were needed.

## What it means
If you tell it "My name is Ottilie." and then ask "Is my name Quenby?", it now says "No. Your name is Ottilie."
instead of the false "Yes." Asking "Is my name Ottilie?" (in any capital letters) still gets "Yes." If it
doesn't know your name, it never says "Yes." Nothing else it says changed on any test suite.

## What it doesn't mean
It only fixes questions that already reached the name answer with "Yes. Your name is …". Other ways of
asking, like "My name's Sorrel, right?", "I'm Kezia, aren't I?" or "So my name is Idris?", still get
230's old replies. Those are not false yeses, but they are not good answers either. It matches a short
list of sentence patterns and does not understand grammar. "X or Y" questions are not handled.

## Reproduce
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; R="uv run --offline --no-project --python 3.12 --with torch --with numpy python -B"
$R scripts/claude_namecheck230b_marks.py --panel ; $R scripts/claude_namecheck230b_score.py --panel
$R scripts/claude_namecheck230b_marks.py --dev
$R scripts/fable_suitediff218.py --agent scripts/claude_loop230b_agent.py --config artifacts/claude-namecheck230b-20260922/loop230b-config.json --base-dir artifacts/claude-yesprefix230-20260922 --out <dir> --only sessions152,bench,marks123
$R scripts/fable_suitediff218.py --agent scripts/claude_loop230b_agent.py --config artifacts/claude-namecheck230b-20260922/loop230b-config.json --base 138i --out <dir> --only rt136,rt143 ; python3 scripts/claude_namecheck230b_score.py --rt <dir>
$R scripts/fable_sleepsmoke206.py --agent scripts/claude_loop230b_agent.py --config artifacts/claude-namecheck230b-20260922/loop230b-config.json --root <dir> --report <f> --label s1-230b --seed 1 --idle-seconds 30.0 ; python3 scripts/claude_namecheck230b_score.py --smoke <f>
