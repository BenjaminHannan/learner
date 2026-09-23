# PASSMARKS — Exp 76: LTT with candidate-quantile grid (sealed before the run)

Date: 2026-09-22 · dir: `artifacts/fable-abstain76-20260921/` · selector:
`scripts/fable_abstain76_ltt.py` (numpy only; imports tail test / CP bound /
stats from `scripts/fable_abstain64_ltt.py`, never edited).
Recipe: doc 59 fixed-sequence LTT; the ONE change vs exp 64 is the grid (§2).

## 0. Inputs (fixed, byte-identical to exp 64 PASSMARKS §0)

- `per_sentence_tape_cal.json` sha256 e2d25a1238d52ad19df597f4bead34be1f651528332d9868d0c57f9dcbf1d046
- `per_sentence_tape_t_seen.json` sha256 f8d20fc41951f270bca4fd7250d9486736fdf8c087aa2eb6a0c414e065a559ae
- `per_sentence_tape_t_new.json` sha256 025a936aff97c52238f19b875bf47b9ec71abcec53d3e7de3c835edf2d03e8f8
- `per_sentence_tape_t_hard.json` sha256 14872b797bd87aed4407c4f8f5aad852ed068dd8af4323470a10d202e9999d83
- `per_sentence_bigru_cal.json` sha256 bd064ee7409791141739cdc91a9e6b9eef644f2bd1b207f024d23b845ffd2a7a
- `per_sentence_bigru_t_seen.json` sha256 fe24db5e45b24b0bd8f0e898e46910f08ffed3595f3418c187e72e221edbebd1
- `per_sentence_bigru_t_new.json` sha256 bfe9ff0280c83e4ae5b0b6bd1099ff90a662394453477fa938a6adf5b148ef9d
- `per_sentence_bigru_t_hard.json` sha256 93743c9afc91d95acc941dd985915ef110603481c7328041b33221b472a22d45

CAL = `*_cal.json`. TEST = t_seen, t_new, t_hard (ensemble). t_trap / t_far
excluded as in exp 64. Score `s(x)`, write-candidate, STATE gold, writes /
wrong / rate / coverage definitions identical to exp 64 PASSMARKS §1.

## 1. Label-free facts used to fix the grid rule (s/cand only, never gold/ok)

- tape CAL: N_cand = 1429; 114th-best candidate score 0.872229.
- bigru CAL: N_cand = 1363; 114th-best candidate score 0.820564.

## 2. Fixed LTT rule (single change vs exp 64)

alpha = 0.02, delta = 0.10 pooled, fixed-sequence most→least conservative,
stop at first non-rejection, binomial tail P(X ≤ k | m, 0.02) ≤ 0.10 accept,
CP-bound duality asserted. Grid per arm: G = 15 target acceptance counts
linspace(114, N_cand, 15) rounded/deduped; tau_j = m_j-th largest CAL
candidate score; dedupe ties preserving order. Every grid point admits
m ≥ 114 by construction (asserted in code). Grid built from (s, cand) only,
sealed to GRID_SEAL.json before any gold/ok label is read: scores and
candidate status are model outputs from inputs alone, so the candidate
hypotheses are fixed prior to observing calibration labels and the
fixed-sequence FWER guarantee holds (doc 59 §2 "label-independent grid";
§5 forbids tuning the grid after seeing errors — no error was seen).

## 3. Marks

- **G1 (2 checks):** per arm, tau-hat certified with m ≥ 114 accepted CAL
  candidates and k = 0 errors at the accepted point. If an arm stops at
  candidate 1 (top-114 holds ≥ 1 error), report ABSTAIN-ALL with the exact
  stop point, m, k, p — that outcome is reported, not hidden.
- **G2 (6 checks):** per test panel-arm, LTT policy wrong-write rate ≤ 2%
  (integer wrong/writes; 0/0 passes vacuously, labeled).
- **G3 (6 checks):** coverage (state_written/state_golds) per panel-arm
  reported, with uncertified tau = 0.5 and tau0 = 0.0 columns beside it.
- **G4:** no test file opened before tau-hat is sealed; additionally no
  label read before the grid is sealed. Enforced by loader asserts plus the
  open-path log. PASS iff the run completes with asserts on.

## 4. Predictions P76.1–P76.4 (ledger, before the run)

- P76.1 (0.60): tape certifies a finite tau-hat (m ≥ 114, k = 0 at the
  accepted point). Falsified by ABSTAIN-ALL. Basis: construction guarantees
  m ≥ 114 everywhere, so only the top-114 error count decides; exp 64 test
  evidence (0 wrong in ~2,100 tape writes at tau0) suggests errors are rare,
  but no CAL label has been read.
- P76.2 (0.55): bigru certifies a finite tau-hat. Same basis, lower: the
  single exp-64 test error was bigru/t_hard at tau0.
- P76.3 (0.85): at tau-hat, wrong-write rate ≤ 2% on all 6 panel-arms.
- P76.4 (0.60): coverage at tau-hat ≤ 20% on every panel-arm.

Reproduce: `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 uv run --offline --no-project --python 3.12 --with numpy python -B scripts/fable_abstain76_ltt.py --dir artifacts/fable-abstain76-20260921`.

## What it means

A pre-registered WRITE gate whose grid can always be tested (every point
holds certifiable mass), chosen without reading any label or test sentence.

## What it does not mean

Not a promise that anything certifies (top-114 errors still force
ABSTAIN-ALL); not a cross-panel guarantee (certificate covers the CAL
distribution only); not a re-tune of exp 64 (exp 64 files untouched).
