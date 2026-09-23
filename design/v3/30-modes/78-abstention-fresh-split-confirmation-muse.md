# 78 — Abstention: fresh-split confirmation of the exp-76 WRITE gate (exp 78, muse)

Date: 2026-09-22 · Experiment 78 · Artifact:
`artifacts/fable-abstain78-20260921/` (PASSMARKS sealed pre-run,
`SEAL.sha256.txt` re-verified post-run; run subdirs `seed7801/`,
`seed7802/`; resplit `scripts/fable_abstain78_resplit.py`, selector
`scripts/fable_abstain78_ltt.py`, numpy-only at selection, exp 64/76 files
untouched). Project rule: fresh confirmation panels are mandatory before a
result counts — this doc is that confirmation for exp 76.

## The question

Exp 76 certified finite WRITE thresholds on both rung-1 ears (tape 0.088756,
bigru 0.30286, 0 wrong in 3,126 test writes — see §4 for the count
correction) but on a single CAL draw, and its own report flagged the worry
(doc 76: "a fresh CAL draw would strengthen the claim"; doc 59 §4: fresh
calibration draws only). Exp 78 asks: with a fresh CAL/test split, does the
same machinery still certify, and — the sharper test — does exp 76's tau-hat
applied unchanged stay error-free?

## Why this design (the one change, and the shareability verdict)

- **The panels are structurally distinct, so the fresh draw is within-CAL
  only.** This was checked, not assumed: CAL vs t_seen/t_new/t_hard share 0
  utterances, with distinct generator seeds (PANEL_SEEDS cal 4502, t_seen
  4503, t_new 4504, t_hard 4507) and distinct distributions (seen-names /
  new-names / hard). Per doc 59 §5 ("never move test sentences into
  FIT/VAL") no test sentence may enter calibration — the pool of sentences
  legitimately shareable between CAL and test is the CAL pool alone, and
  t_seen/t_new/t_hard stayed test-only as byte-identical copies.
- **The one change:** per fresh seed (7801, 7802), a bootstrap redraw of CAL
  (N = 5000 with replacement, one index multiset shared across arms so both
  ears score the same sentences). The draw uses nothing but N and the seed —
  no score, candidate, gold, or ok value — so it is label-free and the
  fixed-sequence FWER argument is intact. Recorded limitation: a bootstrap
  overlaps its parent (~63% unique here), so this renews the draw without
  renewing the distribution; a generator-fresh CAL panel would be stronger.
- **Everything else is exp 76 verbatim:** candidate-quantile grid
  (linspace(114, N_cand, 15), every point m ≥ 114, sealed before any label
  read), alpha 0.02, delta 0.10 pooled, fixed-sequence most→least
  conservative, exact binomial tail with CP duality asserted, test opened
  only after tau-hat is sealed. Added reporting only: H3 applies exp 76's
  tau-hat unchanged to the test panels.

## What happened

Both fresh draws certify finite gates with zero CAL errors at the accepted
point: seed 7801 tape 0.088756 (m = 1439, k = 0), bigru 0.414803 (m = 1364,
k = 0); seed 7802 tape 0.126850 (m = 1413, k = 0), bigru 0.355056 (m =
1350, k = 0). All 15 grid points accept on every arm-seed, as in exp 76.
On the untouched test panels: **0 wrong in 3,093 writes (7801) and 0 wrong
in 3,117 (7802)**, coverage 0.41–0.62 beside tau = 0.5. And the real
confirmation: **exp 76's tau-hat unchanged gives 0 wrong in 3,126 writes on
both runs**. Predictions P78.1–P78.6 TRUE; P78.7 (|Δ| < 0.05 everywhere)
FALSE — bigru's fresh tau-hats sit 0.112/0.052 above exp 76's.

The P78.7 miss is mechanism, not danger. With error-free CAL the sequence
never stops early, so tau-hat is simply the resample's minimum candidate
score, which jitters upward under bootstrap (the parent min is missed with
probability ≈ 1/e). Safety and coverage are the stable quantities — every
gate, fresh or old, writes with zero errors — while the threshold number
itself moves. Tape, whose score floor is densely populated, reproduced
0.088756 exactly on seed 7801.

## What it means

The WRITE gate is not a one-draw accident: new calibration draws certify
finite thresholds on both ears, and the previously certified gate stays
error-free. Fresh-split confirmation — the project's bar for "counts" — is met.

## What it does not mean

It does not anoint a threshold value (tau-hat jitters with the draw when
CAL is error-free); it is not a new distribution (bootstrap of the same
pool, ~63% unique — generator-fresh CAL remains the stronger follow-up);
not a cross-distribution guarantee (CAL-distribution only); not evidence
the ears never err (tau0's bigru/t_hard 1/117 persists outside every
certified gate); and it corrects nothing about exp 76 except a typo (§4).

## §4. Correction to exp 76's reported write count

Exp 76's RESULTS.md, design doc 76, and the ledger say "3,139" LTT test
writes. Its `ltt_summary.json` sums to 698+770+120+662+763+113 = **3,126**
(0 wrong). Recomputed independently here (old-gate columns: 3,126 twice).
**3,126 is right; 3,139 is a transcription error.** The tau0 total 3,155 in
the ledger is correct and unaffected. Rates (0 everywhere) are unchanged.

Deviations: (1) pre-run bugfix — the new selector shipped without its
`__main__` guard (silent exit 0); fixed before any registered run,
PASSMARKS (which hashes only itself) unaffected; (2) the pre-registered
bootstrap limitation above. Reproduce: `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch
--with numpy python -B scripts/fable_abstain78_resplit.py --seed 7801
--outdir artifacts/fable-abstain78-20260921/seed7801` (then 7802), then
`uv run --offline --no-project --python 3.12 --with numpy python -B
scripts/fable_abstain78_ltt.py --dir
artifacts/fable-abstain78-20260921/seed7801` (then seed7802).
