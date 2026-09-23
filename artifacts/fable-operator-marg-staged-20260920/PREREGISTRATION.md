# Canonical-operator variant `marg-staged` — delay the marginal, change nothing else

Written 2026-09-20 EDT, before any `marg-staged` run. Drafted by the build agent from
Ben's brief. **Review and amend before running `freeze`: `freeze` hashes this file and
`check_manifest` re-verifies the hash before every worker and every wave.**

## The question

Two results sit next to each other on the same curriculum, same seeds, same everything else:

| run | one-hop train acc @ 6000 | notes |
| --- | --- | --- |
| `grow-blind`, seeds 0/1/2 | 1.00, 1.00, 1.00 | perfect lookup; reaches 1.0 by update ~1,500–3,000 |
| `marg-full --startup grow-blind`, seeds 0/1/2 | 0.156, 0.188, 0.125 | never exceeds ~0.4 at any point; mean marginal probability 0.220 / 0.238 / 0.213 |

`grow-blind` builds its LINK and terminal single-call records from gold intermediates;
`marg-full` removes them and trains the two-hop path only through the exact marginal
`-log sum_e P(e | S, x, LINK) * P(y | S, e, r)`. The result is not merely "the composition
did not form" — **even the one-hop attribute lookup never forms**, which it does reliably
without the marginal term. Something about the marginal term at update 0 is destroying the
lookup that everything else depends on.

Hypothesis (i): **the marginal term is pure noise until the terminal attribute lookup is
sharp, and it dominates the shared weights.** At initialisation `p1` is near-uniform over
the sixteen entity tokens and `P(y | S, e, r)` is near-chance for every `e`, so
`-log P(y)` has no usable direction; its gradient flows into the same embedding, memory and
readout weights the one-hop CE is trying to shape, at a third of the total weight, every
update, from the very first one.

`marg-staged` tests exactly that: **withhold the marginal term until the lookup has had
time to form, then switch it on at full strength.**

## The change

**ONE change vs `marg-full --startup grow-blind`.** The marginal two-hop term carries
weight **exactly 0** for updates `< M` (`--marg-start`, default **2500**) and its normal
weight from `M` on. Hard switch, no ramp, no warm-up.

* Before `M` the loss is `w1 * one_hop_CE + w3 * monolithic_CE`, where `w1` and `w3` are
  **the record weights `marg-full` computes on the same batch** — the marginal term is
  *removed*, not renormalised away. At 16 visits that is `(1/3) * one_hop + (1/3) *
  monolithic`. The check suite asserts this equals `marg-full`'s loss with the marginal
  term dropped, on the same batch, to 0.0e+00.
* From `M` on the step is `marg-full`'s step **verbatim** — the code literally calls
  `fable_operator_startup.margfull_losses`. The check suite asserts one update at `M`
  leaves parameters bit-identical to `marg-full`'s update on the same batch.
* Monolithic records are kept exactly as `marg-full` has them: answer cross-entropy on the
  full two-hop question `[4, x, 11, r, 5]`. That is label-free (no intermediate, no
  supporting line) and it is the only two-hop signal in the loss before `M`.
* Before `M` the LINK call and the 16-way terminal expansion are **not forwarded during
  training**, which is where the time is saved. FLOPs count only the forwards actually
  performed; `training_flops` drops from 4.26 to 0.56 GFLOP/update in the pre-`M` phase.

`M = 2500` is chosen so the switch lands after the curriculum has grown most of the way
back (`G1 = 1500`, `G2 = 3000`, so the story is at 2/3 of full size at `M`) and after the
window in which `grow-blind` reaches a perfect lookup (~1,500–3,000).

**Everything else is `marg-full --startup grow-blind` unchanged**: same runner, model,
init, AdamW, clipping, v3r lr decay, `random.Random(1101)` world stream, 6,000 updates,
16 visits per update, `--blind-lines 16` of the 24 fact lines grown back over [1500, 3000),
both EXACT reductions (`--terminal-dedupe`, `--single-forward`) on, `--marg-visits 0` (all
16 visits marginalised, no approximation), `--balance` off, the same ten panels and cutoffs,
final-checkpoint-only scoring.

The curriculum RNG is deliberately `random.Random("fable-startup-marg-full:<seed>")` —
`marg-full`'s **own** namespace, not this module's — so the story subsets and every
constructed record are identical to `marg-full --startup grow-blind` batch for batch. The
check suite verifies the first 20 batches and the final world-RNG state agree exactly. The
"one change" claim is therefore literal, not statistical.

## HONESTY: what is and is not supplied

**Supplied to the model during training:**

* the visible story (a random subset of fact lines early, the full story from update 3,000);
* the visible question tokens;
* **the final answer** of every record (one-hop, monolithic two-hop, and the marginalised
  two-hop target `y`);
* **the decomposition itself** — that a two-hop question is answered by a LINK call followed
  by a terminal call. The marginal's *form* encodes that; the model is not asked to discover
  the program.

**NOT supplied, at any time, in any loss, or to build any record:**

