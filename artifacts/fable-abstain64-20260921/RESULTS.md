# RESULTS — Exp 64: LTT abstention threshold on rung-1 ears 

Date: 2026-09-22 · Selector: `scripts/fable_abstain64_ltt.py` (numpy only) · Inputs: 8 `per_sentence_*.json` dumps (sha256s sealed in PASSMARKS §0) · PASSMARKS sealed **before** the run (`SEAL.sha256.txt` verified OK).

## Headline

The pre-registered fixed-sequence LTT returned **ABSTAIN-ALL for both arms**: the only certified write policy at wrong-write rate ≤ 2% (90% confidence) writes nothing. Uncertified, both arms at tau0 make 1 wrong write in 3,155 (bigru/t_hard, 1/117) — an ordering the certificate cannot reach.

## Why ABSTAIN-ALL

Certifying ≤ 2% at 90% confidence with **0** errors needs **m ≥ ln(0.1)/ln(0.98) = 113.97 → 114** accepted CAL items; with 1 error, m = 194 (printed by the run, L2). The grid's most-conservative point tau₁ is the 99th percentile of all 5,000 CAL scores (0.9453 / 0.9321), yet the best of the 1,429 / 1,363 CAL write-candidates (ensemble EXECUTE: 3-ear agreement + brakes) tops out at 0.91848 / 0.87791 — m = 0, p = 1.0 > 0.10, stopping immediately. Stopping at the first non-rejection is what makes the certificate valid and forbids descending to looser taus that would accept hundreds error-free: the price of finite-sample validity, not a code bug.

## Marks (from `ltt_run.log`)

| Mark | Verdict |
|---|---|
| L1 — wrong-write rate ≤ 2% at tau-hat, 6 test panel-arms | **PASS ×6**, all vacuous: 0/0 writes under ABSTAIN-ALL (sealed definition: vacuously ≤ 2%) |
| L2 — CAL arithmetic matches doc 59 | **PASS**: 113.97→114 asserted; exact needs k=0→114, k=1→194 (doc said ~195); tail-test ⇄ Clopper-Pearson duality asserts held at every probed point |
| L3 — coverage reported | **PASS**: 0.0000 at tau-hat on all 6 panel-arms (no bar) |
| L4 — tau chosen before any test file opened | **PASS**: loader asserts `_TAU_SEALED`; open-log assert confirms only `*_cal.json` pre-seal |

## Uncertified comparison (per PASSMARKS §1)

| panel-arm | LTT tau-hat | rung-1 tau_exec=0.5 | tau0=0.0 (all candidates) |
|---|---|---|---|
| tape/t_seen | 0, 0, 0.000 | 667, 0, 0.5924 | 702, 0, 0.6234 |
| tape/t_new | 0, 0, 0.000 | 722, 0, 0.4781 | 772, 0, 0.5113 |
| tape/t_hard | 0, 0, 0.000 | 109, 0, 0.4022 | 120, 0, 0.4428 |
| bigru/t_seen | 0, 0, 0.000 | 659, 0, 0.5853 | 664, 0, 0.5897 |
| bigru/t_new | 0, 0, 0.000 | 675, 0, 0.4470 | 780, 0, 0.5166 |
| bigru/t_hard | 0, 0, 0.000 | 107, 0, 0.3948 | 117, **1** (0.85%), 0.4317 |

Cells: writes, wrong, coverage.

## Predictions

P64.1/P64.2 TRUE (both arms ABSTAIN-ALL). P64.3 TRUE — vacuously (0/0 on all 6 per the sealed definition; tau0's one error is outside the certificate). P64.4 TRUE (all coverage 0.0000 ≤ 20%).

## Deviations

1. On resume, `stats_at` treated tau-hat=None as "accept all candidates", putting uncertified tau0 numbers in the LTT column; fixed before any RESULTS/ledger write to ABSTAIN-ALL = 0 writes per sealed PASSMARKS §2. No mark flipped (L1 passed under both readings).
2. Exact k=1 need is m=194, not doc 59's approximate "~195" (only the k=0/114 check is a gated assert).
3. rung-1 `score-*.json` hold aggregates only; per-sentence dumps were regenerated from the frozen ears read-only (`scripts/fable_abstain64_dump.py`), pre-registered in PASSMARKS §0.
4. t_trap (zero STATE golds) and t_far (recorded-only shift panel) excluded as pre-registered.

## Reproduce

`OMP_NUM_THREADS=1 uv run --offline --no-project --python 3.12 --with numpy python -B scripts/fable_abstain64_ltt.py --dir artifacts/fable-abstain64-20260921`

## What it means

A valid, test-blind LTT gate, applied honestly to the rung-1 ears, refuses to certify **any** writing at ≤2% / 90% because the top of the calibration list holds no write candidates. ABSTAIN-ALL is a pass, not a crash: the machinery worked, never touching a test panel while choosing tau.

## What it does not mean

It does not mean the ears rarely err — tau0's 1/3,155 is below any 114-item certificate's resolution — nor that the uncertified tau=0.5 policy is safe. The blocker is structural: best CAL candidate scores (0.918/0.878) sit below the grid's first point. It does not license re-tuning the grid on the same CAL to fish a pass (doc 59 §4: fresh calibration draws only), and any certificate would cover the CAL distribution only, not every panel.
