# DRYRUN: swarm screen box kit, CPU dry run of 2026-10-18

> **Status note (Opus layer, 2026-10-18):** this dry run proves the kit at commit f27adf94e plus the kit files. Afterwards
> the manifest list was widened to 18 files (identity, preprocess, flops, learnlab step1/metrics/policy), and the Q26
> code-review fixes are still pending. The house sealing rule needs the dry run **re-run at the sealed commit** before C0 books.

**THIS IS A DRY RUN. The tiny preset (d = 32, 304k parameters), 60 train / 24 validation visits, CPU, T = 30 s. Every accuracy,
ratio, step count and verdict below is meaningless. The accuracies are 0.0 everywhere because 30 seconds of tiny-model training
learns nothing. NOTHING here is a peek at the screen and nothing was tuned on it.** What this run proves is only that every
mark of the S0 card and of the S1 card can be computed from the files the box script writes, end to end, and that the box
script's guards work.

## What ran

Commit `f27adf94ec89079882315fcad6e76b553ae2f24d` (branch `claude/swarm-thinkers`) plus the uncommitted kit files, so the
manifest was regenerated first (box.log says so). Host: 4-core x86_64 CPU VM, Python 3.13.16, torch 2.14.1+cpu, no GPU.

```
DRYRUN=1 PIN=$(git rev-parse HEAD) WORKERS=3 bash scripts/premonition_swarm_box.sh      # 950 s, exit 0
```

sha256 of the files this run used (all in `scripts/premonition_swarm_manifest.txt`):
`premonition_swarm_screen.py` 1c849485..., `premonition_swarm_marks.py` c40f7544..., `premonition_swarm_box.sh` 862eb75b....

Before this run, the tiny village data and every cache were deleted, so the `data` step below is a from-scratch build
(village generation, tokenizer load, train-token encoding, oracle indexes). `data/village/stream/` is git-ignored.

## Wall times per step (seconds)

| step | seconds | rc |
|---|---|---|
| data | 145 | 0 |
| c0 | 131 | 0 |
| train-D1-s0 | 56 | 0 |
| train-S0-s0 | 54 | 0 |
| train-D1-s1 | 56 | 0 |
| train-S0-s1 | 54 | 0 |
| train-D1-s2 | 54 | 0 |
| train-S0-s2 | 54 | 0 |
| eval-D1-s0 | 9 | 0 |
| eval-S0-s0 | 10 | 0 |
| eval-D1-s1 | 9 | 0 |
| eval-S0-s1 | 9 | 0 |
| eval-D1-s2 | 9 | 0 |
| eval-S0-s2 | 10 | 0 |
| marks-S0 | 0 | 0 |
| marks-S0-minitems1 | 0 | 0 |
| train-S1-s0 | 57 | 0 |
| train-S1-s1 | 55 | 0 |
| train-S1-s2 | 55 | 0 |
| eval-S1-s0 | 10 | 0 |
| eval-S1-s0-board | 11 | 0 |
| eval-S1-s0-notes | 10 | 0 |
| eval-S1-s0-cards | 11 | 0 |
| eval-S1-s1 | 9 | 0 |
| eval-S1-s1-board | 10 | 0 |
| eval-S1-s1-notes | 9 | 0 |
| eval-S1-s1-cards | 10 | 0 |
| eval-S1-s2 | 9 | 0 |
| eval-S1-s2-board | 9 | 0 |
| eval-S1-s2-notes | 10 | 0 |
| eval-S1-s2-cards | 10 | 0 |
| marks-S1 | 0 | 0 |
| marks-S1-minitems1 | 0 | 0 |

Step seconds sum to 945 s; the box script reports 950 s wall (15.8 min). The whole box script, S1 extension included, is under the 40-minute aim.
The S0 part alone (data to MARKS-S0) took 660 s of that (data 145, C0 131, 6 trains 328, 6 evals 56); the S1 extension (3 trains, 12 evals) took 285 s.

## C0 (tiny, CPU): every field is written

| arm | gold | teacher | own | weighted s/update | x D1 |
|---|---|---|---|---|---|
| D1 | 0.188 | 0.238 | 0.353 | 0.316 | 1.000 |
| S0m2 | 0.198 | 0.252 | 0.284 | 0.271 | 0.859 |
| S0m4 | 0.227 | 0.296 | 0.310 | 0.302 | 0.957 |
| S0m8 | 0.287 | 0.480 | 0.437 | 0.440 | 1.395 |
| S1m4 | 0.240 | 0.319 | 0.380 | 0.358 | 1.134 |

