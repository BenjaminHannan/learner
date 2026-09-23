# 119b — Ears relation-namespace remap PREP (Muse; GPU wave launched by Claude)

Status: PREP complete on Mac CPU. No BensPC GPU job started here; the 3-seed
wave, 47-panel scoring, and reading94 scoring are specified exactly for the
director (Claude). PASSMARKS sealed (`f16b2cc8…e053`, verified §7);
predictions P119b.1–P119b.7 in the ledger before the run.

## 1. Goal (one sentence)

Give the GPU wave everything it needs to test ranked fix 1 of doc 119d:
whether fixing the relation namespace in the TRAINING LABELS — a closed-list
WebRED-relation → inventory remap — moves the ears off the registered 119
FAIL (224/312 relation-wrong, exact 0, W2 = 0 writes on 3/3 seeds).

## 2. Premise (verified, not assumed)

Doc 119d (seed 11901, 312 reading94 triples): relation-wrong 224, of which
`located in…` → `country` alone is 80; spans are often right (42
rel-right-span-wrong frames, 11 fully-correct-but-below-tau). Length coverage
(119) changed ungated reads essentially not at all. So the ONE CHANGE is
labels, not window, head, encoder, or recipe: 119's window (192), lengthened
synth, SciBERT + FrameEars, 517 classes, 2-epoch recipe, CAL calibration, and
47 tau rule are all untouched.

## 3. The remap (built ONLY from training sources; reading94 untouched)

Canonical table: `artifacts/fable-ears119b-20260922/remap.json` (4 entries,
one-line reason each; `mapping` dict identical to the REMAP dict in
`fable_ears119b_data.py`, cross-checked by the audit script). Sources: WebRED
frames `relations.json` (names + counts) + WebRED-train positive example
sentences + SimpleWiki86 training sentences (wording checks for synth-side
renames). No reading94 sentence, triple, or count was inspected to choose any
entry — stated here and in PASSMARKS.

- `country` → `located in the administrative territorial entity`: WebRED-train
  positives are place/org → sovereign-state containment (e.g. University of
  Sheffield → United Kingdom, Quebec → Canada); the inventory containment
  relation is located-in.
- `city` → same target: synth STATE rows are person/place-in-place locatives
  ("X is in Y"); same containment wording, spans unchanged.
- `birthplace` → `place of birth`: synth "X born in Y" matches WebRED
  place-of-birth positives ("born … in <place>"); both registered 517-classes.
- `job` → `occupation`: synth "X's job is Y" is the frame the inventory calls
  occupation (WebRED-train has 9 occupation positives of the same shape).

Documented exclusions (NOT remapped, reasons in remap.json): country of
citizenship → occupation (spans differ: citizenship points at the country,
occupation at the profession — a blind rename would manufacture false rows);
birth/death swap (both already inventory relations; the error is contextual);
capital direction (training source mixes argument order); contains-inverse and
other out-of-inventory relations. All span-preserving renames only; every
target is a registered 517-class.

## 4. Data + training + scoring (all sealed in PASSMARKS)

- `fable_ears119b_data.py --build-pool` (BensPC): 119's pool builder with the
  REMAP applied to every training gold before encoding (synth golds +
  WebRED-train golds); the pool file stores ENCODED rows, so the remap is
  baked into what the trainer loads. Identity gates unchanged (synth ==
  60,000; kept ≥ 140,903; dropped ≤ 614; lengthened-synth median in [38,48]).
- Seeds 11911–11913 (119's 11901–11903 renamed); steps = 2·ceil(kept/32).
  `fable_ears119b_train.py` / `fable_ears119b_score.py` are thin shims that
  patch ONLY the hardcoded seed namespace in 119's trainer/scorer
  (SEEDS119 + renamed positional W3 bars 11911≥27/11912≥33/11913≥30) and
  delegate to their main()s — recipe, gates, verdicts, and the 106 normaliser
  are 119 verbatim. Needed because 119 asserts its seed ids; verified on the
  Mac that 11911 passes the seed gate (fails only at the CUDA assert, as it
  should on CPU) and 11901 is rejected.
- `fable_ears119b_wave.bat` (staged as `C:\Users\benja\ears119b\wave119b.bat`):
  pool build → seeds sequential → `--score47` → `--score-panel`. Scorer is the
  119 scorer via the shim; falsifier scored by the director with
  `fable_ears119d_diagnose.py` on seed 11911 (relation-wrong/(312−exact) ≥
  0.50 → the head, not the labels, is at fault).

## 5. Mac evidence (the only training on the Mac; discarded)

- Label audit (200 random training-source rows: 100 WebRED-train + 100 base
  synth, seed 11900; no encoder, no reading94): 31 changed / 169 unchanged —
  country→located 20, city→located 7, birthplace→place-of-birth 3,
  job→occupation 1 (`audit119b.json`). Lengthening appends text only and never
  touches golds, so base-gold pair counts equal pool-gold pair counts.
- Smoke (real SciBERT fp32, 113 mixed rows incl. 8 long rows >96 tokens, seed
  11910, 50 updates): step loss 25.20 → 11.63 (25) → 7.99 (50); full-subset
  25.04 → 7.39 (falls ✓). Panel-eval path 20/20 decoded, runs only (no
  scores). 1.36 s/step; 92.9 s total. Params 109,664,018 = 47/119 count ✓.

## 6. Forecasts (ledger P119b.1–P119b.7, before the run)

W3 ≥2/3 (0.30); W1 (0.40); W2 ≥2/3 (0.30); carried 47 marks (0.25 — remapped
synth rows now predict inventory names the un-remapped 47 panels still score
as city/birthplace/job, the honest risk); clock <2,700 s (0.60); pool gates
(0.85); falsifier stays ≥0.50 (0.45).

## 7. What this does and does not claim

Does: whether the relation-namespace remap unlocks real-text reads while
holding template behaviour and safety, with the head-vs-labels question
pre-registered as a falsifier. Does not: that any panel number transfers to
papers, that reading94 is still an untouched test set for anything beyond the
sealed marks (it is untouched by the REMAP; thresholds were never fitted on
it), or that the ears "understand" anything. A registered FAIL stops the line
per PASSMARKS §2.

Deviations (prep, pre-run): the train/score seed shims (119 hardcodes seed
ids; §4); the wave bat calls them instead of the 119 scripts. Smoke used 113
rows (vs 119's 83) because the sampler guarantees ≥8 long rows. Questions for
Ben: none.
