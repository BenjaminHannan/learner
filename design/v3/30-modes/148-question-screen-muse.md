# 148 — Question screen for meaning-changing words (Muse, 2026-09-22)

For Ben in plain language: the assistant used to ignore words like "not"
and years ("Who is *not* married to Bram Kite?" → answered the spouse
anyway). Now it checks every question for those words first and honestly
says it can't handle them, instead of answering as if they weren't there.
Normal questions work exactly as before. One side-effect keeps this a FAIL:
two old test suites still demand the previous (buggy) answers in two spots.

## Target

`scripts/fable_loop134_agent.py` (shipped arm) and
`scripts/fable_loop132_agent.py` (the exp-143 red-team target). The defect
(143 RESULTS classes 1-2): `compose_n_hop`
(`scripts/fable_bench92_english_arm.py:237-239`) never inspects negation or
date residues, so negated/time-qualified questions are answered as if the
word were absent.

## The one change

`QuestionScreenMixin148` (`scripts/fable_loop148_agent.py`) overrides only
`hear()`, and only on trailing-"?" turns with the notebook bound: it reads
the live notebook triples (`fable_loop90_agent.notebook_triples`), removes
taught entity/value mentions from the question, and scans the remainder
with sealed regexes (`scripts/fable_screen148_mixin.py`). First hit wins —
negation message or time message — returned as `clarify`; no composer or
lookup ever runs. Statements skip the screen entirely (byte-identical base
path). Unscreened asks pass through untouched, so base-correct answers stay
correct by construction. Two thin subclasses carry the mixin:
`Loop148Ears134` (shipped) and `Loop148Ears132` (Q1 arm).

## Word list (sealed with reasons in PASSMARKS.md)

Triggers: not, never, n't, "no one", nobody, none; 4-digit year, "as of",
before, after, formerly, originally, "used to", currently. Deliberately
excluded: bare "no" (correction prefix + titles like "No More Heroes"),
"now"/"still" (current-fact semantics — answerable), neither/nor/nothing
(no evidence), substrings inside tokens (Knot, Notre-Dame, Norway,
Annotated never match), year-tokens inside taught mentions (1984, Windows
2000, Can't Buy Me Love name things, not times).

## Evidence

Q1: all 8 red-team targets clarify; 0 of 116 other cases worse. Q2: 20/20
trigger probes clarify (the base answered every one confidently — the screen
did the work); 20/20 innocents byte-identical. Q3: 800 bench verdicts
identical; only the 37 predicted never-taught items changed reply text
(verdict abstain either way). Q4 FAIL: P2-D8 fixed as predicted and all
other suites identical, but p3 L5-Z1 seals OK on two "in 2019" questions
(the old bug, verbatim) and L5-Z2 scores the 37 never-clarifies MISS —
both because an ears-level clarify carries no reasoner status (NO_RECORD),
which status-based judges don't count as an abstention. Zero wrong writes
and zero bench wrongs throughout; the failure is record plumbing plus stale
expectations, not new wrong answers.

## Limits

English only; single deterministic runs; no sleep/thinker involvement. The
screen is lexical, not semantic ("not" inside an untaught name it hasn't
seen still fires; paraphrased scope like "outside of 2019" is uncaught).
A status-preserving refusal (MISSING_FACT record) is the natural follow-up
and needs its own experiment — this FAIL stands.

## What it means

One pre-composer word check removes the two most user-facing wrong-answer
classes (negation, time qualifiers) at no cost to intact questions.

## What it does not mean

It does not mean the assistant can reason about negation or time, and it
does not mean every old suite accepts the new refusal — p3 L5 still wants
the old behaviour in three dozen spots.
