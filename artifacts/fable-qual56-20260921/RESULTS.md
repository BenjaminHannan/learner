# Experiment 56 results: qualifier-aware reasoner + miner filter (2026-09-21)

Problem: thought rows v2 carry qualifiers (e.g. "in 2019"), but reasoner50 and
sleep see them only through to_v1(), which drops qualifiers. A fact true only
in 2019 could answer a year-less question, and sleep could mine chains through
qualified rows. Fix (additive only): `scripts/fable_qual56_reasoner.py` wraps
reasoner50 (imported, never edited) and re-runs its hop loop over
qualifier-filtered views; `scripts/fable_qual56_miner_filter.py` is a pure
function dropping qualified-chain turns before livesleep52 mines episodes.

## Marks (integers only)

| id | mark | bar | got | verdict |
|----|------|-----|-----|---------|
| Q1 | wrapper conformance (status+answer+reason) | 24/24 | 24/24 | PASS |
| Q2 | naive control (plain reasoner50) fails | >= 6 | 13/24 fail | PASS |
| Q3 | reasoner50 selftest unchanged | PASS | PASS (19 frames, 0 disagreements) | PASS |
| Q4 | wrong answers over the 24 | 0 | 0 | PASS |

Miner filter checks (reported): 6/6 (qualified-chain ask dropped, clean
ask+confirm kept, qualified correction dropped, smalltalk untouched, input
unmutated, walk detector exact on qualified/clean/unknown).

The 24 cases cover 1-hop gating (bare vs matching vs mismatching qualifier),
multi-qualifier rows (partial match still gated), unqualified-taught priority
(wins bare AND matched), 2- and 3-hop chains gated at the last hop, plus
passthrough (BROKEN_CHAIN, plain MISSING without reason). Naive fails all 13
gate cases (answers through the projection, newest-first); it agrees on the 11
clean ones, confirming the suite discriminates.

## What it means

A conditioned fact can no longer leak into an unconditioned answer: bare
questions get MISSING_FACT with reason `qualified`, matched questions get the
answer, and sleep never trains on chains that pass through qualified rows.

## What it does not mean

This is not semantic understanding of time or conditions: matching is exact
string equality on qualifier type+value ("2019" != "2019-05"). It does not
change what is stored, only what answers and what gets mined.

## Deviations

None from PASSMARKS.md. Notes: (1) ledger P-numbers are P240-P243, not
P234-P237, because parallel agents claimed those first; (2) the priority test
uses a non-functional `skill` relation because the contract refuses a second
active taught value on functional relations (CONFLICT); (3) reasoner50's
selftest flag is `--stage selftest`, not `--selftest`.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_qual56_conformance.py --out artifacts/fable-qual56-20260921
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_reasoner50.py --stage selftest
Seal: artifacts/fable-qual56-20260921/SEAL.sha256.txt. No web sources used.
