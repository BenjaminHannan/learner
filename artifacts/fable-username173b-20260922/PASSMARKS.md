# Exp 173b PASSMARKS — word-names count as names (sealed BEFORE any registered run)

Base agent: loop173 (scripts/fable_loop173_agent.py,
artifacts/fable-username173-20260922/loop173-config.json; its RESULTS.md,
PASSMARKS.md, cases173.json read first). No 173/166 file is edited or
touched. New files only: scripts/fable_fix173b_username.py,
scripts/fable_loop173b_agent.py, scripts/fable_fix173b_probe.py,
scripts/fable_fix173b_bench.py, scripts/fable_fix173b_g3.py,
scripts/fable_fix173b_marksdiff.py, scripts/fable_fix173b_scan.py (dev
only); artifacts/fable-username173b-20260922/ (cases173b.json,
loop173b-config.json, this file); design/v3/30-modes/173b-word-names-user-muse.md.

## Step 1 — what the base does today (file:line)

loop173's name-shape test (scripts/fable_fix173_username.py:140-168):
capitalised token counts iff lowercase absent from /usr/share/dict/words
OR in GIVEN_NAMES. Hence "My name is Maya." / "Call me Pip." / "I am
Grace." clarify with 0 writes (maya/rose/grace/rue/sol/pip/hope/faith/
iris/dawn/sky/reed/rich/grant/will/mark are all in dict words; only
dawn/iris are in 173's GIVEN list). Verified live pre-seal on loop173:
"My name is Maya.", "My name is Rose.", "My name is Grace.",
"My name is Rue.", "My name is Sol.", "Call me Pip.", "I am Grace."
-> all "I didn't understand that. Could you say it another way?" 0 writes.

## THE ONE CHANGE vs loop173 (scripts/fable_fix173b_username.py)

