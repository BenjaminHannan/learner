# rsn-296 CPU re-evaluation (rsn-296-reeval)

Re-ran the SAME eval commands from the sealed origin/main code on CPU
(`--device cpu`) against the 8 local checkpoints at
`~/premonition-models/rsn296/<run>/{copy_only.pt,final.pt}`, because the
rental-run panel JSONs were lost (DATA-LOSS notes on origin/builder-outbox).
No training, no rental, no GPU, no code edits, no panel items read or quoted.
Only category-level counts are reported below.

## Provenance

- Clean export: `git archive origin/main | tar -x -C /tmp/rsn296re`; everything
  run from `/tmp/rsn296re`.
- `shasum -a 256 -c` on the export: SEAL-code.sha256.txt every line OK,
  SEAL-v2.sha256.txt (reasonpanel296) every line OK, SEAL-v3.sha256.txt
  (reasonpanel294) every line OK.
- All 8 checkpoints match origin/builder-outbox
  `artifacts/claude-rsn296-20260924/SEAL-run.sha256.txt` exactly (8/8 lines):
  plain-s1 copy_only 90b2938a..., plain-s1 final 25106163...,
  loop-s1 copy_only 27802068..., loop-s1 final f4bfa4e0...,
  plain-s2 copy_only 89a65b43..., plain-s2 final ab600d43...,
  loop-s2 copy_only f2d62926..., loop-s2 final 1a530c0c....
- Each of the 16 evals run exactly once, `--device cpu`, at most 4 processes
  at a time. Command form:
  `python -B scripts/claude_rsn296_run.py eval --device cpu --ckpt
  ~/premonition-models/rsn296/R/C.pt --panel <items-v2|items-v3>.jsonl
  --out artifacts/claude-rsn296-20260924/reeval-cpu/R/panel<296|294>-<copy|final>.json`
- Each output JSON holds a `total` block, a `by_category` block
  (category-level counts only), `ckpt`, `arm`, `eval_steps`, and an item count
  (`items`: 298 for panel296 files, 300 for panel294 files). No item text is
  stored or quoted here.

## Totals vs RESULTS.md (origin/builder-outbox)

`checked_answered_without_fact` key is ABSENT from every `total` block (16/16);
only `raw_answered_without_fact` is present (shown where present, else absent).
`checked_right` compared against the RESULTS.md panel-totals tables.

### reasonpanel296 v2 (n = 298 each)

| file | checked_right | raw_right | raw_answered_without_fact | checked_idk | checked_wrong | RESULTS.md | match |
|---|---|---|---|---|---|---|---|
| plain-s1/panel296-copy.json | 167 | 164 | 5 | 114 | 17 | 167 | YES |
| plain-s1/panel296-final.json | 225 | 222 | 5 | 34 | 39 | 225 | YES |
| plain-s2/panel296-copy.json | 181 | 176 | 7 | 102 | 15 | 181 | YES |
| plain-s2/panel296-final.json | 217 | 214 | 6 | 38 | 43 | 217 | YES |
| loop-s1/panel296-copy.json | 57 | 72 | 1 | 228 | 13 | 57 | YES |
| loop-s1/panel296-final.json | 106 | 109 | 4 | 159 | 33 | 106 | YES |
| loop-s2/panel296-copy.json | 47 | 75 | (absent) | 236 | 15 | 47 | YES |
| loop-s2/panel296-final.json | 101 | 105 | (absent) | 162 | 35 | 101 | YES |

### reasonpanel294 v3 (n = 300 each)

| file | checked_right | raw_right | raw_answered_without_fact | checked_idk | checked_wrong | RESULTS.md | match |
|---|---|---|---|---|---|---|---|
| plain-s1/panel294-copy.json | 194 | 195 | (absent) | 95 | 11 | 195 | NO (-1) |
| plain-s1/panel294-final.json | 238 | 238 | (absent) | 15 | 47 | 238 | YES |
| plain-s2/panel294-copy.json | 205 | 205 | (absent) | 84 | 11 | 205 | YES |
| plain-s2/panel294-final.json | 238 | 238 | (absent) | 15 | 47 | 238 | YES |
| loop-s1/panel294-copy.json | 59 | 68 | (absent) | 225 | 16 | 59 | YES |
| loop-s1/panel294-final.json | 89 | 88 | 2 | 172 | 39 | 89 | YES |
| loop-s2/panel294-copy.json | 49 | 72 | 1 | 236 | 15 | 49 | YES |
| loop-s2/panel294-final.json | 87 | 86 | 1 | 173 | 40 | 87 | YES |

## Differences (reported, not explained away)

1. plain-s1/panel294-copy.json: reeval `checked_right` = 194, RESULTS.md = 195
   (difference of 1; reeval `raw_right` = 195, `checked_idk` = 95,
   `checked_wrong` = 11; 194 + 95 + 11 = 300 = n, internally consistent).
2. `checked_answered_without_fact` is missing from all 16 `total` blocks, so it
   cannot be reported as an integer from files; `raw_answered_without_fact` is
   reported instead where present. The "invented answers" marks in RESULTS.md
   match the reeval `raw_answered_without_fact` values on the finals
   (plain-s1 fresh 5, plain-s2 fresh 6, loop-s1 fresh 4, loop-s2 fresh 0;
   transfer plain finals absent = 0, loop-s1 transfer 2, loop-s2 transfer 1).

All other 15 files: `checked_right` equals the RESULTS.md number exactly.
