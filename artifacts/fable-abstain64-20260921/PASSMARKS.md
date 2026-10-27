# PASSMARKS — Exp 64: LTT abstention threshold on rung-1 ears (sealed before the run)

Date: 2026-09-22 · dir: `artifacts/fable-abstain64-20260921/` · selector: `scripts/fable_abstain64_ltt.py` (numpy only).
Recipe: design doc 59 (Learn-then-Test, fixed-sequence, binomial tail); where doc 59 is silent, the LTT paper's fixed-sequence rule is used as stated below.

## 0. Inputs (fixed)

Per-sentence dumps regenerated from frozen rung-1 ears (`runs/<arm>-<seed>/ear.pt`) with the rung-1 decoder imported read-only (rung-1 `score-*.json` hold aggregates only, no per-sentence confidences):

- `per_sentence_tape_cal.json` sha256 e2d25a1238d52ad19df597f4bead34be1f651528332d9868d0c57f9dcbf1d046
- `per_sentence_tape_t_seen.json` sha256 f8d20fc41951f270bca4fd7250d9486736fdf8c087aa2eb6a0c414e065a559ae
- `per_sentence_tape_t_new.json` sha256 025a936aff97c52238f19b875bf47b9ec71abcec53d3e7de3c835edf2d03e8f8
- `per_sentence_tape_t_hard.json` sha256 14872b797bd87aed4407c4f8f5aad852ed068dd8af4323470a10d202e9999d83
- `per_sentence_bigru_cal.json` sha256 bd064ee7409791141739cdc91a9e6b9eef644f2bd1b207f024d23b845ffd2a7a
- `per_sentence_bigru_t_seen.json` sha256 fe24db5e45b24b0bd8f0e898e46910f08ffed3595f3418c187e72e221edbebd1
- `per_sentence_bigru_t_new.json` sha256 bfe9ff0280c83e4ae5b0b6bd1099ff90a662394453477fa938a6adf5b148ef9d
- `per_sentence_bigru_t_hard.json` sha256 93743c9afc91d95acc941dd985915ef110603481c7328041b33221b472a22d45

CAL = `*_cal.json` (calibration only). TEST = t_seen, t_new, t_hard (ensemble). t_trap excluded (zero STATE golds: coverage undefined); t_far excluded (recorded-only shift panel).

## 1. Fixed definitions

- Score `s(x)` = ensemble min-confidence over the arm's 3 ears. Write-candidate = ensemble EXECUTE at tau=0 (all hard gates pass: agreement, brakes 1/4/5, no forced echo) with decoded act in WRITE_ACTS.
- STATE gold = gold act in WRITE_ACTS = {person, alias, teach, correct, forget} (rung-1 definition).
- At threshold tau: writes = candidates with s >= tau; wrong writes = writes whose item != gold; rate = wrong/writes (0 writes -> 0/0, reported, vacuously <= 2%); coverage = STATE-gold items written / STATE-gold items.
- Registered rung-1 comparison: ensemble tau_exec = 0.5 both arms (score-*.json), tau0 = 0.0.

## 2. Fixed LTT rule (doc 59 sec 2 + LTT fixed-sequence)

alpha = 0.02, delta = 0.10 pooled (single stratum). G = 15 grid: acceptance fractions linspace(0.01, 1.00, 15); tau_j = linear-interpolation quantile of ALL CAL s-values at level 1 - f_j (scores only, label-independent); dedupe to distinct values preserving order; test most-conservative (highest tau) first. Candidate j: m = #{cand, s >= tau_j}, k = #{cand, s >= tau_j, item != gold}; p = binomial tail P(X <= k | m, alpha) (m = 0 -> p = 1). Accept iff p <= delta; stop at first non-rejection; tau-hat = last accepted, else ABSTAIN-ALL. Certificate bound at tau-hat: Clopper-Pearson upper = p* with tail(k; m, p*) = delta via bisection; duality (p <= delta <=> bound <= alpha) asserted in code.

## 3. Marks

- **L1 (6 checks):** per test panel-arm (t_seen/t_new/t_hard x tape/bigru), empirical wrong-write rate at tau-hat <= 2% (integers reported; 0/0 passes vacuously, labeled).
- **L2:** CAL arithmetic printed: zero-error need m >= ln(0.1)/ln(0.98) = 113.97 -> 114 (doc 59 sec 3, pooled); exact-tail need for observed k; per-candidate (m, k, p); bound at tau-hat. PASS iff the 114-check and duality asserts hold.
- **L3:** coverage at tau-hat reported per test panel-arm (6 numbers). No bar. PASS iff reported.
- **L4:** no test panel used for choosing tau. Selector opens only `*_cal.json` before sealing tau; test dumps open after; enforced by `assert _TAU_SEALED` in the test loader plus an opened-path log assert. PASS iff run completes with asserts on.

## 4. Predictions P64.1-P64.4 (ledger, before the run)

- P64.1 (0.80): tape returns ABSTAIN-ALL. Falsified by a finite tape tau-hat. Basis: tau_1 ~= 99th pct of 5000 CAL scores -> m_1 <= ~51 < 114, so tail p >= 0.98^51 ~= 0.36 > 0.10 whatever the labels (unless a top tie cluster lifts m_1 >= 114 with 0 errors).
- P64.2 (0.80): bigru returns ABSTAIN-ALL. Same basis/falsifier.
- P64.3 (0.90): at tau-hat, wrong-write rate <= 2% on all 6 test panel-arms. Falsified by any rate > 2%.
- P64.4 (0.70): coverage at tau-hat <= 20% on every test panel-arm (doc 59 expects certified coverage <= ~20%). Falsified by any coverage > 20%.

Reproduce: `uv run --offline --no-project --python 3.12 --with numpy python -B scripts/fable_abstain64_ltt.py --dir artifacts/fable-abstain64-20260921` (OMP_NUM_THREADS=1).

## What it means

A pre-registered, finite-sample WRITE gate: with 90% confidence the accepted wrong-write rate is <= 2%, chosen without ever opening test data.

## What it does not mean

Not a guarantee that anything gets written (ABSTAIN-ALL is a valid pass); not a cross-panel guarantee (certificate covers the CAL distribution only); not a fix for rung-1 coverage.
