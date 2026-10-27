# 137e — one hearsay reply (Muse, 2026-09-22)

## Problem

Loop137d ends framed WRONG-WRITEs but speaks two hearsay replies: its
new sealed sentence for sentence-initial framings ("Supposedly ...",
"Apparently ...", "They say ...") and loop102's old HEARSAY_MSG ("Do
you know that yourself, or did you hear it somewhere? I only save
facts you tell me directly.", `scripts/fable_loop102_agent.py:70-71`)
for trailing/base hearsay ("Nia's boss is Obi, I heard."). Seven
frozen judge checks expect the old sentence everywhere, so 137d
records FAIL on G2/G3 while storing nothing. Ben's frame rules treat
all hearsay alike: one input class deserves one reply.

## Design

`Loop137eEars` subclasses `Loop137dEars` (mixin, no base file edited).
`hear()` asks the 137d closed-list matcher `frame_kind` first: on
"hearsay" it returns one clarify carrying HEARSAY_MSG imported
read-only from `fable_loop102_agent` (same object, never retyped);
every other turn falls through to `super().hear()`, so the Say-group
echo + pretend parenthetical, the 137c hypo guard, and the whole base
pipeline render byte-identical to loop137d. Framed turns never reach a
teach path (0 writes); follow-up questions answer only from real saved
facts. Mouth, reasoner, sleeper, thinker, daemon settle: inherited
unchanged; `Loop137eDaemon` only swaps the builder and keeps
`idle_seconds`.

## Why this shape

The 7 frozen checks compare reply text, not stored triples. Restoring
the exact old sentence (rather than updating the judges, which stay
frozen as witnesses) reunites the class: leading, trailing, and
base-path hearsay all get HEARSAY_MSG. The Say group is untouched on
purpose -- pretend-echo stays distinct from hearsay-decline.

## Marks (summary; bars in PASSMARKS.md)

T1 reuses 137d's sealed cases by import (Say identical to 137d,
hearsay == HEARSAY_MSG); T1b adds 31 new dialogues (19 hearsay incl
lower-case/filler/trailing/base varieties, 12 identical teaches/Say);
T2 0 framed writes. G1 bench 0 moves (scan: 0 fires/800). G2
per-case identical to marks137c (scan fires only where 137c already
replies HEARSAY_MSG, except p2-A4's turn-1 text which the p2 row does
not record). G3 0 moves everywhere (the 7 broken checks return). G4
< 25 min each, daemon `idle_seconds`.

## What it means

Every hearsay framing the agent catches gets one fixed reply and
stores nothing; pretend-Say keeps its echo; all regressions match
loop137c per-case.

## What it does not mean

Not a change to what counts as evidence (framed content is refused,
never modelled); "my friend says ..." is still a plain decline, not
hearsay, on both agents.
