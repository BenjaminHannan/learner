# 166c — Title-case-only display fix, registered cleanly (Muse)

## Problem

Exp 166 (first-person "my" on loop162b) is a registered FAIL on G3 only:
"My dog is biscuit." stores the value entity's display lowercase, so three
later S4 replies render "biscuit's ..." where loop162b renders "Biscuit's ..."
(verdicts all OK). Exp 166b tried the display-case fix and is a registered
FAIL kept as FAIL: its registered G1 run moved 4 bench teach replies
("judo" matched inside "World Judo Championships"), the adjacency guard was
added after the seal, and the marks re-ran in the open. Then the director's
08:27 probe on the guarded loop showed a second hole: "My friend is ana." +
"ANA's city is Rome." renders "Your friend is ANA." -- an ALL-CAPS shout
must never become the display name. 166c registers the whole feature
cleanly, with both guards, sealed before any run.

## Design (one change vs loop166)

`Loop166cAgentLoop` (scripts/fable_loop166c_agent.py) is a mixin subclass of
loop166's loop with the same ears (`Loop166Ears`); no 166/166b/162b/contract
file is edited. After each turn, for every entity whose stored display is
all-lowercase, a per-loop override `{entity_id: Title-case form}` is
recorded when the turn contains a mention that (a) differs ONLY in letter
case, (b) is Title-case -- first letter uppercase, NOT all letters
uppercase; multi-token names need EVERY token Title-case; a single capital
letter counts -- and (c) stands as the whole name: a match adjacent (spaces
only) to another capitalised word is rejected. Clause (c) is 166b's
adjacency guard, copied with attribution; clause (b) is new in 166c. Said
lines are rewritten with the override from that turn on. The notebook event
log stays append-only (the contract has no display-rename event: ENTITY sets
the display at fable_notebook_contract.py:196-198, ALIAS at :279-286 never
changes it). Matching stays case-insensitive, so entity ids, stored triples
and fact_writes are byte-identical to loop166 on every turn -- only the
rendered capital letter can change.

## Why this shape

The display lives in three places (sets: `new_entity`; renders: `_show`,
`assert_fact`/`ask`, `FakeMouth.say`), all copying the stored string
verbatim, so an agent-layer override map is the smallest additive fix that
touches no existing file. Restricting to Title-case (rather than 166b's
"first letter uppercase") is exactly the director's probe: shouts differ
from names only by being ALL-CAPS, and genuine mentions in this system
(teaches, answers) are Title-case. Scanning every match per turn (rather
than first-match-wins) means a shout cannot shadow a later genuine mention.

## Evidence

Sealed PASSMARKS + cases before any run; ledger P166c.1-7. T1 52/52
byte-identical to loop166. T1b 30/30 OK, verdicts identical to loop166b's
open re-run (0 mismatches). T1c 24/24: 8 shouts (incl. ana/ANA) and 8
embeds byte-identical to loop166 with lowercase display intact; 8 genuine
Title-case upgrades fire visibly. T2: 0 wrong writes, 0 new entities (106
cases). G1: 600/600 verdict+reply identical. G2: per-case identical to
marks166 except one verdict-identical rt110 R5 log-only race line, confirmed
by an open re-run showing the same line (both reported). G3: exactly the 3
predicted S4 returns byte-identical to loop162b ("Biscuit" is genuine
Title-case, so the fix still fires there), 0 other moves. G4: max run
187.6 s. No post-seal edits; seal re-verified clean.

## Limits

Only same-letters case variants count ("Biscuits" never matches); names
never upgrade from lowercase mentions or from inside longer titles; single
capital letters count as Title-case (needed for one-letter names); the
override is per-loop memory, not notebook truth, so a fresh loop starts
from stored displays again.

## What it means / does not mean

Small-letter names take their capital from the first genuine Title-case
mention on, everything else byte-identical to loop166. It does not guess
names, never rewrites the notebook, and shouts never rename.
