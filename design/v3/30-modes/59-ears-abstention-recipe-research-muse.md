# 59 — Ears abstention recipe: guaranteed ≤2% accepted-error (research, 2026-09-21)

Status: research only. No code changes. Scout prefix `muse`; owns doc 59 only.

## 0. Bottom line

Use **Learn-then-Test with fixed-sequence testing and exact binomial p-values** on `s = min over the five temperature-scaled heads`. It is the only one of the three that (a) controls the *conditional* accepted-error rate, (b) gives a high-probability certificate, and (c) stays valid when risk is **not monotone** in the threshold — which ours is not. WebRED dev (3,898 rows) suffices alone down to ~6% coverage; expect certified coverage to be low (single digits to ~20%) at α = 0.02.

## 1. What the three papers actually say (verified)

**Learn-then-Test (Angelopoulos et al., 2021).** Risk control as multiple testing: for each candidate threshold λ, test H₀: R(λ) > α with a finite-sample p-value, select via a FWER procedure at δ. Every selected λ̂ is (α, δ)-risk-controlling — P(R(λ̂) ≤ α) ≥ 1 − δ — for *any* model and distribution, with **no monotonicity assumption**. §3.2 is exactly our case: selective classification, risk = error conditional on predicting, exact binomial p-value. Fixed-sequence testing (most→least conservative, stop at first non-rejection) needs **no multiplicity correction**. https://arxiv.org/abs/2110.01052

**Conformal risk control (Angelopoulos et al., 2022/ICLR-2024).** Controls E[loss] ≤ α **in expectation** (not per-deployment) and **requires monotone loss** in λ (Proposition 2 shows it fails otherwise). Formula: λ̂ = inf{λ : (n·R̂(λ) + B)/(n+1) ≤ α}, tight to O(1/n). Wrong tool twice over: we need a per-deployment certificate on the *conditional* accepted error, and our risk is not monotone (§4). Keep only as a secondary operating point (add-one (k+1)/(m+1)). https://arxiv.org/abs/2208.02814

**SGR — Selection with Guaranteed Risk (Geifman & El-Yaniv, NeurIPS 2017).** Sort calibration by softmax-response confidence, binary-search the threshold, certify with the exact Clopper–Pearson bound B*(k; m, δ/⌈log₂n⌉) with union correction over search steps. Demo: 2% top-5 ImageNet error at 99.9% with ~60% coverage. Effectively single-score LTT with binary search; LTT fixed-sequence is preferred (no log-correction, cleaner two-stratum variant). https://arxiv.org/abs/1705.08500

**Calibrated expectation-setter (verified 2026-09-21):** a 2026 extraction study (13,859 fields, CORD receipts) got coverage 0.318 at risk 0.096 for a 10% target with an expected-risk rule, but only **0.171 at 0.068** with rigorous Mondrian LTT (δ = 0.10), 0.140 cluster-corrected, 0.060 document-level; blind human audit: 1.3% accepted error vs the 10% budget. Warnings: fitting score and threshold on the same data violates the guarantee in 95% of splits; fine grids destroy certification — use a coarse pre-specified grid. https://arxiv.org/html/2608.14639v1

## 2. Exact recipe for the ears

