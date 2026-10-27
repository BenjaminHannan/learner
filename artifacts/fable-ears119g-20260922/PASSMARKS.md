# PASSMARKS — Exp 119g: relation-conditioned pointers + multi-fact decode (Muse BUILD)

Written and hashed **before any registered run** (open audit + Mac CPU smoke
only after the seal; the registered wave runs on BensPC by the director).
Artifact dir: `artifacts/fable-ears119g-20260922/`. Build doc:
`design/v3/30-modes/119g-ears-build-muse.md`. Date: 2026-09-22.
Open audit (pre-seal): import closure proved in a clean folder (every wave
module imports with only the scp119g.txt files present); U=0 identity and
the 50-step + 2-fact smoke are post-seal Mac-CPU checks that report no scores.

## 0. The one change vs exp 119f (model + decode only)

119f director diagnosis (frozen weights): the head can output ONE fact per
sentence — its 4 span pointers `ptr_q` (scripts/fable_ears47_model.py) are
fixed vectors not tied to the relation; real sentences state 2-3 facts and
the date or nationality wins the single slot (119f: occupation exact 1/94 on
reading94b, every seed; gated writes 0/0/0). THE ONE CHANGE:
`scripts/fable_ears119g_model.py` subclasses FrameEars with pointer queries
`q_r = ptr_q + U(rel_emb[r])`, U initialised to ZERO (at init it equals the
old model, proved by the smoke); training teacher-forces the gold relation.
Decode: act head unchanged (one act per sentence); for STATE, relations in
order of calibrated probability, up to K with p >= FLOOR, each decoded with
its own conditioned pointers (S47.decode for K=1, forced-rel frames reusing
S47 verdicts per frame); duplicate triples dropped. Everything else
identical to 119f: same pool file (built by fable_ears119f_data.py), same
seeds 11911-11913, same steps/lr/batch/epochs, same 47 gate/taus rule, same
scorer logic by import.

Sealed multi-fact constants: **K = 3, FLOOR = 0.10**. K=3 is the smallest K
covering the 2-3 facts/sentence density stated in the director diagnosis (no
reading panel opened for this choice); FLOOR=0.10 is a fixed calibrated-mass
floor far above uniform (1/517) and above the noise tail. Both are fixed a
priori, never tuned on any reading panel; K=1 is always reported alongside.
CAL multi-emission at K=3 is reported descriptively (never tuned on).

## 1. Fixed recipe (all sealed)

- Encoder: `allenai/scibert_scivocab_uncased`, snapshot
  `24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1` + our `RelCondEars` head.
- Pool (`fable_ears119f_data.py --build-pool`, BensPC): identical to 119f
  (60k synth with the 1:1 occupation replacement + remapped WebRED-train).
  Identity gates (else prep FAILs, no seed trains): synth rows == 60,000;
  occ rows == 5,000; kept total in [141377, 141408]; dropped <= 614.
- Seeds **11911, 11912, 11913**; steps = 2 * ceil(kept/32) asserted == **8838**
  in the trainer (else prep FAILs). Batch 32, 2 epochs, AdamW 3e-5 cosine,
  wd 0.01, clip 1.0, bf16 on CUDA, freeze 0, CAL temperatures (unchanged 47
  rule, base pointers), 47 tau rule on CAL only. BensPC work dir
  `C:\Users\benja\ears119g\`.
- Wave (scripts/fable_ears119g_wave.bat): step 0 = re-score the existing
  119f checkpoints (`C:\Users\benja\ears119f\runs`) with the K=1 old decode
  on reading94b (per-seed emitted triples + ungated precision = the M3
  baseline; gated writes at the 119f taus also recorded); then train 3
  seeds; then 47 panels (gate47/W1 reported, not gating) and reading94b +
  reading94 with K=1 and K=3. Registered K=1 numbers are the verbatim-decode
  `K1` blocks; registered K=chosen numbers are the `Kchosen` blocks of the
  K=3 runs. No test.pt anywhere.

## 2. The marks (per seed, never averaged)

Registered panel = `data/open/reading94b/panel.jsonl` (400 sentences; sealed
by exp 94b; reference by path, NEVER opened here; scorer only). All counts
below are on reading94b at K=3 (ungated: all emitted triples, deduped per
row; gated: S47.verdict_single per frame at the seed's tau_exec_single,
triples deduped per row), unless stated:

- **M1** occupation exact on reading94b **>= 10/94 in 3/3 seeds**
  (119f: 1/94 every seed).
- **M2** W3b raw exact (all emitted triples, K=3) per seed **>= the 119f
  bars 33/40/37 positionally** (11911 >= 33, 11912 >= 40, 11913 >= 37)
  **in 3/3 seeds**.
- **M3** precision guard: exact/emitted (K=3, ungated) per seed **>= the
  step-0 119f K=1 ungated precision for that seed minus 0.10**. (Gated
  precision is undefined — 119f gated writes were 0/0/0 — so the baseline
  is ungated by construction.) If the step-0 baseline precision is null
  (0 emitted), M3 instead requires wrong/emitted (K=3) <= 0.10 per seed.
- **M4** safety: for each seed with gated writes > 0, wrong-write rate
  **<= 5%**; seeds with 0 writes pass vacuously.
- **F1 (slot stealing)**: 119f non-occupation exact on reading94b per seed
  is 23/18/26 positionally (W3_raw minus occ_exact from report119f_94b.json:
  24-1, 19-1, 27-1). If M1 passes but non-occupation exact (K=3) falls
  below 119f's for that seed, report **"slot stealing"** and the claim is
  void (verdict FAIL).
- W2b writes and gate47 are **reported, not pass conditions**. reading94
  (K=1 and K=3) is **descriptive only**.

Verdict = PASS iff M1 ∧ M2 ∧ M3 ∧ M4 ∧ ¬F1. A registered FAIL is recorded
as FAIL with one diagnosis note, never re-run.

## 3. Pre-registered deviations (from the 119g task brief)

1. K/FLOOR are fixed a priori (K=3 from the diagnosis density, FLOOR=0.10
   as a round conservative floor), not selected by a CAL search: with
   U=0-at-init weights a pre-training CAL search cannot reflect trained
   behaviour, and any post-training change would break the seal. The wave
   reports the CAL multi-emission histogram descriptively instead.
2. Temperatures are fit by the unchanged 47 rule on the base pointers;
   conditioned pointers reuse them (same rule, no new fitting).
3. STATE rows with zero candidate relations (all p < FLOOR) fall back to
   the single old decode (a backstop, not a tuning choice).
4. `--score-panel` runs twice per panel (K=1 run + K=3 run); registered
   numbers are the K1 blocks (verbatim decode) and the K=3-run Kchosen
   blocks respectively.
5. Mac smoke reports no scores (no panels, no taus).

## 4. Predictions

P119g.1–P119g.7 in `artifacts/fable-predictions-ledger.md`, appended before
the seal (see that file).

## 5. GPU wall-clock plan (<= 2400 s / 40 min; one RTX 5070 Ti)

Anchors from `wave119f.log` (total 2098 s: pool 77 s + 3 seeds ~1900 s +
scoring ~120 s): pool build ~1.5 min (same builder) + 3 seeds x ~10.8 min
(119f 10.5 min/seed + ~3% for the embedding/U path by flop arithmetic) +
step-0 119f re-score ~1 min + score47g with CAL multi ~3 min + four panel
scorings (94/94b x K=1/K=3) ~3 min → ≈ 39 min total (<= 40 min). Any
overrun is a reported deviation, never compensated by touching bars,
gates, K, or FLOOR.
