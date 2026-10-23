# Fix #10: HALT target "correct AND all gold evidence fetched" (written 2026-10-23, before any run)

Branch claude/ten-weak-halt = claude/v1-assembly + ten-weaknesses fixes (PR #99). Village model only (D, no creative, no bridge). The small card
experiments are not touched. The sealed `test` split is never built, opened or scored.

## Problem (shown in code, effect size untested)
`premonition/model.py` trains HALT with BCE against `correct` = every answer token argmax-correct at this loop. At inference the model stops once
sigmoid(halt) > 0.5 and a stop cancels that loop's fetch. So HALT learns "a guess is right now", not "more fetching is not needed". `have_all`
(every gold card fetched) is computed and used only to scale the answer loss.

## The one change
`MiniConfig.halt_target` in {"correct" (default, v1 bit-identical), "correct_and_evidence"}. With the second value the HALT target is
`correct * have_all`. Questions with no told evidence have an empty gold set, so have_all is True and their target is just `correct`.
Needs the card store (refused otherwise). Inference code unchanged. The default value is left out of `mini_config_dict`, so v1 config dicts,
digests and checkpoints are unchanged.

## Experiment
- Runner: `generalize/dtrain_only.py` (copied from claude/project-thread-tpxowg), D with decoder_raw_cards, v1 FULL recipe for D (Muon, 55k tokens/batch,
  LR 1e-3, warmup 100, curriculum), no extra data, no weight-decay change.
- Arms, run one after the other on ONE box, same data build: `base` (halt_target=correct) and `halt_evidence` (correct_and_evidence).
- Seed 0 only. 6,000 steps each. Dev = 20 dev shards (full), validation = full validation split. Same data, same seed, same batch stream in both arms.
- Reported per arm: dev and validation accuracy, loops_mean, halt_rate, by_depth (accuracy and loops per depth), gold_recall_at_4.
- Cost cap $3 for the whole box (RTX 4090 class, about $0.3-0.5/h). Expected about 1.7-2.2 GPU hours, about $0.6-1.0.

## Pass marks (fixed now)
- PASS (mechanism works, safe): validation loops_mean(halt_evidence) - loops_mean(base) >= 0.2 AND validation accuracy(halt_evidence) >= base - 1.0 point.
- SUCCESS claim (the fix helps): in addition validation accuracy(halt_evidence) >= base + 2.0 points.
- Proved wrong: loops_mean does not rise by 0.2 (the target does not change behaviour), OR loops rise but validation accuracy is more than 1.0 point
  below base (more looping hurts), OR loops rise and accuracy does not move (depth >= 2 by_depth accuracy flat within 1 point): then early stopping
  is not the bottleneck and the idea is dropped.
- One seed cannot separate 1-2 points from noise on small slices: report Wilson intervals on the totals; any "success" stays labelled "suggested"
  until a second seed repeats it. An arm that stops early (spend guard, deadline, NaN) is reported as incomplete and not judged against the marks.

## Not part of this test
No change to inference, to ASK, to loop counts, to the loss weights, or to the data. No full-recipe (creative/bridge) run.
