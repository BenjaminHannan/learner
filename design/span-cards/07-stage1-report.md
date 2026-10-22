# Stage 1 report (SC-1; booked by the coordinator after Stage 0)

**Status: COMPLETE (2026-10-19).** All three seeds trained both arms to F at rung 2 (40,000, 35) with
`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` (attempt 2, rulings Q159/Q160/Q187). Every parent, LINE and SPAN
run stayed under the memory guard. DEV readout per seed and family calls are under "Final family verdict" at the end.

**Stage 1 result in one paragraph:** SPAN did not keep its card budget in any seed. Its DEV tokens per card ended at
1.97, 2.94 and 3.29 against N = 11.16 (G3 FAIL, 3/3), and line alignment collapsed (P3 falsified, 3/3).
First-ask recall fell in every seed (G1 FAIL, 3/3). On DEV, SPAN was WORSE than LINE on `far` in seeds 1 and 2 and
on overall in seed 2 (G2 FAIL, 2/3); in seed 0 it was non-inferior overall. Under the card, G3's failure means
Stage 1 is **not a placement-at-equal-storage result**. Compute was matched in every seed (G4 pass, 3/3) and entity
overflow never flagged (G5). P1, P2 and P4-P6 are on the sealed E1/E3 sets and are scored by the coordinator.
**Total actual Stage 1 spend: $7.98** (to 08:45Z on 2026-10-19, both attempts, all boxes), inside the $18 hard stop.

Attempt 1 (rung 2 without the allocator setting) failed the memory guard on all three seeds; its record is kept below.

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

### Timing and money (22:45Z)
- Progress: seed 0 SPAN share 0.270; seed 2 LINE 0.960; seed 1 LINE 0.314.
- Rates measured so far: seed 0's LINE arm took 1.57 h, and its SPAN arm is running about 1.65x slower than its LINE
  arm (about 2.6 h projected). Seed 1's box is about 3.4x slower: LINE projected to end about 03:00Z, SPAN about
  13:00Z on 2026-10-19 (a projection, not a measurement).
- **Watchdog deadline extended from 16 h to 24 h** (to 20:12Z on 2026-10-19). Without it, the attempt-2 watchdog would
  have destroyed seed 1's box at about 12:12Z, before its SPAN arm ends. The money rule is unchanged: everything is
  destroyed if Stage 1 spend since the $32.588 baseline passes $16.
- Spend $2.93 at 22:40Z. Projected Stage 1 total about $8-9: seed 1 about $3 more, seeds 0 and 2 about $0.5-0.7 each
  more, the attempt-1 disks about $0.10/h. Inside the $18 hard stop.

## Readout per seed
Attempt 2 (rung 2, `expandable_segments:True`). Each arm's DEV is the full validation split (8,675 questions,
7,683 told). The paired G2 and the guards are computed once both arms of a seed are in. E1/E3 are the coordinator's.

### Seed 0
**LINE arm: done.**
- 37,993 steps (teacher 13,080, own 24,913), 1.359B tokens, 5,637 s. Stopped on the FLOP budget, share 1.000004,
  budget_ok, 0 loop mismatches.
- **Peak reserved 7.52 GB** over the whole arm, under the guard.
- Final train: loss 1.040, answer acc 0.902, first-ask acc 0.263, recall@k 0.777.
- Checkpoint `artifacts/span-stage1/20261018T201349Z/seed0/line` on the box disk (state 788ed448...a6e, config
  69b06931...5f3).

| DEV (LINE, seed 0) | n | accuracy |
|---|---|---|
| overall (told) | 7,683 | 0.3884 |
| near | 4,290 | 0.3569 |
| far | 2,924 | 0.4593 |
| far_deep | 2,427 | 0.4351 |
| multi_hop | 5,155 | 0.3717 |
| not told | 469 | 0.2345 |

Economy after the arm: line layout, line_aligned 1, asked rate 0.827, 4.05 fetches per question, first-ask recall
0.513, full gold fetched 0.527.

