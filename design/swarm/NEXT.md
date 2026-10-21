# Swarm screen: where it stands, for a fresh session (2026-10-21)

**State: PARKED with Ben, awaiting the coordinator's design recommendation. No code is pending. No box is
running. Nothing has trained, and no swarm accuracy result exists.** Spend: about $1.19 of the $5.25 total approved
(run 1 $0.36, run 2 $0.47, run 3 $0.36).

Read first: `RUNCARD-S0.md` (sealed; see its amendments and the run-3 re-seal), then
`RUN1-C0-STOP-2026-10-20.md`, `RUN2-C0-STOP-2026-10-20.md` and `RUN3-C0-STOP-2026-10-21.md`.

- The sealed PIN is 5917746e5bd4528b5741a92590586b714c728da4; the code is at 34a82da7a.
- The box is `scripts/premonition_swarm_box.sh`, rented by `scripts/claude_swarm_rent.py`.
- Coordinator: session_018Ybowk1FLjHVsZsWFonjEk.

## What the three runs established (all on RTX 4090 24 GB boxes, before any training)

1. **Run 1:** D1 reserved 14.98 GiB in gold mode, above the 14 GiB guard. This was allocator fragmentation:
   with `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` (set in the rental job, every arm), the same bench needs much
   less memory.
2. **Bench memory (runs 2 and 3, guard-free probe, peak allocated / reserved in GiB):**
   - D1: gold 5.61 / 6.80, teacher 5.61 / 7.83, own 6.74 / 8.95.
   - S0m4: gold 6.09 / 8.20, teacher 9.29 / 9.63, own 9.35 / 9.44.
   - S0m8 (optional) trips the guard, at 15.33 GiB in teacher.
3. **Speed:** T_raw 4,408 s (run 2) and 3,544 s (run 3), so **T = 3,600 s** (the cap). The steps-in-T ratio S0m4 / D1
   is about **0.85**: S0 gets slightly more updates than D1, far below the 2.5 stop line.
4. **Run 3, the decisive one:** C0's S0 train-overhead probe ran in a fresh subprocess with per-phase memory logging.

   | phase | allocated | reserved |
   |---|---|---|
   | start | 0.01 | 0.03 |
   | **calibration** | **14.28** | **14.43** |
   | first training step | **5.67** | (14.43, still held from calibration) |
   | validation | 1.21 | — |
   | save | 0.05 | — |

   **S0's FLOP calibration inside `train_d`** needs 14.28 GiB allocated. It runs `trainer.calibrate(head)`: 4 head
   batches at 55,000 tokens × 3 modes, FlopCounterMode, forward + backward. S0's real training step needs 5.67 GiB.
   The guard checks after step 1 and sees the calibration's peak, so **every registered S0 train would abort at
   step 1.**
5. **In the code:** under a seconds budget the FLOP fit steers nothing. Phases follow training time, and the FLOP
   budget is 1e30. It only does FLOP accounting, but `MiniTrainer.train` refuses to start without a fit
   (`premonition/train.py:310-311`, `392-393`).

**D1's calibration memory was never measured.**
- C0 runs `d1.calibrate(fixed[:4])` in-process for T's FLOP fit (`scripts/premonition_swarm_screen.py:683`). It
  completed in runs 2 and 3 (no CUDA OOM on 24 GB), but no peak was logged and no guard was checked.
- The D1 train-overhead probe never ran: each run's S0 probe ran first and aborted C0.
- So it is unknown whether real D1 trains would also trip the guard at step 1 through their calibration.

## Options (the coordinator recommends; Ben decides; none taken)

1. **Calibrate on smaller pieces of the head batches** (the swarm session's lean). The fit is linear in tokens and
   question-loops, so this changes only the reported FLOPs, not training or the guard.
2. **Reset the CUDA peak after calibration in `train_d`,** so the guard covers training steps only. This narrows
   the guard's scope; the coordinator has kept the guard unchanged so far.
3. **Give S0 trains a fit from elsewhere.** Not equivalent: S0's per-question cost differs.
4. **Stop the screen here.**

Every code option needs a re-seal, a $0 CPU dry run and a review round. Any further box needs Ben (coordinator ruling:
"a box-3 stop before training parks the line with Ben").

## The exact marks

**Registered for run 3** (RUNCARD-S0 re-seal amendment; outcome: proved wrong):
- **Pass:** the fresh-process S0 probe completes under 14 GiB, C0 finishes with D1 and S0m4 under 14 GiB, and c0.json
  is written.
- **Proved wrong:** the fresh-process probe trips again. Then S0's real training step or calibration needs the memory:
  exit 3, stop, and the line goes to the coordinator for a design review. **This happened.**
- Any other stop is exit 3, stop and report. The 14 GiB guard is unchanged, and raising it was declined.

**Suggested for a next attempt** (not registered; the coordinator fixes these):
- **Pass:** S0's and D1's calibration phases peak under 14 GiB reserved in the fresh-process probes, both probes
  complete, C0 finishes and writes c0.json, and then the trains run.
- **Proved wrong (option 1):** S0's calibration still peaks at or above 14 GiB on the smaller pieces, which would
  mean the cost is not batch size.

The card's science marks (M1-M6 on far_deep, near and overall) are unchanged and untouched: no S0 result has been read.

## Notes the fresh session needs (added 2026-10-21, swarm session on stand-by)

- **Money:** Ben approved the calibration fix at a total of about $5.60, including the $1.19 already spent.
- **T depends on the same calibration.** C0 computes T from `d1.calibrate(fixed[:4])`
  (`scripts/premonition_swarm_screen.py:683`) through `curriculum_flops(fit, ...)` and `t_raw_from_modes`. Changing
  `MiniTrainer.calibrate` itself therefore also changes T's FLOP fit.
  - The past T_raw values were 4,408 s and 3,544 s, both giving T = 3,600, because T = min(3600, 300·⌈T_raw/300⌉).
  - A fit that moves T_raw below 3,300 s would change T.
  - Either leave C0's T fit untouched (change only `train_d`'s calibration), or declare the change on the card before
    the run.
- **D1 too:** D1's calibration peak has never been measured. A fix and its marks should cover D1's probe as well as
  S0's. The probes run in the order S0 then D1, and an S0 abort stops C0 before D1's probe runs.
- **Practical lessons from runs 1-3:**
  - After a re-seal, bump `PIN` in `scripts/claude_swarm_rent.py`, and check that GitHub serves the new sha.
  - Run `git status -sb` before every push: a review run once left the repo on a detached HEAD, and three commits
    silently went unpushed.
  - Vast offer ids rotate within seconds, so book with `rent()` straight from a search.
  - The controller destroys a box whose billed rate is above the box's DPH.
  - Price the 80 GB disk into the search (`allocated_storage`).
  - Require ≥ 12 effective cores: the data step runs `min(12, cpu_count - 1)` workers.
  - Vast `execute` works only on stopped instances. Box progress is invisible until the job prints `SWARM EXIT`, so
    watch the container log and the GPU/CPU heartbeat.
  - The data build takes 35-47 min and is not reusable (it is rebuilt on every box).
  - On exit 3 the job also writes `checks/memprobe.json`, with bench memory per arm and mode.
