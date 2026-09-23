# PASSMARKS — Exp 119f: panel-shaped occupation supervision (Muse BUILD)

Written and hashed **before any registered run** (open audit + Mac CPU smoke
only after the seal; the registered wave runs on BensPC by the director).
Artifact dir: `artifacts/fable-ears119f-20260922/`. Plan:
`design/v3/30-modes/119f-ears-plan-muse.md`. Build doc:
`design/v3/30-modes/119f-ears-build-muse.md`. Date: 2026-09-22.
Open audit (pre-seal): 5,000 occ rows, 0 sentence / 0 name overlap vs the old
panel, 500/500 encode, 20,763 STATE targets.

## 0. The one change vs exp 119b (training data only)

119b/119e diagnosis (frozen weights): ensemble CAL executes 570 yet panel
writes 0 on 3/3 seeds; occupation is the largest fixable cluster (44 panel
golds, 41 relation-wrong: occ→dob 17, →citizenship 16, →located-in 8) with a
shape provably absent from training, while 1,936 citizenship rows teach
demonym→citizenship. THE ONE CHANGE: `scripts/fable_ears119f_data.py`
replaces (not adds) N_REPLACE=5,000 lengthened synth STATE rows 1:1 with
panel-worded occupation rows ("PERSON was a/an DEMONYM PROFESSION",
"PERSON (YYYY-YYYY) was a DEMONYM PROFESSION and PROFESSION2";
gold = STATE/occupation/person-span/profession-span; demonym never gold).
Pool size, steps, recipe, scorer, and tau rule are unchanged.

## 1. Fixed recipe (all sealed)

- Encoder: `allenai/scibert_scivocab_uncased`, snapshot
  `24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1` + our `FrameEars` head, N_REL=517.
- Pool (`fable_ears119f_data.py --build-pool`, BensPC): 60k synth with the 1:1
  occupation replacement (RNG_OCC 11950; first 5,000 STATE rows) + all
  WebRED-train rows with the 119b REMAP. Identity gates (else prep FAILs, no
  seed trains): synth rows == 60,000; occ rows == 5,000; kept total in
  [141377, 141408] (same step count as 119b's 141,398); dropped <= 614.
- Seeds **11911, 11912, 11913**; steps = 2 * ceil(kept/32) asserted == **8838**
  in the trainer (else prep FAILs). Batch 32, 2 epochs, AdamW 3e-5 cosine,
  wd 0.01, clip 1.0, bf16 on CUDA, freeze 0, CAL temperatures, 47 tau rule on
  CAL only. BensPC work dir `C:\Users\benja\ears119f\`.
- Scorers: `fable_ears119f_score.py --score47e` (119e logic verbatim by import:
  remapped golds, CAL taus); `--score-panel` (119/119b panel path generalized:
  no hardcoded triple counts; W3 bars by the formula below; occupation-subset
  exact per seed for F1). No test.pt anywhere.

## 2. The marks (per seed, never averaged)

All 47/119e bars kept verbatim (SAFE 0 silent; NEG <= 2 % of 2,092; SEEN
1,940/2,000 AND 589/654 exec; NEW 2,400/3,000 AND 784 exec; NAMES 300/500;
ASK <= 25; WEB 28 exec AND 85 % exact; NEWREL <= 1 %; W1 23/46 exec + 0
silent). Old-panel marks re-reported with 119e bars but NON-GATING
(reading94 is descriptive-only: it shaped this change):
- **W3 (94):** raw exact 11911 >= 27, 11912 >= 33, 11913 >= 30 (>= 2/3 seeds).
- **W2 (94):** correct >= 30 AND wrong <= 5 % of writes (writes > 0), >= 2/3.

REGISTERED panel = `data/open/reading94b/panel.jsonl` (400 sentences; sealed
by exp 94b; never opened here). N94b = its sealed gold-triple count, counted
by the scorer (a fixed property of the sealed panel, never tuned):
- **W3b (94b):** raw exact per seed >= bar_seed with
  **bar_seed = ceil(base_seed * N94b / 312)**, bases 27/33/30 (119b's
  reading94 bars, positional per seed), required in **3/3 seeds**.
- **W2b (94b):** writes > 0 AND wrong writes <= **5 %** of writes (the 119b W2
  bar), required in **>= 2/3 seeds** (no minimum-correct bar: any write is
  signal after 119e's 0/0/0).
- **T-CLOCK** (recorded only): 3-seed wave < **1800 s** (§6).

Verdict = PASS iff SAFE ∧ NEG ∧ SEEN ∧ NEW ∧ NAMES ∧ ASK ∧ WEB ∧ NEWREL ∧ W1
∧ W3b ∧ W2b ∧ ¬F1. A registered FAIL is recorded as FAIL, never re-run.

## 3. Falsifier F1 ("panel-shaped"; scored by the director)

Let r94 = occ-exact-rate on reading94 under 119f, b94 = 119b occ-exact-rate on
reading94 (director's frozen diag: 44 occ golds, 41 relation-wrong on seed
11911), r94b = occ-exact-rate on reading94b under 119f (occ_exact/occ_gold in
`report119f_94[b].json`, per seed; use each seed's own rate, never averaged).
**F1 fires iff r94 > b94 AND r94b <= b94 on >= 2/3 seeds** (the gain exists
only on the panel the change was designed from). If F1 fires the verdict is
FAIL with the single word "panel-shaped" and the generalization claim is void.

## 4. Pre-registered deviations (from the 119f plan + 119b recipe)

1. W3b uses the scaled-formula bar (3/3 seeds), not the plan's fixed 35: the
   94b triple count is sealed by another agent and unknowable here.
2. `--score-panel` generalizes the 119 asserts (counts, not tuning) and adds
   occupation-subset exact (F1 inputs); 94 runs reproduce 119e bars exactly.
3. ~30 % of occ rows carry "(YYYY-YYYY)" + "and PROFESSION2" (plan wording);
   gold is the first profession only (single-frame decode, as trained).
4. Occ rows skip the 10 % hearsay augmentation (all 5,000 stay STATE
   occupation golds; the augmentation rate shift is 5,000/141,398 = 3.5 %).
5. No Qwen practice sentences (same as 47 §2.13, 119 D1). Per-batch dynamic
   padding (119 D2). `panel.jsonl` files scoring-only (119 D5). No 118 gate.
6. Mac smoke (seed 11910, 50 updates, discarded) proves the builder + loss
   fall WITH occ rows; it reports no scores.

## 5. Predictions

P119f.1–P119f.6 in `artifacts/fable-predictions-ledger.md`, appended before
the seal (see that file).

## 6. GPU wall-clock plan (< 1800 s; one RTX 5070 Ti)

Anchors from `wave119b.log`/metas: pool build ~1.5 min (119b: 77 s) + 3 seeds
x ~9.3 min (119b: 608 s/seed at ~22 k tok/s; occ rows are short, ~8 % fewer
tokens/step by throughput arithmetic) + CAL temps & three panel scorings ~3
min → ≈29 min. The throughput gain is a forecast; any overrun is a reported
deviation, never compensated by touching bars or gates.
