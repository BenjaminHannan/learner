# Skill-Sleep 1 results (2026-10-25, one seed)

Labels: shown = measured here; suggested = a reading of the numbers that this run cannot prove.
Run: Vast RTX 5090 box 57702325 (second box; the first, 57686593/57686980, hung on a bare-`wait` bug after the
day and was thrown away). Raw files: skillsleep/results/. Wall 2.05 h. Cost about $2.18 for the three boxes (cap $2.50).

## The day and the night (shown)
- Day: K2-Horizon-3.7B passed 99 of 148 retail-train runs (67%); 61 of 74 tasks passed at least once.
- Fix: 13 tasks never passed. 13 got a Sonnet critique, and 33 hinted retries passed 9 times, which fixed 5 tasks.
- Night lessons: 108 positives, 33 pass/fail pairs, 16 lone negatives. None was over 16k tokens.
- Training: 54 optimizer steps per arm, peak 19.6 GB (A2). The probe NLL went from 0.533 (base) to 0.524 (A1) and 0.525 (A2),
  so the model moved only a little. The A2 DPO loss fell from 0.69 to about 0 within about 10 steps: the 33 pairs were
  learned quickly.
- Every eval was complete: 160/160 retail and 40/40 airline sims per arm, all ending in user_stop, with no infra or 429 errors.
  Each arm's own model was served; per-task results differ between arms.

## Next-day test (shown)
| arm | retail test (40 tasks x 4) | airline test (20 x 2) | ARC-Easy 200 |
|---|---|---|---|
| A0 no sleep | 63.7% (102/160) | 60.0% (24/40) | 71.0% |
| A1 good only | 68.1% (109/160) | 52.5% (21/40) | 71.0% |
| A2 good + bad | 66.9% (107/160) | 57.5% (23/40) | 71.0% |

Paired sign-flip test over tasks: retail A2-A0 +3.1 (p=0.57), A1-A0 +4.4 (p=0.38), A2-A1 -1.2 (p=0.88).
On the first box, the same A0 setup (sharing the GPU with the day) scored 99/160, so run-to-run noise is about 3 points.

## Verdicts (pass marks from PREREG.md)
- P1 sleep teaches skill (A2 >= A0+6, p<0.05): FAIL. The gain is +3, which is inside the noise.
- P2 bad examples add something (A2 >= A1+4): FAIL. A2 is 1 point below A1, also noise.
- P3 skills carry over to airline (label only): FAIL. A2 is 2.5 points below A0 (one task on 40 runs).
- P4 no harm: PASS. Airline is within 7.5 points, and ARC is unchanged (same answers on all 200).
- Wrong-if lines: neither triggered. A2 is not <= A0, and A2 is not below A1 by more than 4.
So this run does not show that one night of sleep improves skills. It also does not show that sleep can't do it.

## Why so small (suggested, untested)
1. Dose. 54 LoRA steps barely changed the model (NLL -2%). In the memory sleep work, night length was the biggest lever (4x work).
2. Copying its own wins teaches little. 61 of 74 tasks already passed, so most positives show what the model already does.
   The new behaviour sits in the 13 tasks it failed, and only 5 of those were fixed.
3. The 33 DPO pairs were separated fast and then gave no gradient, so A2 got little extra signal from the bad runs.
4. Power. With 40 test tasks, the test can only detect gains of about 8 points or more.

## Next, one change at a time
Night x4 (EPOCHS 8, same data) on A1 and A2, with the same test. Pass if A2 >= A0 + 6 points with p < 0.05, using the same
A0. It is wrong if the probe NLL keeps falling but retail stays within 3 points of A0. After that: several
days (more failed tasks to fix) and a batched Sonnet critique (Message Batches API).

## Input for Skill-Sleep 2 (coordinator, 21:43Z, from Ben's question on why good+bad didn't beat good-only)
The pairs were too easy (DPO loss ~0 within 10 steps) and too few (33 pairs, 16 negatives). Keep one change per arm:
- Arm 1: night x4 only (same data).
- Arm 2: night x4 + near-miss pairs. Good and bad share a prefix and differ at one decision step, e.g. fork points
  from Doubt Forks (resample the model's next turn at an uncertain step and let tau2's check score each branch).
  Use many more of them. Log the DPO margin and accuracy per step, and if they saturate (loss < 0.05 for 10 steps),
  report it as saturated rather than as learning.
Same A0, same test, and pass marks fixed before the run.
