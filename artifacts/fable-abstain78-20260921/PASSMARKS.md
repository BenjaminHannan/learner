# PASSMARKS — Exp 78: fresh-split confirmation of exp 76 (sealed before the run)

Date: 2026-09-22 · dir: `artifacts/fable-abstain78-20260921/` (run subdirs
`seed7801/`, `seed7802/`) · resplit:
`scripts/fable_abstain78_resplit.py` · selector:
`scripts/fable_abstain78_ltt.py` (numpy only; tail test / CP bound / stats
imported read-only from `scripts/fable_abstain64_ltt.py`, grid builder from
`scripts/fable_abstain76_ltt.py`; exp 64/76 files never edited).
Recipe: exp 76's exact procedure (doc 76); the ONE change is a fresh CAL draw.

## 0. Source inputs (byte-identical to exp 76 PASSMARKS §0, read-only)

- `per_sentence_tape_cal.json` sha256 e2d25a1238d52ad19df597f4bead34be1f651528332d9868d0c57f9dcbf1d046
- `per_sentence_tape_t_seen.json` sha256 f8d20fc41951f270bca4fd7250d9486736fdf8c087aa2eb6a0c414e065a559ae
- `per_sentence_tape_t_new.json` sha256 025a936aff97c52238f19b875bf47b9ec71abcec53d3e7de3c835edf2d03e8f8
- `per_sentence_tape_t_hard.json` sha256 14872b797bd87aed4407c4f8f5aad852ed068dd8af4323470a10d202e9999d83
- `per_sentence_bigru_cal.json` sha256 bd064ee7409791141739cdc91a9e6b9eef644f2bd1b207f024d23b845ffd2a7a
- `per_sentence_bigru_t_seen.json` sha256 fe24db5e45b24b0bd8f0e898e46910f08ffed3595f3418c187e72e221edbebd1
- `per_sentence_bigru_t_new.json` sha256 bfe9ff0280c83e4ae5b0b6bd1099ff90a662394453477fa938a6adf5b148ef9d
- `per_sentence_bigru_t_hard.json` sha256 93743c9afc91d95acc941dd985915ef110603481c7328041b33221b472a22d45

## 1. Shareability verdict (why the fresh draw is within-CAL only)

CAL vs test panels share 0 utterances (checked 2026-09-22: |CAL ∩ t_seen| =
|CAL ∩ t_new| = |CAL ∩ t_hard| = 0 of 4,281/1,946/2,864/495 unique
utterances) and were generated with distinct PANEL_SEEDS (cal 4502, t_seen
4503, t_new 4504, t_hard 4507). The panels are structurally distinct
distributions (seen-names / new-names / hard), so per doc 59 §5 ("never move
test sentences into FIT/VAL") NO test sentence may enter CAL: the pool of
sentences legitimately shareable between CAL and test is the CAL pool alone.
t_seen/t_new/t_hard stay test-only, byte-identical copies (sha-verified).

## 2. Fresh-CAL rule (the ONE change; label-free)

Per fresh seed S in {7801, 7802}: draw N = 5000 indices with replacement
from range(5000) with `random.Random(S)` using NOTHING but N and S (no
score, candidate, gold, or ok value enters the draw); apply the SAME index
multiset to both arms (tape and bigru score the same sentences). Fresh CAL
size = 5000/arm, same as exp 76. Limitation (recorded, not hidden): a
bootstrap resample overlaps its parent (~63% unique), so this is weaker
than a generator-fresh CAL panel; the per-draw certificate remains valid
but strict CAL↔test exchangeability is approximated, not renewed.

## 3. Fixed LTT rule (identical to exp 76)

alpha = 0.02, delta = 0.10 pooled, fixed-sequence most→least conservative,
stop at first non-rejection, binomial tail P(X ≤ k | m, 0.02) ≤ 0.10 accept,
CP-bound duality asserted. Grid per arm: G = 15 target acceptance counts
linspace(114, N_cand, 15) rounded/deduped; tau_j = m_j-th largest fresh-CAL
candidate score; every point m ≥ 114 (asserted). Grid built from (s, cand)
only, sealed to GRID_SEAL.json before any gold/ok label is read; test files
opened only after tau-hat is sealed. Old gate for H3b (uncertified
reference): exp 76 tau-hat unchanged, tape 0.088756 / bigru 0.30286.

## 4. Marks

- **H1 (2 checks × 2 seeds):** per arm, tau-hat certified with m ≥ 114
  accepted fresh-CAL candidates and k = 0 at the accepted point (report the
  point and m, k). ABSTAIN-ALL, if it happens, is reported with stop point.
- **H2 (6 checks × 2 seeds):** per test panel-arm, fresh-tau-hat wrong-write
  rate ≤ 2% (integer wrong/writes; 0/0 passes vacuously, labeled).
- **H3 (per arm × 2 seeds):** |tau-hat(78) − tau-hat(76)| reported, plus
  whether exp 76's tau-hat applied unchanged to the test panels also gives
  ≤ 2% on all 6 panel-arms (integers). This unchanged-gate check is the
  real confirmation.
- **H4 (6 checks × 2 seeds):** coverage (state_written/state_golds) per
  panel-arm at tau-hat, beside the uncertified tau = 0.5 column (plus tau0).

## 5. Predictions P78.1–P78.7 (ledger, before the run)

- P78.1 (0.60): seed-7801 tape certifies a finite tau-hat. Falsified by ABSTAIN-ALL.
- P78.2 (0.55): seed-7801 bigru certifies a finite tau-hat. Falsified by ABSTAIN-ALL.
- P78.3 (0.60): seed-7802 tape certifies a finite tau-hat. Falsified by ABSTAIN-ALL.
- P78.4 (0.55): seed-7802 bigru certifies a finite tau-hat. Falsified by ABSTAIN-ALL.
- P78.5 (0.85): at fresh tau-hat, wrong-write rate ≤ 2% on all 6 panel-arms in both seeds.
- P78.6 (0.95): exp 76's tau-hat unchanged gives ≤ 2% on all 6 panel-arms (test byte-identical).
- P78.7 (0.70): |tau-hat(78) − tau-hat(76)| < 0.05 on every arm-seed (error-free bootstrap → loosest point certifies; min-score jitter only).

Also to be reported (not a prediction): exp 76's RESULTS.md says 3,139 test
writes but its JSON sums to 3,126 — exp 78 recomputes from JSON and states
which is right.

Reproduce: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_abstain78_resplit.py --seed 7801 --outdir artifacts/fable-abstain78-20260921/seed7801` (then 7802), then `uv run --offline --no-project --python 3.12 --with numpy python -B scripts/fable_abstain78_ltt.py --dir artifacts/fable-abstain78-20260921/seed7801` (then seed7802).

## What it means

A pre-registered fresh-CAL confirmation: same gate machinery, new
calibration draw, test panels never touched before the seal.

## What it does not mean

Not a new distribution (bootstrap of the same CAL pool); not a cross-panel
guarantee (certificate covers the CAL distribution only); not a re-tune
(exp 64/76 files untouched).