**SPAN arm:** started at t = 6,422.9 s from P_0 (step 3,487, share 0.0500; at the branch 11.16 tokens per card,
line_aligned 1). **Arm probe: SPAN PASSED.** Progress at global step 5,000 (1,513 arm steps, t = 6,755.7 s) with no
guard error.

**SPAN arm: done.**
- 37,963 steps (teacher 13,073, own 24,890), 1.358B tokens, 9,961 s. Stopped on the FLOP budget, share 1.000024,
  budget_ok, 0 loop mismatches.
- **Peak reserved 8.03 GB.**
- Final train: loss 1.877, answer acc 0.774, first-ask acc 0.262, recall@k 0.675.
- Checkpoint `artifacts/span-stage1/20261018T201349Z/seed0/span` (state c3622431...c0fa, config 68391c1a...9633).
- `S1-DONE ok`, box exit 00:47:49Z. The watchdog stopped box 56611901 at 00:48:31Z; the parent, LINE and SPAN
  checkpoints are on its disk.

**Seed 0 readout (DEV = E2; per-seed values; the family rule needs 2 of 3 seeds).** Paired by question with
`exp1.paired` (alpha 0.01) on the per-question correctness bits of each arm. The slices use the box's own masks
(ids_sha256 0c91568c... on parent, LINE and SPAN). BETTER/WORSE need significance and a difference of at least 3.0
points; non-inferior means `paired(SPAN, LINE, margin=-0.03)` is significant.

| DEV slice | n | P_0 | LINE | SPAN | SPAN - LINE | p (SPAN > LINE) | p (LINE > SPAN) | p (non-inf.) | per-seed call |
|---|---|---|---|---|---|---|---|---|---|
| overall | 7,683 | 0.1104 | 0.3884 | 0.3989 | +1.05 | 0.030 | 0.973 | 0.0001 | non-inferior; not BETTER, not WORSE |
| near | 4,290 | 0.1175 | 0.3569 | 0.3795 | +2.26 | 0.0013 | 0.999 | 0.0001 | significant but under +3.0; non-inferior |
| far | 2,924 | 0.1149 | 0.4593 | 0.4497 | -0.96 | 0.867 | 0.151 | 0.011 | inconclusive (not WORSE; non-inferiority p 0.011 > 0.01) |
| multi_hop | 5,155 | 0.0941 | 0.3717 | 0.4204 | +4.87 | <0.0001 | 1.0 | 0.0001 | BETTER in this seed |
| far_deep | 2,427 | 0.0968 | 0.4351 | 0.4400 | +0.49 | 0.320 | 0.709 | 0.0002 | non-inferior |

Each arm minus its parent on DEV overall: LINE +27.8 points, SPAN +28.9 points.

**Guards and P3 (seed 0):**

| check | rule | SPAN | LINE | result |
|---|---|---|---|---|
| G1 asked_rate | >= LINE - 0.05 | 0.850 | 0.827 | pass |
| G1 fetches_per_q | >= 0.8 x LINE | 4.82 | 4.05 | pass |
| G1 null_share | <= LINE + 0.05 | 0.082 | 0.148 | pass |
| G1 first_ask_recall | >= LINE - 0.05 | **0.379** | 0.513 | **FAIL** |
| G2 DEV slip | SPAN not WORSE on overall and far | +1.05 / -0.96 | | pass |
| G3 budget held | SPAN tokens_per_card within +/-25% of N = 11.155539 | **1.97** (ratio 0.18) | 11.16 | **FAIL** |
| G4 compute matched | both budget_ok | 1.000024 | 1.000004 | pass (0 / 0 loop mismatches) |
| G5 entity overflow | < 0.02 | 0.000 | | no flag |
| P3 adaptation small | SPAN line_aligned >= 0.85 | **0.019** | 1.0 | **falsified (this seed)** |

