# 157c — Filler+Capitalised title guard on loop157b (Muse)

## Problem
Exp 157b taught loop157 to strip capitalised/stacked fillers ("Btw
Tom's sister is Jo."). But the strip
(scripts/fable_fix157b_capfiller.py:59) fires whatever follows the
filler, so a leading capitalised name word is eaten too: director probe
05:30 shows "Hey Jude's singer is Paul." saving under "Jude" and "Oh
Brother's director is Joel." saving under "Brother" — WRONG-WRITE class.
The parse gate cannot save these: the shortened remainder ("Jude's
singer is Paul.") is a complete frame.

## Design
One change, as a mixin on loop157b
(scripts/fable_fix157c_titleguard.py, stacked by
scripts/fable_loop157c_agent.py; loop157b imported read-only): a pure
gate, blocked157c, checks the turn-initial filler (same closed list, any
capitalisation). A capitalised filler (as typed, not all-lowercase)
followed directly — no comma, period, !, ?, ellipsis, dash, or other
punctuation — by a Capitalised word blocks the strip; blocked turns
return the deep loop157 parse of the original turn, so the whole
capitalised run including the filler word is treated as the name, exactly
as loop157b treats any other multi-word name (refuse/clarify; refusing
is fine, a wrong save is not). Everything else delegates to loop157b
byte-identically: lowercase fillers ("btw Tom's..."), comma fillers
("Hey, Kim's..."), punctuation follows ("Oh. And also..."), lowercase
follows ("Btw who is..."), stacked pairs, corrections. Cost of the rule:
capitalised filler + capitalised name with no comma ("Btw Tom's...") now
refuses instead of saving — the safe direction; comma or lowercase forms
still save.

## Evidence (registered)
T1 56-case probe: 22/22 titles never shortened (refused or full-name),
22/22 punctuation/lowercase-follow fillers identical to loop157b,
12/12 others identical; T2 0 wrong writes. G1 bench 600/600 per-item
identical to loop157b. G2 marks123 per-case identical to loop157b's
marks157b. G3 sessions byte-identical plus redteam136/143 two-arm 0
moves. G4 all runs < 25 min Mac CPU. See RESULTS.md.

## What it means / does not mean
Means: name/title leads that collide with filler words ("Hey Jude",
"Oh Brother", "Well Charlie") can no longer be silently shortened into
wrong saves, with zero measured regressions. Does not mean: the
assistant understands titles — blocked turns refuse rather than save
under the full name — nor does it change any other refusal class.
