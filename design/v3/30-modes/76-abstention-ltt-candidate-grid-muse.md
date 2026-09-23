# 76 — Abstention: LTT over the candidate-score grid (exp 76, fable)

Date: 2026-09-22 · Experiment 76 · Artifact:
`artifacts/fable-abstain76-20260921/` (PASSMARKS sealed pre-run,
`SEAL.sha256.txt` verified post-run; `RESULTS.md`; selector
`scripts/fable_abstain76_ltt.py`, numpy only, importing exp 64's tail test
verbatim; exp 64 files untouched).

## The question

Exp 64 (doc 69) built an honest LTT WRITE gate and got ABSTAIN-ALL on both
rung-1 ears — not because the ears err (tau0: 1 wrong in 3,155 writes) but
because the grid's first point, the 99th percentile of *all* 5,000 CAL
scores, sat above the best write-candidate score (0.9453 vs 0.918), so m = 0
stopped the fixed sequence immediately. Exp 76 tests the written diagnosis
with exactly one change: build the grid over the *unlabeled
write-candidate score distribution* so every grid point holds certifiable
mass (≥ 114 candidates).

## Why this design (the one change, and why validity holds)

- **Grid rule (only difference from exp 64).** Per arm, G = 15 target
  acceptance counts linspace(114, N_cand, 15); tau_j = the m_j-th largest
  CAL candidate score, most conservative first, ties deduped. Tape:
  N = 1429, tau from 0.8722 down to 0.0888; bigru: N = 1363, tau from
  0.8206 to 0.3029. Code asserts m ≥ 114 at every tested point.
- **Label-free, so the FWER guarantee survives.** Scores s(x) and candidate
  status are model outputs from inputs alone — no gold/ok label enters the
  grid. The selector loads CAL through a restricted (s, cand)-only
  projection, seals the grid to GRID_SEAL.json, and only then reads labels
  (asserted in code, G4). Candidate hypotheses fixed before observing
  calibration labels is exactly what fixed-sequence LTT needs (doc 59 §2:
  "label-independent grid"; the LTT paper's rule is otherwise verbatim).
- **Everything else identical:** alpha = 0.02, delta = 0.10 pooled,
  fixed-sequence most→least conservative, stop at first non-rejection,
  exact binomial tail with Clopper–Pearson duality asserted, test panels
  opened only after tau-hat is sealed, same dumps (byte-identical shas),
  same tau = 0.5 / tau0 = 0.0 uncertified comparisons.

## What happened

**Both arms certified through all 15 grid points with zero CAL errors.**
Tape tau-hat = 0.088756 (m = 1429, k = 0, bound 0.0016); bigru tau-hat =
0.302860 (m = 1363, k = 0, bound 0.0017). The old failure mode is gone:
first points pass with m = 115/114, k = 0, p = 0.0979/0.0999 — right at
the predicted boundary. On test panels the certified policies made **0
wrong writes in 3,139 writes** across all 6 panel-arms, at 0.42–0.62
coverage; the certified bigru threshold even excludes exp 64's lone tau0
error (113/113 vs tau0's 116/117 on t_hard). Predictions P76.1–P76.3 TRUE;
P76.4 FALSE — coverage ≈ tau0-level, not ≤ 20%, because error-free CAL
lets the loosest grid point certify (doc 59's ≤ 20% prior assumed errors
would stop the sequence early).

## What it means

The diagnosis is confirmed: exp 64's ABSTAIN-ALL was grid
mis-specification, and a label-free candidate grid is a valid fix — the
machinery now certifies substantial, error-free writing on both ears. It
also reframes rung 1: CAL itself holds zero candidate errors, so the
2%/90% certificate rides on mass (~1,400 items), and the score ordering
provably filters the one known test error.

## What it does not mean

It does not bless re-tuning grids freely: this was a pre-registered
single change with a written label-free argument (doc 59 §4's anti-fishing
rule still stands — a fresh CAL draw would strengthen the claim). It is
not a cross-distribution guarantee (CAL-distribution only), not evidence
the ears never err (the tau0 t_hard error exists, outside the certified
policy), and not a verdict that high coverage is safe in general — here
coverage is certified only because CAL was error-free down to the loosest
candidate score.

Reproduce: `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 uv run --offline --no-project --python 3.12 --with numpy python -B scripts/fable_abstain76_ltt.py --dir artifacts/fable-abstain76-20260921`
