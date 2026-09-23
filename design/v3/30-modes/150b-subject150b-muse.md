# 150b — Clause-in-subject guard on loop150 (Muse)

Loop150b = loop150 + one stackable mixin. The bug: a teach whose subject
span swallows a whole second clause ("Ann is famous for Cats and Tom died
in the city of Oslo" -> subject "Ann is famous for Cats and Tom") saves a
wrong triple on loop129b, loop144 and loop150. Exp 150's guard only screens
hedge/reporting/filler words, so it waves this through.

## Step 1 — the code responsible (read before sealing, nothing edited)

1. `scripts/fable_bench73_english_arm.py:89` — the pattern
   `(.+?) died in the city of (.+?)`. The `(.+?)` subject group matches
   anything, including a whole relation clause.
2. `scripts/fable_bench73_english_arm.py:194-205` — `hear_teach_template`
   tries the ordered patterns and returns the first fullmatch triple. No
   validation of the subject span ever happens. Pattern order decides:
   `died` (line 89) precedes `famous-for` (line ~93), so the t14 sentence
   parses as subject "Ann is famous for Cats and Tom", relation
   `place_of_death`, object "Oslo".
3. `scripts/fable_bench92_english_arm.py:58-68` / `:176-188` — the extra
   patterns (`is employed by`, `works in the field of`, `'s child is`,
   ...) with the same unchecked-subject shape, tried after bench73.
4. `scripts/fable_loop121_agent.py:206-220` — Loop121Ears accepts any
   parsed triple into a structured teach action (only the value is
   screened).
5. `scripts/fable_earsguard91.py:39-60` and
   `scripts/fable_fix139b_valueguard.py:99-115` — the value screens: they
   only ever look at the VALUE span, so a clean value ("Oslo") passes.
6. `scripts/fable_fix150_subjectguard.py:152-163` — the 150 subject guard:
   hedge/reporting openers, filler strip, lowercase-lead catch-all. None
   fires on "Ann is famous for Cats and Tom" (starts capitalised, no
   opener), so the polluted subject stores verbatim.

The twin with the extra clause in the VALUE ("Bea was born in the city of
Lima and Tom died in Oslo" -> value "Lima and Tom died in Oslo") never
reaches the notebook: 139b's bare-"and" screen refuses it on loop150.

## The one change

`scripts/fable_fix150b_subject150b.py` (`Subject150BMixin`, in the style of
`scripts/fable_fix150_subjectguard.py`): after the 129 strip and the 150
screen, at ears `hear()` and again at loop `_act()` just before the write,
refuse with the existing SPLIT reply (0 writes) any teach/correct whose
subject span contains (a) a relation cue from the loop's own relation
tables (`REL_CUES_150B`: multi-word verb-holding phrases from
STATEMENT_PATTERNS, EXTRA_STATEMENT_PATTERNS and the REL_MENTION_CUES
tables), or (b) a lower-case finite verb/copula token (`VERBS_150B`: is,
was, died, born, lives, works, ... — full list in PASSMARKS). Both checks
are case-sensitive: only lowercase occurrences fire.

`scripts/fable_loop150b_agent.py` stacks the mixin onto loop150 at both
levels (ears + pre-write), with the daemon wrapper (`idle_seconds`).

## Why titles still teach

Capitalised title words ("Gone", "Framed", "Stood", "Is", "May", "Lives",
"Born") never match the lowercase-only checks, so "Gone with the Wind was
written by Margaret Mitchell" and "Who Framed Roger Rabbit was created by
Robert Zemeckis" store exactly. Bare role nouns ("author", "director")
and verbless of-phrases ("city of", "capital of") are deliberately not
cues — they occur in legit single-fact subjects (possessive tails, role
phrases) — so "Rabbit's director" tails pass. Single-token subjects are
exempt (one token cannot swallow a clause). Values, relations,
forget/ask/clarify are untouched.

## Evidence and marks

Pre-seal pure-function scans (new loop never ran): 0/3775 bench teach
subjects fire; probe parses match predictions (23 refuse -> split, 24
must-write -> store); cases150 fires only where 150's earlier hearsay
screen pre-empts with the identical reply; f1-cases fires only on t14;
sessions/redteam98/rt110/cases136 fire nowhere. Registered marks: S1 new
49-case probe (23 refuses with 0 wrong writes; 24 must-writes >= 90 %
exact incl. 10 verb-titles; t14 refuses); S2 cases150 re-run identical;
G1 bench, G2 marks123 suites, G3 phone sessions identical to loop150
except written-predicted turns; G4 every run < 25 min Mac CPU.
Sealed in `artifacts/fable-subject150b-20260922/` (PASSMARKS.md,
cases150b.json, loop150b-config.json, SEAL.sha256.txt); predictions
P150b.* in the ledger before any run. A FAIL is FAIL with one diagnosis
note; no silent re-runs.