* T formula: `D1 FLOP/s` = 2.198e+10, `T_raw` = 1182787 s, formula T = 3600 s (the 3,600 s cap), **overridden to T = 30** (`--t-override`).
* `ratio_s0m4_over_d1` = 0.957; `stop_and_ask` = False; `money_stop` = False
  (projected S0 0.064 box-hours at $0.4/h = $0.025).
* Eval-time estimate: 3.24 s (second pass; the first pass, which builds the validation cache, took 6.70 s).
* **Not exercised on CPU, so not proven by this run:** `peak_allocated_bytes` (null off CUDA), `gpu_busy` (null off CUDA), the
  `torch.cuda.synchronize()` calls, the CUDA out-of-memory handling of a C0 arm, and the profiler sum
  (`gpu_busy_fraction`). The profiler attribute names (`device_type`, `self_device_time_total`) were checked against a CPU-only
  profile on torch 2.14, nothing more.

## Trains (30 s each)

| arm | seed | train_seconds | steps | loop_mismatches | status |
|---|---|---|---|---|---|
| D1 | 0 | 30.20 | 103 | 0 | completed |
| S0 | 0 | 30.19 | 92 | 0 | completed |
| S1 | 0 | 30.10 | 84 | 0 | completed |
| D1 | 1 | 30.13 | 107 | 0 | completed |
| S0 | 1 | 30.32 | 98 | 0 | completed |
| S1 | 1 | 30.33 | 87 | 0 | completed |
| D1 | 2 | 30.29 | 109 | 0 | completed |
| S0 | 2 | 30.25 | 91 | 0 | completed |
| S1 | 2 | 30.42 | 83 | 0 | completed |

