# ch07 notes: The talker ("Writing down the answer")

12 scenes, 473 s (+5 s title card). Audit: 0 flags. `hyperframes check`: passed (4 info lines: the "____" blank in s10 is covered by the "mat" box on purpose).

## SOURCES READ
- architecture/FINISHED-MODEL-2026-10-09.md sec. 1, 2 (Talker row), 3, 4 (tables: Span copy rules, Word splitter, Last letter first; lines 79-85), 5 items 2-4, 11, 12. Decides every "how it works today" fact.
- custom_io/models/tool.py @17a356e62 (docstring 18-20, 33-41; answers() 407-416; line 510 cut to 8), custom_io/models/ledger.py:70-72 (9 registers = 8 letters + end mark), custom_io/data.py:109, custom_io/g8a/caps_b3.json (max_ans 35), custom_io/capcount.py:17.
- architecture/redesign-ideas-2026-10-07.md sec. 6 (lines 91, 92, 94); notes/hearer-talker/RESULTS-SMALL-LM.md lines 8-16; reader-talker-compare/RESULTS-CT.md lines 8-18; big-run/PLAN.md lines 77, 87, 139, 148, 149, 284-285; idea-swarm/raw/areas/talker.json.
- Earlier chapters (ch01, ch03, ch04, ch05, ch06, ch09 json) for names and numbers already on screen.

## NUMBERS AS WRITTEN IN SOURCES
- 91.5% of answers, 98% of written operands: FINISHED sec. 4, Span copy row (shares of uses, not accuracy).
- 8 answer letters, 0 of 200,000 training answers over 8, 35 letters under caps_b3: FINISHED sec. 4 lines 79-83; caps_b3.json.
- 373.1M = 271.0M frozen Gemma + 102.1M trained; ~25M English talker (planned): FINISHED sec. 1.
- 66.1 vs 92.6: RESULTS-SMALL-LM.md lines 10-11 (350M system vs 1.2B system, 192 fresh questions, 6 paired seeds). 13.6 vs 78.2: RESULTS-CT.md line 15 (copy talker vs all-pointer talker, 384 unseen-kind questions, 6 paired seeds).
- 73.01 / 0.66 (G1 3M seed 400, 6,040 questions) and 18.09 (EGE, seed 200, familiar questions): FINISHED sec. 5 item 2.
- 84% web / 16% our own text: PLAN.md line 149 (plan figure, measured in word pieces).
## NUMBERS I COMPUTED
- Strip widths in s07 are drawn to scale from 271.0 : 102.1 : 25 (picture only). The 373.1M total is as written in FINISHED sec. 1, not recomputed.

## DISAGREEMENTS
- Brief recap said "copy talker tested at small size". No talker-only test exists, so the recap chip says "ran in 3M tests, never alone".
- Brief's "66.1 vs 92.6" and "13.6 vs 78.2" are two different tests of an older (1.2B reader) design. Shown separately, labelled older, not today's talker.
- ch09 s07 labels the talker's input "notes"; FINISHED sec. 5 item 4 says the talker reads the thinker's final state. ch07 follows FINISHED.
- Planned total with a 25M talker: 397M (FINISHED) vs 398M (PLAN line 148). Not shown. PLAN row 8 races the 30M model (~301M whole); FINISHED keeps the 100M thinker. Video does not say which size races.
- PR #54 talker numbers appear only in the memory index, not in checked files. Left out.
- Length: 473 s is above the pilot's 330-420 s aim; kept because the project owner asked that the chapter carry all the information. Heaviest scenes: s04, s06, s08 (44 s).

## ILLUSTRATIONS
- s01 "10" and the vector strip (shading is decoration); s02 all three examples; s03 reply strings and the 0/1 digit boxes; s05 "yes"; s06 "umbrellas"; s10 "The cat sat on the mat". Each carries a "made-up" chip.

## NEW TERMS
- "span copy" (s02-s04) and "stand-in" (s01) are introduced here; "stop head" is reused from ch05 and kept apart from the stop switch.

## KIT REQUESTS
- None needed. Local code only.
