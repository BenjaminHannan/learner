# Exp 148b RESULTS — status-preserving question screen (3.8 s + 2.2 s + 42.9 s + 138.7 s + 143.3 s, Mac CPU)

One change from 148, record plumbing only: a screened question is answered
through the reasoner record path (kind "answer" + abstain status) instead of
a status-less ears clarify. Every user-visible reply is byte-identical to
148's. 148's FAIL stands; this is a separate registered follow-up.

## Marks

| mark | bar | result |
|---|---|---|
| R1 Q1 143 re-run on loop132+148b | verdicts + reply texts identical to 148's report | PASS: 0 verdict diffs, 0 reply diffs (124 cases); targets 8/8 no confident answer; worse [] (100 OK / 14 WRONG / 10 MISSED, as sealed) |
| R1 Q2 new 40-probe | identical to 148's report | PASS: 0 verdict/reply diffs; 20/20 trigger clarify, 20/20 innocents byte-identical to base |
| R2 benches (edit200, old/new 121/132 4-hop) | 800/800 per-item verdicts identical to 148's rows | PASS: 0 verdict diffs, 0 reply diffs on all 800 items |
| R3 marks123 148b vs loop134 | identical except P2-D8 + L5-Z1 42/43 (predicted); 37 never-items no longer MISS | PASS: only diffs are D8 BUG->OK and turns 42/43 UNSUPPORTED_QUESTION-vs-OK (predicted); L5-Z2 37/37 MISSING_FACT abstain_ok, 0 MISS; every other suite verdict-identical |
| R4 time | each run < 25 min; daemon idle_seconds | PASS: 3.8 / 2.2 / 42.9 / 138.7+143.3 s; idle_seconds default 30.0 |

P148b.1 TRUE | P148b.2 TRUE | P148b.3 TRUE | P148b.4 TRUE.
SCORE: PASS (R1-R4).

## Diagnosis note (the one predicted non-identity)

p3 L5-Z1 turns 42/43 ("What is Mira's city in 2019?", "What is Jon's job in
2019?") observe UNSUPPORTED_QUESTION where the base observes OK. The base
answers OK from taught year-named relations (city_in_2019/job_in_2019, e.g.
trail F00024, reply "Mira's city in 2019 is Port Azure.") — the sealed
expectation encodes that qualifier-blind answer, so the mark still
mismatches there by design. The refusal is honest: the fact exists, so it is
NOT labelled MISSING_FACT (that would be literally false); the new
UNSUPPORTED_QUESTION status says the qualifier is outside notebook
semantics. No other turn is affected: the 37 never-items keep the reasoner's
own MISSING_FACT (literally true by construction — the relation was never
taught), and 0 wrong writes occur anywhere. A future experiment could exempt
year-tokens inside taught relation names (as 148 already does for
entity/value mentions), but that changes the sealed word list and is out of
scope here.

## Deviations / limits

No deviation from plan; single deterministic runs; English only; no sleep
involved. Analysis notes (all verdict-neutral, documented in the verifier):
L6 `replied_before_kill` and 3 rt110 `statuses` log fields are harness
timing noise (replies, verdict rows, writes all exactly identical; the
sealed judges never read those fields); sleep SKIP reason differs by agent
filename only (exp-150 precedent); marks123-bench edit200 reply-diffs are
exactly the sealed 37 never-items (verdicts identical), the same phenomenon
as 148's Q4. Q1 reuses the sealed 143 runner by import (daemon class + ART
path swapped only). Verifier: scripts/fable_loop148b_verify.py.

## Reproduce

`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_loop148b_q1.py` (then `..._q2.py`, `..._bench.py --run`, the two `fable_marks123_all.py` lines in PASSMARKS.md, then `..._verify.py`).

## What it means

The screen's refusal is now a first-class abstention in the record: every
status-based judge that accepted the base's abstentions accepts ours, with
zero change to anything the user sees.

## What it does not mean

It does not mean the assistant understands negation or time — it still only
knows when to shut up — and it does not mean the two stale sealed
expectations (L5-Z1 42/43) now pass; they still demand the old buggy answers.
