# 124 — Red team round 3: the N-hop composer and its fallback (Muse)

## What was attacked
The NEWEST question-side code: `compose_n_hop` (N-hop walk with coverage
gate, `scripts/fable_bench92_english_arm.py:198-240`), the 2-hop
`compose_question` fallback frame (`fable_bench73_english_arm.py`), and the
loop113b router that asks composer frames but delegates to the exact loop102
chain only when BOTH composers return None
(`scripts/fable_loop113b_agent.py:68-103`). Teach path is byte-identical
across arms, so teach bugs hit both. Earlier rounds (98: loop90 hearsay/
forget/mailbox; 110: loop102 pronouns, relaunches, unicode, case, self-Q,
daemon) were not repeated — all 62 cases are new ground, 12 families.

## Method
Sealed 62 cases + PASSMARKS before any run (seal `cdef0361…`), ledger block
P124.1–P124.6 appended first. Each case runs in a fresh daemon dir through
the mailbox (`inbox` file → `process_file` → `outbox` reply) on both arms;
verdicts mechanical against sealed expectations; post-hoc triage separates
genuine agent bugs (43 case-arms) from my expectation errors (48, mostly
absent-decoys echoed in `Saved:` acks, e.g. `Spain's capital is Madrid`
tripping absent `Madrid`).

## Findings (genuine)
1. **Prefix truncation (both arms).** Composer returns the walked prefix at
   any break (branch, forgotten/re-pointed hop, chain end) and the router
   asks it: 9 broken-chain cases on 113b answer 1–3-hop prefixes (B6:
   `Roberto's country_of_citizenship is Spain` for a language question).
   Loop102 has the same shape at 2 hops via `Bench73Stage` (16 cases),
   because the explicitness gate lives only in 113/113b routing.
2. **One-directional coverage gate (113b).** Extra/unknown relations
   (`occupation`, `employs`), `whose`, and question qualifiers (`as of
   2020`) never block the frame: 5 cases answer confidently (U3: `AJ Lee`
   for "who employs").
3. **Trailing-period junk writes (both arms).** `Actually,…Portugal.` and
   duplicate teaches with `.` write `'Portugal.'`/`'Spain.'`/`'AJ Lee.'`
   triples (5 cases × 2 arms = M1 10), cascading into junk answers and
   broken walks. Fix: strip terminal `.` before template match (or compare
   dotted values as duplicates) in the F3/duplicate teach path.
4. Suggested router fix: only ask a composer frame whose walk ends at a
   sink with full coverage AND no qualifier/extra-relation residue;
   otherwise fall through to the loop102 chain (which already abstains
   safely on these shapes).

## What held (evidence of absence, sampled)
6-hop/long/shouted/rephrased chains answer (C01–C05,C07,V1,W1,V10,T2);
loops (L1–L4), ambiguity (S2/S4), forget (G2/G3), qualifier-drop teaches
(Q1/Q3/Q4), hearsay/self/packed inputs (V8/V9/E1/E3/E4/W4), over-cap (V2)
and no-entity (V3) all safe. Fallback possessive/hearsay/loop paths: 0
failures anywhere — the new risk is entirely composer-frame shape.

## Scope limits
Single-seed, single-run per case (deterministic code paths, no training);
mailbox-via-`process_file` in-process (same code as the subprocess daemon);
English only; no sleep/thinker involvement (all waves < threshold, 0 sleeps
observed). Claims stay inside the 124 runs.
