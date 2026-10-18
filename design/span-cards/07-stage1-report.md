# Stage 1 report (SC-1; booked by the coordinator after Stage 0)

**Status: GO FILED (rung 2).** The coordinator named rung 2, (40,000, 35), for both arms and all seeds; the go
file is filed. Training starts when the boxes accept it (confirmed below).

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
Filed 2026-10-18 about 19:25Z, as the boxes reported. Boxes: vast 56601518 (seed 0), 56601519 (seed 1), 56601524 (seed 2),
labels `claude-spancards-s1-seed{0,1,2}`, RTX 3090, torch 2.11.0+cu128, script sha256 47577a35...d127 on every box,
code_sha256 5c2b9237...ca95 on every box.

**Data (identical on every box):** train cache a53ab45b...6cd9, validation cache 762082f1...3549, N = 11.155539,
100,000 / 1,000 visits, 855,962 / 8,675 questions, 112,736,485 train tokens, newline id [23].

Limit = 15.03 GB guard - 1.0 GB = **14.03 GB** on peak *reserved* memory. 36 tracked steps per child; no child hit an
OOM; LINE and SPAN children had line_aligned = 1 (stress child 0.53 by design). The pre-flight stops a rung at its first
failing arm, so the failed rungs on seed 2 have only the LINE child.

| seed | rung (tokens, visits) | arm | peak reserved GB | peak allocated GB | fp32 calibration reserved GB | fits |
|---|---|---|---|---|---|---|
| 0 | 55,000, 48 | LINE | 8.54 | 8.33 | 14.54 | yes |
| 0 | 55,000, 48 | SPAN | 10.16 | 9.71 | 15.64 | yes |
| 0 | 55,000, 48 | SPAN-stress | 10.08 | 9.75 | 15.71 | yes |
| 1 | 55,000, 48 | LINE | 11.62 | 8.33 | 10.10 | yes |
| 1 | 55,000, 48 | SPAN | 11.70 | 9.71 | 11.36 | yes |
| 1 | 55,000, 48 | SPAN-stress | 11.70 | 9.74 | 11.41 | yes |
| 2 | 55,000, 48 | LINE | **16.14** | 8.33 | 12.89 | **no** (over the guard itself) |
| 2 | 48,000, 42 | LINE | **14.13** | 6.93 | 18.50 | **no** (over the margin, under the guard) |
| 2 | 40,000, 35 | LINE | 7.39 | 5.97 | 7.83 | yes |
| 2 | 40,000, 35 | SPAN | 7.34 | 7.02 | 8.75 | yes |
| 2 | 40,000, 35 | SPAN-stress | 8.46 | 7.04 | 8.78 | yes |

Fitted rungs: seed 0 rung 0, seed 1 rung 0, seed 2 **rung 2 (40,000, 35)**. **Rung 0 does not fit every arm on every
box. Under the ruling, no go is filed.**

**What the numbers show (shown):** peak *allocated* memory is the same on every box to 0.01 GB (rung 0: LINE 8.33,
SPAN 9.71, stress 9.75). Peak *reserved* memory, the number the guard checks, is not: at rung 0 the same LINE arm
reserved 8.54, 11.62 and 16.14 GB on the three boxes. The first nine pre-flight batches depend on the seed's epoch
order; the last three (adversarial packings) are the same on every box. The gap is the CUDA caching allocator's
fragmentation (reserved / allocated from 1.02 to 2.04 across the children), not the model or the arm. SPAN costs
about +1.4 GB allocated at rung 0 and +1.05 GB at rung 2; the stress card count adds almost nothing.

**What this means for a nine-hour arm (suggested, not measured):** the guard raises `MemoryGuardError` and stops the
arm the first time peak reserved memory passes 15.03 GB. 36 steps cannot bound how badly the allocator fragments over
the whole run. With the worst ratio seen here (2.04), rung 0 (allocated up to 9.75 GB) could reach about 19.9 GB on
any box, seeds 0 and 1 included. Rung 2 (allocated up to 7.04 GB) would reach about 14.4 GB: over the margin but
still under the guard.

**Options for the coordinator (the rung is the coordinator's call; each applies to both arms and all seeds):**
- **(a) Rung 2, (40,000, 35), for every seed.** It fits on every box with at least 5.6 GB of margin, and every box's
  fitted rung allows it. The boxes can start as soon as the go file names it: no restart, no script change. Cost:
  about 1.38x as many optimizer steps for the same F, so the batch differs from the sealed card's (55,000, 48); both
  arms see the same change. Wall time per step drops, so the GPU-hours should stay close to the 17.5 GPU-h projection,
  but this is untested.
- **(b) Rung 0 with `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`** on every box. This targets the cause
  (fragmentation) and keeps the sealed batch. It needs a box restart and a fresh pre-flight (the data cache is on
  disk, so about 15 min each), plus a review of the environment change. The script hash does not change, but the
  setting is not bound by the go file unless the script records it.
- **(c) Rung 1, (48,000, 42).** Seed 2 measured 14.13 GB, under the guard but 0.10 GB over the margin. I do not
  recommend it: the margin is the fixed rule.

My recommendation is (a). It is the only option the fixed rules allow today with no new code.

**Money:** Stage 1 spend $0.368 at 19:15Z since the $32.588 baseline. The three boxes cost $0.227 + $0.234 + $0.291 =
$0.75/h together while they wait. Each box waits up to 4 h for the go (until about 23:00-23:15Z). If no go comes by
then, the box exits and the watchdog stops it (stopped, not destroyed; the data stays on disk). The whole wait costs at
most about $3 of the $18.

## Rung ruling (coordinator, 2026-10-18)
**Rung 2: max_tokens 40,000, max_visits 35, for both arms and all seeds.** The pre-flight peaks are accepted as
filed: rung 0 and rung 1 fail the reserved-memory guard on seed 2, and rung 2 fits every box with room to spare. The
rung changes the batch size only: same F, same marks, same pairing. This replaces the sealed card's (55,000, 48)
batch for Stage 1; the change is identical for LINE and SPAN.

The go file (`stage1-go.json`), filed with exactly the coordinator's content:
`{"go": true, "seeds": [0, 1, 2], "script_sha256": "47577a35...d127", "code_sha256": "5c2b9237...ca95",
"train_cache_sha256": "a53ab45b...6cd9", "validation_cache_sha256": "762082f1...3549", "N": 11.155539,
"flop_budget": 3.15e16, "size": "full", "max_tokens": 40000, "max_visits": 35}` (full hashes in the file and in
`05-seal.md` part 2; they match what every box reported).

## Go accepted
(filed when the boxes log the go and start the parent)

## Readout per seed
(filed when each seed finishes)