**SPAN card economy at the end (200 DEV visits):** 105,278 cards, 526 per visit (p10 377, p50 511, p90 697). LINE has
93 per visit. 58.5% of SPAN's cards are 1 token long, 22.4% are 2 tokens, 11.8% are 3-4. split_lines 0.893, merged
0.0001, newline precision 0.177, newline recall 0.9996. The last training-log entries (steps 41,350-41,400): gate
start rate 0.32-0.37 of tokens (1/N = 0.090), span tokens per card 2.7-3.1, rate term 1.94.

**What this shows (shown, seed 0 only):**
- SPAN did not keep the card budget. It cut almost every line into many 1-2 token cards: 5.7x LINE's card count.
- By the run card's own rule (G3), this seed's SPAN-vs-LINE comparison is not "placement at equal storage" and must
  not be reported as a placement result. G1 also fails (first-ask recall), and P3 is falsified in this seed.
- The DEV numbers are reported as measured, for the record only: SPAN was not worse overall or on far, and was better
  on multi_hop. Under G3 these are a different comparison: about 5.7x more, much smaller cards at the same compute.

**Why (suggested, not tested):** the rate loss (w_rate 0.03) did not hold the gate's start rate near 1/N against the
answer loss's pull toward fine cards. The rate loss is 1.0 at the target (start rate = gate mean = 1/N); at the end it was 1.94, so after the 0.03 weight it
added about 0.06 to a total train loss of 1.88. That suggests the term was active but outweighed. The
branch check showed SPAN started at 11.16 tokens per card and line_aligned 1, so the drift happened during training.
No other seed has a SPAN result yet. Seed 2's SPAN arm is about half done and seed 1's has not started. Nothing is
stopped or changed; G3 is a measured outcome, not a stop rule.

### Seed 2
**LINE arm: done.**
- 37,936 steps (teacher 13,086, own 24,850), 1.357B tokens, 7,569 s. Stopped on the FLOP budget, share 1.000002,
  budget_ok, 0 loop mismatches.
