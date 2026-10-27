# 75 — Independent audit of Exp 29 (new names) and Exp 46 (harden-before-gate)

Read-only audit. New files only: `scripts/fable_audit75_*.py`,
`artifacts/fable-audit75-20260921/`, this doc. No existing file modified.

## Verdicts

- **Exp 29: CONFIRMED-WITH-CAVEATS.** Every headline number re-derives from
  `gates.json` / `report.txt` / `readouts/*.json` with 0 mismatches; seals
  verify; registration preceded training; wave-1 verdict preceded wave-2.
- **Exp 46: CONFIRMED-WITH-CAVEATS.** All 120 rows re-derive from the 10 run
  JSONs with 0 mismatches; seals verify; pass marks preceded runs; a full
  independent re-run of seed 4102 reproduces all 12 rows field-for-field and
  the checked weights bit-for-bit (max abs diff 0.0).

## Exp 29 trace (claim → JSON path)

- PASS 3/3 arm F: `gates.json:verdict` = "PASS", `F_seeds_passed` = 3,
  `F.<seed>.passed` true ×3, `failed_cells` [] ×3.
- Table (30 F cells): all match RESULTS.md, 0 mismatches
  (`gates.json:F.<seed>.cells.<cell>.R`). Worst paired delta (−11, 2106,
  p12-3): `gates.json:F.2106.cells.p12-3.paired_delta`. Control 512/512
  everywhere re-checked (0 non-512 cells).
- L 1/3: only `L.2106.passed`; 2107/2108 fail `p12-3` paired (−14/−21).
  F6 1/3: 2106 passes; 2107/2108 fail `s3` paired (−18/−15).
- F vs F6 "same run stopped early": `integrity.fingerprint_at_4000` equal
  per seed. Miss totals (F 67/68/65; F6 185/137/134; L 118/87/144)
  re-arithmetic'd from R values — match. First-step rates (F
  2.54/2.44/1.66%) match `report.txt` LINK accuracies
  (e.g. 2106: (13+13)/1024). Final scales (F 1.2; L 0.67/1.06/0.69) match
  `report.txt` trace lines. Open-set (~0.59/0.57/0.60 F; 0.54/0.58/0.56 F6;
  0.66/0.59/0.67 L) match `readouts/<arm>-<seed>.json:openset_B.pooled_accuracy`.
- Seal/timing: `RESULTS-SEAL` 3/3 OK (from artifact dir — bare filenames).
  `FREEZE-NOTE.md` sha matches its `.sha256` file, written Sep 20 23:26:49,
  before first training log 23:46; `FABLE-PREDICTIONS.md` (22:42) sha matches
  the freeze note. Wave-1 verdict sealed 23:48–23:49, before wave-2 trains
  (23:59+) and scores (00:09+). Ledger holds R29-P1..P20 + P126..P133 with
  outcomes (order by content: predictions cite pre-run shas, outcomes cite
  results). `integrity.problems` = [].
- Scoring leaks: none found. Reserved 1,024 codes never trained on (separate
  `train-codes` vs `panel-codes` namespaces, fresh panel seed base
  202609212900); pass computed on held-out reserved panels with a paired
  training-pool reference; every seed reported, never averaged; no silent
  retries (update counts, fingerprints, per-row LR enforced by the integrity
  gate; the one coordinator fix — float tolerance on 1.2 — is disclosed in
  BUILD-NOTES.md with a byte-identical panel re-run). The wrapper only
  observes (`_score_cell29` returns the scorer's value untouched).

## Exp 46 trace (claim → JSON path)

- 15/15 installs at 0/2/4 wrong per batch, 0/15 at 20 wrong: re-derived from
  all 10 `runs/hard-seed*.json` — batch1 and batch2 each 15/15, 15/15, 15/15,
  0/15. 120 rows total. 0 wrong installs / 120 under the registered
  definition (`PASSMARKS.md` H1). All 90 installed rows have
  `audit_disagree_of_60` = 0 AND `fresh_accuracy` = 1.0.
- Seal/timing: `SEAL.sha256` 4/4 OK (PASSMARKS + 3 scripts);
  PASSMARKS/SEAL mtime 20:18:25, before first run JSON 20:19:32 and RESULTS
  20:21:10. `RESULTS-SEAL` 11/11 OK. Ledger P201–P204 + outcomes present.
- Scoring leaks: none found. Episodes come from the train60 village only;
  `fresh_qs` from the held-out fresh60 village; CV folds split by start
  person so each fold prediction is genuinely out-of-fold; checkpoint choice
  (OOF match ≥ 0.80, then OOF NLL) is held-out model selection, pre-registered;
  install also needs refit agreement ≥ 0.90, unchanged base probe, identical
  reload — all computed, all in-JSON. Integer counts per batch, no averaging.
  Batch 2 (fresh seeds 4107–4111) was a pre-registered confirmation, not a
  re-run-into-pass. The 60-start audit is declared evaluation-only.
- Re-run: seed 4102 into our folder (~2 min Mac CPU) — 12/12 rows identical
  in installed/fresh/audit/cv_table/routed_chain/chosen_updates (only
  path/seconds differ, as expected); one word .pt bit-identical.
  Paudit75.1 TRUE, Paudit75.2 TRUE.

## Caveats

Exp 29: (1) seeds share training worlds (disclosed Q1 limitation) — 3/3 is
less independent than it looks. (2) Descriptive overlay printed nulls; totals
above are my arithmetic from R/LINK values, not the pipeline. (3)
`undertraining_unclear` turns on 0.04pp (2.54% vs 2.5% rule) — rule applied
correctly. (4) No full code audit of `fable_newnames27.py`; verdict
arithmetic, seals, and timing only. (5) Report header/filenames still say
"27" (disclosed, contents are 29's). (6) Open-set ~0.6 is first-stage LINK
under gold-path inputs, marked DESCRIPTIVE ONLY — weaker than full naming.
(7) No audit retraining (10k-update cost); Exp 29 relies on saved artifacts.
Exp 46: (1) ε=0.10 matched the true noise by construction (disclosed). (2)
Only nonsense tested is 20/20 wrong. (3) Pass rests on behavioral equivalence,
not chain identity: seed-4102 maternal_grandmother@wrong4 routes
[mother,keep,mother] ≠ true [mother,mother] yet audits 0/60 at fresh 1.00.
(4) Toy village, no language; soft-router scaling warning stands (disclosed).
(5) Only 1 of 10 seeds re-run; all 10 JSONs verified against RESULTS.

## What it does not show

Neither experiment shows open-vocabulary naming, language understanding, or
scaling past toy worlds (16-candidate / 60-person villages). Exp 46 does not
show robustness to mismatched noise levels. Nothing here changes the live
recipe; it confirms the evidence behind it.