Name-shape test for user-name statements ONLY (questions, x-heads,
namecheck, gates, replies = loop173 literally):
(a) After "My name is" / "Call me" / "You can call me", 1-3 letter tokens
count as a name even if in dict words, EXCEPT sealed CLOSED_173B (37
entries, whole-value lowercase match): not, not important, a secret,
secret, unknown, none, nothing, later, back, anytime, whatever, anything,
maybe, tomorrow, soon, crazy, stupid, lazy, a nurse, nurse, tired, happy,
sick, a teacher, teacher, from oslo, important, nobody, no one, anyone,
someone, sorry, please, hello, hi, a friend, the boss, my friend --
EXCEPT values containing a determiner (DETERMINERS_173B = {a, an, the},
any token, case-insensitive) or a digit (any 0-9 char). "My name is"
capitalises lowercase silently (as 173); "Call me"/"You can call me"
REQUIRE Title-case (every token already capitalised).
(b) After "I'm"/"I am", 173's conservative rule stays (never capitalise;
states common) but GIVEN_173B = 173 GIVEN_NAMES + /usr/share/dict/
propernames (1,308 lines).
Stacking: Loop173bEars(Name173bMixin, Loop173Ears); Name173bMixin is
standalone (not a subclass of Name173Mixin, avoids double-claim); the ONE
173-accept/173b-reject shape (Call-me-lowercase) bypasses loop173's stage
to Loop166Ears directly; Loop173bAgentLoop mirrors loop173's tick keyed on
the 173b parser (so S13 keeps loop166's clarify reply).

Evidence correction (pre-seal, this Mac): propernames CONTAINS grace/dawn/
rich/grant/will/mark/aaron (lowercased) but NOT maya/rose/rue/sol/pip/
hope/faith/iris/sky/reed. So "I'm Grace." NAMES in 173b; the accepted
known miss after I'm is maya/rose/rue/sol/pip/hope/faith/iris/sky/reed
(e.g. "I am Grace." is NOT a miss -- it sets the name).

## Sealed inputs

- T1: 166's sealed probe UNCHANGED: artifacts/fable-me166-20260922/cases166.json (52 rows).
- T1b: 173's sealed probe UNCHANGED: artifacts/fable-username173-20260922/cases173.json (45 rows).
- T1c: NEW probe artifacts/fable-username173b-20260922/cases173b.json (42 dialogues, fictional names only, each row a FRESH loop, steps in order):
  16 word-names W01-W16 (Maya, Rose, Grace, Rue, Sol, Pip, Hope, Faith, Iris, Dawn, Sky, Reed, Rich, Grant, Will, Mark after My-name/Call-me frames);
  14 closed/look-alikes C01-C14 ("My name is not important.", "Call me later.", "call me back", "My name is a secret.", "I'm tired.", "I am from Oslo.", "My name is unknown.", "Call me Whatever.", "My name is nothing.", "You can call me Tomorrow.", "I am Happy.", "I'm a nurse.", "My name is crazy.", "Call me Soon.");
  6 I'm-propernames I01-I06 (Grace, Grant, Mark, Will, Rich new-names; Aaron control identical);
  6 other O01-O06 (incl. unset "Who am I?").
- Config: artifacts/fable-username173b-20260922/loop173b-config.json.
- G1 reference: loop173's FROZEN rows artifacts/fable-username173-20260922/fable_bench173_loop173_*_rows.jsonl (read-only).
- G2 reference: loop173's marks173 (artifacts/fable-username173-20260922/marks173, read-only).
- G3 reference: loop173's frozen artifacts/fable-username173-20260922/redteam136-loop173.json, redteam143-loop173.json, sessions152-loop173.json (read-only).

## Marks (integer counts, every seed/case reported, never averaged)

- T1 (scripts/fable_fix173b_probe.py --which t1, new=loop173b vs base=loop173): 52/52 byte-identical. Prediction: 52/52 OK, ZERO moves.
- T1b (--which t1b): 44/45 identical to loop173; the ONE listed pre-seal difference is S13 "You can call me lena." (173 names Lena via silent capitalise; 173b requires Title-case after Call-me, so 0 writes + loop166 clarify). Harness verdict: 44 OK + 1 LISTED-DIFF. Prediction: exactly that, no other diff.
- T1c (--which t1c): W 16/16 name set + "What is my name?" answers; C 14/14 zero writes + byte-identical to loop173; I 6/6 name set (I06 Aaron also byte-identical); O 6/6 byte-identical. Prediction: 42/42 OK.
- T2: 0 wrong writes over all 139 rows (52+45+42); name-statement rows hold entities <= {USER} (0 new non-USER entities).
- G1 bench (scripts/fable_fix173b_bench.py, bench121-lineage driver by import): per-item verdict AND reply AND teach-replies identical to frozen loop173 rows on all 600 items, 0 new wrong. Prediction: ZERO moves.
- G2 marks123 (scripts/fable_marks123_all.py --agent scripts/fable_loop173b_agent.py --config artifacts/fable-username173b-20260922/loop173b-config.json --out artifacts/fable-username173b-20260922/marks173b --workers 2, then scripts/fable_fix173b_marksdiff.py): per-case identical to marks173 after the disclosed scrub (drop timing keys; rewrite agent paths/config/dir/loop tokens). Prediction: 0 case-moves, 0 whole-diffs after scrub. rt110 log-only flakes: re-run once in the open, report both.
- G3 (scripts/fable_fix173b_g3.py): 0 verdict/reply/write moves, 0 new WRONG/WRONG-WRITE vs loop173 frozen rows on redteam136 (145) + redteam143 (124) + sessions152 (180 turns). Prediction: ZERO moves.
- G4: each registered run (probe t1/t1b/t1c, bench, G3, marks123, diffs) < 25 min wall-clock (< 1500 s) Mac CPU (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B ...).
- Anything else anywhere (any unpredicted move, any new WRONG, any raw-USER leak): FAIL, recorded as FAIL.

## Pre-seal evidence (dev only, NOT registered runs)

- Dev scan (scripts/fable_fix173b_scan.py) over 2885+ sealed input turns (same corpora as 173): 173b statement fires == 173 statement fires == 0 (DIFF-NEW 0); question fires 0; USER-token inputs 0. Hence no regression-suite run can set a name: zero moves predicted on G1/G2/G3/T1.
- Dev trial of the 173b pure parser on director probes + T1c values to scratch (no artifacts): 7/7 director probes name except "I am Grace." also names (propernames evidence); S13 rejects; all C rows reject; all W/I rows accept.
- Reverse check on loop173 live pre-seal: 7 director turns clarify with 0 writes (mechanism above).

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims never exceed evidence. No rule changes after the seal; no silent re-runs.

## Registered reproduce (worktree root, after sealing, one at a time)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173b_probe.py --which t1 --out artifacts/fable-username173b-20260922/probe173b-t1.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173b_probe.py --which t1b --out artifacts/fable-username173b-20260922/probe173b-t1b.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173b_probe.py --which t1c --out artifacts/fable-username173b-20260922/probe173b-t1c.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173b_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173b_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop173b_agent.py --config artifacts/fable-username173b-20260922/loop173b-config.json --out artifacts/fable-username173b-20260922/marks173b --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173b_marksdiff.py
