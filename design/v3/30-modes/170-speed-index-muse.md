# 170 — Fast asks in the stacked agent (index-backed composers)

Base: loop138d (138b + 10 late fixes). Problem: 138d M6 FAIL — p50 5383 ms
per ask on a doorway-built 15,000-fact notebook (bar 50 ms); soak p99 grew
135 → 4517 ms. Exp 142 got 2–4 ms but its "?" reroute was honestly left OUT
of 138d (it bypasses the 148b screen and the 132 rewriter); 138d kept only
142's store/reasoner index, and "composers still scan".

## Diagnosis (STEP1, before seal)

cProfile of 25 asks on the 15k notebook with loop138d exactly as M6 built
it: 714.8 s total; 3,000,450 `re._compile` cache misses dominate. Every "?"
ask rescans the whole notebook in seven places, all read-only:

- C1 `notebook_triples` (loop90:101) rebuilds the 15k triple list per hear —
  twice on clarifies (138:121, 138b:214 via the 132 rewriter).
- C2 whole-word mentions (wordmatch149, applied in-process) compile one
  regex PER ENTITY per composer call — 15k compiles × several calls/ask.
- C3 `compose_n_hop` (bench92:198): ents build + per-step triple walks.
- C4 `compose_question` MQuAKE section (bench73:246): same shape.
- C5 `frame_consumes_question` (113c:112): 30k-name set + sort + replace/ask.
- C6 `compound_subject_hit` (loop113:123): normalized triple scan per ask.
- C7 `_screen148b_kind` (148b:141): 30k-name exemption scan per "?" turn.

## The one change

Same call sites, same order, same decisions; only the scanning leaves read
142's incremental per-(subject, relation) index (built and updated on every
notebook append), so each ask costs work proportional to the facts it
touches: C1 cached triples list (element-for-element verified); C2
`str.find` prefilter + one cached compiled pattern per entity string as the
oracle — the sealed regexes themselves emit the spans; C3/C4 walks over
`_sro`/`_srel` (order-equivalent); C5 cached names; C6 index walk +
precomputed subjects; C7 trigger-regex pre-check (the exemption scan runs
only when a trigger fires — exemptions can only remove hits). Unknown
shapes delegate to the saved originals. No path, screen, or rewriter is
skipped or reordered. All in `scripts/fable_fix170_compose.py`
(`install_index170`, process-local rebinding — the established
`apply_wordmatch` pattern); the agent (`scripts/fable_loop170_agent.py`) is
a mixin subclass of loop138d. No base file edited.

## Equivalence argument

Set-order: entity sets are rebuilt from the cached triples in original
order, so `sorted(set, key=len, reverse=True)` iterates exactly as the
sealed code. Walk-order: `_sro`/`_srel` append in event order, matching
triples order (replace-in-place on supersede, removal on retract — verified
through teach/correct/forget). Reverse lookup (`_one_hop`) uses a lazily
built per-version first-seen map. Possessive/backtracking semantics are the
cached sealed patterns', not a reimplementation. Checked empirically: S1/S2
reply+state identity (2,159 turns), G1 800 bench items, G2/G3 full suites.

## Results (summary)

S1 PASS: p50 28 ms, p99 64 ms, 25/25 replies identical. S2 PASS: 2000/2000
replies + states identical (fresh + 15k). S3: soak exactly-once PASS, K4 p99
under bar. G1 PASS: 0 moves vs 138d, 0 new wrong vs 138b. G2 PASS:
per-case verdict-identical (l6 kill-timing counter only). G3: 0 moves vs
138d on all four suites; recorded FAIL on the sealed letter because the
13 vs-138b moves are 138d's sealed M4 inheritance (see RESULTS).

## What it means

Ask cost no longer scales with notebook size; the stack keeps every sealed
behaviour (screens, rewriters, guards run unchanged, just faster).

## What it does not mean

It does not change any accept/answer boundary: 138d's M4
inverted-teach/yes-no shapes are inherited byte-identically, not fixed.
