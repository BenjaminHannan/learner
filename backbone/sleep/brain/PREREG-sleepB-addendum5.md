# Sleep-B addendum 5: sleep that adapts to the hardware (written 2026-10-24 ~18:50Z, before any addendum-5 code or run)

Labels: shown / suggested / untested. Same model (Qwen3.5-2B), week, tests, scoring, seed (1), step schedule and open-book
rehearsal as addenda 2-4. Not the village model, not the card experiments.

## Why (Ben, 18:42Z)
"Are we able to change it so that sleep is ... adaptive to the GPU, or is it just one constant ... process? So for example, if we
have a stronger GPU, sleep can be more effective with the time it's allotted."

Today a night's work is fixed: the AB stage-1 schedule sets the training steps, and fixed caps set the dreams (4 paraphrases and
4 Q&A per item, at most 160 items, 30 REM chains and 30 gist dreams). A faster chip finishes sooner and then sits idle.

## Design: a time-budgeted night
- The night gets a time budget B (seconds), the window the device can spare.
- At the start of sleep, the scheduler times a short benchmark on a fixed synthetic batch. This takes a few training steps without
  an optimizer step, plus one generation batch, and it touches no model weights or random streams. From these timings it
  estimates R, the seconds that the reference night (the fixed schedule above) would take on this chip.
- Work scale s = clip(B / R, 0.25, 4). Every knob of the night is multiplied by s:
  - training steps (the schedule's steps x s; lr stays cosine over the night's steps);
  - dreams per item (paraphrases and Q&A, round(4 s) each);
  - the item cap (160 s), REM chains (30 s) and gist dreams (30 s).
- The morning gate is unchanged. A night that hurts ARC or consolidated recall is undone, whatever its size.
- At s = 1, the night is exactly the reference night. The code must reproduce `ab_ob` bit for bit at s = 1, checked by a CPU smoke.
- For the experiment, `--budget-scale` pins s, so the result does not depend on timing noise. The timing path gets its own unit
  test: given fake timings, the scheduler must return the expected s.

## Arm
- **ab_ob_b2, "a chip twice as fast, same hours":** ab_ob with s = 2. That gives twice the training steps and twice the dreams per
  item, with the item cap, REM chains and gist dreams doubled too. It is one change from ab_ob: the night's work budget.
- **Control:** the seed-1 `ab_ob` (s = 1). Weights only: recall C2+C4 56, integration 47, changed-new 70. With the diary: pooled 82.
  ARC-Easy: 92.4.

## Pass marks (fixed now)
- **B1 memory:** recall >= 61 (control + 5).
- **B2 no harm:** ARC-Easy >= 87.6 and diary pooled >= 77.
- **B3 integration:** integration >= 43 (control - 4).
- **Wrong if:** recall <= 56. Doubling the night's work then adds nothing, and adapting to a faster chip would only fit the
  window, without making sleep better.
- **Reported, not marked:**
  - Wall time per night, which should be about 2x the control's.
  - Steps, dreams kept and items dreamed per night.
  - Gate reverts.
- One seed. Any gap under 4 points is not called shown.
- Untested here, next: s = 0.5 ("a slower chip such as the Mac"). This would show how much a weaker device loses in the same
  hours.

## Evidence so far (suggested)
- Sleep-B stage 2: switching Ben's rule off trained on more items for more steps, and it scored best overall (53 from memory, 77
  with the diary). That is a hint that more work per night helps, but the comparison was not clean.
- Multistep thread: more sleep nights raised Hard accuracy, from 10% at 2 nights to 17% at 4.

## Compute
- One Vast A100 40GB box, about 1.5-2 hours, under $1. It goes on the same box as, or right after, the addendum-4 arms.
- The box is destroyed as soon as its result reaches its label.
