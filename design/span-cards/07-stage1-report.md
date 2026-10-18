# Stage 1 report (SC-1; booked by the coordinator after Stage 0)

**Status: ATTEMPT 2 STARTING (ruling Q159).** In attempt 1 all three seeds failed the memory guard at rung 2. Seeds 0
and 1 failed in the parent's gold phase; seed 2 failed 94 s into its LINE arm, after the ruling's snapshot. Attempt 2
restarts all three seeds at rung 2, unchanged, with one change: the allocator setting
`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`. Seed 2's restart falls under Q159 (5).

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

## Go accepted, and the first minute (2026-10-18)
Every box logged the go record `{"max_tokens": 40000, "max_visits": 35}` and started P_s.

| seed | go accepted (box clock) | outcome |
|---|---|---|
| 0 | t = 3164.5 s | **failed** at t = 3207.1 s (43 s later): `MemoryGuardError: peak reserved GPU memory 16.43 GiB exceeds the 14.00 GiB limit`, in `trainer.train` of the parent (gold phase), before step 1000. `S1-DONE failed`, box exit 19:44:17Z; the watchdog stopped the box at 19:47:33Z. |
| 1 | t = 2696.9 s | **failed** at t = 2755.4 s (59 s later): the same error at **16.91 GiB**, same place. Box exit 19:45:13Z; stopped 19:47:42Z. |
| 2 | t = 3200.7 s | **training**: step 1000 (share 0.0144, DEV-256 accuracy 0.088), step 2000 (share 0.0288, accuracy 0.202), about 8.7 steps/s in the gold phase. |

Neither failed seed produced a parent checkpoint; nothing of theirs is usable. The guard is checked after the first
step and every 50 steps, and `reset_guard` (empty cache, reset peak) runs between the fp32 calibration and training,
so the 16.4-16.9 GiB peaks come from the training steps themselves.

**What this shows (shown):** the pre-flight did not bound the real run's reserved memory. At rung 2 the pre-flight's
worst child reserved 8.46 GB (seed 2); the real parent runs on seeds 0 and 1 reserved more than 17.6 GB (16.43 GiB)
within about 400 steps. Allocated memory at rung 2 was at most 7.04 GB in the pre-flight, so reserved / allocated
reached at least 2.5 in the real run, above the worst 2.04 the pre-flight saw.

**Why (suggested, not tested):** the reserve grows with the CUDA caching allocator's fragmentation, which depends on
the order of batch shapes. The pre-flight replays 12 batches for 36 steps; the real stream gives a new shape at every
step. That matches the warning filed with the pre-flight ("36 steps cannot bound how badly the allocator fragments"),
but the real growth came faster and larger than that estimate. Seed 2 has passed at least 40 guard checks so far; it
can still fail later in the run for the same reason.

**Not done (on purpose):** no lower rung, no allocator setting, no restart of seeds 0 and 1. The rung and any change
to the run are the coordinator's call. The go file still reads as the coordinator filed it. The stopped boxes run
nothing unless they are started, and a restart would reread that go and repeat the same configuration, so I will not
start them without a ruling.

**Money:** $0.78 spent at 19:47Z since the baseline. Seed 2 alone costs $0.29/h; the stopped boxes cost only disk.

