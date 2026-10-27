# 155 — Inverted teach frames (Muse)

Teach the loop to understand backwards sentences: "Rita is Ann's mother"
should save exactly what "Ann's mother is Rita" saves.

## Step 1 — the code responsible (found before sealing, nothing edited)

Canonical possessive teaches ("Ann's mother is Rita") are parsed by
`FakeEars.hear` in scripts/fable_agent_loop.py: the `_STATEMENT` regex
(line 96) splits the turn, `_chain` (line ~101) splits the left side on
`'s`, and lines 134-145 build the teach — but only when the left side has
exactly two parts (line 137-139: anything else gets "Please say it like
...") and the name is one word (line 141-142). So "Rita is Ann's mother"
(left side "Rita", one part) and "Rita is the mother of Ann" fall through
to "I didn't understand that", via the `ChainEars`+`FakeStage` path in
scripts/fable_loop90_agent.py (lines 173+). "The mother of Ann is Rita"
instead matches the LAST entry of `STATEMENT_PATTERNS` in
scripts/fable_bench73_english_arm.py (line 127: `The (.+?) is (.+?)` ->
officeholder), parsed by `hear_teach_template` (line 194) and taught by
`Loop121Ears.hear` calling it directly (scripts/fable_loop121_agent.py
line 185) — hence the wrong ("mother of Ann", officeholder, "Rita") write.
Exp 135 guards that catch-all in `hear_teach135`
(scripts/fable_fix135_office.py lines 175-191) by allowing only
table-derived office heads.

## Step 2 — the one change

`InvertedFrame155Mixin` (scripts/fable_fix155_inverted.py), stacked at the
outer ears level: "V is X's R." / "V is the R of X." / "The R of X is V."
saves (X, R, V) — but only when R is a relation cue from the loop's own
tables (cue-table keys + person table, 42 keys, minus the office family and
office-head nouns). Everything else (office phrases, unknown relations,
hedges, two-fact messages, questions) keeps the exact base path.

One-word names go through the literal canonical sentence ("Ann's mother is
Rita"), so guards, audit trail and replies match by construction; longer
names get the same structured action the bench path builds, screened by the
same three screens. Two configs: loop155 (on loop150) and loop155x135
(with the 135 guard, proving they coexist: the mother sentence saves while
president sentences behave exactly as on loop135).

## Step 3 — boundary cases (sealed)

boss/teacher/friend invert to their correct triples (the loop already
teaches them in canonical form). president/mayor/king/director/coach stay
on the base path (office heads or non-table keys). "who is ned's teacher"
(without "?") stays a question — the base answers it, and the mixin never
touches ask/forget paths. A FAIL is recorded as FAIL; results are in
artifacts/fable-inverted155-20260922/RESULTS.md.
