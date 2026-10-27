# 157b — Capitalised fillers strip on loop157 (Muse)

## Problem
Exp 157 taught loop150 to ignore one lowercase leading filler ("btw
Marta's brother is Kai"). But phones capitalise the first word, so the
most common real form — "Btw ...", "Oh and ...", "So ..." — still fails
on loop157 (director probe 04:20: "Oh and Tom's mother is Rita.", "So
Tom's boss is Bob.", "Oh and Jo's teacher is Max.", "Btw who is Tom's
sister's teacher?" all refused). Cause: 157's title rule
(scripts/fable_fix157_filler.py:67-101, capitalised block lines 92-96)
only strips a filler typed all-lowercase or followed by a comma.

## Design
One change, as a mixin on loop157 (scripts/fable_fix157b_capfiller.py,
stacked by scripts/fable_loop157b_agent.py; loop157 imported read-only):
at ears hear(), try the unchanged loop157 hear first; only on
clarify/fallback, strip up to TWO leading fillers from the SAME closed
list as 157 (longest-match per step, any capitalisation, each optionally
comma-followed) and accept a remainder only if the unchanged loop157
chain parses it as a complete teach/correct/question. This covers single
capitalised fillers ("Btw", "Also", "So") and stacked pairs ("Okay so",
"Oh and btw", "And also"). Titles ("Hey Jude", "Also Sprach
Zarathustra", "So Far Away", "Well Played") need no special rule: their
remainders never parse as complete frames, so the gate rejects them.
Correction markers are untouched (base parses them first-try).

## Evidence (registered)
T1 60-case probe (34 cap-filler vs bare twins, 13 titles, 13
garbage/correction): see RESULTS.md. G1 bench 600/600 per-item identical
to loop157. G2 marks123 per-case identical to loop157's marks157. G3
sessions byte-identical to loop157's runs (0 moves). G4 all runs < 25
min Mac CPU.

## What it means / does not mean
Means: phone-style capitalised and stacked fillers now save and answer
exactly like their bare twins, with zero measured regressions. Does not
mean: the assistant understands titles or fixes any other refusal class —
anything whose remainder is not already a complete base frame behaves
exactly as on loop157.