- **Peak reserved 7.90 GB** (attempt 1's LINE arm crossed at 21.10 GiB).
- Final train: loss 1.337, answer acc 0.884, first-ask acc 0.258, recall@k 0.725.
- Checkpoint `artifacts/span-stage1/20261018T201637Z/seed2/line` (state e1b5a961..., config 1fb3dbc3...).

| DEV (LINE, seed 2) | n | accuracy |
|---|---|---|
| overall (told) | 7,683 | 0.3749 |
| near | 4,290 | 0.3417 |
| far | 2,924 | 0.4248 |
| far_deep | 2,427 | 0.4508 |
| multi_hop | 5,155 | 0.4194 |
| not told | 469 | 0.3667 |

Economy after the arm: line_aligned 1, asked rate 0.796, 4.23 fetches per question, null share 0.136, first-ask
recall 0.427, full gold fetched 0.385.

**SPAN arm:** started at t = 8,741.0 s from P_2 (attempt 2) at step 3,484 (11.16 tokens per card, line_aligned 1).
**Arm probe: SPAN PASSED.** Progress at global step 5,000 (1,516 arm steps, t = 9,149.1 s) with no guard error.

**SPAN arm: done.**
- 37,907 steps (teacher 13,078, own 24,829), 1.356B tokens, 11,760 s. Stopped on the FLOP budget, share 1.000019,
  budget_ok, 0 loop mismatches.
- **Peak reserved 8.18 GB.**
- Final train: loss 1.882, answer acc 0.638, first-ask acc 0.273, recall@k 0.720.
- Checkpoint `artifacts/span-stage1/20261018T201637Z/seed2/span` (state a7b601ba...e0ff, config a36256e2...877f).
- `S1-DONE ok`, box exit 01:59:36Z. The watchdog stopped box 56611889 at 02:03:01Z; the checkpoints are on its disk.

**Seed 2 readout (DEV = E2, paired as for seed 0; ids_sha256 0c91568c... on all three DEV records):**

| DEV slice | n | P_2 | LINE | SPAN | SPAN - LINE | p (LINE > SPAN) | per-seed call |
|---|---|---|---|---|---|---|---|
| overall | 7,683 | 0.2037 | 0.3749 | 0.2745 | **-10.04** | <0.0001 | **SPAN WORSE** |
| near | 4,290 | 0.1986 | 0.3417 | 0.2382 | -10.35 | <0.0001 | SPAN WORSE |
| far | 2,924 | 0.2438 | 0.4248 | 0.3266 | **-9.82** | <0.0001 | **SPAN WORSE** |
| multi_hop | 5,155 | 0.2281 | 0.4194 | 0.2982 | -12.12 | <0.0001 | SPAN WORSE |
| far_deep | 2,427 | 0.2550 | 0.4508 | 0.3317 | -11.91 | <0.0001 | SPAN WORSE |

Discordant pairs overall: LINE-only 1,308 and SPAN-only 537. Each arm minus its parent on DEV overall: LINE +17.1
points, SPAN +7.1 points.

**Guards and P3 (seed 2):**

| check | rule | SPAN | LINE | result |
|---|---|---|---|---|
| G1 asked_rate | >= LINE - 0.05 | **0.627** | 0.796 | **FAIL** |
| G1 fetches_per_q | >= 0.8 x LINE | 3.393 | 4.232 | pass, narrowly (3.393 >= 3.385) |
| G1 null_share | <= LINE + 0.05 | 0.103 | 0.136 | pass |
| G1 first_ask_recall | >= LINE - 0.05 | **0.308** | 0.427 | **FAIL** |
| G2 DEV slip | SPAN not WORSE on overall and far | -10.04 / -9.82 | | **FAIL** |
| G3 budget held | tokens_per_card within +/-25% of N | **3.29** (ratio 0.29) | 11.16 | **FAIL** |
| G4 compute matched | both budget_ok | 1.000019 | 1.000002 | pass (0 / 0) |
| G5 entity overflow | < 0.02 | 0.00003 | | no flag |
| P3 adaptation small | line_aligned >= 0.85 | **0.000** | 1.0 | **falsified (this seed)** |

**SPAN card economy at the end:** 63,184 cards, 316 per visit (p10 222, p50 307, p90 430); 3.29 tokens per card
(1 token 34.0%, 2 tokens 24.1%, 3-4 19.3%, 5-8 16.3%, 9-16 5.4%). split_lines 0.895, **merged 0.258**, **newline
precision 0.014, newline recall 0.047**, so cards no longer start at line starts at all. Last training-log entries
(steps 41,250-41,350): gate start rate 0.33-0.36, tokens per card 2.8-3.0, rate term 1.70-1.89.

**Seed 0 and seed 2 compared (shown):** both SPAN arms abandoned the card budget (G3) and line alignment (P3). They
took different shapes. Seed 0 kept every line start (newline recall 1.00) and cut lines into 1-2 token pieces, and was
not worse on DEV. Seed 2 dropped line starts (recall 0.05), merged across lines, and lost 10 points on DEV.

### Seed 1
**LINE arm: done.**
- 37,782 steps (teacher 13,031, own 24,751), 1.351B tokens, 19,102 s on the slow box. Stopped on the FLOP budget,
  share 1.000014, budget_ok, 0 loop mismatches.
- **Peak reserved 7.65 GB.**
- Final train: loss 1.073, answer acc 0.889, first-ask acc 0.253, recall@k 0.759.
- Checkpoint `artifacts/span-stage1/20261018T201824Z/seed1/line` (state edfbf50c...fc35, config d0592b41...8627).

| DEV (LINE, seed 1) | n | accuracy |
|---|---|---|
| overall (told) | 7,683 | 0.4544 |
| near | 4,290 | 0.4317 |
| far | 2,924 | 0.5205 |
| far_deep | 2,427 | 0.5200 |
| multi_hop | 5,155 | 0.4916 |
| not told | 469 | 0.2495 |

Economy after the arm: line_aligned 1, asked rate 0.813, 3.97 fetches per question, null share 0.146, first-ask
recall 0.463, full gold fetched 0.433.

**SPAN arm:** started at t = 21,678.1 s (about 02:19Z) from P_1 at step 3,470 (11.16 tokens per card, line_aligned
1). **Arm probe: SPAN PASSED.** Progress at global step 5,000 (1,530 arm steps, t = 22,765.0 s) with no guard
error.

**SPAN arm: done.**
- 37,751 steps (teacher 13,023, own 24,728), 1.350B tokens, 22,721 s. Stopped on the FLOP budget, share 1.000016,
  budget_ok, 0 loop mismatches.
- **Peak reserved 8.09 GB.**
- Final train: loss 1.602, answer acc 0.836, first-ask acc 0.258, recall@k 0.725.
- Checkpoint `artifacts/span-stage1/20261018T201824Z/seed1/span` (state b115f29a...ddf9, config 31f1de88...dec5).
- `S1-DONE ok`, box exit 08:44:10Z. The watchdog stopped box 56611888 at 08:45:12Z; the checkpoints are on its disk.

**Seed 1 readout (DEV = E2, paired as for seeds 0 and 2):**

| DEV slice | n | P_1 | LINE | SPAN | SPAN - LINE | p (LINE > SPAN) | p (non-inf.) | per-seed call |
|---|---|---|---|---|---|---|---|---|
| overall | 7,683 | 0.2021 | 0.4544 | 0.4257 | -2.86 | <0.0001 | 0.385 | significant but under 3.0: not WORSE; not non-inferior |
| near | 4,290 | 0.1944 | 0.4317 | 0.4100 | -2.17 | 0.0004 | 0.098 | not WORSE (under 3.0); not non-inferior |
| far | 2,924 | 0.2350 | 0.5205 | 0.4685 | **-5.20** | <0.0001 | 0.997 | **SPAN WORSE** |
| multi_hop | 5,155 | 0.2223 | 0.4916 | 0.4310 | -6.05 | <0.0001 | 1.0 | SPAN WORSE |
| far_deep | 2,427 | 0.2447 | 0.5200 | 0.4479 | -7.21 | <0.0001 | 1.0 | SPAN WORSE |

Discordant pairs overall: LINE-only 821 and SPAN-only 601. Each arm minus its parent on DEV overall: LINE +25.2
points, SPAN +22.4 points.

**Guards and P3 (seed 1):**

| check | rule | SPAN | LINE | result |
|---|---|---|---|---|
| G1 asked_rate | >= LINE - 0.05 | 0.868 | 0.813 | pass |
| G1 fetches_per_q | >= 0.8 x LINE | 4.31 | 3.97 | pass |
| G1 null_share | <= LINE + 0.05 | 0.102 | 0.146 | pass |
| G1 first_ask_recall | >= LINE - 0.05 | **0.402** | 0.463 | **FAIL** |
| G2 DEV slip | SPAN not WORSE on overall and far | -2.86 / **-5.20 (WORSE)** | | **FAIL** |
| G3 budget held | tokens_per_card within +/-25% of N | **2.94** (ratio 0.26) | 11.16 | **FAIL** |
| G4 compute matched | both budget_ok | 1.000016 | 1.000014 | pass (0 / 0) |
| G5 entity overflow | < 0.02 | 0.000 | | no flag |
| P3 adaptation small | line_aligned >= 0.85 | **0.000** | 1.0 | **falsified (this seed)** |

**SPAN card economy at the end:** 70,547 cards, 353 per visit (p10 260, p50 350, p90 448); 2.94 tokens per card
(1 token 34.6%, 2 tokens 26.6%, 3-4 22.1%, 5-8 10.8%, 9-16 5.5%). split_lines 0.932, merged 0.240, newline precision
0.014, newline recall 0.053, the same shape as seed 2. Last training-log entries (steps 41,100-41,200): gate start
rate 0.33-0.36, tokens per card 2.8-3.1, rate term 1.68-1.90.

### Family status after two of three seeds (02:05Z)
The run card's family rule needs 2 of 3 seeds. With two seeds in:
- **G3 (budget held): FAIL in seeds 0 and 2.** That is 2 of 3 whatever seed 1 shows. Under the card, Stage 1's
  SPAN-vs-LINE comparison is not "placement at equal storage" and is not reported as a placement result.
- **P3: falsified in seeds 0 and 2** (line_aligned 0.019 and 0.000): 2 of 3 whatever seed 1 shows.
- **G1: FAIL in seeds 0 and 2** (first-ask recall in both; asked rate in seed 2): 2 of 3.
- **G2 (DEV slip):** pass in seed 0, FAIL in seed 2. Seed 1 decides the family call.
- **G4:** pass in both. **G5:** no flag in either.
- P1, P2, P4-P6 are on the sealed E1/E3 sets and are the coordinator's to score.

Seed 1's LINE arm is near its end; its SPAN arm (about 10 h, about $2-3 projected) has not started. It is not stopped.
The registered plan runs three seeds, and G3/P3/G1 are measured outcomes, not stop rules. Whether to finish it is
the coordinator's call.

**Ruling Q187 (coordinator):** finish seed 1's SPAN arm as registered: sealed SC-1 marks, same rung (40,000, 35) and
the same allocator setting as the other seeds, inside the $18 hard stop. The family verdict on G3, P3 and G1 is
already settled by seeds 0 and 2; seed 1 completes the three-seed design and settles G2. When it lands, the final
Stage 1 report gives all three seeds' readouts and the total actual Stage 1 spend. Nothing else changes.

### Final family verdict (three seeds; family rule >= 2 of 3, never averaged or pooled)
| item | seed 0 | seed 1 | seed 2 | family |
|---|---|---|---|---|
| G1 ASK/fetch not collapsed | FAIL (first-ask recall) | FAIL (first-ask recall) | FAIL (asked rate, first-ask recall) | **FAIL (3/3)** |
| G2 DEV slip (overall, far) | pass (+1.05 / -0.96) | FAIL (far -5.20 WORSE) | FAIL (overall -10.04, far -9.82 WORSE) | **FAIL (2/3)** |
| G3 budget held (tokens per card vs N = 11.16) | FAIL (1.97) | FAIL (2.94) | FAIL (3.29) | **FAIL (3/3)** |
| G4 compute matched | pass | pass | pass | **pass (3/3)**; loop mismatches 0 in all six arms |
| G5 entity overflow | no flag | no flag | no flag | **no flag** |
| P3 line_aligned >= 0.85 | 0.019 | 0.000 | 0.000 | **falsified (3/3)** |

DEV overall per seed (LINE / SPAN): 0.388 / 0.399, 0.454 / 0.426, 0.375 / 0.275. DEV far: 0.459 / 0.450,
0.521 / 0.469, 0.425 / 0.327.

**What this shows (shown):**
- At w_rate 0.03, the SPAN gate does not hold a card rate near 1/N on this data. Every seed ended with a gate start
  rate of 0.32-0.37 of tokens against a target of 0.090. The cards were 3.4-5.7x more numerous than LINE's and 1-3
  tokens long.
- Two of the three SPAN arms (seeds 1, 2) also stopped starting cards at line starts at all (newline recall about
  0.05).
- Because G3 fails, the card says Stage 1's SPAN-vs-LINE differences are **not** a placement result. They compare
  LINE with a model that stores many more, much smaller cards at the same compute.
- On that different comparison, SPAN was worse on DEV `far` in two of three seeds and never better on overall.

**Suggested, not tested:** the rate loss's weight (0.03, H-Net's value, recorded in the card as an assumption) is too
small against the answer loss here. A redesign of the budget mechanism would be a new pre-registered card, not a
change to SC-1.