Every `train_seconds` is within T +- 2% (0.6 s of 30). That needed `--max-tokens 3000` (the box script's `DRY_MAXTOK`):
with the real 55,000 tokens a tiny CPU step takes 1.5-3 s and the run overshoots T by more than 2%. The real run
(T of 300-3,600 s, GPU steps) cannot overshoot by that much.

## Which marks were computed

Every mark of both cards: S0 {M1, M2, M3, M4, M5, M6, KILL}; S1 {M1, M2, M3, M4, M5, M6, M6b (cells), KILL-COMM}, with the
information rows (steps in T, all decision cells, per-depth cells, the `changed` cell, the three lesion drops, S1 vs D1).
Cell membership: every eval file's `decision_cells`, `per_depth` and `changed` cell were rebuilt from the items and matched
the file's own values, with no mismatch (a mismatch would make the verdict VOID (schema)).

## Verdict lines (all four readout passes)

```
MARKS-S0.md:VERDICT: INSUFFICIENT: far_deep below 100 items in 6 of 6 eval files (smallest 62, largest 62)
MARKS-S0-minitems1.md:VERDICT: KILL: S0 does not beat D1 on far_deep (pooled +0.00 pts, negative on 0/3 seeds); the swarm line stops
MARKS-S1.md:VERDICT: INSUFFICIENT: far_deep below 100 items in 18 of 18 eval files (smallest 62, largest 62)
MARKS-S1-minitems1.md:VERDICT: KILL-COMM: S1 does not beat S0 on far_deep (pooled +0.00 pts, negative on 0/3 seeds)
```

* First pass (`--min-items` 100): INSUFFICIENT, honestly, because the tiny validation split has 62 `far_deep` items in every
  file. Every other mark is still computed and printed in the table.
* Second pass (`--min-items 1`): the full verdict path runs. It lands on KILL / KILL-COMM only because every accuracy is 0.0
  (pooled difference 0). The other verdict branches (VOID, PROMOTE, FAIL, HOLD, COLLAPSED, BOARD-UNUSED, ...) are exercised
  by `tests/test_premonition_swarm_screen.py`, not by this run, because this run cannot produce a signal.
* The dry-run S0/S1 desks are silent (`ask_rate` 0) after 30 s of training, so M3/M4 read FAIL / "silent 3-4 desks". Meaningless.

## Guard checks run outside the dry-run folder (scratch outputs, not kept)

| check | result |
|---|---|
| `PIN` not equal to `git rev-parse HEAD` | REFUSED, exit 2 |
| a pinned file's sha256 differs from the manifest | REFUSED, exit 2 |
| `MAXH 8 x DPH 1.0` above `CAP 4.20` | REFUSED, exit 2 |
| non-dry run on a host with no CUDA | REFUSED, exit 2 (before the data build) |
| `DRYRUN=1 PART=c0 DPH=100` (projected S0 cost $6.42 > $3.50) | `money_stop` True, `STOP-AND-ASK.txt` written, exit 3, no training |

## Files in this folder

Folder size 2,005,377 bytes (75 files before this one), under the 5 MB limit; checkpoints are removed.
`swarm-screen-out.tgz` is the copy-back bundle the box script packs (JSON, logs, MARKS, host, box.log; no checkpoints).

| file | bytes |
|---|---|
| MARKS-S0-minitems1.json | 17,227 |
| MARKS-S0-minitems1.md | 2,787 |
| MARKS-S0.json | 17,272 |
| MARKS-S0.md | 2,843 |
| MARKS-S1-minitems1.json | 36,152 |
| MARKS-S1-minitems1.md | 3,588 |
| MARKS-S1.json | 36,213 |
| MARKS-S1.md | 3,665 |
| box.log | 14,898 |
| c0.json | 4,616 |
| c0.log | 3,842 |
| data.json | 582 |
| data.log | 2,612 |
| eval-D1-s0.json | 83,881 |
| eval-D1-s0.log | 407 |
| eval-D1-s1.json | 83,884 |
| eval-D1-s1.log | 407 |
| eval-D1-s2.json | 84,524 |
| eval-D1-s2.log | 407 |
| eval-S0-s0.json | 83,828 |
| eval-S0-s0.log | 407 |
| eval-S0-s1.json | 86,280 |
| eval-S0-s1.log | 407 |
| eval-S0-s2.json | 83,772 |
| eval-S0-s2.log | 407 |
| eval-S1-s0-board.json | 110,846 |
| eval-S1-s0-board.log | 414 |
| eval-S1-s0-cards.json | 110,846 |
| eval-S1-s0-cards.log | 414 |
| eval-S1-s0-notes.json | 110,848 |
| eval-S1-s0-notes.log | 414 |
| eval-S1-s0.json | 110,827 |
| eval-S1-s0.log | 408 |
| eval-S1-s1-board.json | 83,797 |
| eval-S1-s1-board.log | 413 |
| eval-S1-s1-cards.json | 83,797 |
| eval-S1-s1-cards.log | 413 |
| eval-S1-s1-notes.json | 83,795 |
| eval-S1-s1-notes.log | 413 |
| eval-S1-s1.json | 83,778 |
| eval-S1-s1.log | 407 |
| eval-S1-s2-board.json | 83,806 |
| eval-S1-s2-board.log | 413 |
| eval-S1-s2-cards.json | 83,807 |
| eval-S1-s2-cards.log | 413 |
| eval-S1-s2-notes.json | 83,808 |
| eval-S1-s2-notes.log | 413 |
| eval-S1-s2.json | 83,789 |
| eval-S1-s2.log | 407 |
| host.txt | 2,019 |
| manifest-check.log | 341 |
| marks-S0-minitems1.log | 2,974 |
| marks-S0.log | 3,010 |
| marks-S1-minitems1.log | 3,775 |
| marks-S1.log | 3,832 |
| steps.tsv | 579 |
| swarm-screen-out.tgz | 152,065 |
| train-D1-s0.json | 7,532 |
| train-D1-s0.log | 761 |
| train-D1-s1.json | 7,532 |
| train-D1-s1.log | 762 |
| train-D1-s2.json | 7,557 |
| train-D1-s2.log | 763 |
| train-S0-s0.json | 5,781 |
| train-S0-s0.log | 601 |
| train-S0-s1.json | 5,767 |
| train-S0-s1.log | 603 |
| train-S0-s2.json | 5,774 |
| train-S0-s2.log | 602 |
| train-S1-s0.json | 5,785 |
| train-S1-s0.log | 602 |
| train-S1-s1.json | 5,780 |
| train-S1-s1.log | 602 |
| train-S1-s2.json | 5,782 |
| train-S1-s2.log | 602 |
