# RESULTS — Experiment 120: talker mouth fine-tune PREP (Muse), 2026-09-22

## Result

PREP COMPLETE, both smoke gates PASS. Everything the GPU fine-tune needs
exists, is sealed, and is proven on the Mac CPU path. No fine-tuning has
happened — the registered O1–O6 remain predictions (ledger P120.3–P120.8).

## Marks table (integers; smoke seeds reported, never averaged)

| Mark | Bar | Got (seed 12001) | Verdict |
|---|---|---|---|
| S1 loss falls (100 CPU steps, bs2, ctx256, lr 1e-4) | last20-mean < first20-mean | 5.4466 → 3.5888 | PASS |
| S2 20 held-out decodes | run, no crash, all reported | 20/20 non-empty, 5.3 s | PASS |
| O1–O6 (registered GPU run, seed 12002) | PASSMARKS.md (seal 4bb165df) | not run yet | OPEN |

Smoke decode detail (20 records, 100-step baby model): before-brake
violations 17/20, after-brake 0/20, status correct 17/20, OK answers 9/9,
fallbacks 17, p_gen mean 0.45. Fallback net verified separately: all 500
held-out fallbacks pass the brake, classify to their own status, and carry
their OK/SAVED answer (500/500 × 3).

## 10 verbatim smoke examples (raw -> final)

1. OK good-via-fallback: `ld.` -> `Ysolde's baker is Kito.` PASS (net holds).
2. UNKNOWN babble caught: `'sa'sa'sa…` -> `I don't know Farah's spouse.` PASS.
3. OK web suffix kept: `'s h mother's h.` -> `Amos's mother's uncle's hometown
   is Otis. (I read that online; you didn't tell me.)` PASS.
4. FORGOT loop caught: `'s G's G's G's G's G.` -> `I've forgotten Gideon's
   nurse.` PASS.
5. SAVED fragment caught: `a'saaa…` -> `Saved: Farah's school's father is
   Runa.` PASS.
6. OK single-char caught: `m.` -> `Amos's teammate is Sten.` PASS.
7–10. Same pattern: raw decoder copies `'s`-fragments in a loop (untrained
copy head, p_gen 0.40 → 0.74 during smoke); every one falls back correctly.

## Data (measured)

3,000 train + 500 held-out pairs (250 OK + 50×5), seed 12001, all machine-checks
green: train/test name pools (48+48) and place pools (12+12) disjoint;
3,500/3,500 sentences pass the brake; 3,500/3,500 classify to their own
status; 1,550/1,550 OK/SAVED sentences contain their answer; surface forms
per status 199/34/30/46/87/30 (bar ≥ 30 each). Max prefix 61 tokens, max pair
104 tokens (ctx 256).

## Deviations from my own plan (all before the registered run)

1. Live `full_run/ckpt_last.pt` NOT copied for the smoke: the trainer rewrites
   it every step (~3/s), so any copy risks a torn file, and the GPU run must
   not be disturbed. Smoked from the stable CPU ckpt instead; the registered
   run resumes from the finished full-run checkpoint.
2. Record markers are plain words (`record status OK name … end`), not
   `<REC>`-style tags: the talker101 BPE has no spare special rows, and growing
   our embedding would break clean resume from any talker101 checkpoint.
3. Fallback is our own `fallback_say` (one fixed template per status), not
   wire51's TemplateMouth: the contract does not know these six statuses (it
   echoed `UNKNOWN`, which the brake rightly rejected). Found by the smoke,
   fixed, verified 500/500.
4. Brake word list = exp 53's verbatim + 30 documented generic words
   (forgotten/forgot + 28 ordinary words the new templates need); none names a
   fact. Two train-script off-by-ones (causal/target masks) fixed in the smoke.
5. Full-model fine-tune (nothing frozen — it is our model), lr 1e-4.

## GPU run: time estimate, launch, fetch, score (for the director)

Estimate: ~1.05M tokens (5 epochs × ~0.21M) at the measured 49,000 tok/s ≈
25 s compute + 500-record greedy scoring + wire51 replay ≈ **4–6 min total**
(bar O4 < 25 min). VRAM ≈ 2 GB (28.85M bf16 + AdamW + bs32×256).

1. Pre-check (read-only; proceed only if empty):
   `ssh benspc "nvidia-smi --query-compute-apps=pid,process_name --format=csv | findstr /i python"`
2. Sync to `C:\Users\benja\talker101\`: `scripts/fable_talker120_*.py`,
   `scripts/fable_talker101_model.py`, `artifacts/fable-talker120-20260922/data/`
   (as `fable-talker120-data/`), `artifacts/fable-talker101-20260921/fable_talker101_tokenizer.json`.
3. Detached launch (after the pretraining run exits):
   `ssh benspc "powershell.exe -NoProfile -NonInteractive -Command \"Invoke-CimMethod Win32_Process -MethodName Create -Arguments @{CommandLine='cmd /c cd /d C:\\Users\\benja\\talker101 & py -3.10 fable_talker120_train.py --device cuda --ckpt full_run\\fable_talker101_ckpt_last.pt --tok fable_talker101_tokenizer.json --data fable-talker120-data --out fable-talker120-ft --epochs 5 --bs 32 --ctx 256 --lr 1e-4 --seed 12002 > fable_talker120_ft.log 2>&1'}\""`
4. Score + replay on BensPC, then fetch:
   `scp benspc:C:/Users/benja/talker101/fable-talker120-ft/fable_talker120_ckpt_last.pt artifacts/fable-talker120-20260922/adapter/`
   Mac re-score: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
   --no-project --python 3.12 --with torch --with numpy python -B
   scripts/fable_talker120_score.py --data artifacts/fable-talker120-20260922/data
   --ckpt artifacts/fable-talker120-20260922/adapter/fable_talker120_ckpt_last.pt
   --tok artifacts/fable-talker101-20260921/fable_talker101_tokenizer.json
   --out artifacts/fable-talker120-20260922/score.json`

## Exact reproduce (Mac smoke)

```
python3 -B scripts/fable_talker120_data.py --out artifacts/fable-talker120-20260922/data --seed 12001
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_talker120_train.py --ckpt artifacts/fable-talker101-20260921/fable_talker101_smoke_cpu/fable_talker101_ckpt_last.pt --tok artifacts/fable-talker101-20260921/fable_talker101_tokenizer.json --data artifacts/fable-talker120-20260922/data --out <dir> --steps 100 --bs 2 --ctx 256 --lr 1e-4 --seed 12001 --device cpu
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_talker120_score.py --data artifacts/fable-talker120-20260922/data --ckpt <dir>/fable_talker120_ckpt_last.pt --tok artifacts/fable-talker101-20260921/fable_talker101_tokenizer.json --out <score.json> --limit 20
```

## Questions for Ben

None. Defaults taken: full-model FT, plain-word markers, own fallback, live
checkpoint untouched, GPU launch left to the director after ~04:00.

## What it means

The whole second-stage pipeline is proven: our talker ingests serialized
records, its copy head trains on the target span (p_gen 0.40 → 0.74 in 100
steps), greedy mixture decoding runs, and the brake + status-aware fallback
hold 20/20 and 500/500 while the baby model still babbles.

## What it does not mean

The model has learned almost nothing yet (17/20 raw violations) — O6 (≤ 10 %
raw unfaithful after 5 GPU epochs from the fully-pretrained checkpoint) is an
open prediction, and a FAIL stays a FAIL. No GPU job was started, and the
live pretraining run was never touched.
