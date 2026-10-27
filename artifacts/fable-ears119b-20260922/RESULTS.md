# RESULTS — Exp 119b PREP (Muse, Mac CPU only; GPU wave NOT run)

**Result: PREP complete — the wave is staged and ready for the director to
launch on BensPC after the 119 line ends.** PASSMARKS sealed (`f16b2cc8…e053`,
verified §6), P119b.1–P119b.7 in the ledger, remap table + 200-row audit +
50-update Mac smoke green (loss falls with remapped labels; 20/20 panel
decodes, no scores). No BensPC GPU job started here; no panel score exists yet
and none is claimed. One staging bug found and fixed during prep (§5).

## 1. Files (all new, prefix `fable_ears119b_`)

- `scripts/fable_ears119b_data.py` — 119's pool builder + REMAP of every
  training gold before encoding (pool stores encoded rows, so the remap is
  baked into training). Diff vs 119 shows only the remap block + seed tuple +
  names.
- `scripts/fable_ears119b_train.py` / `fable_ears119b_score.py` — thin shims
  patching ONLY 119's hardcoded seed namespace (→11911–11913, renamed W3 bars)
  and delegating to 119's main()s (§5).
- `scripts/fable_ears119b_smoke.py` — Mac smoke (discarded seed 11910).
- `scripts/fable_ears119b_audit.py` — 200-row label audit (no encoder).
- `scripts/fable_ears119b_wave.bat` — staged as
  `C:\Users\benja\ears119b\wave119b.bat`.
- `artifacts/fable-ears119b-20260922/`: `PASSMARKS.md`, `SEAL.sha256.txt`,
  `remap.json`, `audit119b.json`, `smoke.json`, `scp119b.txt` (this file's
  folder; RESULTS.md here too).
- `design/v3/30-modes/119b-ears-remap-muse.md`.

## 2. Remap + audit (training sources only; reading94 untouched)

4 span-preserving renames (reasons in remap.json): country→located-in (20/200
audit rows), city→located-in (7), birthplace→place-of-birth (3),
job→occupation (1); 169/200 unchanged. Excluded with reasons: citizenship
(spans differ), birth/death swap (contextual), capital direction, inverses.

## 3. Smoke (real SciBERT, fp32 CPU, batch 8, 113 rows incl. 8 long rows >96)

Step loss 25.20 → 11.63 (25) → 7.99 (50); full-subset 25.04 → 7.39 (falls ✓).
Panel-eval path: **20/20 decoded, runs** (no scores). 1.36 s/step; 92.9 s
total. Params 109,664,018 = 47/119 count ✓.

## 4. Launch / fetch for the director (from this worktree root)

Stage per `scp119b.txt` (scripts closure + 10 sealed 47 panels + panel.jsonl
for scoring only + bat; big data via local `xcopy` from `ears119\repo\data`
on the PC — no re-upload). **Launch only after the 119 line ends; stop the
Qwen llama-server first if it holds VRAM; install nothing.** Detached launch
logs to wave119b.log; pool gates STOP the wave unless synth==60000,
kept>=140903, dropped<=614. Fetch: report47/report119/taus/wave119b.log +
per-seed meta.json. Falsifier: director runs
`scripts/fable_ears119d_diagnose.py` on seed 11911 (≥0.50 → head at fault).

## 5. Staging bug found in prep (fixed, declared deviation)

119's trainer/scorer hardcode `SEEDS119=(11901,11902,11903)` (assert + `w-<seed>`
paths), so the renamed seeds 11911–11913 would have crashed the wave on the
PC. Fixed additively with the two shims (§1); verified on the Mac: 11911
passes the seed gate (fails only at the CUDA assert, correct on CPU), 11901
is rejected, score-shim globals read (11911,11912,11913)/{27,33,30}.

## 6. Reproduce (Mac, prep only)

`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B ...` then
`scripts/fable_ears119b_audit.py --out <json>` (no snapshot needed) and
`scripts/fable_ears119b_smoke.py --snapshot <scibert> --out <json>`. Seal check:
`shasum -a 256 -c artifacts/fable-ears119b-20260922/SEAL.sha256.txt` → OK
(`f16b2cc834583acd611aa8cd4b999d6288b73c88efa3449613ce84d71acee053`).

## 7. What it means / What it does not mean

What it means: the wave can launch exactly as sealed; the remap is built from
training sources alone (reading94 untouched), audited (31/200 rows relabelled,
all into registered classes), and proven trainable (falling loss, eval runs,
staging, snapshot).
What it does not mean: no accuracy number exists yet — W1/W2/W3, the carried
47 marks, and the falsifier are forecasts (P119b.1 0.30 / P119b.2 0.40 /
P119b.3 0.30 / P119b.4 0.25 / P119b.5 0.60 / P119b.6 0.85 / P119b.7 0.45); the
remap does not touch citizenship/demonym or birth/death-swap errors by design.

Deviations: PASSMARKS D1–D7, plus (prep, pre-run) the seed shims (§5) and a
113-row smoke sample (≥8 long rows guaranteed). Questions for Ben: none.
