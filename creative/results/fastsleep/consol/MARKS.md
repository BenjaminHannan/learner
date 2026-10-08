# Consolidation sleep: pass marks (written 10-08 about 11:20 AM ET, before any sleep run in this folder)

Ben's ask (10-08): a sleep that (a) absorbs the day's finds in very few updates, (b) loses no old skills, (c) ideally improves old skills
through transfer. Code: `creative/consol.py`. Literature and the three candidates: `LIT.md`.

## Setting (the same for every arm)

- Parents: the research loop's six, B2 s200-s205 (branch claude/b2-confirm-checkpoints, sha256 checked), each rebuilt into its N on this
  cloud CPU with `creative.fastsleep setup --T 3.0` (warm-up + stepping stones; T is only used for the setup's cached night, which no arm reads).
  The rebuild counts as correct when the warm-up and stepping-stone last losses equal `confirm/<parent>/setup.json` to 4 decimals.
  Outcome (10-08): not met. s202 warm-up 1.4104 = 1.4104, but stepping stones 0.5141 vs 0.5151; s201 warm-up 1.2657 vs 1.2568, stones 0.4661 vs 0.4492.
  The rebuilt N are close to, not equal to, the research loop's (single-batch losses after 256 updates on different CPUs and thread counts).
  Every arm here shares the same rebuilt N, so the paired comparisons are unaffected; the comparison with the stored 71.3% is between near-copies.
- The day: the model runs its own night on 896 of the 1,024 C2 pool questions (`creative/rl/m/selfnight.py`: it picks its temperature from its
  own tries, 32 tries per question, up to 2 fitting programs per question), plus chain search (an outside tool). The other 128 pool questions
  (seeded) are held back as the model's own practice check (fit-only, no answers). Every arm on a parent sleeps on the same finds.
- Skills replay: half of every batch, fresh rows from skills TRAIN, never repeated within a night. 100 training rows per family (3,400) are held
  back as the model's own self-check and never replayed.
- Optimiser: fresh AdamW, lr 1e-3 peak, warm-up then cosine, batch 1,024 (512 day rows + 512 replay rows), as the research-loop sleep. On this CPU
  each 1,024-row update is computed as 4 to 16 backward passes of 64 to 256 rows, row-weighted and summed into one optimiser step
  (a 1,024-row pass needs about 9 GB). The research loop did one 1,024-row pass on a GPU. The two give the same mean when the loss is a per-row mean.
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
- `rp` (transfer control; replaces `ro`, amended below): the learner's exact skills replay rows (same rows, same order, 512 per update), the
  day half removed: batch 512, same updates and schedule. It separates "old skills improve because of the new skill" from "because the night
  is also skills practice". `ro` (both halves skills replay, twice the replay rows) is dropped: it was never run, and it would have made
  "learner - control > 0" a much stronger bar than transfer.

## Screen A: fresh dreams vs re-read rows (s201, s202; DEV only)

Amended 10-08 12:05 PM ET, before any Screen A run: parents s201 and s202 instead of s200 and s201, because s200's rebuild stalled and was restarted
(about 45 minutes behind). No result of any arm existed when this was changed.

Amended 10-08 11:40 AM ET, before any sleep run: one update takes about 80 CPU-seconds, so Screen A stops at 128 updates.
`rlc` and `fd` with a 128-update schedule, saved and measured at 32, 64 and 128 updates (the 32 and 64 snapshots are mid-schedule, at a higher
lr than a 32- or 64-update sleep would end on); `rp` at 128 (batch 512).

- A1 (re-reading is the cause): at 64 and 128 updates, `fd`'s in_dist drop vs N is at least 1.0 point smaller than `rlc`'s, on both parents.
- A2 (no loss of learning): at the same updates, `fd`'s C2 DEV first try is no more than 2 points below `rlc`'s (point estimate), on both parents.
- **Screen A passes = A1 and A2.**
- If `rlc` itself shows little harm (its in_dist drop is under 2.0 points at 128 updates on either parent), A1 cannot be tested. Then Screen A
  is "not testable", not "proved wrong", and the confirm uses `fd` if `fd` passes harm_measure on both parents and its C2 DEV first try is
  within 2 points of `rlc`'s at 128 updates (point estimate); otherwise `rlc`.
- Proved wrong (fresh rows don't help): at every saved step, on both parents, `fd`'s in_dist drop is not smaller than `rlc`'s.
- Update cap for the confirm, fixed now: U* = the smallest saved step at which `fd`'s two-parent mean C2 DEV first try is at least 71.2 (the research
  loop's DEV mean) and harm_measure passes on both parents. If no step up to 128 qualifies, `fd` is rerun with a 256-update schedule (saves at 192,
  256) on both parents, and the same rule picks U* from those. If still none qualifies, U* = 256 and the confirm says the C2 or harm mark is not
  expected to be met.

## Screen B: self-chosen scale (no training; only if `fd` at U* fails harm on a parent)

- B passes if, on both parents, the picked scale's harm_measure passes and its C2 DEV first try is no more than 2 points below unscaled `fd`.
- Proved wrong: on both parents the picked a is 1 (the model's own check never sees the harm) while DEV harm fails.

## Screen C: interference-weighted replay (only if harm remains after A and B)

- C passes if, on both parents, `fdw` passes harm_measure and its C2 DEV first try is no more than 2 points below `fd` at the same updates.
- Proved wrong: `fdw`'s in_dist drop is not smaller than `fd`'s on either parent.

## Confirm (six parents s200-s205; the winning recipe; the model stops itself)

The recipe = the passing screens' pieces, run with the model's own stop: it checks its held practice fit rate every 16 updates, stops when two
checks in a row do not beat its best, and keeps its best checkpoint; never more than U* updates. Plus `rp` at the same number of updates as the
recipe used on that parent.

1. **C2 (a): six-parent mean holdout first try at least 71.3%** (the research-loop sleep's holdout mean, 6 parents).
2. **Speed (a): at most U* updates on every parent, U* at most 256, and at most half the research-loop sleep's updates on the same parent**
   (its updates = 80 x records / 512; reported per parent).
3. **No harm (b): harm_measure vs N passes on every parent.**
4. **Old skills improve (c): skills DEV in_dist, learner - N, pooled over six parents: point above 0 and paired 95% interval above 0.**
   Labelled "through transfer" only if learner - `rp` (pooled) is also above 0 with its interval above 0; otherwise "improved, not shown to come
   from the new skill".
- Claims: (a) needs 1 and 2; (b) needs 3; (c) needs 4.
- Proved wrong (the recipe does not avoid harm): harm_measure fails on at least 3 of 6 parents.

## Report only (no mark)

- Harm of every learner against the raw B2 parent as well as against N (the build costs about 2.7 in_dist points; harm_measure vs B2).
- The research-loop sleep run on the same rebuilt N (`creative/rl/rescore_harm.py`): its C2 and its harm_measure with the new rule, as the paired
  baseline for the 71.3% bar. Needs a GPU or about 7 CPU-hours per parent.
- The research-loop sleep itself (`creative/rl/method.py`, full budget, unchanged) re-measured with harm_measure on s200 and s201 (DEV),
  if the CPU has room: its real harm, which the pooled-5 guard never measured.
- Compute per night: updates, rows, CPU seconds; held-check curves.

## Amendments after Screen A started (10-08 about 1:30 PM ET; no `ro`, `rp` or DEV snapshot had been read)

- `ro` replaced by `rp` (above); the fall-back rule for a harmless `rlc` (above); harm vs B2 and the research-loop re-score are report-only.
- Memory, not a mark: dream targets are dropped from the target cache after each update, and runs are capped at three at once (cgroup limit
  13.4 GiB). Neither changes any computed value.
