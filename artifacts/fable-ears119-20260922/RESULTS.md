# RESULTS — Exp 119 PREP (Muse, Mac CPU only; GPU wave NOT run)

**Result: PREP complete — the wave is staged and ready for Claude to launch on
BensPC after the talker run ends.** PASSMARKS sealed (`840c0bad…38174`,
verified §6), P119.1–P119.6 in the ledger, length histograms before/after
green, 50-update Mac smoke green (loss falls with long rows; 20/20 panel
decodes, no scores). No BensPC GPU job started here (files staged into
`C:\Users\benja\ears119\` only); no panel score exists yet and none is claimed.

## 1. Files (all new, prefix `fable_ears119_`)

- `scripts/fable_ears119_data.py` — `--audit` / `--length-hist` /
  `--build-pool` (imports 47 modules read-only; MAX_LEN override in-file).
- `scripts/fable_ears119_train.py` — BensPC wave trainer (fixed 47 recipe,
  seeds 11901–11903, asserts CUDA, temps on sealed 47 CAL).
- `scripts/fable_ears119_score.py` — `--score47` (47 gate + corrected SEEN +
  W1, emits taus) + `--score-panel` (W2/W3 on held-out reading94).
- `scripts/fable_ears119_smoke.py` — Mac smoke (discarded seed 11900).
- `scripts/fable_ears119_wave.bat` — staged as `C:\Users\benja\ears119\wave119.bat`.
- `artifacts/fable-ears119-20260922/`: `PASSMARKS.md`, `SEAL.sha256.txt`,
  `hist.json`, `smoke.json` (+ logs).
- `design/v3/30-modes/119-ears-length-coverage-muse.md`.

## 2. Length histograms before/after (`hist.json`, SciBERT WordPiece, no model)

| corpus | n | med | p90 | p99 | ≤96 | ≤192 |
|---|---|---|---|---|---|---|
| WebRED-train | 81,517 | 41 | 81 | 183 | 94.10% | **99.37%** |
| simplewiki86 sentences | 200,000 | 21 | 34 | 46 | 99.9995% | **99.9995%** |
| synth before (47 recipe) | 60,000 | 14 | 20 | 26 | 100% | 100% |
| synth after (lengthened) | 60,000 | 43 | 83 | 179 | 93.8% | 100% |

MAX_LEN **192** covers ≥99% of both required corpora (the one over-long
SimpleWiki row is 304 tokens). Lengthened synth (med 43 / p90 83 / p99 179)
matches WebRED-train (41 / 81 / 183); median-gate [38,48] holds at 43.

## 3. Smoke (real SciBERT, fp32 CPU, batch 8, 83 rows incl. 8 long rows >96)

Step loss 23.17 → 16.05 (25) → 4.65 (50); full-subset 24.73 → 5.15 (falls ✓).
Panel-eval path: **20/20 decoded, runs** (no scores). 1.38 s/step; 91.6 s
total. Params 109,664,018 = 47's count ✓.

## 4. GPU memory estimate (names batch 32, MAX_LEN 192, bf16)

Params 0.22 GB + grads 0.22 GB + AdamW m/v 0.88 GB ≈ 1.3 GB; activations
worst-case full-192 batch ≈ 1.3 GB (12 layers × ~105 MB: hidden copies +
32×12×192² attention); ×2 fragmentation margin → **≈ 5–6 GB, fits 16 GB at
batch 32** with headroom (batch 64 would also fit).

## 5. Wave time estimate (T-CLOCK, recorded only)

47 measured 14.8/7.9/7.9 min/seed (8,808 steps) at static width 96. 119 does
~8,826 steps with per-batch dynamic padding (masked-identical compute); mean
batch-max ≈ 110–130 tokens → ≈ 1.2–1.3× 47's per-step cost → **≈ 35–45 min
for 3 seeds + calibrate/score, vs the 2,700 s bar. Confidence MEDIUM-LOW**:
passes only if seeds 2–3 hold 47's fast rate; seed 1 pays compile + tail rows.
The trainer prints a step-200 projection; a miss resolves T-CLOCK FALSE with
no improvisation.

## 6. Launch / fetch / score commands for Claude (from this worktree root)

Files are already staged (scripts, PASSMARKS, 47 panels, webred-train at the
repo-relative path, panel.jsonl for scoring only); snapshot verified on
BensPC (`...scibert_scivocab_uncased\snapshots\24f92d32…fc1` holds
config/pytorch_model.bin/vocab.txt). **Launch only after the talker run ends
(~04:00); stop the Qwen llama-server first if it holds VRAM; install nothing.**

```sh
# detached launch (single fire-and-forget; logs to wave119.log)
ssh benspc "powershell -NoProfile -Command \"Invoke-CimMethod Win32_Process -MethodName Create -Arguments @{ CommandLine = 'cmd /c C:\\Users\\benja\\ears119\\wave119.bat' } | Out-Null; echo LAUNCHED\""
# poll (pool gate STOPs the wave unless synth==60000, kept>=140903, dropped<=614)
ssh benspc "type C:\Users\benja\ears119\wave119.log"
# fetch + score (scores run on BensPC inside the .bat; fetch the reports)
scp "benspc:C:/Users/benja/ears119/report47.json" "benspc:C:/Users/benja/ears119/report119.json" "benspc:C:/Users/benja/ears119/taus.json" "benspc:C:/Users/benja/ears119/wave119.log" artifacts/fable-ears119-20260922/
scp "benspc:C:/Users/benja/ears119/runs/w-11901/meta.json" "benspc:C:/Users/benja/ears119/runs/w-11902/meta.json" "benspc:C:/Users/benja/ears119/runs/w-11903/meta.json" artifacts/fable-ears119-20260922/
```

`wave119.bat` runs: pool build (identity gates) → seeds 11901–11903 sequential
→ `--score47` (47 gate + W1 + taus) → `--score-panel` (W2/W3).

## 7. Reproduce (Mac, prep only)

`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B ...` then
`scripts/fable_ears119_data.py --length-hist <out> --snapshot <scibert>` and
`scripts/fable_ears119_smoke.py --snapshot <scibert> --out <json>`. Seal check:
`shasum -a 256 artifacts/fable-ears119-20260922/PASSMARKS.md` =
`840c0bad88e0f66fa024bdbbb1a7609934d65042065faf58c8cc92427db38174`.

## 8. What it means / What it does not mean

What it means: the wave can launch exactly as sealed; the length mismatch is
closed on paper (window covers 99%+ of both corpora; synth matches WebRED's
histogram bin-for-bin); plumbing (falling loss with long rows, eval runs,
staging, snapshot) is proven.
What it does not mean: no accuracy number exists yet — W1/W2/W3 and the
carried 47 marks are forecasts (P119.1 0.20 / P119.2 0.35 / P119.3 0.25 /
P119.4 0.45 / P119.5 0.60 / P119.6 0.85); length coverage does not touch the
doc-107 relation-namespace mismatch, and the T-CLOCK window is tight, not safe.

Deviations: D1–D6 in PASSMARKS §3, plus (prep, pre-run) the smoke sampler was
fixed to guarantee ≥8 long rows (first attempt yielded 5; recipe unchanged)
and `--panel` was added to the scorer for the BensPC path. Exp-118 brake was
absent at seal — sealed without it, as instructed. Questions for Ben: none.