**Not decided here:** P1, P2 and P4-P6 (sealed E1/E3, the coordinator's). Cell B is conditional on Cell A passing
G1-G4 for SPAN (run card section 4). G1, G2 and G3 failed. The card's registered outcome for that case is "the
mechanism breaks retrieval on today's data", and B is not funded, unless the coordinator rules otherwise.

### Money (final)
| item | amount |
|---|---|
| Stage 1 baseline credit (before any Stage 1 rental) | $32.588 |
| credit at 08:45Z on 2026-10-19 (all six boxes stopped) | $24.611 |
| **total actual Stage 1 spend, both attempts** | **$7.98** (hard stop $18) |

Attempt 1 cost about $0.82 (data, pre-flight, go wait, the failed runs). Attempt 2 cost about $7.16 (three boxes,
about 4.6 h, 5.8 h and 12.5 h, plus the stopped disks). The six stopped boxes still cost disk, **about $0.16/h in
all**, until they are destroyed:

| instance | label | holds | disk $/h |
|---|---|---|---|
| 56611901 | claude-spancards-s1b-seed0 | P_0, LINE, SPAN (seed 0) + data | 0.014 |
| 56611888 | claude-spancards-s1b-seed1 | P_1, LINE, SPAN (seed 1) + data | 0.019 |
| 56611889 | claude-spancards-s1b-seed2 | P_2 (attempt 2), LINE, SPAN (seed 2) + data | 0.019 |
| 56601518 | claude-spancards-s1-seed0 | data only (attempt 1) | 0.014 |
| 56601519 | claude-spancards-s1-seed1 | data only (attempt 1) | 0.060 |
| 56601524 | claude-spancards-s1-seed2 | P_2 (attempt 1) + data | 0.031 |

Weights were not pushed (house rule). Keeping or destroying these boxes, and retrieving any checkpoint, is a
coordinator ruling (Q160 (4) keeps P_2 until Stage 1 completes, which is now).

### Rulings on the final report (coordinator)
- **Q192 (Cell B):** no override. Cell B stays not funded, per sealed SC-1 section 4. Any redesign starts as a new
  pre-registered card.
- **Q193 (stopped boxes):** first retrieve the attempt-2 checkpoints needed for the sealed P1/P2 scoring, file them
  where the scoring can reach them, verify their hashes and report what was retrieved. Do **not** destroy the boxes:
  that is Ben's call; the coordinator recommends destroying them once retrieval is verified. Stage 1 actuals are
  recorded in the funding ledger at $7.98 of the $18 stop.

### Q193 retrieval: status (2026-10-19, nothing retrieved yet)
**Needed for P1/P2 (Cell A on E1):** the six attempt-2 arm checkpoints (each a `state.pt` plus `config.json`):

| seed | arm | box | path | state sha256 | config sha256 |
|---|---|---|---|---|---|
| 0 | LINE | 56611901 | artifacts/span-stage1/20261018T201349Z/seed0/line | 788ed4485cd3d4e3766cbc78578f660a62a894b31292675da902394d6ca1ca6e | 69b069311675ef35c69a080db7fcdfc73f0e71a6ed3a781ebd9783dc298df5f3 |
| 0 | SPAN | 56611901 | artifacts/span-stage1/20261018T201349Z/seed0/span | c36224318ef9aade7ca83d515aa9eabb8733d76c7c8d66300daba3eeaea8c0fa | 68391c1ade57275b9e2ab48eb832b88ca7af55180fadaf548b9a065c32a29633 |
| 1 | LINE | 56611888 | artifacts/span-stage1/20261018T201824Z/seed1/line | edfbf50c5b7bca6d46d0ee02dcccdb133c6a964ea16bc4859bd8e8aad8a1fc35 | d0592b417bcf0aee8eb80412d2e513d3cfb9643c7ff72e5dff9a7f7504f08627 |
| 1 | SPAN | 56611888 | artifacts/span-stage1/20261018T201824Z/seed1/span | b115f29af975ad76968b4caf47cea0c0b06321d6fa8c9b1fb5a4e97a5744ddf9 | 31f1de88736bbd2b70fee7dc42f8f8aaed3928d0cfb4b7450cb52d71ee54dec5 |
| 2 | LINE | 56611889 | artifacts/span-stage1/20261018T201637Z/seed2/line | e1b5a961fe669b561fd431f3d1981c25281339ac2377387070c02a887ddf2673 | 1fb3dbc33f7cefce7e4427fe9b1852d17092c58f7d4d3aba61e07d26b0cdcdd9 |
| 2 | SPAN | 56611889 | artifacts/span-stage1/20261018T201637Z/seed2/span | a7b601bab9170e1cf8f3f873daadbdafac45e32b08a2d0ad1301c776a4f0e0ff | a36256e2b542993d31924f08ae6b9f3da401274cb943d8c15de94e1aedc5877f |

The hashes are the ones the boxes logged (`arm_ckpt` records). The paths are relative to `/root/tree` on each box. The
models have about 2M parameters, so each `state.pt` (weights, Adam moments, trainer state) is on the order of 25 MB.

**Why nothing is retrieved yet (shown):**
- This session cannot open a connection to the boxes: no SSH, and outbound connections to non-standard ports fail.
- The Vast account has no cloud-storage connection (`/users/cloud_integrations/` is empty), so Vast's own cloud
  copy has nowhere to send files.
- Vast's remote command on an instance allows only `ls`, `rm` and `du`.
- A stopped box can only restart with its original launch command. That reruns the pinned script: data, then the
  old pre-flight, then the go gate. The go file then said `"go": true` (attempt 2; now superseded, see below), so a restarted box would
  start training again. Before any box restarts, `stage1-go.json` must become a plain stop (`{"go": false}`). The
  script then exits at the gate without training, and the box idles.
- Weights are not pushed to the repo (house rule), and I will not put them on a public file host.

**Routes that would work (a decision for Ben or the coordinator):**
1. **A private cloud-storage connection in the Vast account** (Ben adds one under Vast "Cloud Connections", e.g. his
   Google Drive, S3 or Backblaze). Then Vast's cloud copy moves each checkpoint directory from its box into that
   storage, and the scoring reads it from there. Hashes are checked on arrival. The weights stay private, and no
   script change is needed. This is the recommended route.
2. **Score where the checkpoints are.** Run the sealed E1 scoring on a box. Vast can copy instance to instance, so the
   six checkpoints could be gathered on one attempt-2 box (plain-stop go first). This needs the sealed E1 set and a
   reviewed scoring script on that box, and the box stays rented until scoring is done.
3. **Through the box log** (the channel the readout used). This needs a new box script that prints each file in
   chunks, run on a new rental after an instance-to-instance copy. About 150 MB of base64 over the log API is slow and
   untested at that size, and it means writing and reviewing a new script.

The boxes are held, stopped, as ruled (about $0.16/h of disk).

### Go file set to a plain stop (coordinator safety ruling, Q195 follow-up)
`design/span-cards/stage1-go.json` is now `{"go": false, ...}`, a plain stop with only a note (commit 8d7e675a5,
served on the branch's raw URL). A restarted box still reruns the pinned script's data step and old pre-flight. At the
go gate, `wait_for_go` sees `go: false` with no script/code hash and no seed list, which the script reads as "a plain
stop": it raises `SystemExit("the go file says stop")` before any training. Checked locally against the pinned
script (sha256 47577a35...d127): `wait_for_go` on this file raised exactly that `SystemExit`. The boxes stay
stopped; the retrieval route is Ben's decision.
