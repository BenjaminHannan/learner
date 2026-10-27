# 130 — Sleep grows one word slot (registered follow-up to exp 115)

Exp 115 proved the daemon installs 3 relations with zero forgetting, then
stops exactly where the architecture ends: relations 4-5 (boss_of_father,
teacher_of_spouse) have no word slot (R44 N_WORDS=3), so no episodes queue
and the model honestly abstains (0 wrong). This doc makes exactly one change:
when every slot is taken, sleep may ADD one slot.

## The one change

Grow the word/code table by one row per new relation, initialised by the same
rule the recipe uses for its existing slots (torch.zeros, verbatim from
Reasoner.__init__), and train only the new row with the certified recipe:
robust loss eps=0.10, harden phi to argmax +/-30 after each fold fit and the
refit, 4-fold CV gate (OOF >= 0.80, refit agreement >= 0.90, old skills
unchanged, reload identical). Every existing slot and skill weight is frozen,
verified by sha256 of each tensor before/after every sleep (frozen_ok in each
recipe row; a grown sleep with a moved frozen tensor reports installed=False).

Everything else is unchanged: episode collection (same walk-and-queue rule,
widened to the new chains), gate floors, install audit (non-keep stages in row
order must equal the chain's skill indices), daemon wiring, atomic word file.

## Why this shape

The live reasoner already stores words in a dict (unbounded) -- the cap lives
only in the R44 training table (ParameterList of 3) and in 115's 3-word feed.
So growth touches only training: a K-slot GrowModel with R44's maths
generalised (K=3 reproduces R44 exactly), and a feed that queues episodes for
the new chains. When every requested word has a free sealed slot the code
delegates to the 115/wire57 path untouched -- that is the G3 byte-identical
guarantee, by construction rather than by hope.

## New relations (all inside the 8 sealed skills)

4 boss_of_father = father+boss [2,4]; 5 teacher_of_spouse = spouse+teacher
[3,8]. Climb extras (all two-hop, all distinct pairs): mother_of_spouse
[3,1], boss_of_mother [1,4], teacher_of_father [2,8], doctor_of_spouse [3,7],
father_of_mother [1,2], doctor_of_boss [4,7], teacher_of_mother [1,8].

## Marks (sealed in artifacts/fable-sleep130-20260922/PASSMARKS.md)

G1: 115's L4 verbatim (400 turns, 5 sleeps, seeds 1-2): all 5 install, 25/25
probes, 0 wrong, 0 wrong installs, 0 taught overwrites; growth fires exactly
in sleeps 4-5. G2: first 3 words stay 15/15; frozen hashes bit-identical after
every sleep. G3: 115's L1-L3 outcomes byte-identical (timing excluded), growth
never fires. G4 (unregistered): 8 over 8 sleeps, then 12; per-sleep seconds
and break point reported. G5: wave < 30 min (seeds parallel, OMP=1 each).

## What it means / does not mean

Means: sleep can extend its own vocabulary without touching what it already
knows, one frozen-preserving row at a time. Does not mean: sleep decides what
it needs (still a turn counter), unbounded growth is safe (G4 climbs until it
breaks -- watch gate floors and latency, not just installs), or latency is
predictable on a shared Mac (report per-sleep seconds, never average them).
