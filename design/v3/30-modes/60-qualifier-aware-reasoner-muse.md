# 60 — Qualifier-aware reasoner (experiment 56 design)

## Problem

Thought rows v2 (doc 49) attach qualifiers to claims: "Acme" is where Ann
works *in 2019*; "Oslo" is where Fay lives *at 300 K*. The v1 projection
`to_v1()` drops qualifiers by design, so the two consumers of v1 rows over-
answer: reasoner50's lookup views include qualified rows unconditionally, and
livesleep52's miner turns OK answers into sleep episodes whatever row produced
them. A year-less question gets a year-bound answer; sleep installs words that
fire with no year attached.

## Decision

Gate at read time, never at write time. Nothing stored changes; the notebook,
its hash chain, source priority and supersede rules are untouched. Two new
plain-software modules, both additive:

- `scripts/fable_qual56_reasoner.py`: `QualifierAwareReasoner`, a subclass of
  reasoner50's reasoner that re-runs the identical hop loop (same statuses,
  fields, BAD_REQUEST/Ambiguous/unknown-entity paths, learned-word stage
  tables, 0.9 threshold) over per-(hop, relation) qualifier-filtered views.
- `scripts/fable_qual56_miner_filter.py`: `filter_qualified_turns(turns,
  notebook)`, pure, applied before `mine_episodes()`.

## Rules (Ben's ask gate, extended to hops)

1. A row with qualifiers is used only when the question's qualifiers match:
   exact match on qualifier type+value (relation string normalized for case/
   spacing; value compared exactly as entity id or literal text). Otherwise the
   hop abstains with MISSING_FACT plus `reason: qualified`.
2. An unqualified taught row always beats a qualified one for the same
   (subject, relation), even when the question matches the qualifier. The
   unconditional fact is the safer answer.
3. Hops never pass through qualified rows unless the question is qualified.
   Qualifiers may be one dict (applies at every hop) or a list parallel to the
   relations for per-hop conditions.

## How the view filter works

Per hop and relation: collect active answering-source facts (same set
reasoner50 sees), read each row's qualifiers via `ThoughtV2.from_v1` (rows
without embedded v2 degrade to qualifier-free, so legacy rows answer exactly
as before), drop non-matching qualified rows, apply the unqualified-taught
priority, then the contract's best-source-first/newest order, then build the
same single/multi entries. A miss caused by gating carries the `qualified`
reason; a miss with no rows at all carries none, so the two are
distinguishable downstream.

## Miner filter

`chain_passes_through_qualified` walks (start, chain) through the notebook's
answering view exactly as the contract would (best-source first row per hop)
and reports whether any hop's winning row is qualified. The filter drops
`ask`/`correct` turns whose chain does, keeps everything else, and never
mutates its input. Conservative by construction: if the notebook itself would
have used the qualified row, the turn never becomes an episode.

## What was proved

24 hand-written conformance cases (1-hop gate/match/mismatch, partial
multi-qualifier match still gated, priority bare and matched, 2-/3-hop gating
at the final hop, BROKEN_CHAIN and plain-MISSING passthrough): wrapper 24/24,
plain reasoner50 fails 13, 0 wrong answers, reasoner50 selftest unchanged
(19 frames, 0 disagreements), miner checks 6/6. Full table in
`artifacts/fable-qual56-20260921/RESULTS.md`.

## Limits

Matching is syntactic, not semantic ("2019" vs "2019-05" do not match; no
ranges, no inheritance). The filter is conservative: a chain whose qualified
row lost the source race is still dropped. Learned words route as before;
their skill hops are gated the same way but installed words trained on
ungated logs remain the sleeper's responsibility.

## What it means

Conditioned facts are now first-class at answer time and sleep time without
touching storage, statuses, or any existing module.

## What it does not mean

The system does not understand time, units, or conditions; it enforces exact
qualifier equality and abstains otherwise. No inference, guessing, or
overwriting was added.
