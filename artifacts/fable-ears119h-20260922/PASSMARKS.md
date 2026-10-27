# PASSMARKS — Exp 119h: varied-shape occupation rows (Muse BUILD)

Written and hashed **before any registered run** (open audit + Mac CPU smoke
only after the seal; the registered wave runs on BensPC by the director).
Artifact dir: `artifacts/fable-ears119h-20260922/`. Build doc:
`design/v3/30-modes/119h-ears-build-muse.md`. Date: 2026-09-22.
Open audit (pre-seal): import + runtime closure proved in a clean folder
(seeded with the 119g closure files; CLEAN-IMPORT-OK-4, same rows sha
9909b6d1, novelty clean); CPU smoke (determinism, 5000 rows, span asserts,
novelty, 50 teacher-forced steps falling 23.47 → 5.12) reports no scores.

## 0. The one change vs exp 119g (data only)

119g director diagnosis (frozen weights): the 5,000 synthetic occupation rows
use two past-tense templates and label ONLY occupation, so the model learned
the surface cue "was", not "a job word" (119g reading94b occupation exact
1/94 every seed; occupation ranks 6th or lower on "is a" / birth-bracket
sentences). THE ONE CHANGE: `scripts/fable_ears119h_data.py` replaces
`occ_rows` with a varied-shape generator (is/was ~50/50 overall, "was" with
death dates; ~60% birth/life brackets; ~15% retired/former/professional;
~85% demonyms; ~30% 2-3-job lists; ~35% multi-word first jobs) that labels
EVERY fact each sentence states, one row per fact sharing the same text
(occupation = FIRST job span only; citizenship = demonym span, following the
pool's own WebRED majority 1030 demonym vs 545 country objects; birth/death
dates and birthplace as written). EXACTLY 5,000 rows replace the same 5,000
STATE slots 1:1. Nothing else changes: the 119g RelCondEars model (by
import), the teacher-forced relation, seeds 11911-11913, steps, lr, batch,
epochs, CAL temps, the 47 tau rule, and K=3 / FLOOR=0.10 (sealed in 119g;
not re-chosen).

## 1. Fixed recipe (all sealed)

- Encoder: `allenai/scibert_scivocab_uncased`, snapshot
  `24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1` + `RelCondEars` head (unchanged).
- Pool (`fable_ears119h_data.py --build-pool`, BensPC): 60k synth with the
  1:1 varied-shape replacement + remapped WebRED-train. Identity gates (else
  prep FAILs, no seed trains): synth rows == 60,000; occ rows == 5,000; kept
  total in [141377, 141408]; steps == 8838.
- Seeds **11911, 11912, 11913**; steps = 2 * ceil(kept/32) asserted ==
  **8838** in the trainer (else prep FAILs). Batch 32, 2 epochs, AdamW 3e-5
  cosine, wd 0.01, clip 1.0, bf16 on CUDA, freeze 0, CAL temperatures
  (unchanged 47 rule, base pointers), 47 tau rule on CAL only. BensPC work
  dir `C:\Users\benja\ears119h\`.
- Wave (scripts/fable_ears119h_wave.bat): pool build → train 3 seeds → 47
  panels (gate47/W1 reported, not gating) → reading94b + reading94 with K=1
  and K=3. **No step 0: the 119g registered numbers are the baseline.**
  Registered K=1 numbers are the verbatim-decode `K1` blocks; registered
  K=chosen numbers are the `Kchosen` blocks of the K=3 runs. No test.pt.

## 2. The marks (per seed, never averaged)

Registered panel = `data/open/reading94b/panel.jsonl` (400 sentences; sealed
by exp 94b; reference by path, NEVER opened here; scorer only). 94
occupation golds. All counts below are on reading94b at K=3 (ungated: all
emitted triples, deduped per row; gated: S47.verdict_single per frame at the
seed's tau_exec_single, triples deduped per row), unless stated:

- **M1** occupation exact on reading94b (K=3) **>= 10/94 in 3/3 seeds**
  (119g: 1/94 every seed). Ceiling note: one occupation read-out per
  sentence at most, and 23 sentences state 2+ occupations, so at most 51/94
  is reachable without double reads.
- **M2** non-occupation exact (K=3) per seed **>= 81/73/89 positionally**
  (11911 >= 81, 11912 >= 73, 11913 >= 89: 90% of 119g's 90/81/99).
- **M3** precision guard: exact/emitted (K=3, ungated) per seed **>=
  0.143/0.116/0.154 positionally** (11911 >= 0.143, 11912 >= 0.116,
  11913 >= 0.154: 119g's 0.193/0.166/0.204 minus 0.05).
- **M4** safety: for each seed with gated writes > 0, wrong-write rate
  **<= 5%**; seeds with 0 writes pass vacuously.
- Descriptive only: K=1, reading94 (K=1 and K=3), 47 marks, gate/writes,
  and a training-shape check (40 generated rows: forced-occupation read-out
  exact).

Verdict = PASS iff M1 ∧ M2 ∧ M3 ∧ M4. A registered FAIL is recorded as FAIL
with one diagnosis note, never re-run.

## 3. Pre-registered deviations (from the 119h task brief)

1. The D1 scorer fix (wrap K=1 parses as one-frame lists inside
   score_panel_multi) is built into `fable_ears119h_score.py` itself rather
   than a separate wrapper file; score47g keeps the flat form it needs.
2. "is" is favoured 70/30 on sentences without a death date so the overall
   is/was mix lands ~50/50 (measured 860/900) while "was" stays absolute
   with death dates; all other shape draws are at the brief's rates
   (measured: bracket 58.9%, demonym 85.6%, modifier 15.3%, job lists
   29.5%, multi-word first job 34.6%).
3. Mac smoke reports no scores (no panels, no taus).

## 4. Predictions

P119h.1–P119h.6 in `artifacts/fable-predictions-ledger.md`, appended before
the seal (see that file).

## 5. GPU wall-clock plan (<= 2400 s / 40 min; one RTX 5070 Ti)

Anchors from `wave119g_d1` (2186 s including a ~60 s step 0): pool build
~1.5 min (same line count, slightly longer sentences) + 3 seeds x ~10.8 min
(same recipe/model/flops as 119g) + score47h with CAL multi ~3 min + four
panel scorings (94b/94 x K=1/K=3) ~3 min, minus the step-0 minute → ≈ 39
min total (<= 40 min). Any overrun is a reported deviation, never
compensated by touching bars, gates, K, or FLOOR.
