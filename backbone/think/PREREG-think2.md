# Think-2 preregistration: train the LoRA and the thinking block together (1-seed pilot, Ben's PC)

Written 2026-10-25, before any Think-2 run. Follows Think-1 (`PREREG.md`, `RUNLOG.md`): G-STS was refuted (S(8) 67.0,
laps flat, swap lesion ~0) while plain LoRA given the same 1,254 extra steps reached 70.8 (aplus, 3 seeds).

## The one question
Think-1 froze the backbone and arm a's LoRA, so nothing could learn to read the notes. Does training the LoRA **jointly**
with the block let the notes pay off, compared with plain LoRA given the same extra steps?
This is the last pilot of looped latent thinking on this setup. No other variants run.

## Arms (seed 0 only, all on Ben's PC, RTX 5070 Ti, bf16)
| arm | what it is |
|---|---|
| a | LoRA, 418 steps (stage 1, rerun on the PC because Think-1's adapters were not recovered) |
| aplus | a's adapter, LoRA trained 1,254 more steps (the control) |
| tj | a's adapter, LoRA **and** a new G-STS block trained together for 1,254 steps, laps 0..4 |

tj's loss per batch = aplus's loss (same full forward, no board) + the Think-1 board loss (answer CE at every lap
t = 0..4, read from board t, plus 0.01 x the update penalty). So tj gets every gradient aplus gets, plus the block's.
Same batch order as aplus, same LoRA learning rate and schedule; board learning rates as Think-1. L_max fixed at 4
(Think-1: 4, 8 and 12 laps scored the same, and 4 laps fit the PC's time budget).

## Scores (validation, 8,675 rows, greedy exact match)
- S(L): tj with the board read after L laps; L in {0, 1, 4}.
- gatesoff: tj's LoRA with gates at zero (what the joint LoRA learned on its own).
- swap: row reads the board of a different story at L = 4.
- A+: aplus.

## Pass marks (fixed now)
- **P1 gain:** S(4) - A+ >= +2.0 points, and the paired bootstrap 95% interval excludes 0.
- **P2 notes used:** S(4) - swap >= +1.0 point.
- **P3 laps (reported, needed only to call it "looped thinking"):** S(4) - S(1) >= +0.5.

## Decision rule
- P1 and P2 pass: run seeds 1 and 2 (same PC) before any claim. P3 then decides whether it is looping or just a note pad.
- Anything else: **stop**. Report, and drop looped latent thinking for v2 (spend the effort on plain LoRA training,
  which Think-1 showed still had +4 points left).

## Wrong-if (the result that refutes the idea here)
S(4) - A+ < +1.0, or the swap lesion costs < 0.5. Either means the block, even with a trainable reader, adds nothing a
LoRA cannot get from the same steps.

## Known biases, stated in advance
- tj gets more compute per step than aplus (extra slot and answer passes). This favours tj, so the +2.0 bar is deliberately
  higher than Think-1's noise (re-scoring 0.2, aplus seed spread 0.4).
- One seed: a pass is a signal to expand, never a result.
- Hardware differs from Think-1 (5070 Ti vs 5090); only within-PC comparisons count.

## Addendum A (2026-10-25 14:20Z, before any tj result): arm tf, forced then released
Added at Ben's request ("why not force the notes to get used?"). Runs on the PC right after tj, seed 0, whatever tj scores.
- tf = tj plus blind answer passes in the board loss: with probability p(step) = 0.5 x max(0, 1 - step / (0.6 x 1,254)),
  a micro-batch's answer passes see no prompt at all, only the notes (the slot laps still read the full prompt).
  The aplus loss is never blind. From 60% of training on, nothing is blind.
- Extra readout: blind(4), answers that see only the notes, on the first 2,000 validation rows (how much the notes carry alone).
- Pass marks: the same P1 and P2 as tj, against the same aplus. tj and tf are judged separately. Passing either one
  triggers the 2-seed expansion for that arm only. If both fail, looped latent thinking stops as planned.

## Addendum B (2026-10-25 16:15Z, before any tj or tf result): control arm tc
A review (bug-hunt thread) pointed out that tj's LoRA gets more than aplus's: the aplus loss PLUS the board-path answer CE,
which with closed gates is a second copy of the answer gradient taken through another path. So aplus is not a clean control.
- tc = tj's exact loss and loop with the block switched off: lmax 0, gates frozen at 0, no block parameters trained.
  It gets tj's extra LoRA gradient without anything the notes could carry. Seed 0, PC, queued after tf.
- P1 for tj and tf is now judged against B = max(aplus, tc): S(4) - B >= +2.0 with the bootstrap interval excluding 0.
- P2 is unchanged. A P1 pass with P2 failing is reported as "suggested", not a pass.
- Diagnostic: the LoRA gradient norm before clipping (gn_lora) is logged for tj against aplus's, to see how often the clip engages.

## Addendum C (2026-10-26 00:20Z, before any tj, tf or tc result): give-up rule
Decided by the coordinator under Ben's never-wait rule, after design/research/2026-10-25-think-inner-state-codi.md
(PR #131) showed that a Think-2 fail cannot separate "the loop is useless" from "the notes were never taught".
- If Think-2 fails (neither tj nor tf passes): do NOT drop looped thinking yet. First run PR #131's checks 0-5
  (data check, free P0 diagnostics, toy plumbing check, written-steps teacher + filler sham, gate start 0.3 if the gate
  stayed shut, step-supervised notes), plus its hide-the-story and copy-the-teacher tests if their entry conditions
  are met. Then apply PR #131's give-up rule (every notes test misses a bar, or 18 Think-2-sized runs spent with no pass).
- If Think-2 passes: the 2-seed expansion runs as planned, plus the free checks and the swap test before calling the notes used.
- Recorded for the P0 code reads: Think-1's block trained at refiner/e0/eta lr 5e-4 and gate lr 3e-3 for 1,254 steps.
  tf hides the story with a separate answer pass on a fresh, empty cache, so there is no DeltaNet state leak (a CPU test
  shows blind logits are unchanged when the prompt changes).
- Think-1 checkpoints were never recovered (Vast file copy failed), so P0 runs on Think-2's tj/tf checkpoints.

## Addendum D (2026-10-26 22:00Z, before any toy-0.3, P1, P2a or P2b result): optional JOLT+ arm
Raised by Ben ("use JOLT+"). JOLT+ = on-policy distillation: the student samples its own answer after its laps, and the
loss is reverse KL to a better teacher on those tokens (plus an exact-match reward term), as in Think-3 Addendum A.
- It needs a teacher that is clearly better than answering directly, so it runs only if P1 opens P4
  (T >= max(tc, C1) + 2 and T >= sham + 1). Teacher = the ws model writing its steps; student = the P4 notes arm.
- It is an extra P4 arm `jolt`, run after P4's matching arm, from the same start checkpoint with the same steps.
  Marks: P4's marks, plus J1: S_jolt - S_P4 >= +2.0 (interval excluding 0) to count as better than matching alone.
- It never replaces a P4 or P2b verdict, and its runs count toward the 18 R cap.
