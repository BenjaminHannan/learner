# RESULTS — Exp 119g BUILD + SEAL ONLY (Muse, 2026-09-22)

**Result: built and sealed; no GPU run here.** All 119g files are written,
`PASSMARKS.md` is sealed (`SEAL.sha256.txt` verifies OK), predictions
P119g.1–P119g.7 are in the ledger, the scp closure is proved by a clean-folder
import test, and the Mac-CPU smoke proves the one change works (U=0 identity,
50 teacher-forced steps, 2-frame multi-decode — no scores). The director
launches the GPU wave on BensPC.

## What was built (new files only, prefix `fable_ears119g_`)

- `scripts/fable_ears119g_model.py` — THE ONE CHANGE: `RelCondEars(FrameEars)`
  with pointer queries `q_r = ptr_q + U(rel_emb[r])`, U zero-initialised
  (at init it equals the old model).
- `scripts/fable_ears119g_train.py` — 119f recipe verbatim (batch 32,
  2 epochs, AdamW 3e-5, freeze 0, CAL temps, steps asserted == 8838), seeds
  11911–11913, plus teacher-forced gold relation; `--steps-cap/--allow-cpu`
  smoke path only.
- `scripts/fable_ears119g_score.py` — `--step0` (119f-checkpoint K=1 baseline
  on reading94b: emitted triples + ungated precision per seed), `--score47g`
  (119e logic with the 119g loader, remapped golds, 47 tau rule, gate47
  reported), `--score-panel` (K=1 verbatim + K=3 multi-decode, always both).
- `scripts/fable_ears119g_smoke.py`, `scripts/fable_ears119g_wave.bat`
  (step0 → pool → 3 seeds → 47g → 94/94b × K=1/K=3; plan ≤ 40 min),
  `artifacts/fable-ears119g-20260922/scp119g.txt` (closure proved: the test
  caught 4 missing modules — 45_frames, 45_lexicon, listening_m1,
  notebook_contract — now included, plus remap.json staged at import path).
- `design/v3/30-modes/119g-ears-build-muse.md` (design).

## Marks table (build-time evidence; every seed/case reported, never averaged)

| check | result |
|---|---|
| Clean-folder import (scp119g.txt files only) | CLEAN-IMPORT-OK (5 wave modules) |
| U=0 identity, 5 rows, all heads | max abs diff 0.0 / 0.0 / 0.0 / 0.0 / 0.0 |
| CPU smoke (seed 11910, discarded) | 32 rows (8 occ): step loss 19.05→5.00, falls true; 150 s |
| 2-fact overfit (fictional Aldric Ashdown) | 2 frames: occupation + date of birth (K=2, FLOOR=0.0) |
| Seal | `shasum -c SEAL.sha256.txt` → OK (no post-seal edits) |

No registered scores exist yet (GPU wave is the director's). No GPU contact,
no test.pt, reading94b never opened (path only).

## Registered bars (sealed)

reading94b, K=3: M1 occ exact ≥10/94 (3/3); M2 raw exact ≥33/40/37
positionally (3/3); M3 precision ≥ step-0 K=1 baseline −0.10 per seed;
M4 gated wrong-write rate ≤5% wherever writes exist. F1 voids the claim on
slot stealing (non-occ exact below 119f's 23/18/26 per seed). PASS =
M1∧M2∧M3∧M4∧¬F1. W2b, gate47, reading94 reported only.

## Deviations

D1–D5 in PASSMARKS.md §3 (fixed K/FLOOR a priori; temps on base pointers;
single-decode backstop; two runs per panel; smoke reports no scores).

## Reproduce

`scp119g.txt` (director, from worktree root) → BensPC `wave119g.bat` →
fetch back `step0_119f.json + report47g.json + taus119g.json + 4 panel
reports + wave119g.log + 3×meta.json`. Mac smoke:
`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_ears119g_smoke.py --snapshot <scibert> --out artifacts/fable-ears119g-20260922/smoke.json`.

## Questions for Ben

None.

What it means: the one-change build is staged, sealed, and pipeline-proven; the wave can launch.
What it does not mean: no score, no gate, and no multi-fact claim exists until BensPC + F1 decide.