* the intermediate entity `e` — no LINK record ever receives a target. The LINK call is
  learned only through the marginal, and only from `M` on;
* any supporting line / attention target — there is no evidence term at any point
  (`evidence_lines_used = 0` in every batch's accounting);
* `row.gold`, `row.supplied`, `row.answer`, `row.hops`, `row.relation` — never read. The
  check suite poisons all five and asserts the batch, the losses and every gradient are
  identical, at a pre-`M` step and at a post-`M` step.

**The curriculum is label-free too.** Kept lines are a uniformly random subset of the
visit's fact lines, recognised from visible tokens only; questions whose chain falls
outside the kept subset are replaced by questions that are answerable from it, with every
answer read off a kept visible fact row.

**Evaluator-only diagnostics.** The 250-update log reports the LINK call's argmax accuracy
against the true intermediate and the terminal call's accuracy given the true intermediate.
The true intermediate is read off the visit's kept visible `[world] a LINK b` row while the
batch is built and stored in `batch.diagnostics`, which **no loss function reads**. The
probe runs under `torch.no_grad()` and its forwards are not counted in training FLOPs. The
check suite scrambles `batch.diagnostics` and asserts every loss and every gradient is
bit-identical.

## Cost

Measured single-process, `-B`, one torch thread, 3 warm-up + 8 timed updates at each
curriculum point, with the **real** registered exclusion set loaded (so the per-record
overlap sha256 is paid), on a Mac already running three registered training workers.

| phase | updates | fraction | marginal | GFLOP/update | updates/s |
| --- | --- | --- | --- | --- | --- |
| A: 0–1,499 | 1,500 | 0 | off | 0.56 | 21.7 |
| B: 1,500–2,499 | 1,000 | 0 → 0.67 | off | 0.91 → 1.17 | 15.4 → 14.8 |
| C: 2,500–2,999 | 500 | 0.67 → 1 | **on** | ~4.0 | ~3.7 |
| D: 3,000–5,999 | 3,000 | 1 | on | 4.26 | 3.56–3.62 |

Projected single-process 6,000-update wall time: **~1,104 s** (A 69 s + B 61 s + C 136 s +
D 836 s + 24 diagnostic probes at 0.11 s). With the ×1.10 contention factor measured for a
real 3-seed wave: **~1,214 s**, against the registered 1,500 s training cap — **fits, with
~19% margin**. `marg-full` under the same conditions projects ~1,625 s single-process, so
the staged schedule is also *cheaper* than the variant it is one change away from.

## Pass marks

Astra's ten R cutoffs, on the recursive arm **R** with actual discrete tokens passed
between calls, **every seed separately, no averaging**:

| cells | cutoff (of 512) |
| --- | --- |
| c1, c2, p12-1, p12-2 | >= 487 |
| c3, c4, c5, c6, p12-3, s3 | >= 461 |

plus the R gate: **every autonomous LINK stage >= 487/512 in every seed** (every panel,
every side, `diagnostics[side]['native_links'][j] >= 487` for every stage `j`), every
terminal-oracle count >= 487, s3 native joint >= 461. Incomplete = failed. Averaged results
never count. Wave 1 is seeds 0, 1, 2.

Reported alongside, descriptively, never as a pass mark: one-hop train accuracy, mean
marginal probability, LINK argmax accuracy and terminal-given-true accuracy, every 250
updates. Three outcomes must be reported as different results:

1. the lookup forms before `M` and survives the switch (one-hop stays high, LINK rises
   after `M`) — the hypothesis holds;
2. the lookup forms before `M` and **collapses** at the switch — the marginal term is
   harmful at any time, not just at start-up;
3. the lookup forms and holds but LINK never sharpens (marginal probability rises while
   LINK argmax stays near chance) — the marginal is being satisfied diffusely, and
   counterfactual cell c4 is where that would show.

## Fable's predictions

Written 2026-09-20 by Fable before freeze; no run of this variant has been scored.

* At the switch (update 2,500) the single-call lookup is already sharp: one-hop training accuracy ≥ 0.95 in 3/3 seeds (grow-blind reached this 6/6).
* After the switch the final-answer signal is informative for the first time, because the last-step lookup it is averaged through is already
  correct. I expect the LINK call to be learned from it: LINK diagnostic accuracy ≥ 0.90 by the end in the seeds that pass.
* Registered marks (all ten R cells): **marg-staged passes in ≥ 2/3 seeds — my probability 55 %; marg-staged-dense — 60 %.**
  All 3/3: about 35 %.
* If it fails, the failure I expect is a shock at the hard switch: lookup accuracy drops after update 2,500 and LINK stays near chance
  (≈ 1/6 on six-person stories). A seed that never recovers one-hop accuracy ≥ 0.9 after the switch would point to that.
* If the two arms disagree, the dense arm's different record weights (0.6/0.2/0.2) are a confound, as already flagged above.
* M (single pass) fails transfer cells in every seed regardless (< 461/512 on c3–c6), as in every earlier build.
