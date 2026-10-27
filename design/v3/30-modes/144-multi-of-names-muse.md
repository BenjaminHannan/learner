# 144 — Multi-"of" names are one fact (Muse)

## The problem in plain words

Ben teaches "Charles M. Schulz is famous for The Protocols of the Elders
of Zion." The assistant refuses — "I can take one fact at a time, could
you split that?" — and stores nothing. Shorter titles ("The Lord of the
Rings", "The Protocols of the Elders") save fine. Because the edit never
lands, the old fact stands and a later 4-hop question answers wrong
(bench132-4hop-022 answered Washington, D.C. instead of Charleroi).

## Step 1: why this sentence triggers it (found before sealing anything)

The reply text is `SPLIT_MSG` at `scripts/fable_earsguard91.py:34`,
returned by `screen_value()` at `fable_earsguard91.py:53-60`. The parsed
value "The Protocols of the Elders of Zion" is 7 whitespace-separated
words, and the rule refuses any value over 6 (`MAX_VALUE_WORDS` at
`fable_earsguard91.py:45`, check at `:58`). There is no "of"-counter
anywhere in the codebase — the director's "two of-phrases" pattern is a
side effect of word count (each extra "of X" adds two words). Loop121
added a Title-Case-name exemption (`fable_loop121_agent.py:78-99`) but it
requires the word "and" (for names like "United Kingdom of Great Britain
and Ireland"), so a pure-"of" name refuses at
`fable_loop121_agent.py:117` and again at `fable_earsguard91.py:58` on
the fallback path. Probes confirmed: 5-word values pass, the 7-word
value refuses, on the live loop129b.

## The one change

Rule: a message counts as multi-fact only when the extra part is itself
a complete teach frame — its own subject (a capitalised span) plus a
relation cue plus a value — not when "of"/"of the" merely continues a
capitalised name.

`scripts/fable_fix144_ofname.py` implements `screen_value_144()`: the
loop121 screen, except the >6-word clause also passes a value that (a)
is one capitalised name span (tokens start uppercase or are lowercase
glue "of"/"the"/"and", and the span contains "of") and (b) embeds no
complete teach frame. Every other screen ("?", ";", possessive-is,
and-possessive, second copula) refuses exactly as before, so genuine
two-fact messages still refuse — each carries a second copula (or
";"/possessive), and each embeds a complete frame ("the capital of Peru
is Lima"). Copula-free joins ("Cats and Tom died in the city of Oslo")
fail the name-span test and trip a verbless-cue backstop
("died/plays/speaks/works/written-in-the-language-of" with a capitalised
subject before and a value after).

`scripts/fable_loop144_agent.py` (same style as `fable_loop140_agent.py`)
stacks it on loop129b: `Loop144Ears` runs the exact loop129b path first
and only upgrades a single SPLIT clarify — when the turn re-parses as
one teach (bench73 first, else exp-92 extra patterns, same preprocessing
as loop121) whose value passes the new screen — to the structured
teach/correct the chain would have built. All other turns are
byte-identical, stage tags included. The loop class and `_act` path are
inherited unchanged, so writes get the same punctuation sanitize as
loop129b. No existing file is edited.

## Evidence and limits

Pre-seal scan of 5,863 suite/bench turns flagged exactly two sentences
needing the new door (bench132-022 and bench121-069, the same edit
shape); both flipped wrong->correct in the registered runs and nothing
else moved. Sealed F1: 26/26 must-write exact, 19/20 two-fact clean.
The one miss (t14) is a pre-existing loop129b wrong write, verified live
on the base loop: the place_of_death template matches before famous-for
and the guards never inspect the subject, so a second fact hiding in the
subject slips through. That is a subject-side bug this change does not
claim to fix. Marks123 suites are per-case identical to the loop129b
reference; every run took seconds (bench ~20 s, marks123 ~134 suite-s).

## Connection to neighbours

Exp 146 (refused-correction doubt) treats the same 022 refusal from the
other side: 144 removes this class of refusal, 146 abstains honestly
while any refusal still stands. Exp 139b's and-name work is untouched.
