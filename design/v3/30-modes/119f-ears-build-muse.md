# 119f — Ears borrowed-encoder build: panel-shaped occupation supervision (Muse)

Status: BUILD + SEAL ONLY. No GPU run, no BensPC contact, no weights changed,
no scores. The director launches `wave119f.bat` on BensPC after the reading94b
seal. PASSMARKS sealed (`fea68656…`); predictions P119f.1–P119f.6 in the ledger.

## 1. Why this one change

119b doubled raw real-text reading (W3 23/19/18 vs 119's 11/11/8) but the 119e
re-gate still executes nothing on the panel (CAL 570 vs SEEN 276 < 589, NEW
365 < 1038) and writes 0/0/0. The frozen-weight diag (seed 11911) names the
largest fixable cluster: 44 occupation golds, 41 relation-wrong (occ→dob 17,
→citizenship 16, →located-in 8). Training shape is provably absent (synth job
= person→ORG; WebRED has 9 odd occupation positives, zero "X was a DEMONYM
PROFESSION" rows) while 1,936 citizenship rows teach demonym→citizenship —
exactly the distractor the panel embeds ("American television writer").
Occupation is the biggest evidence-backed exact-frame lever that holds the
wrong-write budget fixed (no gate/threshold/decoder change).

## 2. The change (data only)

`scripts/fable_ears119f_data.py`: 5,000 rows in two panel wordings —
"PERSON was a/an DEMONYM PROFESSION." (70 %) and
"PERSON (YYYY-YYYY) was a/an DEMONYM PROFESSION and PROFESSION2." (30 %) —
gold `(STATE, occupation, person-span, profession-span)`; the demonym is a
distractor by construction. Closed lists written in the file: 69 bare-noun
professions, 40 demonyms, 66×80 fictional names paired procedurally
(RNG_OCC 11950). The first 5,000 synth STATE rows are REPLACED 1:1, so the
pool stays 60,000 synth / 8,838 steps; WebRED rows keep the 119b REMAP.
Builder asserts (prep FAILs otherwise): synth == 60,000, occ == 5,000, kept ∈
[141377,141408], dropped ≤ 614; trainer asserts steps == 8,838.

## 3. Novelty (no copying)

Pre-seal audit vs the OLD panel only (descriptive use): 0/5,000 sentence
overlap, 0 name-substring hits (4 bank names swapped before sealing), 500/500
sample encodes with zero flags, 20,763 STATE targets. Twelve single common
nouns (writer, actor…) coincide with panel gold objects — unavoidable generic
vocabulary; every sentence and every name is novel. The registered
`data/open/reading94b/panel.jsonl` was never opened (path only).

## 4. Scoring both panels + the falsifier

`fable_ears119f_score.py`: `--score47e` is the 119e re-gate verbatim by import
(remapped golds, 47 rule on CAL only). `--score-panel` generalizes the 119
panel path: no hardcoded counts; W3 bar = `ceil(base·N/312)` with positional
bases 27/33/30 (exact 27/33/30 on reading94 since N = 312; N is a fixed sealed
property, never tuned); W2 thresholds by flag (94: ≥ 30 correct + ≤ 5 % wrong;
94b: writes > 0 + ≤ 5 % wrong); occupation-subset exact per seed on each
panel. Falsifier F1 (PASSMARKS §3): if the occupation-exact rate rises on
reading94 but not on reading94b (≥ 2/3 seeds), verdict FAIL "panel-shaped",
claim void. All 47/119e bars kept; old-panel W2/W3 re-reported, non-gating.

## 5. Staging, timing, smoke

`scp119f.txt` stages the full script closure + sealed 47 panels + both panels
(scoring only) + the REQUIRED `data/open` folders (119e crashed without
webred: `relations.json` is read at scorer import; verified on-PC before
launch). Wall plan < 1,800 s: ~1.5 min pool + 3 × ~9.3 min seeds (119b: 608
s/seed; shorter occ rows forecast ~8 % fewer tokens/step) + ~3 min scoring.
Mac-CPU smoke (post-seal, seed 11910, discarded): 176 rows incl. 18 occ + 8
long, 50 steps, loss 24.69 → 7.91 (full 24.35 → 8.17); trainer CPU path (4
steps, meta-smoke.json) and scorer import verified; no scores reported.

## 6. What this does and does not claim

Does: stage one falsifiable, budget-fixed training change with sealed bars, a
scaled-bar rule for the unseen panel, and a panel-shaped falsifier. Does not:
claim any 119f score, move any gate, or touch the decoder. Deviations D1–D4
in PASSMARKS §4 / RESULTS. Questions for Ben: none.
