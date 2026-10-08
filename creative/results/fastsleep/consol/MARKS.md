# Consolidation sleep: pass marks (written 10-08 about 11:20 AM ET, before any sleep run in this folder)

Ben's ask (10-08): a sleep that (a) absorbs the day's finds in very few updates, (b) loses no old skills, (c) ideally improves old skills
through transfer. Code: `creative/consol.py`. Literature and the three candidates: `LIT.md`.

## Setting (the same for every arm)

- Parents: the research loop's six, B2 s200-s205 (branch claude/b2-confirm-checkpoints, sha256 checked), each rebuilt into its N on this
  cloud CPU with `creative.fastsleep setup --T 3.0` (warm-up + stepping stones; T is only used for the setup's cached night, which no arm reads).
  The rebuild counts as correct when the warm-up and stepping-stone last losses equal `confirm/<parent>/setup.json` to 4 decimals.
- The day: the model runs its own night on 896 of the 1,024 C2 pool questions (`creative/rl/m/selfnight.py`: it picks its temperature from its
  own tries, 32 tries per question, up to 2 fitting programs per question), plus chain search (an outside tool). The other 128 pool questions
  (seeded) are held back as the model's own practice check (fit-only, no answers). Every arm on a parent sleeps on the same finds.
- Skills replay: half of every batch, fresh rows from skills TRAIN, never repeated within a night. 100 training rows per family (3,400) are held
  back as the model's own self-check and never replayed.
- Optimiser: fresh AdamW, lr 1e-3 peak, warm-up then cosine, batch 1,024 (512 day rows + 512 replay rows), as the research-loop sleep.
- Measures (never seen by the sleep): C2 DEV greedy first try (256); skills DEV in_dist (34 families x 200) for harm and transfer; the C2 research-loop
  holdout (512) only in the confirm, once per parent, for the winning arm. C2 test and labelled are never opened.
- Harm: `creative/harm_look.py` harm_measure(N, learner): fails if in_dist drops more than 1.5 points, or any family drops more than 5 points with
  its paired 95% interval below 0.
- Intervals: paired 95% bootstrap over rows (`c2_pilot.boot`); pooled over parents by concatenating (parent, row) pairs.

## Arms

- `rlc`: the research-loop sleep's data, capped: the finds + 3 execution replays per find (fixed rows, re-read across updates).
- `fd` (candidate 1, fresh dreams): every update's day half is newly made: a find's program is run by the executor on fresh inputs (from inputs the
  day showed) to write a new prompt of the same rule. No day row is read twice. One change from `rlc`.
- `scale` (candidate 2): N + a (W - N), a from {0.25, 0.5, 0.75, 1} picked by the model: the largest held practice fit rate among the a's whose
  self-check in_dist is at most 1.0 point below N's. No training.
- `fdw` (candidate 3): `fd` with the replay half weighted by family, weight = (own held-slice loss now / at the start of the night)^2, at least 1,
  re-measured every 16 updates. Run only if `fd` (and `scale`) leave harm.
- `ro`: replay-only control, the same updates with both halves skills replay. It separates "old skills improve because of the new skill" from
  "old skills improve because the night is also more practice".

## Screen A: fresh dreams vs re-read rows (s200, s201; DEV only)

`rlc` and `fd` at 256 updates, saved and measured at 32, 64, 128 and 256 updates; `ro` at 256.

- A1 (re-reading is the cause): at 128 and 256 updates, `fd`'s in_dist drop vs N is at least 1.0 point smaller than `rlc`'s, on both parents.
- A2 (no loss of learning): at the same updates, `fd`'s C2 DEV first try is no more than 2 points below `rlc`'s (point estimate), on both parents.
- **Screen A passes = A1 and A2.**
- Proved wrong (fresh rows don't help): at every saved step, on both parents, `fd`'s in_dist drop is not smaller than `rlc`'s.
- Update cap for the confirm, fixed now: U* = the smallest saved step at which `fd`'s two-parent mean C2 DEV first try is at least 71.2 (the research
  loop's DEV mean) and harm_measure passes on both parents. If no step qualifies, U* = 256 and the confirm says the speed mark is not met.

## Screen B: self-chosen scale (no training; only if `fd` at U* fails harm on a parent)

- B passes if, on both parents, the picked scale's harm_measure passes and its C2 DEV first try is no more than 2 points below unscaled `fd`.
- Proved wrong: on both parents the picked a is 1 (the model's own check never sees the harm) while DEV harm fails.

## Screen C: interference-weighted replay (only if harm remains after A and B)

- C passes if, on both parents, `fdw` passes harm_measure and its C2 DEV first try is no more than 2 points below `fd` at the same updates.
- Proved wrong: `fdw`'s in_dist drop is not smaller than `fd`'s on either parent.

## Confirm (six parents s200-s205; the winning recipe; the model stops itself)

The recipe = the passing screens' pieces, run with the model's own stop: it checks its held practice fit rate every 16 updates, stops when two
checks in a row do not beat its best, and keeps its best checkpoint; never more than U* updates. Plus `ro` at the same number of updates as the
recipe used on that parent.

1. **C2 (a): six-parent mean holdout first try at least 71.3%** (the research-loop sleep's holdout mean, 6 parents).
2. **Speed (a): at most U* updates on every parent, U* at most 256, and at most half the research-loop sleep's updates on the same parent**
   (its updates = 80 x records / 512; reported per parent).
3. **No harm (b): harm_measure vs N passes on every parent.**
4. **Old skills improve (c): skills DEV in_dist, learner - N, pooled over six parents: point above 0 and paired 95% interval above 0.**
   Labelled "through transfer" only if learner - `ro` (pooled) is also above 0 with its interval above 0; otherwise "improved, not shown to come
   from the new skill".
- Claims: (a) needs 1 and 2; (b) needs 3; (c) needs 4.
- Proved wrong (the recipe does not avoid harm): harm_measure fails on at least 3 of 6 parents.

## Report only (no mark)

- The research-loop sleep itself (`creative/rl/method.py`, full budget, unchanged) re-measured with harm_measure on s200 and s201 (DEV),
  if the CPU has room: its real harm, which the pooled-5 guard never measured.
- Compute per night: updates, rows, CPU seconds; held-check curves.
