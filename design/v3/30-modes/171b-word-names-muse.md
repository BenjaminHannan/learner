# 171b — Word-names save (Muse, 2026-09-22)

Exp 171 closed the description-as-name wrong-write class ("Kim's mom is
sick." now clarifies, 0 writes) with a first-word rule: a name-relation
value whose first word (lowercased) is a dictionary word, determiner, or
place/time adverb is refused. The next morning's director probe (08:40)
showed the rule over-fires: "Zed's boss is Ora.", "Bo's friend is Hope.",
"Tia's brother is Rich.", "Rae's dad is Grant." all clarify — even when the
agent itself just asked "What is Zed's boss's name?". The cause is
structural: givennames171.txt holds 200 names; wordlist171.txt holds
210,675 dictionary words, and many real names (hope, grant, rich, ora,
faith, iris, pearl, sky, rowan, sage, dawn, reed, jade, joy, …) are in it.
Any name that is also an English word is refused. That is the false-refusal
class this experiment closes, with one change.

## The one change

A name-relation value (the same 21 sealed keys as 171) that consists ONLY
of 1–3 Title-case tokens counts as name-shaped and saves exactly like any
real name — even when its lowercase form is a dictionary word — EXCEPT the
sealed closed list (62 state/place/time words), which stays refused with
171's exact clarify. A Title-case token: first letter upper, rest lower,
letters/apostrophe/hyphen only (so "Mary-Kate" and "O'Brien" pass; "JO",
"Hope2", four-token values fail). Any determiner token, any adverb-led
first word, and any lowercase word anywhere fall through to 171's rule
verbatim. So "Hope", "Hope Grace", "Lady Macbeth" save; "Sick", "Here",
"A nurse", "sick", "Queen Sonja of Norway", "actually Ana" refuse.

Why Title-case is the right signal: taught names keep their case through
the ears (verified: "Zed's boss is Ora." parses to value "Ora"), while
genuine descriptions in chat are lowercase-led ("is sick"), determiner-led
("is a nurse"), or contain lowercase words ("Really nice"). The closed list
covers the residual overlap — adjectives and place/time words a user really
does type capitalised ("Tomas's father is Sick."). Multi-token values match
whole against the list, so "Hope Grace" saves while "Sick" refuses.

## Hook points (unchanged from 171)

`NameVal171BMixin` subclasses 171's mixin and bypasses ONLY its guard via
explicit super (resolving to the exact inner-138d-chain target the 171
guard itself delegates to — verified byte-identical delegation on all 44
T1 identical cases), then applies the 171b screen in `hear` (rewrites
refused teach/correct to the same sealed clarify after the inner chain
runs) and `_act` (re-checks before the write, covering structured paths).
Reasoner, notebook, sleeper, thinker, daemon shape inherited from 171.
New files only: `scripts/fable_loop171b_agent.py`,
`scripts/fable_fix171b_{nameval,probe,bench121,g3}.py`,
`artifacts/fable-nameval171b-20260922/`, this doc. 171's files untouched.

## What the evidence showed (dev runs, pre-seal)

T1 76/76 byte-identical to 171's sealed rows: the six Title-case clarify
cases (Sick/Tall/Mean/Brown/Here/There) are all real descriptions and all
on the closed list — holding them is right. G1: "Lady Macbeth" chains
(099/067) heal to correct while "Queen Sonja of Norway" (lowercase "of")
still abstains — the rule draws exactly the intended line. G2/G3: zero
verdict or reply moves vs 171 anywhere (the M3 rt143 counter and session
writes are 138d's own rows, unchanged). T1b 46/46: 20 word-names save and
answer, 18 descriptions refuse, 8 identical.

## Residual risks (not fixed here)

Single-token surnames on the closed list ("Young", "New", "Brown") still
refuse — a known, listed trade-off favouring 0 wrong writes; multi-token
uses ("Young Lee") save. Titles save ("Lady Macbeth") while 171 refused
them: intended, since the chain answers verify correct. ALL-CAPS and
digit-bearing values fall through to 171's rule.

## What it means

Word-names that are also English words save and answer again — including
as the reply to the agent's own "What is X's name?" — while every
description 171 refused still refuses, and bench/marks/junk/sessions match
171 except the two healed "Lady Macbeth" chains.

## What it does not mean

This does not learn new names (the given-names list is untouched) and does
not touch 138d's inherited inverted-frame wrong-writes or the "Queen
Sonja of Norway"-style abstain — phrases with lowercase words still refuse.
