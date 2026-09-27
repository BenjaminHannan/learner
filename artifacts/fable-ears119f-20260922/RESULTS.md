# RESULTS — Exp 119f BUILD + SEAL ONLY (Muse, 2026-09-22)

**Result: built and sealed; no GPU run here.** All 119f files are written,
`PASSMARKS.md` is sealed (`fea68656…`, `SEAL.sha256.txt` verifies OK),
predictions P119f.1–P119f.6 are in the ledger, and the Mac-CPU smoke proves
the pipeline runs (data builder + 50 training steps, loss falls, no scores).
The director launches the GPU wave on BensPC after the reading94b seal.

## What was built (new files only, prefix `fable_ears119f_`)

- `scripts/fable_ears119f_data.py` — the ONE change: 5,000 panel-worded
  occupation rows (69 professions / 40 demonyms closed lists; fictional
  FIRST×LAST names; gold = occupation→profession, demonym never gold) replace
  the first 5,000 synth STATE rows 1:1. Pool stays 60,000 synth; steps 8,838.
- `scripts/fable_ears119f_train.py` — 119b recipe verbatim (batch 32, 2
  epochs, AdamW 3e-5, freeze 0, CAL temps), seeds 11911–11913, steps asserted
  == 8838; `--steps-cap/--allow-cpu` smoke path only.
- `scripts/fable_ears119f_score.py` — `--score47e` is the 119e logic by import
  (remapped golds, CAL taus); `--score-panel` scores BOTH panels with the W3
  bar formula `ceil(base·N/312)` (bases 27/33/30; exact 27/33/30 on reading94)
  plus per-seed occupation-subset exact (F1 inputs).
- `scripts/fable_ears119f_smoke.py`, `scripts/fable_ears119f_wave.bat`,
  `artifacts/fable-ears119f-20260922/scp119f.txt` (staging incl. the
  `data/open` folders the scorer imports — the 119e crash cause).

## Marks table (build-time evidence; every seed/case reported, never averaged)

| check | result |
|---|---|
| Overlap audit (pre-seal, vs old panel only) | 5,000 occ sents: 0 sentence overlap; 0 name hits (4 bank names swapped pre-seal); 500/500 encode, 0 flags; 20,763 STATE targets ≥ 5,000 |
| Value overlap | 12 single common nouns (actor…writer) also panel gold objects — generic nouns, sentences/names clean |
| CPU smoke (seed 11910, discarded, post-seal) | 176 rows (18 occ, 8 long): step loss 24.69→7.91, full loss 24.35→8.17, falls true; 186 s |
| Trainer smoke path | 64-row pool, 4 CPU steps, meta-smoke.json written |
| Scorer import | seeds [11911,11912,11913], 119e logic reachable |
| Seal | `shasum -c SEAL.sha256.txt` → OK (no post-seal edits) |

No registered scores exist yet (GPU wave is the director's). No GPU contact,
no test.pt, reading94b never opened (path only).

## Registered bars (sealed)

All 47/119e bars kept. W3b on reading94b: `ceil(base·N94b/312)` per seed,
3/3 seeds. W2b: writes > 0 in ≥ 2/3 seeds at ≤ 5 % wrong. Falsifier F1: if
occupation exact rises on reading94 but not reading94b (≥ 2/3 seeds), the
verdict is FAIL "panel-shaped" and the claim is void.

## Deviations

D1 (from plan): W3b is a scaled formula, not fixed 35 — the 94b triple count
is sealed by another agent. D2: occ rows skip hearsay augmentation (all 5,000
stay STATE). D3: smoke ran 176 rows not 64 (collector waits for ≥ 8 long AND
≥ 8 occ rows). D4: plan's "same steps" holds as asserted range
kept ∈ [141377,141408] → 8,838 steps (verified on BensPC at wave time).

## Reproduce

`scp119f.txt` (director, from worktree root) → BensPC `wave119f.bat` →
fetch back `report47f/report119f_94/report119f_94b.json + taus119f.json +
wave119f.log + 3×meta.json`. Mac smoke:
`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_ears119f_smoke.py --snapshot <scibert> --out artifacts/fable-ears119f-20260922/smoke.json`.

## Questions for Ben

None.

What it means: the one-change build is staged, sealed, and pipeline-proven; the wave can launch.
What it does not mean: no score, no gate, and no generalization claim exists until BensPC + F1 decide.