**Score.** After per-head temperature scaling (one scalar T_h per head, fitted on FIT only, cf. Guo et al. https://proceedings.mlr.press/v70/guo17a), frame confidence is `s(x) = min(p_act, p_subj, p_obj, p_rel, p_dir)`. WRITE iff s(x) ≥ τ; else ECHO/ASK. Brakes 1, 3, 4, 5 stay as hard gates.

**Calibration split (no leakage).** Split WebRED dev (3,898 rows, ~46% positive) into FIT half (temperatures only) and VAL half (threshold only) — never reuse one for the other (§1 leakage warning). Rung-1 synthetic panels form a **second Mondrian stratum** (trap/quote-like): own τ, δ/2 budget each. Sealed test panels and the 26,302-row WebRED held-out are never touched in calibration.

**Threshold selection (fixed-sequence LTT).** Pre-specify G = 15 candidate τ values = acceptance-fraction quantiles (1%–100%) of VAL scores, snapped to distinct values (label-independent grid). Order most conservative first. For candidate j with m accepted and k errors, p-value = Binomial tail P(X ≤ k | m, α) with α = 0.02. Reject H₀ (accept τ) if p ≤ δ (δ = 0.10 pooled; δ/2 = 0.05 per Mondrian stratum — no further correction). Stop at the first non-rejection; τ̂ = last accepted τ. If none is accepted, the certified outcome is **abstain-all** (valid, not a failure).

**Formula.** Certificate for the reported τ̂: Clopper–Pearson upper bound B(k; m, δ) = BetaInv(1−δ; k+1, m−k) ≤ 0.02. Zero-error case: B = 1 − δ^{1/m}.

## 3. Calibration-set size: the arithmetic

Pooled (δ = 0.10), zero errors observed among accepted:
m ≥ ln(δ)/ln(1−α) = ln(0.1)/ln(0.98) = (−2.3026)/(−0.02020) = 113.97 → **114 accepted with 0 errors**.
With 1 error observed: exact binomial tail gives **m ≈ 195**. SGR binary-search variant pays ⌈log₂3898⌉ = 12 steps, δ′ = 0.00833: **237 accepted with 0 errors**. Mondrian per-stratum (δ/2 = 0.05): ln(0.05)/ln(0.98) = 148.3 → **149 accepted with 0 errors per stratum**.
Sufficiency: 237/3,898 ≈ 6.1% — WebRED dev certifies **any coverage ≥ ~6%**; the trap stratum needs 149 accepted trap-like items (generate to that count). Rows needed = 149/coverage per stratum; at 30% coverage ≈ 500 rows.

## 4. The min-of-heads non-monotonicity, handled

Thresholding s gives **nested acceptance sets**, so LTT applies — but the conditional risk R(τ) = P(wrong | s ≥ τ) is **not guaranteed monotone** (raising τ can drop easy items faster than hard ones; min-of-heads shifts mass between heads). This is why CRC is invalid and LTT valid: FWER control never assumes monotonicity (it only buys power). Do not "fix" with per-head thresholds — one ordered parameter becomes five and multiplies the multiplicity bill. If fixed-sequence stops at τ₁ with near-zero coverage, fall back to Holm step-down over the same 15 candidates (still valid; costs power, not validity).

## 5. Re-calibration after each fine-tune (no test leakage)

Every fine-tune voids all old temperatures and thresholds. Per seed: (1) refit T_h on FIT; (2) re-run fixed-sequence on VAL → new τ̂; (3) append τ̂, m, k, bound to a PASSMARKS addendum and re-hash **before** scoring sealed panels; (4) score test panels once. Never move test sentences into FIT/VAL, never tune G or the grid after seeing VAL errors, never re-run VAL to "improve" τ̂. Report per-seed τ̂; seeds must not share calibration draws unless pre-registered (guarantee is per calibration draw).

## 6. Exact marks to seal for the plain-software experiment (rung-1 scores)

Run on `artifacts/fable-ears45-20260921/score-{tape,bigru,names}.json` (per-panel verdicts, τ₀/τ_exec, integer counts) as a dry run of §§2–3 with the rung-1 confidence standing in for s(x). Calibration = t_seen seed-4301; test = t_seen seeds 4302–4303 + t_new ensemble. Pre-register G = 15 grid + fixed-sequence rule verbatim.
- **E59-CAL:** fixed-sequence returns τ̂ with Clopper–Pearson B(k; m, 0.10) ≤ 0.020 on calibration (report τ̂, m, k, bound). Abstain-all passes if nothing certifies — report ABSTAIN-ALL, not a number.
- **E59-TEST:** accepted-error on held-out ≤ 2% (report x/y integers).
- **E59-TRAP (recorded):** executed trap/quote items on t_new+t_far; expect 0, no gate.
- **E59-COV (recorded):** coverage at τ̂ per split; no gate (sets the rung-2 coverage prior: expect ≤ 20% at α = 0.02).
Success = E59-CAL and E59-TEST pass on tape; bigru/names recorded. Any silent-wrong-write counted under E59-TEST is listed verbatim.

## What it means

A WRITE threshold with a finite-sample certificate — P(accepted-error ≤ 2%) ≥ 90% — computable from ~114–237 accepted calibration items, valid for our non-monotone min-of-heads score, re-fittable after every fine-tune without touching test data, testable today on rung-1 scores.

## What it does not mean

Not a guarantee that any fact gets written (coverage may certify near zero — that is the honest price, not a bug); not a cross-corpus or per-sentence guarantee (exchangeability with deployment is assumed, and WebRED ≠ papers); not calibration of the probabilities themselves (temperature scaling is a separate, weaker claim); not a license to skip the hard brakes.
