# Stage 1 report (SC-1; booked by the coordinator after Stage 0)

**Status: STARTING.** The boxes build the data and run the memory pre-flight; nothing trains before the go file.

## Run record
- Script: `scripts/span_stage1.py` at commit 707bdce90 (sha256 47577a35...d127), reviewed by the coordinator (the
  draft) and by the built-in review (9 rounds, `04-review-log.md`). Each box fetches that exact commit and refuses
  to run on any other script hash.
- Boxes: one RTX 3090 on-demand box per seed s = 0, 1, 2 (the Stage 0 box class). Each runs `span_stage1.py box
  --seed s`: the standard step-1 `large` build, the label-free caches, the pre-flight, the go gate, P_s, the
  branch-point check, LINE and SPAN to F = 3.15e16, then the DEV readout. Checkpoints stay on the box's disk.
- Go file: `design/span-cards/stage1-go.json` on this branch (polled by the boxes); attempt 1 starts `pending`.

## Rules fixed before any measurement
- **Memory pre-flight (coordinator's condition):** for each rung of (max_tokens, max_visits) = (55,000, 48)
  [sealed], (48,000, 42), (40,000, 35), (32,000, 28), a clean child process per arm (LINE, SPAN, and SPAN with
  about 33% more cards than lines). Each runs the run's fp32 FLOP calibration (an OOM there = does not fit), then
  tracked gold, teacher and own steps on the heaviest batches of the Stage 1 stream (by padded tokens,
  questions and lines, plus adversarial packings), the validation hook and the card economy. A rung fits iff
  every arm's peak reserved GPU memory is <= the 15.03 GB guard minus 1.0 GB = 14.03 GB.
- **Go (coordinator's ruling):** if rung 0 fits every arm on every box, I file the go for rung 0 without waiting.
  If only a lower rung fits, I file the peaks and wait; no reduced rung trains until the coordinator names it.
  The same rung applies to both arms and every seed; any change is recorded here.
- **Seal addendum:** the train and validation cache hashes (identical on every box), N and the script and code
  digests go into `05-seal.md` before the go file.
- **Money:** total Stage 1 spend across all boxes and attempts, go-wait included, stays inside the $18 hard
  stop. A watchdog in this session destroys every Stage 1 box when the account's spend since the Stage 1
  baseline (credit $32.588) would pass $16 at the current burn rate, or at each box's own deadline.

## Pre-flight
(filed when the boxes report)

## Readout per seed
(filed when each seed finishes)
