# RESULTS — Exp 78: fresh-split confirmation of exp 76 (bootstrap CAL, seeds 7801/7802)

Date: 2026-09-22 · Resplit: `scripts/fable_abstain78_resplit.py` · Selector:
`scripts/fable_abstain78_ltt.py` (numpy only; tail test/CP/stats from exp 64,
grid builder from exp 76, both read-only; exp 64/76 files untouched) ·
PASSMARKS sealed **before** either run (`SEAL.sha256.txt` re-verified OK
after: `ddcf1dcd…46e165`).

## Headline

**Confirmed on both fresh draws: both arms certify a finite WRITE threshold
with 0 wrong test writes everywhere, and exp 76's tau-hat applied unchanged
also gives 0 wrong everywhere.** The one surprise is honest jitter, not
failure: with error-free CAL the fixed sequence always runs to the loosest
grid point, so tau-hat = the resample's minimum candidate score — bigru's
fresh tau-hats (0.4148, 0.3551) sit above exp 76's 0.3029, while tape's
(0.088756, 0.126850) bracket exp 76's 0.088756.

## Why the fresh draw is within-CAL only (the brief's first question)

CAL and test panels share **0 utterances** (4,281/1,946/2,864/495 unique;
distinct PANEL_SEEDS 4502 vs 4503/4504/4507): they are structurally
distinct distributions, so per doc 59 §5 no test sentence may enter CAL.
t_seen/t_new/t_hard stayed test-only (byte-identical copies, shas match
exp 76). Fresh CAL = bootstrap with replacement (N = 5000, same index
multiset for both arms, label-free: indices from N + seed only):
seed 7801 unique 3,165/5,000 (0.633); seed 7802 unique 3,171/5,000 (0.634).

## Marks (from both `ltt_run.log`s; every seed reported, never averaged)

| Mark | Seed 7801 | Seed 7802 |
|---|---|---|
| H1 tau-hat certified (point; m, k) | **PASS ×2**: tape 0.088756 (m=1439, k=0); bigru 0.414803 (m=1364, k=0) | **PASS ×2**: tape 0.126850 (m=1413, k=0); bigru 0.355056 (m=1350, k=0) |
| H2 wrong-write ≤ 2% per panel-arm | **PASS 6/6**: 0 wrong everywhere (below) | **PASS 6/6**: 0 wrong everywhere (below) |
| H3 \|Δ vs 76\| + old gate unchanged | \|Δ\| tape 0.000000, bigru 0.111943; old gate **PASS 6/6** (0 wrong) | \|Δ\| tape 0.038094, bigru 0.052196; old gate **PASS 6/6** (0 wrong) |
| H4 coverage + tau0.5 column | **PASS**: below | **PASS**: below |
| G4 sealed grids / test-blind | **PASS** (asserts held) | **PASS** (asserts held) |

Test panels at the fresh tau-hat (writes, wrong, coverage; tau = 0.5 beside):

Seed 7801 — tape/t_seen 698, 0, 0.6199 (0.5: 667, 0, 0.5924);
tape/t_new 770, 0, 0.5099 (722, 0, 0.4781); tape/t_hard 120, 0, 0.4428
(109, 0, 0.4022); bigru/t_seen 662, 0, 0.5879 (659, 0, 0.5853);
bigru/t_new 732, 0, 0.4848 (675, 0, 0.4470); bigru/t_hard 111, 0, 0.4096
(107, 0, 0.3948). Total: **0 wrong in 3,093 writes**.
Old-76-gate unchanged on the same panels: 698+770+120+662+763+113 = 3,126
writes, **0 wrong** — the real confirmation.

Seed 7802 — tape/t_seen 698, 0, 0.6199; tape/t_new 769, 0, 0.5093;
tape/t_hard 120, 0, 0.4428; bigru/t_seen 662, 0, 0.5879; bigru/t_new 756,
0, 0.5007; bigru/t_hard 112, 0, 0.4133 (tau0 there: 117 with 1 wrong,
still excluded by both fresh gates). Total: **0 wrong in 3,117 writes**.
Old-76-gate unchanged: 3,126 writes, **0 wrong**.

## The 3,139 vs 3,126 discrepancy (brief's second question)

**The JSON is right: 3,126.** Exp 76's `ltt_summary.json` test writes sum
to 698+770+120+662+763+113 = **3,126** (0 wrong); its RESULTS.md, design
doc 76, and the ledger all wrote "3,139" (off by 13). The tau0 reference
sums to 3,155, matching the ledger's P64.3 outcome line — only the LTT
total was mistyped. Nothing downstream changes (rates stay 0).

## Predictions

P78.1 TRUE (7801 tape finite). P78.2 TRUE (7801 bigru finite). P78.3 TRUE
(7802 tape finite). P78.4 TRUE (7802 bigru finite). P78.5 TRUE (≤ 2% all 6
panels, both seeds — 0 wrong in 3,093 and 3,117). P78.6 TRUE (old gate
≤ 2%: 0/3,126 twice). P78.7 FALSE — forecast |Δ| < 0.05 everywhere;
bigru misses on both seeds (0.112, 0.052), tape passes (0.000, 0.038).
The miss is understood (below), not a safety signal: every gate still
writes with 0 errors.

## Deviations

1. Pre-run bugfix (before any registered run, PASSMARKS unaffected — it
   hashes only PASSMARKS.md): the new selector was missing its
   `if __name__ == "__main__"` guard (ran silent, exit 0, no output);
   added, then both registered runs executed once each. No re-run into a pass.
2. Pre-registered limitation (PASSMARKS §2): bootstrap overlaps its parent
   (~63% unique), so this is weaker than a generator-fresh CAL; the
   per-draw certificate is valid but CAL↔test exchangeability is
   approximated. A generator-fresh CAL panel (new PANEL_SEED, torch
   re-scoring) would be the stronger follow-up.
3. None from the sealed LTT rule: grid, alpha, delta, sequence identical
   to exp 76; asserts held on both runs.

## Reproduce

`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_abstain78_resplit.py --seed 7801 --outdir artifacts/fable-abstain78-20260921/seed7801` (then 7802), then `uv run --offline --no-project --python 3.12 --with numpy python -B scripts/fable_abstain78_ltt.py --dir artifacts/fable-abstain78-20260921/seed7801` (then seed7802).

## What it means

Exp 76's certificate renews on fresh calibration: new draws certify finite
WRITE gates on both ears, and the old gate stays error-free — the safety
claim does not depend on one lucky CAL split.

## What it does not mean

It does not mean tau-hat is a stable number (error-free CAL makes it the
sample minimum, so it jitters with the draw — coverage and safety are the
stable quantities); nor a new distribution (bootstrap of the same pool);
nor that the ears never err (tau0's bigru/t_hard error persists outside
every certified gate).
