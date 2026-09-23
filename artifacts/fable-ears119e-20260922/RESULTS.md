# RESULTS — Exp 119e PREP + open diagnosis (Muse, Mac CPU; scoring NOT run)

**Result: the 119b execute gate is shut because of a label-namespace mismatch
at scoring time — confirmed, not assumed — and 119e (one change: apply the
remap to panel golds at scoring time) is sealed and staged for the director
to score on BensPC.** Full-CAL open diagnosis (seed 11911): 346/5,000 CAL
golds use the old names (city 301, job 24, birthplace 21, country 0); 43 of
the 50 highest-confidence wrong rows are exactly "pred = REMAP[gold], same
spans" (≥ 80 % gate: PASS); the single row fixing tau is a city→located-in
mismatch at conf 0.9625, and my pipeline reproduces the sealed 119b taus
bit-for-bit. PASSMARKS sealed (`7cf3fd80…fc00`, verified §6), P119e.1–P119e.5
in the ledger. No registered scoring ran here; no weights changed.

## 1. Files (all new, prefix `fable_ears119e_`)

- `scripts/fable_ears119e_diagnose.py` — open diagnosis (119 scorer decode by
  import, seed-11911 checkpoint read-only).
- `scripts/fable_ears119e_score.py` — the ONE change: `remap_gold_frame()`
  on 47-panel golds, unchanged 47 rule/marks; `--score-panel` delegates to
  the 119b scorer (compile-checked only, never executed pre-seal).
- `scripts/fable_ears119e_wave.bat` — staged as
  `C:\Users\benja\ears119e\wave119e.bat` (scoring only, frozen checkpoints).
- `artifacts/fable-ears119e-20260922/`: `PASSMARKS.md`, `SEAL.sha256.txt`,
  `scp119e.txt`, `diag119e_full.json` (5,000 rows), `diag119e_subset1000.json`
  (pilot), RESULTS.md here too.
- `design/v3/30-modes/119e-ears-gate-diagnosis-muse.md`.

## 2. Diagnosis (full CAL, seed 11911, 913 wrong at tau 0 of 5,000)

- Old-name CAL golds: **346** (city 301, job 24, birthplace 21, country 0);
  new names: 0. Mismatches overall: **342**, all EXECUTE (city 299, job 24,
  birthplace 19 — every job row and 19/21 birthplace rows read right).
- Top-50 wrong by conf: **43/50 mismatch** (all city→located-in, all
  EXECUTE); other 7 are UNSURE-gold ECHOs (STATE/OPEN), never EXECUTE — they
  cannot fix tau. 4 more old-gold rows are ASK-gold/state-pred act errors
  with the right remapped relation.
- Tau rule (quoted): `tau0_from_cal`, "smallest tau0 with 0 wrong EXECUTED
  writes on CAL" (`scripts/fable_ears47_score.py:458-477`), then
  `tau_exec = 1-(1-tau0)/2` (`scripts/fable_ears119_score.py:99,103`).
  Old golds: worst 0.9625 → tau_exec_single **0.9812427163124084** = sealed
  value exactly. Remapped golds: worst 0.7384 (UNSURE-gold favorite_color
  EXECUTE) → **0.8692**, back in the 119 regime.
- reading94 golds already use inventory names (**311/312**; one `country`
  triple, El Al → Israel, left as-is, scoring only).

## 3. Person-city question: yes.

Synthetic `city` is a PERSON's town ("Eero's town is Raishholm",
"Vabiraine's town is Helroford"). What the notebook would need (not built):
a subject-type check on frames with rel "located in the administrative
territorial entity" — PERSON subject maps back to `city`, place/org subject
keeps located-in. That needs a person-vs-place subject signal in the
notebook; nothing here builds it.

## 4. Launch / fetch for the director (from this worktree root)

Stage per `scp119e.txt` (new scorer + bat via scp; closure via local xcopy;
remap.json at the repo-relative path the scorer asserts). Launch detached;
Qwen llama-server first if it holds VRAM; install nothing; scoring only.
Fetch: `report47e.json` / `report119e.json` / `taus119e.json` /
`wave119e.log` into `artifacts/fable-ears119e-20260922/`.

## 5. What it means / What it does not mean

What it means: the shut gate is explained (confident correct reads scored
wrong on CAL push tau above everything) and 119e is staged to re-open it;
W3 is forecast to stand still (23/19/18, P119e.4 0.80) since no weights move.
What it does not mean: no 119e score exists yet — gate47, W1, W2 are
forecasts (P119e.1 0.70 / P119e.2 0.80 / P119e.3 0.65); the remap does not
touch UNSURE-gold abstain granularity or the 7 ECHO rows.

Deviations: full-CAL decode replaced the 1,000-row pilot (same script,
`--n 5000`, 323 s); scorer compile-checked only. Post-seal writes (reported
per brief): this RESULTS.md, the design doc, and the two diag JSON copies —
scorer, bat, and PASSMARKS untouched since the seal. Questions for Ben: none.

## 6. Reproduce (Mac, open diagnosis only)

`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B
scripts/fable_ears119e_diagnose.py --runs <scratchpad>/ears119b/runs
--panels47 artifacts/fable-ears47-20260921/panels --snapshot <scibert>
--out <json> --n 5000`. Seal check:
`shasum -a 256 -c artifacts/fable-ears119e-20260922/SEAL.sha256.txt` → OK
(`7cf3fd80c395e79052a69694ab4e658bbfe9855a3e7b1d9333f20ed4e56fc00`).
