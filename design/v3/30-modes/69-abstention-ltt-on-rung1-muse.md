# 69 — Abstention: an LTT WRITE threshold on the rung-1 ears (exp 64, fable)

Date: 2026-09-22 · Experiment 64 · Artifact: `artifacts/fable-abstain64-20260921/` (PASSMARKS sealed pre-run, `SEAL.sha256.txt` verified; `RESULTS.md` + `RESULTS-SEAL.sha256.txt`; selector `scripts/fable_abstain64_ltt.py`, numpy only; dumps `scripts/fable_abstain64_dump.py`).

## The question

Rung 1 (ears45) showed tape and BiGRU writers that almost never write wrongly — but "almost never" was judged on test panels with a threshold (tau_exec = 0.5) chosen by eye. Doc 59 registered the recipe for turning that into a number we can defend: a **Learn-then-Test (LTT)** gate for the WRITE decision that certifies, from calibration data alone, `P(wrong write | write) ≤ 2%` with **90% confidence** before any test sentence is opened.

## Why this design (fixed points, and why)

- **LTT / fixed-sequence testing, not CRC or SGR.** Our risk is not monotone in the threshold (min-of-3-ears score mass shifts between heads), which voids conformal risk control's monotonicity assumption (doc 59 §3). Fixed-sequence testing over a coarse pre-specified grid of G = 15 acceptance-fraction quantiles (1%–100%, label-independent, deduped, most conservative first) costs no multiplicity correction; SGR's binary search pays a log-steps union bound. Where doc 59 left a point vague (exact grid construction on our pooled panel), the LTT paper's fixed-sequence rule was used verbatim and stated in the sealed PASSMARKS.
- **Sample-size arithmetic is the spec.** To certify α = 0.02 at δ = 0.10 with zero errors you need m ≥ ln(0.1)/ln(0.98) = 113.97 → **114** accepted calibration items; one error raises the bar to m = 194 (exact tail; doc 59 said ~195). This number, not a hunch about the score, decides whether any threshold can be certified.
- **Candidate score s(x)** = ensemble min-confidence over the arm's 3 ears; write-candidate = ensemble EXECUTE at tau = 0 (all hard gates: agreement, brakes, no forced echo). STATE golds = {person, alias, teach, correct, forget}. A test binomial tail `P(X ≤ k | m, 0.02) ≤ 0.10` is the accept rule, dual-asserted against the Clopper–Pearson upper bound (they must agree, or the run aborts).
- **Test-blind by construction.** Phase 1 opens only `*_cal.json` (5,000 rows/arm) and seals tau-hat; the loader asserts a `_TAU_SEALED` flag before any test file can open, and an open-path log is asserted CAL-only pre-seal (mark L4).
- Inputs were per-sentence dumps regenerated read-only from the frozen rung-1 ears (`score-*.json` carry aggregates only), hashed into PASSMARKS §0. t_trap (zero STATE golds) and t_far (recorded-only shift panel) excluded, pre-registered.

## What happened

**Both arms returned ABSTAIN-ALL**, at the very first grid point: the most conservative tau is the 99th percentile of all CAL scores (tape 0.9453, BiGRU 0.9321), but no CAL write-candidate scores above those ceilings — the best candidates top out at 0.91848 / 0.87791. With m = 0 there is nothing to certify, p = 1.0 > 0.10, the fixed sequence stops, and the certified policy is "write nothing". All four marks passed: L1 vacuous-pass on all 6 test panel-arms (0/0 ≤ 2% per the sealed definition), L2 arithmetic printed and asserted, L3 coverage reported (0.0000 everywhere at tau-hat), L4 asserts held.

The uncertified comparison is the interesting part. Left alone at the loosest registered gate (tau0 = all candidates), the same systems wrote 3,155 items across the ensemble test panels with exactly **one** wrong write (BiGRU/t_hard, 1/117 = 0.85%); at rung-1's tau_exec = 0.5, zero wrong writes in 2,939. The score orders the errors well — but calibration confidence itself caps below the grid's reach, so no finite-sample certificate of "≤ 2% at 90%" exists for *any* threshold on this calibration draw.

## What it means

The abstention machinery (doc 59's recipe) works end-to-end, is honest, and delivers its most conservative valid answer: on these ears, a 2%/90% WRITE certificate is only satisfiable by abstaining. That is the guarantee doing its job — it refuses to certify what calibration cannot see. It also quantifies rung 1's safety story differently: "0 wrong writes" was luck-of-the-sample relative to what we can *prove*, and provable safety at this error budget requires either many more calibration rows in the high-confidence region or ears whose write-candidate confidences actually reach the top of the score scale.

## What it does not mean

It does not mean the ears are unsafe (tau0 observed error rate 1/3,155 ≪ 2%), nor that no threshold could ever be certified — a larger or better-calibrated CAL panel with ≥ 114 zero-error candidates above tau₁ would flip the result. It is not a verdict on tau_exec = 0.5 (uncertified either way). It does not license re-running with a re-tuned grid or swapped CAL to fish a yes (doc 59 §4), and it says nothing about panels outside the CAL distribution. Predictions P64.1–P64.4 all resolved TRUE (P64.3 vacuously), per the ledger.

Reproduce: `OMP_NUM_THREADS=1 uv run --offline --no-project --python 3.12 --with numpy python -B scripts/fable_abstain64_ltt.py --dir artifacts/fable-abstain64-20260921`
