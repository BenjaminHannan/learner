# 119e — Ears execute-gate diagnosis + score-time re-gate PREP (Muse)

Status: open diagnosis complete on Mac CPU (full 5,000-row CAL decode, seed
11911); cause confirmed; 119e sealed (`7cf3fd80…fc00`) and staged for the
director to score on BensPC. No registered scoring ran here; no weights
changed; no BensPC contact. Predictions P119e.1–P119e.5 in the ledger.

## 1. Goal (one sentence)

Find out why the 119b execute gate is shut (ensemble EXECUTED 0 on every 47
panel), and — only with the cause confirmed — prepare a score-time fix that
re-opens it without retraining.

## 2. Premise (verified, not assumed)

119b is a registered FAIL. The training-label remap roughly doubled raw
real-text reading (W3 23/19/18 vs 119's 11/11/8) yet thresholds fitted on the
exp-47 CAL panel rose to tau_exec_ens 0.978 / singles 0.981–0.989 and the
ensemble executed nothing, including CAL itself. The director's hypothesis
(ledger P119b.4's stated risk): CAL golds still use the OLD names while the
remapped model predicts the NEW names, so confident correct reads score as
wrong and the tau rule pushes the threshold above everything.

## 3. Diagnosis method

Decoded all 5,000 CAL rows with the frozen seed-11911 checkpoint using the 119
scorer's decode BY IMPORT (`load_model`/`decode_all`), scored with the 47
`is_correct`/verdict definitions at tau 0, and re-ran the 47 tau rule
(`tau0_from_cal`, smallest tau0 with 0 wrong EXECUTED writes on CAL;
`tau_exec = 1-(1-tau0)/2`) under old vs remapped golds. New file:
`scripts/fable_ears119e_diagnose.py` (checkpoint read-only; reading94 never
touched; test.pt never loaded).

## 4. Findings (counts, never averaged)

- 346/5,000 CAL golds use old names (city 301, job 24, birthplace 21,
  country 0); new names appear 0 times.
- 43/50 highest-confidence wrong rows are exactly "pred = REMAP[gold], same
  act/spans/dir" (≥80 % gate → PASS). All 43 carry EXECUTE verdicts. The
  other 7 are UNSURE-gold ECHOs (STATE/OPEN), which never EXECUTE and cannot
  fix tau under the rule.
- Over all 913 wrong rows: 342 mismatches, every one EXECUTE (city 299, job
  24, birthplace 19); zero UNSURE-free non-mismatch rows except 4
  ASK-gold/state-pred act errors whose predicted relation is still the
  remapped one. I.e. every confident wrong read with an old-name gold is a
  namespace mismatch.
- The single tau-fixing row under old golds is a city→located-in mismatch
  ("fenumover's town is torenkoford", conf 0.9625); the pipeline reproduces
  the sealed 119b single-seed taus bit-for-bit (tau0 0.962485432624817,
  tau_exec_single 0.9812427163124084). Under remapped golds the worst row is
  an UNSURE-gold favorite_color EXECUTE at 0.7384 → tau_exec_single 0.8692.
- reading94 golds already use inventory names (311/312; one `country`
  triple, El Al → Israel, airline→country, left as-is).

## 5. The 119e change (scoring only)

`scripts/fable_ears119e_score.py --score47e`: the 119/119b scoring body
verbatim except `remap_gold_frame()` applied to the 47 panels' golds (all 10
panels incl. CAL; REMAP asserted == remap.json `mapping`; CAL remapped count
asserted == 346), taus re-fitted with the unchanged 47 rule, every 119b mark
re-scored on the frozen 11911–11913 checkpoints. `--score-panel` delegates
to the 119b scorer (reading94 untouched). `wave119e.bat` + `scp119e.txt` let
the director run it on BensPC; PASSMARKS carries the same marks and bars
(W3 bars 27/33/30 unchanged).

## 6. Forecasts (ledger P119e.1–P119e.5)

Gate re-opens (tau_exec_ens < 0.95, 0.70; CAL executed > 0, 0.80); W2 admits
writes in ≥2/3 seeds (0.65, bar passage not predicted); W3 stands still in
all seeds (0.80 — 119e moves no weights and W3 is ungated); no post-seal
edits (0.95).

## 7. Person-city note (question asked; not built)

Yes — synthetic `city` is a person's town ("Eero's town is Raishholm"). If
the notebook must ever write `city` back from a frame whose relation is
"located in the administrative territorial entity", it needs a subject-type
check: PERSON subject → `city`, place/org subject → located-in. That
requires a person-vs-place subject signal in the notebook (entity-type table
or classifier on the subject span). Nothing in 119e builds it; the direction
to map is score-side only (panel golds → inventory names), never notebook
writes.

## 8. What this does and does not claim

Does: pin the shut gate on the scoring-namespace mismatch with a
bit-for-bit tau replication, and stage a one-change re-gate. Does not: claim
any 119e score (all marks are forecasts), change raw reading accuracy, or
fix UNSURE-gold abstain granularity (534/913 wrong rows — the dominant
residual class, gate-irrelevant but correctness-relevant).

Deviations (prep, pre-scoring): 1,000-row pilot superseded by the full-CAL
run (same script, `--n 5000`, 323 s wall); scorer compile-checked only, never
executed. Post-seal writes reported in RESULTS §5. Questions for Ben: none.
