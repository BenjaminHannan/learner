# RESULTS — Exp 76: LTT with candidate-quantile grid (one-change follow-up to exp 64)

Date: 2026-09-22 · Selector: `scripts/fable_abstain76_ltt.py` (numpy only;
tail test / CP bound / stats imported read-only from exp 64's
`fable_abstain64_ltt.py`, never edited) · Inputs: 8 `per_sentence_*.json`
dumps, byte-identical to exp 64 (shas in PASSMARKS §0) · PASSMARKS sealed
**before** the run (`SEAL.sha256.txt` verified OK after the run).

## Headline

The single change worked: **both arms certify a finite WRITE threshold at
wrong-write rate ≤ 2% (90% confidence)** — tape tau-hat = 0.088756
(m = 1429, k = 0, CP bound 0.0016), bigru tau-hat = 0.302860 (m = 1363,
k = 0, bound 0.0017). Exp 64's ABSTAIN-ALL was grid mis-specification, not
weak ears: with every grid point holding certifiable mass, the fixed
sequence accepted all 15 points on both arms (CAL holds **zero** errors
among all 1,429 / 1,363 candidates).

## Marks (from `ltt_run.log`)

| Mark | Verdict |
|---|---|
| G1 — tau-hat certified per arm, m ≥ 114 and k = 0 | **PASS ×2**: tape m = 1429, bigru m = 1363, both k = 0 |
| G2 — LTT wrong-write rate ≤ 2% on 6 panel-arms | **PASS ×6**: 0 wrong everywhere (integers below) |
| G3 — coverage per panel-arm + tau0.5/tau0 columns | **PASS**: reported below |
| G4 — grid sealed before any label read; no test file before tau-hat | **PASS**: loader asserts held; open-log asserted CAL-only pre-seal |

First grid points (the exp-64 failure mode) now pass: tape cand 1
tau = 0.8722, m = 115, k = 0, p = 0.0979 ≤ 0.10 ACCEPT; bigru cand 1
tau = 0.8206, m = 114, k = 0, p = 0.0999 ACCEPT — both near the boundary,
exactly as the 114-item arithmetic predicts.

## Test panels (writes, wrong, coverage)

| panel-arm | LTT tau-hat | rung-1 tau = 0.5 | tau0 = 0.0 |
|---|---|---|---|
| tape/t_seen | 698, 0, 0.6199 | 667, 0, 0.5924 | 702, 0, 0.6234 |
| tape/t_new | 770, 0, 0.5099 | 722, 0, 0.4781 | 772, 0, 0.5113 |
| tape/t_hard | 120, 0, 0.4428 | 109, 0, 0.4022 | 120, 0, 0.4428 |
| bigru/t_seen | 662, 0, 0.5879 | 659, 0, 0.5853 | 664, 0, 0.5897 |
| bigru/t_new | 763, 0, 0.5053 | 675, 0, 0.4470 | 780, 0, 0.5166 |
| bigru/t_hard | 113, 0, 0.4170 | 107, 0, 0.3948 | 117, **1** (0.85%), 0.4317 |

Note: the certified bigru threshold (0.3029) filters out exp 64's single
tau0 error (bigru/t_hard): LTT writes 113/113 correct where tau0 wrote
117 with 1 wrong. The score ordering earned its keep.

## Predictions

P76.1 TRUE (tape finite tau-hat). P76.2 TRUE (bigru finite tau-hat).
P76.3 TRUE (0/… ≤ 2% on all 6). P76.4 FALSE — coverage 0.417–0.620
everywhere, far above the ≤ 20% forecast (doc 59's prior assumed a
non-trivial error rate; CAL turned out error-free so the loosest grid
point certified, and coverage is ~tau0-level).

## Deviations

None from the sealed PASSMARKS. One honesty note: this run re-uses exp 64's
CAL draw with a re-tuned grid, which doc 59 §4 discourages as "fishing a
yes" — the defense is that the grid rule is label-free (a deterministic
function of unlabeled scores, sealed before any label read, so the FWER
argument is intact) and was pre-registered as the single change with a
written diagnosis. A fresh CAL draw would still strengthen the claim; the
certificate covers the CAL distribution only, not every panel.

## Reproduce

`OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 uv run --offline --no-project --python 3.12 --with numpy python -B scripts/fable_abstain76_ltt.py --dir artifacts/fable-abstain76-20260921`

## What it means

A valid, test-blind LTT gate now certifies real writing for both rung-1
ears at ≤ 2% wrong-writes / 90%: ~1,400 zero-error CAL candidates carry
the certificate, and the certified policy writes 40–60% of STATE golds
with zero test errors in 3,139 writes.

## What it does not mean

It does not mean the ears are error-free (bigru/tau0 still errs 1/117 on
t_hard — outside the certified policy), nor that the certificate travels
to new distributions; CAL was error-free, so the bound's strength comes
from mass, not from surviving errors.
