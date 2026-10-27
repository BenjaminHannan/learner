# 121 — Teach-side phrasing coverage for the joined-up agent (Muse, 2026-09-22)

For Ben in plain language: the assistant kept saying "I didn't understand"
to three ordinary ways of telling it facts ("works in the field of", "is
employed by", "X's child is Y") and choked on country names containing
"and". This experiment teaches it those three phrasings and lets "and"
through inside a single proper name — while packed two-facts-in-one lines
are still refused. 22 old rejects → 0; new unseen sentences nearly all teach.

## The one change

`scripts/fable_loop121_agent.py` (new; wraps `scripts/fable_loop113b_agent.py`,
which another agent finished first — so the 113b wrapper was used, not the
loop102 fallback). `Loop121Ears` handles non-"?" turns by mirroring the
loop102 pre-filter phase-for-phase (hearsay, correction prefix, forget,
qualifier strip) with two differences, both teach-side:

1. The teach match tries bench73 first; only on `None` does it try exp-92's
   EXTRA patterns (employer / occupation / child, imported read-only). A hit
   becomes the exact structured teach/correct action `Bench73Stage` builds
   (same notebook correction detection), screened by the exp-91 value screen.
2. The value screen gains one narrowing: the >6-word screen passes a value
   that is a single capitalised name span (every token Title-Case, lowercase
   glue only "of"/"and", contains "and"). The "?", ";", possessive-is,
   and-possessive and second-copula screens are untouched — "Mira's city is
   Oslo and Tom's pet is a cat" still refuses (possessive-is + second copula).

"?" turns delegate byte-identical to loop113b (N-hop router + loop102
fallback). Scorer v2 reused unchanged from exp 113.

## Evidence (sealed P121.1–P121.5: 2/5 TRUE)

Blind split first: 200 fresh 4-hop items, seed 121, zero case overlap with the
two old splits, sealed before marks; sentences never opened (only n=200 and
the relation histogram). Registered bench: new split 136/63/1 with 1 teach
reject in 1 item (T1, T2 PASS); old fresh 157/43/0 with 0 rejects (T3 PASS —
all 22 gone, and the 5 old confident-wrongs fixed since their chains now
teach fully). T4 PASS: R110 L1/L2/L4 + the brief's literal probe all refused
with zero writes. T5 FAIL on P2 only: B7/D8 OK→BUG, C2/C5 still-BUG —
ID-identical to the 113b base's own sealed P2 (conflict/forget/qualifier
questions the N-hop composer answers); the teach change adds zero moves.
P3 (all 7) and P4 (0 refusals) pass.

## Limits

The one residual new-split wrong is a teach-gap partial (same class as
exp-113's): a blind phrasing outside the three added shapes. The 4 P2 cases
need a question-side abstention rule (conflict/forget/qualifier-aware) — a
different one-change experiment, not this one.

## What it means

Teach coverage for fresh phrasings now works through the real mailbox, and
the guard still blocks packed facts: coverage up, safety unchanged.

## What it does not mean

It does not mean the loop regressed nothing — T5's P2 FAIL stands as
recorded (inherited from the wrapped base), and it does not mean every
future phrasing will parse (one blind item already shows the next gap).
