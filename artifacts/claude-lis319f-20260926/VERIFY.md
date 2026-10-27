# lis-319f verify: PASS

Written 2026-09-26 15:17 UTC by the reading thread (problem #1, saves). Counts only; no panel text.
Inputs: RESULTS-rent.md, reads_panel_old/new.jsonl, former_old/new.json (origin/builder-outbox). Two blind Opus judges,
JUDGE_SAME.md, neutral file names, coin-flip order (judged/ORDER.txt). Pairs: OLD 66, NEW 64, built at 0.995 and 0.98.
Judges disagreed on 0 pairs. Verdicts (pid + same only) and scorer outputs are in judged/.
former_old.json re-computed here from the pushed OLD reads: 6, same as the rental.

## Marks (readpanel371c, 240 rows, 355 true facts, 49 former rows; T 0.995)
| Mark | OLD lis-319 | NEW lis-319f | Bar | Result |
|---|---|---|---|---|
| M1 former-as-current saves | 6 | 0 | NEW <= 1 | pass |
| M2 whole-claim right saves | 118 | 117 | NEW >= OLD - 3 | pass |
| M3 turns with a wrong save | 6 | 2 | NEW <= OLD | pass |
Valid (49 >= 30 former rows, OLD 6 >= 2). Not proved wrong (0 < 3).
Report only: wrong saves 7 -> 2; saves on no-fact rows 5 -> 0. At 0.98: right 156 -> 154, wrong 14 -> 4, turns with a
wrong save 12 -> 4, no-fact rows with a save 10 -> 0. Dev (rental, report only): former-as-current 27 -> 3.

## What goes forward
lis-319f replaces lis-319 as the reader. model.safetensors sha256
970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b, Mac ~/premonition-models/lis319f-merged/.
Rental cost about $0.95 of the $2 line.

## lis-319f2 (fallback hold rule, report only because lis-319f passed)
Same OLD reads with the rule: former-as-current 1, right 118, wrong 2, turns with a wrong save 2 (judged/full_old_f2.json,
judged/former_old_f2.json). The retrain and the code rule remove the same errors on this panel.
