# 148b — Status-preserving question screen (Muse, 2026-09-22)

For Ben in plain language: last time, the assistant learned to shut up on
tricky questions ("Who is *not* married to Bram Kite?"), but it shut up in a
way the grading scripts couldn't see — like raising your hand without
saying "I don't know". Now it says "I don't know" through the same channel
as every other abstention, so all the old graders accept it. What you read
on screen didn't change by a single letter.

## Target

`scripts/fable_loop148_agent.py` (the exp-148 screen) over
`scripts/fable_loop134_agent.py` (shipped) and `scripts/fable_loop132_agent.py`
(Q1 arm). The defect (148 RESULTS diagnosis): a screen clarify is an
ears-level `{"act": "clarify"}` with no reasoner status, so status-based
judges score it differently — p3 L5-Z2's 37 never-items become NO_RECORD
(MISS) where the base had MISSING_FACT (abstain_ok).

## The one change

Three small classes in `scripts/fable_loop148b_agent.py` (148 imported
read-only, subclassed/wrapped, nothing edited):

1. `ScreenStatusMixin148b.hear` — detection copied from 148 verbatim (same
   "?" gate, same taught entity/value exemption, same sealed word list via
   `fable_screen148_mixin`, neg beats time). On a hit it parses the turn
   with the unchanged base ears and tags the ask `screen148b=neg/time`
   instead of clarifying. Statements skip the screen entirely.
2. `ScreenStatusReasoner148b.answer` (over `QualifierAwareReasoner77`) —
   tagged asks run the real lookup first (read-only, never writes). A
   non-OK verdict returns as-is plus a marker: MISSING_FACT is then
   literally true by construction (the store itself said so — this covers
   all 37 never-items, whose relations were never taught). An OK verdict
   (the qualifier-blind answer 148 screens) is replaced with an
   UNSUPPORTED_QUESTION refusal: MISSING_FACT would be literally false
   there, because the fact exists (e.g. L5-Z1 42/43 answer from taught
   year-named relations city_in_2019/job_in_2019).
3. `ScreenTextMouth148b.say` — marked records render 148's exact clarify
   text (imported, byte-identical); everything else falls through to the
   base mouth. Two thin subclasses carry the stack on each lineage
   (134 + 132 arms, each with its own daemon; `idle_seconds` default 30.0).

## Status honesty accounting (every judge that reads statuses)

- p3 L5-Z2 (`status in B65.ABSTAIN`): never receives the new status — all
  its screen hits are genuinely never-taught relations, so the reasoner's
  own MISSING_FACT flows through (37/37 abstain_ok, 0 MISS, verified
  per-item). No existing status but MISSING_FACT was ever literally true
  here (BROKEN_CHAIN/UNKNOWN_ENTITY/AMBIGUOUS are all false), so no new
  status was needed on this path.
- p3 L5-Z1 (exact status match): turns 42/43 observe UNSUPPORTED_QUESTION
  vs sealed OK — the sealed expectation encodes the old qualifier-blind
  answer, so the mismatch is predicted in PASSMARKS and stands as the only
  non-identical turns (58/60 otherwise identical, 0 wrong writes).
- Reply-text judges (P2/R98 `is_abstain`, RT110, 143-runner, benches, Q1/Q2
  drivers): see 148's byte-identical clarify text, so they abstain exactly
  as in 148 (P2-D8 BUG->OK preserved).

## Evidence

R1: Q1 0 verdict/reply diffs vs 148 (8/8 targets, 0/116 worse); Q2 20/20 +
20/20, 0 diffs. R2: 800/800 bench verdicts+replies identical to 148's rows.
R3: 148b-vs-134 marks123 differ only in D8 BUG->OK and L5-Z1 42/43
(UNSUPPORTED_QUESTION, predicted); L1-L4/L6, p4, rt110, q1, bench
per-item, rt81, sleep (SKIP, filename-only reason diff), soak, q4 all
verdict-identical. R4: 3.8/2.2/42.9/138.7+143.3 s, all < 25 min.

## Limits

English only; single deterministic runs; no sleep/thinker involvement. The
screen is still lexical (same false-positive profile as 148 — e.g. years
inside taught relation names still fire). The lookup runs silently on
screened turns to earn the honest status (side-effect-free; replies,
records, and writes are the refusal either way). Exempting year-tokens
inside taught relation names would fix 42/43 but changes the sealed word
list — a new experiment, not this one. 148's FAIL stands.

## What it means

Refusals now travel the same record path as every other abstention, so the
whole existing suite farm scores them correctly at zero user-visible cost.

## What it does not mean

It does not mean the two stale sealed expectations (L5-Z1 42/43) pass, and
it does not mean the assistant understands a single new word — the new
status names the refusal honestly, nothing more.
