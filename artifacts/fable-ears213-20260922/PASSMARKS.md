# PASSMARKS — Exp 213: EARS WRITE SAFETY MAP + GATE RESCORE (Muse BUILD)

Written and hashed **before any registered run** (Mac CPU pilots only before
the seal; the registered wave runs on BensPC by the director on the frozen
119g + 119h checkpoints, 3 seeds each: 11911/11912/11913).
Artifact dir: `artifacts/fable-ears213-20260922/`.
Design doc: `design/v3/30-modes/213-earssafety-muse.md`. Date: 2026-09-22.
Open audit (pre-seal pilots): A1 probe 48/48 Mac pilot
(`probe213_pilot.json`); smoke on random-init RelCondEars + real encoder, 20
self-built rows (`smoke213_pilot.json`); old-fallback descriptive 30/48
wrong on the same probes, reproducing both review examples
(`norvish`, `birthplace`).

## 0. Background (director-verified review finding)

`pick_surface` (fable_ears47_score.py:179-218) falls back to "any content
word in the sentence"; `canonical_relation` turns that word into a relation
name the listening validator accepts ("Aldric Venmore is a Norvish pianist."
-> `norvish`; a birth date -> `birthplace`). Scorers judge only the frame's
class, never the rendered item. Separately the write gate is tau0 = the most
confident wrong EXECUTE on cal moved halfway to 1: ultra-conservative and
wrong-write-blind (on cal ~4,214/5,000 frames read correctly, ~86 executed).

## 1. The fix — Part A (scorer side only; no training)

`scripts/fable_ears213_relmap.py`: RELMAP (12 ears classes -> notebook
relation: residence->city; birthplace/place of birth->birthplace;
date of birth->date_of_birth; date of death->date_of_death;
occupation->occupation; mother/father/sibling/friend/employer/age->same
name). Every other class (incl. OPEN/UNSURE) is ECHO-only and can never be
written. `render` uses ONLY the table (fixed per-class surface; zero use of
sentence content words) plus `expected_from_gold47` / `judge` scoring the
RENDERED item. Verdict/decode code is verbatim by import and untouched.

## 2. Marks (per seed, never averaged)

- **A1** probe of 48 sealed fictional sentences
  (`probe213_cases.json`, incl. both review examples): rendered relation ==
  expected on 48/48 AND 0 invented/wrong relation names (emitted relation
  always in NOTEBOOK_RELATIONS). Verdict = PASS iff 48/48 ∧ invented == 0.
- **A2** frozen checkpoints: recomputed 47-rule taus EXACTLY equal the sealed
  taus AND per-panel `correct`/`executed` EXACTLY equal the sealed
  `ens_correct`/`ens_executed` for all 10 panels, both models (119g vs
  report47g.json/taus119g.json; 119h vs report47h.json/taus119h.json).
  Verdict = PASS iff all equal. Descriptive: rendered-item wrong writes
  among old-tau cal EXECUTEs per seed.
- **B1** gate mechanics (code-asserted): per-seed LTT on cal ONLY, alpha in
  {0.01, 0.02, 0.05}, one-sided 95% CP bound (delta=0.05); G=15 count grid
  from M_MIN(alpha)=ceil(ln(0.05)/ln(1-alpha)) = 299/149/59 (L76-style);
  exact-tail/CP duality asserted; taus sealed to taus213_*.json BEFORE any
  test panel opens (in-process flag; test loader asserts it). ABSTAIN-ALL
  (tau_hat null) is a legal outcome. Verdict = PASS iff seal files exist
  and the flag assertion held (mechanical).
- **B2** measurement (no bar): with sealed taus AND old tau side by side,
  per seed per alpha: executed / correct / wrong (rendered item) on t_seen,
  t_new, reading94, reading94b. Reading panels aggregate counts ONLY.

Verdict = PASS iff A1 ∧ A2 ∧ B1 ∧ B2 present. A registered FAIL is recorded
as FAIL with one diagnosis note, never re-run into a pass.

## 3. Pre-registered deviations (from the 213 task brief)

1. LTT uses a fixed-sequence count grid (per-alpha M_MIN start, G=15) rather
   than a pointwise minimum over all confidences: the pointwise minimum
   over a label-dependent grid has no error control; the sequential rule
   keeps it (reuses abstain64 tail/bound verbatim).
2. Reading-panel judging compares notebook-relation triples against the raw
   labeller gold sets (vocabularies differ): CONSERVATIVE — can over-count
   wrong, never hides a wrong write.
3. A2 compares exact taus + aggregate verdict counts (not per-row labels);
   same GPU + same code path => deterministic equality expected.
4. Mac smoke uses 20 self-built rows (never cal) + random-init model (no
   checkpoints on Mac) + a synthetic non-empty LTT check (random model
   abstains: real eligible = 0 -> ABSTAIN-ALL, asserted legal).
5. Probe runner uses char-level spans (tokenizer-independent); the GPU wave
   uses real WordPiece spans through the same `render` code.

## 4. Predictions

P213.1–P213.6 in `artifacts/fable-predictions-ledger.md`, appended before
the seal (see that file).

## 5. Reproduce (director-run GPU wave)

`scripts/fable_ears213_wave.bat` (logs wave213.log): probe re-verify, then
`--wave` per model (A2 -> cal LTT + seal -> test scoring, one process).
Fetch: probe213_out.json, taus213_119g/h.json, report213_119g/h.json,
wave213.log. Staging list: `artifacts/fable-ears213-20260922/scp213.txt`.

## 6. GPU wall-clock plan (<= 2400 s / 40 min; one RTX 5070 Ti)

Per model: A2 K=1 decodes (~19k rows x 3 seeds, forward-only, batched) ~6
min + cal LTT (exact tails on <=15 grid points) ~1 min + test scoring
(t_seen/t_new reuse A2 parses; 800 reading rows x 3 seeds) ~3 min. Two
models + probe ≈ 22 min total (<= 40 min). Any overrun is a reported
deviation, never compensated by touching grids, alphas, or bars.
