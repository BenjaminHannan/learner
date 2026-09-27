# PASSMARKS — Exp 119e: score-time gold-remap re-gate of frozen 119b checkpoints (Muse PREP)

Written and hashed **before any registered scoring** (Mac prep + open
diagnosis only after the seal; the registered scoring runs on BensPC by the
director). Artifact dir: `artifacts/fable-ears119e-20260922/`. Design doc:
`design/v3/30-modes/119e-ears-gate-diagnosis-muse.md`. Date: 2026-09-22.
Open diagnosis: `diag119e_full.json` (full 5,000-row CAL decode, seed 11911).

## 0. The one change vs exp 119b scoring (diagnosis ref: full-CAL §4)

119b is a registered FAIL: the remapped model predicts the NEW relation names
while the 47 panels' gold labels still use the OLD names, so confident correct
reads score as WRONG on CAL and the 47 tau rule pushes tau_exec_ens to 0.978 /
singles 0.981-0.989 (ensemble EXECUTED 0 on every panel). Full-CAL open
diagnosis (seed 11911, 119 scorer decode by import) confirms the mechanism:
346/5,000 CAL golds use old names (city 301, job 24, birthplace 21, country 0);
43/50 highest-confidence wrong rows are exactly "pred = REMAP[gold], same
spans" (all 43 EXECUTE; other 7 are UNSURE-gold ECHOs, never EXECUTE); the
single tau-fixing row is a city→located-in mismatch at conf 0.9625, and the
pipeline reproduces the sealed 119b taus bit-for-bit (tau0 0.962485432624817,
tau_exec_single 0.9812427163124084). Under remapped golds the same rule gives
worst 0.7384 → tau_exec_single 0.8692.

The ONE CHANGE: the scorer applies remap.json's REMAP to the 47 panels' GOLD
labels at scoring time (all 10 panels incl. CAL; acts/spans/dirs untouched),
re-fits taus with the unchanged 47 rule, and re-scores every 119b mark on the
existing 3 checkpoints. reading94 golds already use the inventory names
(311/312; the single `country` triple, El Al → Israel, is left as-is), so
`--score-panel` is the 119b scorer verbatim. NO training, NO weight change,
NO panel edits. Checkpoints are frozen at
`C:\Users\benja\ears119b\runs\w-1191x\ear.pt` (11911/11912/11913).

## 1. Fixed recipe (all sealed)

- Checkpoints: frozen 119b `ear.pt` for seeds **11911, 11912, 11913** (reused
  in place; never copied to the repo, never modified).
- Encoder snapshot: `24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1` (same as 47/119).
- Scorer: `scripts/fable_ears119e_score.py` (`--score47e`: 119/119b scoring
  body verbatim except `remap_gold_frame()` on golds; `--score-panel`:
  delegates to the 119b scorer). REMAP dict asserted == remap.json `mapping`
  at runtime; CAL remapped-gold count asserted == **346** (else scoring FAILs).
- Temperatures: not re-fitted (checkpoints frozen; temps sealed in 119b run).
- Thresholds: 47 rule on CAL with remapped golds (ensemble tau0/tau_exec +
  per-seed singles): tau0 = smallest tau0 with 0 wrong EXECUTED writes on CAL
  (`scripts/fable_ears47_score.py:458-477`), tau_exec = 1-(1-tau0)/2
  (`scripts/fable_ears119_score.py:99,103`).
- BensPC work dir `C:\Users\benja\ears119e\` (`wave119e.bat`; scoring only).

## 2. The marks (per seed, never averaged; verdict = ALL gated marks pass)

Copied verbatim from `artifacts/fable-ears119b-20260922/PASSMARKS.md` §2
(same bars; positional W3 bars 11911 ≥ 27, 11912 ≥ 33, 11913 ≥ 30 unchanged):

- **SAFE:** silent wrong writes over t-seen+t-new+t-trap+t-hard = **0**.
- **NEG:** wneg STATE-only EXECUTE writes / 2,092 <= **2 %**.
- **SEEN:** t-seen correct >= **1,940/2,000** AND executable STATE rows
  correctly EXECUTED >= **589/654**.
- **NEW:** t-new correct >= **2,400/3,000** AND STATE correctly EXECUTED >=
  **784**.
- **NAMES:** t-hard correct >= **300/500**.
- **ASK:** wrong EXECUTED questions on t-seen+t-new <= **25**.
- **WEB:** wclosed (n=46) executed >= **28** AND exact >= **85 %** of executed.
- **NEWREL:** wnewrel EXECUTE with a concrete seen relation / 1,500 <= **1 %**.
- **ECHO** (recorded only): echoed wrong writes over the 6,500 <= 65.
- **W1:** wclosed ensemble executed >= **23/46** AND silent wrong writes = **0**.
- **W2:** reading94 panel (held-out; 400 sentences / 312 triples / 245
  NO_FACT), per seed at its own (re-fitted) tau_exec_single: correct writes
  >= **30** AND wrong writes <= **5 %** of writes (writes > 0 required), in
  **>= 2/3 seeds**.
- **W3:** reading94 raw exact STATE frames (ungated single decode, strict 106
  match) 11911 >= **27**, 11912 >= **33**, 11913 >= **30**, in **>= 2/3 seeds**.
- **T-CLOCK** (recorded only, not gated): scoring wave wall-clock.

Exp verdict = PASS iff SAFE ∧ NEG ∧ SEEN ∧ NEW ∧ NAMES ∧ ASK ∧ WEB ∧ NEWREL ∧
W1 ∧ W2 ∧ W3. A registered FAIL is recorded as FAIL, never re-run into a pass.

## 3. Forecast note (not a gate; why W3 is expected to stand still)

119e changes no weights and W3 is an UNGATED raw-exact count, so W3 stays at
the 119b values (23/19/18 vs bars 27/33/30 → expected FAIL). 119e re-opens the
execute gate (taus); it cannot change raw reading accuracy. See P119e.1–P119e.5.

## 4. Pre-registered deviations

1. No Qwen practice sentences (same as 47 §2.13, 119 D1).
2. reading94 is scoring-only; the single `country` triple is never re-fitted,
   re-tuned, or renamed (scoring only). Never load test.pt.
3. Mac prep ran the open diagnosis (full-CAL decode, seed 11911, discarded
   subset run first); the scorer itself was compile-checked only
   (`py_compile`) — no registered scoring ran on the Mac.
4. `panel.jsonl` is referenced on BensPC for scoring ONLY (same as 119 D5).
5. Exp-118 brake absent at seal (same as 119 D6); no 118 gate applies.

## 5. Predictions

P119e.1–P119e.5 in `artifacts/fable-predictions-ledger.md`, appended before
the run (see that file).
