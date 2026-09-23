# 147 — Mention-walk alignment (Muse, 2026-09-22)

For Ben in plain language: the assistant used to read a question, walk the
taught facts all the way to the end, and then check "did I walk past
anything the question didn't mention?" — but never the reverse. So "Who is
Joren Hale married to?" (with Petra's citizenship taught too) got "I didn't
understand that", while "What country is the spouse of Bram Kite a citizen
of?" (spouse only taught) confidently answered the spouse. One fix to the
question walker repairs both directions, plus the "Who developed HarborOS?"
type mix-ups, with zero regressions across 124 red-team cases, 1,000 bench
items and every regression suite.

## The bug (doc 143)

`compose_n_hop` (`scripts/fable_bench92_english_arm.py:198-240`) walks from
the single mentioned entity to the chain's sink, then demands
walked ⊆ mentioned. Consequences: (a) suffix blindness — a 1-hop question
fails whenever the taught chain continues (P1/P2/Q1/Q2/D2 MISSED);
(b) short-chain prefix answers — an asked-but-untaught hop is dropped
while the taught prefix is answered (class 3: A1/U1–U5/K8/S4/T4/L4);
(c) cue-stem type mismatches — "developed"/"created" cue several relations
and the walked one is answered regardless of the wh-word (class 4:
K6/K10). The 2-hop sibling (`fable_bench73_english_arm.py`) shares the
one-sided gate. Teach path, notebook, fallback and rewriter are untouched.

## The one change

`scripts/fable_align147_compose.py` (new) + `Align147Mixin` layered on
loop134 / loop113e / loop132 (new wrappers, subclass only). The mixin swaps
the two composers in around one `super().hear()` call (try/finally
restore — no global leak, verified by selftest). The aligned walk stops at
the first unmentioned hop; the prefix asks only when (1) every walked hop
is mentioned, (2) the wh-word's class fits the terminal hop (who→not a
place, where/country/city/capital/language→not a person), and
(3) every extra mentioned relation is tolerated: shared-stem ambiguity
("leader" beside walked head_of_government), subordinate modifiers
identifying a chain node ("the music played by Harborlight Choir"),
fragments of schema-implausible hops ("develop" beside a walked origin
ending at a place). Whole-word main-clause evidence of an un-walked hop
("a citizen of" beside a walked spouse) always blocks. Entity classes come
from the taught graph itself (spouse endpoints are persons), no ontology.

Mention definition deltas (same substring scan otherwise): possessive
"country's" counts as citizenship (D2); weak cues count only on-chain
("where"→origin, "located"→headquarters, "son"→child, "house",
"city where", "develop"→developer, "created"→creator); bare "found" never
cues (whole "founded"/"founder" still do); unteachable keys dropped
(creator_country, founder); cue spans inside entity names ignored
("... Markup Language"). Each delta is tied to a sealed case that is
otherwise unsatisfiable in both directions (details in RESULTS.md).

## What it does not do

Negation (N1–N5), qualifiers (T1/T5/B1 "in 2019"/"as of"), substring
entities (O3), typo/missing-"?" gaps (H3/J5/J8–J10) are unchanged — still
wrong/missed exactly as on the base, listed as still-open follow-ups (doc
143's screens). No new wrong answer anywhere: every abstain the base got
right is kept, every intact chain still answers.

## Integration

Three variants share the one mixin: loop147 on loop134 (this experiment),
on loop113e and on loop132 (integration stack). All three report all
suites; A1 is registered on the loop132 variant.

## What it means

Question understanding now matches the asked chain against the taught
chain in both directions: continued chains answer the asked hop, short
chains abstain, shared cue stems defer to the wh-word.

## What it does not mean

It does not mean the assistant understands negation, dates, or typos — any
extra word with meaning outside relation vocabulary is still invisible —
and it does not mean teaching changed (all teaches reply byte-identical).
