# RESULTS — Exp 109 PREP (Muse, Mac CPU only; GPU wave NOT run)

**Result: PREP complete — wave ready for Claude to launch on BensPC.**
All four scripts written, PASSMARKS sealed (`69644d…06e4`, verified below),
P109.1–P109.6 in the ledger, Mac audit + 100-update smoke green. No GPU job
started here; panel scores do not exist yet and none are claimed.

## 1. Files (all new, prefix `fable_ears109_`)

- `scripts/fable_ears109_data.py` — audit / `--build-pool` / `--build-cal` /
  `--write-alias` (imports 47 modules read-only).
- `scripts/fable_ears109_train.py` — BensPC wave trainer (fixed recipe,
  asserts CUDA + seeds 10901–10903, temps on calwebred).
- `scripts/fable_ears109_score.py` — `--calibrate` (tau_op) + `--score-panel`
  (R1–R4, alias view).
- `scripts/fable_ears109_smoke.py` — Mac smoke (discarded seed 10900).
- `artifacts/fable-ears109-20260921/`: `PASSMARKS.md`, `SEAL.sha256.txt`,
  `calwebred.json` (3,898 rows, sha `0842a465…a58c97f`), `relation_aliases.json`
  (sha `2ab3413d…3b6754`), `counts.json`, `smoke.json`.
- `design/v3/30-modes/109-ears-real-text-supervision-muse.md`.

## 2. Counts (audit, `--audit`, no model)

Panel 400 sentences / 312 triples / 245 NO_FACT ✓. WebRED train 81,517
(44,080 pos / 37,437 neg); dev 3,898 (1,806 / 2,092); heldout 26,302 rows.
Overlap (normalised exact): train∩panel **0**, dev∩panel **0** (P109.6 TRUE).
Label audit: all 481 train Wikidata names already in the 517 classes →
**no extension**. Caveat: 40/3,898 cal rows (1.0%) duplicate train
annotations exactly (published-split property; optimistic-gate bias, §3 doc).

## 3. Smoke (real SciBERT, fp32 CPU, batch 8, seed 10900, discarded)

96 short rows (all WebRED-train): step loss 22.16 → 5.52 (50) → 4.76 (100);
full-subset 22.88 → 2.88 (falls ✓). Panel-eval path: **20/20 decoded, runs**
(no scores). 0.707 s/step; 81.6 s total. Params 109,664,018 = 47's count ✓.

## 4. Timing → R5 estimate (confidence LOW-MEDIUM)

Same 8,808 steps/seed as 47 on the same GPU → training ≈ 24–31 min (47
measured 14.8/7.9/7.9) + calibrate/score ≈ 3–6 min → **wave ≈ 27–37 min vs
the 30-min bar**. Passes only if every seed holds the fast 0.054 s/step rate
and seeds launch back-to-back. Mac 0.707 s/step is a plumbing check, not the
anchor (different batch/width/precision).

## 5. Launch commands for Claude (from this worktree root)

Snapshot on BensPC (47 log):
`C:\Users\benja\.cache\huggingface\hub\models--allenai--scibert_scivocab_uncased\snapshots\24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1`
(use `$SNAP` below; work dir `C:\Users\benja\ears109\` = `$W`).

```sh
# 0. stage files (repo scripts + sealed data + R4 panels + held-out panel for scoring ONLY)
ssh benspc "mkdir C:\Users\benja\ears109\repo\scripts C:\Users\benja\ears109\runs"
scp scripts/fable_ears109_data.py scripts/fable_ears109_train.py scripts/fable_ears109_score.py \
  scripts/fable_ears47_data.py scripts/fable_ears47_model.py scripts/fable_ears47_encoder.py \
  scripts/fable_ears47_train.py scripts/fable_ears47_score.py scripts/fable_read106_score.py \
  scripts/fable_bert_loader.py scripts/fable_listening_english.py scripts/fable_ears45_data.py \
  "benspc:C:/Users/benja/ears109/repo/scripts/"
scp artifacts/fable-ears109-20260921/calwebred.json artifacts/fable-ears109-20260921/relation_aliases.json \
  artifacts/fable-ears109-20260921/PASSMARKS.md data/open/reading94/panel.jsonl \
  "benspc:C:/Users/benja/ears109/"
scp artifacts/fable-ears47-20260921/panels/t_seen.json artifacts/fable-ears47-20260921/panels/t_new.json \
  "benspc:C:/Users/benja/ears109/"
# 1. pool (STOP unless kept=140903 dropped=614 excluded=0)
ssh benspc "cd C:\Users\benja\ears109\repo\scripts && python fable_ears109_data.py --build-pool C:\Users\benja\ears109\pool109.jsonl --snapshot $SNAP"
# 2. three seeds, sequential; record step200 lines + wall times (R5 window starts here)
for s in 10901 10902 10903; do ssh benspc "cd C:\Users\benja\ears109\repo\scripts && python fable_ears109_train.py --seed $s --pool C:\Users\benja\ears109\pool109.jsonl --snapshot $SNAP --cal C:\Users\benja\ears109\calwebred.json --out C:\Users\benja\ears109\runs\w-$s"; done
# 3. calibrate gate, then score panel (R5 window ends at score write)
ssh benspc "cd C:\Users\benja\ears109\repo\scripts && python fable_ears109_score.py --calibrate --runs C:\Users\benja\ears109\runs --cal C:\Users\benja\ears109\calwebred.json --snapshot $SNAP --out C:\Users\benja\ears109\taus.json"
ssh benspc "cd C:\Users\benja\ears109\repo\scripts && python fable_ears109_score.py --score-panel --runs C:\Users\benja\ears109\runs --taus C:\Users\benja\ears109\taus.json --snapshot $SNAP --alias C:\Users\benja\ears109\relation_aliases.json --panels47 C:\Users\benja\ears109 --out C:\Users\benja\ears109\report109.json"
# 4. fetch (checkpoints ear.pt 438 MB x3 optional)
scp "benspc:C:/Users/benja/ears109/taus.json" "benspc:C:/Users/benja/ears109/report109.json" artifacts/fable-ears109-20260921/
scp "benspc:C:/Users/benja/ears109/runs/w-10901/meta.json" artifacts/fable-ears109-20260921/meta-10901.json
```

GPU-memory note: if a llama-server holds VRAM, stop it first (47 did); do
not kill other people's processes, install nothing (`torch 2.11+cu128` is
there; no `transformers` needed — plain-PyTorch loader). Another job may be
running — schedule, don't pre-empt.

## 6. Reproduce (Mac, prep only)

`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B ...` then
`scripts/fable_ears109_data.py --audit`, and `scripts/fable_ears109_smoke.py
--snapshot <scibert> --out <json>` (81.6 s here). Seal check:
`shasum -a 256 artifacts/fable-ears109-20260921/PASSMARKS.md` =
`69644d240f57a01998b370392cc99c6db55a48b36ff64b7262fcdc8b06e4076b`.

## 7. What it means / What it does not mean

What it means: the wave can launch exactly as sealed; training mix, labels,
gate rule, bars, and baselines are fixed and the plumbing (loss falls, eval
runs) is proven on the real encoder.
What it does not mean: no panel number exists yet — R1–R5 are forecasts
(P109.1 0.15 / P109.2 0.40 / P109.3 0.25 / P109.4 0.70 / P109.5 0.55), and the
40-row cal/train duplication plus the tight R5 window are stated risks, not
fine print.

Deviations: D1–D5 in PASSMARKS §3 (dev reserved for cal; no label extension;
smoke discarded; panel copied for scoring only; R4 spans two gates).
Questions for Ben: none.
