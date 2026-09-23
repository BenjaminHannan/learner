# 139c — trailing chat words glued onto values (design)

Director probe 04:35 on loop138b: every trailing chat word is stored as
part of the value. "Tom's boss is Ann too" saves "Ann too"; "Tom's city
is Oslo actually" saves "Oslo actually"; "Mia's pet is Rex as well";
"Mia's school is Hill High though"; "Mia's coach is Dan lol"; "Mia's
town is Leeds btw"; "Mia's teacher is Max again"; and on a correction,
"Rex's color is black now" prompts "change it to black now?" and saves
"black now". This is a WRONG-WRITE class: the notebook holds junk the
user never meant as fact, and later questions repeat it back.

## The one change

Before the save path, strip from the END of the value a closed list of
lowercase chat tails, fixed in `scripts/fable_fix139c_tail.py` before
any panel read and nowhere else:

singles: too, also, actually, though, tho, lol, lmao, haha, btw, again,
now, anyway, then, instead, rn, right, ok, okay. pairs: as well, i guess.

Each is stripped only when typed entirely lowercase, optionally followed
by trailing punctuation/emoji (the exp-140 cleaner runs first and
exposes the bare word), and only when at least one value word remains
(a value that is just "too" is left alone for the downstream guards).
Stripping repeats for stacked tails ("Oslo too lol" becomes "Oslo"; a
leftover boundary comma goes too: "Ann, too" becomes "Ann").
Capitalised tail words are never stripped, so real names survive:
"Take That", "Let It Be", "Home Alone", "Say It Again", "Right Said
Fred", "All Right", "Right Now", "Me Too" all save exactly.

If the stripped tail was "now", "instead" or "actually" and the fact
already exists with another value, nothing special happens on purpose:
the strip runs before `super()._act()`, so the existing correction
prompt automatically carries the clean value ("change it to black?",
never "change it to black now?").

## Where it sits in loop138b

Step 1 locations. Value extraction: `scripts/fable_agent_loop.py:136`
(the FakeEars possessive path `value = found.group(2).rstrip(".")`;
loop138b wraps this with the exp-140 cleaner). 139b value guard:
`scripts/fable_fix139b_valueguard.py:99` (`screen_value_139b`),
applied per-action at `:118`/`:131` and called from loop138b's ears
`hear()` and loop `_act()`. The 139c mixin subclasses loop138b and
strips at two levels: ears `hear()` strips outgoing teach/correct
actions after the full 138b chain, and loop `_act()` strips before
`super()._act()`, so the 140 clean, the 139b veto and the 150 veto all
re-check the clean value. `turn()` is inherited verbatim; no loop138b
file is edited.

## Known edges (accepted)

Lowercase trailing "right" strips even in "all right" (the brief's
closed-list rule; the capitalised song "All Right" is untouched).
"Was that a question?" inputs ending in "?" were never teaches and are
unchanged. Sleep, daemon settle, and the L2 self layer are untouched.