## Seed 2: parent done, LINE arm failed (2026-10-18)
- **Parent P_2:** 3,484 gold steps, 124.5M tokens, 387 s, share 0.0500 of F. Peak reserved **10.70 GB** (the
  trainer's own report): inside the guard. Final train loss 0.905, train answer accuracy 0.825.
  Checkpoint `artifacts/span-stage1/20261018T184858Z/seed2/parent` on the box disk (state sha256 76986173...eb2,
  config sha256 bbed5131...e22e).
- **Parent DEV:** 8,675 / 8,675 questions scored, aligned; overall 0.2116 (n = 7,683 told), near 0.207, far 0.252,
  multi_hop 0.236, not told 0.000 (n = 469).
- **Branch-point check: passed.** 5,967 cards; CPU key and value differences 0.0; natural and eager passes identical on
  576 / 576 questions (eager fetched 16,128 cards over all 576); line_aligned = 1.
- **LINE arm:** started at step 3,484 (the parent's line economy at the branch: 93 cards per visit, 11.16 tokens per
  card, line_aligned 1). It failed at t = 3716.8 s, 94 s after its start: `MemoryGuardError: peak reserved GPU memory
  21.10 GiB` (22.66 GB on the 24 GB card), in `trainer.train` of the arm. Box exit 19:50:56Z; the watchdog stopped
  the box at 19:53:00Z. No LINE or SPAN checkpoint.

**What the three failures show together (shown):** on the same rung and the same code, the reserved peak was
10.70 GB for one full gold phase (seed 2) and 17.6-18.2 GB within about 400 gold steps for two others (seeds 0 and 1).
The first post-gold minutes of seed 2's LINE arm reached 22.66 GB. Before each training run the script frees the
cache and resets the peak; the parent, probe and branch batches are off the GPU or deleted before the arms.

**Possible causes (suggested, none tested):**
1. Allocator fragmentation from the changing batch shapes, as already filed. This fits the spread across seeds.
2. Memory that depends on the *trained* model's behaviour after the gold phase: the number of ASK/HALT loops per
   question, and the cards fetched. The pre-flight measured teacher and own steps with fresh weights, so it could not
   see this. This fits the jump at the arm's start, after a full gold phase that stayed at 10.7 GB.
3. Growth over time inside the training loop (something held from step to step). Nothing in the logs shows this
   directly.

A Linux card does not spill to system RAM. The guard (from train_d's `MiniTrainer`, written for Windows) stops the run
at 14 GiB reserved, and the 24 GB card itself did not run out. Whether the guard should bind on these boxes is a
ruling, not something I change.

**Boxes and money:** spend $0.817 at 19:53Z since the baseline (of the $18 hard stop). All three boxes are stopped.
Their disks cost about $0.10/h together (seed 0 $0.014/h, seed 1 $0.060/h, seed 2 $0.031/h). Seed 2's disk holds
the P_2 checkpoint and the built data; seeds 0 and 1 hold the data only. The watchdog stops a finished box and never
destroys it. It exits once no box is active, so nothing destroys the stopped boxes or P_2 until the coordinator
rules. A stopped box costs only its disk, so a restart, a destroy, or keeping P_2 is a ruling.

## Readout per seed
(filed when each seed finishes)

## Attempt 2 (ruling Q159, 2026-10-18)
**Ruling:** seeds 0 and 1 restart at rung 2 unchanged (40,000 tokens, 35 visits, same F, same marks, same pairing),
with one change: `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`. The setting changes memory management only, not
the math. Under Q159 (5), the same ruling covers seed 2's restart, because seed 2 failed the same guard (its LINE arm,
19:50Z). Before a restarted box commits to the full run, it must pass a strengthened pre-flight on the real training
stream: at least the first 1,000 steps with peak reserved memory under the 14.00 GiB limit. A crossing stops that
box, and I report instead of proceeding.

**How the setting is passed: launch environment only, no script change.** The box launch script exports
`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` before anything runs, and logs it as `S1BOX-ALLOC ...`. The
pre-flight child processes inherit the environment (`subprocess.run` without `env=`). `scripts/span_stage1.py` is
unchanged: commit 707bdce90, sha256 47577a35...d127, and every box refuses any other hash. The launch script also
logs `nvidia-smi` memory.used every 30 s (`S1BOX-MEM`). That reading is the whole card, CUDA context included, so it
is an upper bound on reserved memory, sampled. The guard's own peak is exact.

**Amended go record** (`stage1-go.json`, commit 9d15e6626): the coordinator's rung-2 record unchanged, plus
`"attempt": 2`, `"env": {"PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"}`, `"ruling": "Q159"` and a note.
The boxes ignore keys they do not check, so the record documents the run without changing what the script accepts.

**Strengthened pre-flight: the first 1,000 steps of the real run, guard on (fixed before any result).** No separate
script is needed. The parent's training *is* the real stream in the real batch-shape order. The trainer's guard
compares peak reserved memory (since the reset after calibration) with 14.00 GiB after step 1 and every 50 steps, and
stops the run at the first crossing. So:
- **pass** = the box logs `progress ... step 1000` with no `MemoryGuardError` before it (20 guard checks clean). The
  run then continues to the full run, as released.
- **fail** = `MemoryGuardError` at or before step 1,000. The run stops, `S1-DONE failed`, the watchdog stops the box,
  and I report.
- The exact peak over the whole gold phase (3,484 steps) is in the parent record (`peak_gpu_reserved_bytes`).
  `S1BOX-MEM` gives the trace between.
- The old 12-batch pre-flight still runs before the go gate (the script does it). It is recorded but no longer the
  release test.
- What this does not cover: attempt 1's seed 2 failed at the LINE arm's start, after 3,484 clean gold steps. A pass
  at step 1,000 does not bound the arms. The guard stays on for the whole run, so a later crossing stops that seed
  and I report it.

**Boxes (attempt 2):** new RTX 3090 on-demand rentals, rented 20:12Z, running the same commit and script.

| seed | instance | label | $/h |
|---|---|---|---|
| 0 | 56611901 | claude-spancards-s1b-seed0 | 0.242 |
| 1 | 56611888 | claude-spancards-s1b-seed1 | 0.216 |
| 2 | 56611889 | claude-spancards-s1b-seed2 | 0.240 |

The attempt-1 boxes (56601518, 56601519, 56601524) stay stopped, not destroyed. Their disks (about $0.10/h) count in
the Stage 1 spend. Seed 2's attempt-1 disk holds the attempt-1 P_2 checkpoint. A new watchdog has the same money rule:
spend since the $32.588 baseline covers both attempts and every box, and everything is destroyed if it passes $16 (hard
stop $18). Spend at 19:53Z was $0.817.

### Addendum Q160 (coordinator, 2026-10-18), and how it is applied (fixed before the arm results)
1. **The 14 GiB guard binds as written** for Stage 1. It will not be re-examined or loosened mid-run. A guard
   redesign (for example binding on allocated memory) can be proposed only as a separate pre-registered change for
   future runs.
2. **Rung-3 fallback, pre-approved.** If any attempt-2 box (setting on) crosses the guard, in the 1,000-step parent
   probe, the arm probe or anywhere in the run, then **all seeds drop to rung 3 (32,000 tokens, 28 visits)**,
   identical across arms and seeds, under the same probe standard, without waiting for a ruling. Mechanics:
   - an amended go record: attempt 3, rung 3, the same allocator setting;
   - every attempt-2 box stopped, healthy ones included, because the rung is common to all seeds;
   - fresh boxes rented for all three seeds with the same launch script. A fresh box keeps the watchdog's log
     handling clean; a restarted box replays its old log, including its `S1-DONE`.
   The drop is recorded here.
3. **Arm probe.** The probe standard extends to the arm phase, for every seed. The **LINE arm's first 1,000 steps
   from the trained parent**, with reserved memory under 14.00 GiB, are the arm probe; the same applies to the SPAN
   arm. Measurement: the guard checks every 50 global steps. Progress records come at global steps that are multiples
   of 1,000, and an arm starts at the parent's last step (about 3,484). So **pass** = the first progress record at
   least 1,000 steps after `arm_start`'s step (for example global step 5,000 when the arm starts at 3,484) with no
   `MemoryGuardError` before it. **Fail** = a guard error in that window, which triggers (2). A crossing later in the
   run also triggers (2).
4. **P_2 (attempt 1).** It stays on the stopped attempt-1 seed-2 box (56601524) until Stage 1 completes:
   `artifacts/span-stage1/20261018T184858Z/seed2/parent`, state 76986173...eb2, config bbed5131...e22e. **Attempt 2
   does not rely on it.** The restarted seed-2 box trains its own parent, P_2 (attempt 2), from the same seed, data
   and rung, now with the setting on, and its arms branch from that parent. The run script has no way to start the
   arms from an outside parent checkpoint without a script change, which would be DRAFT until reviewed. Re-training
   the parent costs about 7 minutes ($0.03). So the arm probe in (3) for seed 2 runs from the trained P_2 of attempt
   2, and no copy is needed: Q160 (4) asks for a copy only "before relying on it". If the coordinator wants the
   attempt-1 P_2 itself used, that needs the script change.

### Attempt 2 outcomes
(filed per seed as the boxes report)

**Seed 0 (56611901): strengthened pre-flight PASSED.**
- Boot 20:12:54Z; `S1BOX-ALLOC PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`; commit 707bdce90; script hash checked.
- Data: train a53ab45b..., validation 762082f1..., N 11.155539, identical to the seal.
- Old 12-batch pre-flight, now with the setting: rung 0 fits. Peak reserved / allocated: LINE 9.44 / 8.33,
  SPAN 9.90 / 9.70, stress 9.90 / 9.73 GB. In attempt 1 the same box class reserved up to 1.94x allocated; here the
  reserve is within 0.2 GB of allocated.
- Go accepted at t = 435.5 s: rung 2 (40,000, 35).
- **Step 1,000 at t = 514.7 s, no `MemoryGuardError`** (20 guard checks clean, limit 14.00 GiB). Gold loss 1.109,
  train answer accuracy 0.693. `nvidia-smi` memory.used (whole card) during the parent: 4.1-6.1 GB. The run
  continues to the full run, as Q159 releases it.
- Parent P_0 (attempt 2): 3,487 gold steps, share 0.0500, **peak reserved 6.02 GB** over the whole gold phase. In
  attempt 1 the same seed failed at 16.43 GiB. Checkpoint `artifacts/span-stage1/20261018T201349Z/seed0/parent`
  (state 01559606..., config ba04714e...). DEV: aligned, overall 0.110.
- Branch-point check: passed (5,967 cards, key/value diff 0.0, 0 differing answers natural and eager, 0 GPU flips).
- **Arm probe (Q160 (3)): LINE PASSED.** The arm started at step 3,487 (t = 727.7 s). Progress at global step 5,000
  (1,513 arm steps, teacher phase, t = 950.6 s) with no guard error. Whole-card memory during the arm: about 7.0 GB.
  The LINE arm continues; it was at step 7,000 (share 0.117) at t = 1,187 s.

**Seed 2 (56611889): strengthened pre-flight PASSED.**
- Boot 20:15:08Z; setting logged; commit 707bdce90. Data identical to the seal.
- Old pre-flight: rung 0 fits, worst 9.91 GB reserved / 9.73 GB allocated. In attempt 1, the same seed's box
  reserved 16.14 GB at rung 0.
- Go accepted at t = 706.8 s. **Step 1,000 at t = 814.0 s with no guard error.**
- Parent P_2 (attempt 2): 3,484 gold steps, **peak reserved 6.15 GB**. Checkpoint state 094e96a1..., config
  aec7376b.... This differs from attempt 1's P_2 (76986173...), as expected for a re-trained parent. The attempt-1 P_2
  stays on box 56601524. DEV: aligned, overall 0.204.
- Branch-point check: passed (same figures as seed 0). The LINE arm started at step 3,484 (t = 1,086.7 s).
- **Arm probe (Q160 (3), from the trained P_2): LINE PASSED.** Progress at global step 5,000 (1,516 arm steps,
  teacher phase, t = 1,393.5 s) with no guard error. In attempt 1 the same seed's LINE arm crossed at 21.10 GiB 94 s
  after its start; this time the arm ran 307 s clean. The LINE arm continues.

**Seed 1 (56611888):** slower CPU box (12 cores). Boot 20:15:58Z; setting logged; commit 707bdce90. Data identical
to the seal. Old pre-flight: rung 0 fits, worst 9.90 GB reserved / 9.73 GB allocated (attempt 1: 11.70 GB). Go
accepted at t = 1,198.5 s (about 20:37Z).
- **Step 1,000 at t = 1,487.6 s with no guard error: strengthened pre-flight PASSED.**
- Parent P_1 (attempt 2): 3,470 gold steps, **peak reserved 6.07 GB**; in attempt 1 this seed failed at 16.91 GiB.
  Checkpoint state 94a26d1d..., config 31b2c806.... DEV: aligned, overall 0.202.
- Branch-point check: passed (5,967 cards, key/value diff 0.0, 0 differing answers, 0 GPU flips).
- **Arm probe: LINE PASSED.** The arm started at step 3,470 (t = 2,219.1 s). Progress at global step 5,000 (1,530
  arm steps, t = 3,152.3 s) with no guard error.
- This box trains about 3.4x slower than seed 0's (about 390 s per 1,000 LINE steps against about 116 s), probably
  CPU-bound. This changes wall time and cost, not the run.

**All three seeds passed both probes (parent 1,000 steps, LINE arm 1,000+ steps from the trained parent) at rung 2
with the setting on. No rung-3 drop.** At 21:13Z: seed 0 LINE at global step 24,000 (share 0.509, own phase), seed 2
LINE at 17,000 (share 0.312, own phase), seed 1 LINE at 5,000. Spend $1.716. The guard stays on; the SPAN arm probe
(its first 1,000 steps) is filed as each SPAN arm starts.
