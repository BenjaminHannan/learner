# Link isolation — can the LINK call be learned when the terminal lookup cannot move?

Written 2026-09-20 EDT, before any `fable-link-isolation` run. Drafted by the build agent
from Ben's brief. **Review and amend before running `freeze`: `freeze` hashes this file and
`check_manifest` re-verifies the hash before every worker and every wave.**

## The question

The open problem is to learn the LINK call **with no label for the middle person** — only the
final answer `y` — through the exact marginal

```
-log sum_e p_link(e | S, x, LINK) * p_term(y | S, e, r)          e over the 16 entity tokens 52..67
```

Two attempts have failed, both with everything trained jointly in the one 79,316-parameter
model:

| run | one-hop train acc @ 6,000 | LINK | mean marginal probability |
| --- | --- | --- | --- |
| `marg-full --startup grow-blind`, seeds 0/1/2 | 0.156 / 0.188 / 0.125 | ~6% | 0.220 / 0.238 / 0.213 |
| `marg-staged` (same marginal switched on at 2,500) | *(see that run's report)* | — | — |

A reviewer's hypothesis is **mutual interference**:

> both calls share weights, so the terminal lookup learns from LINK's uncertain choices while
> LINK needs a terminal lookup that already distinguishes candidates.

and a second point:

> 10 of the 16 summed identities are not in the story at all.

Detaching the gradient does not test the first hypothesis, because the shared weights still
move: the terminal distribution `p_term(· | e, r)` drifts under the one-hop CE and under the
marginal's own pull on every other entity, whether or not a `detach()` is written. The only
way to settle it is to make the terminal distribution **literally unable to move**.

## The design

### Stage A — build a lookup, and nothing else

Train on **single-call attribute questions only**: relations 8, 9, 10; never a LINK query;
never a two-hop or monolithic record; no evidence/attention loss; no gold intermediate.

* Curriculum: `grow-blind`'s label-free small-story curriculum (a uniformly random subset of
  each visit's fact lines, recognised from **visible tokens only**, `--blind-lines 16` of 24,
  grown back to the full story linearly over [G1, G2) = [750, 1500)).
* Records: one attribute record at each of the visit's four question lines — the generator's
  own two one-hop questions when their fact line is kept, a replacement drawn from the kept
  facts otherwise, and **always** a replacement at each of the two two-hop question lines —
  plus K = 2 further attribute records at the first question line. That is **6 single-call
  attribute records per visit**, exactly `grow-blind`'s record count, all of them attribute.
* Loss: the plain mean answer cross-entropy over those records (one record group, so equal
  weight per record is the mean; `grow-blind`'s .75/.25 split is between its canonical and
  monolithic groups and has no analogue here).
* Schedule: **3,000 updates**, 16 visits per update, the v3r lr shape **rescaled to the stage
  length** (`lr_at_scaled(step, 3000) == lr_at(2 * step)`: warm-up over the first 50 updates,
  flat at 1e-3 to 2/3 of the run, linear to 1e-4 at the end).
* Output: `stage_a.pt` — model weights, **optimizer state**, and every RNG state (torch, the
  `random.Random(1101)` world stream, the curriculum stream, the extra-record stream).

`grow-blind` reaches a perfect one-hop lookup in 3/3 seeds under a strictly harder record mix
(it spends 2 of its 6 records per visit on LINK questions), so stage A is expected to end with
a lookup at or near 1.00. **If it does not, stage B is uninterpretable and the run stops.**

### Stage B — three arms, one batch

Every arm starts from the **same** `stage_a.pt` (same weights, same optimizer moments, same
RNG states) and sees **byte-for-byte identical batches**: the batch builder never reads which
arm it is serving, the curriculum RNG namespace does not contain the arm, and the world stream
continues from the state saved in `stage_a.pt`. The check suite asserts all of this, over 8
fresh batches and again after 3 real updates once the three models have diverged.

Each batch is `marg-full --startup grow-blind`'s batch at curriculum fraction 1 **minus the
monolithic group**: 2 one-hop attribute records and 2 marginalised two-hop records per visit,
with both of `marg-full`'s EXACT reductions on (`--terminal-dedupe`, `--single-forward`).

| arm | `p_term` comes from | sum over | `p_link` renormalised |
| --- | --- | --- | --- |
| `shared` | the trainable model | all 16 entity tokens | no |
| `frozen-terminal` | a frozen copy of the stage-A model | all 16 entity tokens | no |
| `frozen-terminal-6` | a frozen copy of the stage-A model | the people **visibly present** | yes, over those people |

* `shared` is the current approach minus the monolithic records: one model, both calls, both
  receiving gradient.
* `frozen-terminal`: the terminal probabilities come from a `deepcopy`, `eval()`,
  `requires_grad_(False)` copy of the stage-A model that the optimizer never sees and nothing
  ever updates; its forwards run under `torch.no_grad()`. **The one-hop CE on the trainable
  model stays on**, so the only difference from `shared` is where `p_term` comes from. The
  check suite asserts the frozen copy is bit-identical after N updates and receives no
  gradient at all.
* `frozen-terminal-6`: as `frozen-terminal`, but the marginal sums only over the entity tokens
  that appear in the **visible story rows** (subject of a visible fact row, or object of a
  visible LINK row) and `p_link` is renormalised over them. Note the consequence, which is the
  arm and not an oversight: mass on absent identities and on non-entity tokens is no longer
  penalised.

Loss, all arms: `w1 * one_hop_CE + w2 * marginal`, with `(w1, w2)` = `marg-full`'s
equal-weight-per-record rule and the monolithic group **removed, not renormalised away** — the
denominator still counts the monolithic record every two-hop question carries in `marg-full`.
At 16 visits that is exactly `(1/3) * one_hop + (1/3) * marginal`, so the one-hop term keeps
the weight it has in `marg-full`. The check suite asserts `shared`'s two terms equal
`marg-full`'s one-hop and marginal terms on the same batch **at tolerance 0**.

Schedule: **3,000 updates**, 16 visits per update, the same rescaled v3r lr shape, final
checkpoint only.

## HONESTY: what is and is not supplied

**Supplied during training:**

* the visible story (a random subset of fact lines early in stage A, the full story from
  update 1,500 of stage A onward and throughout stage B);
* the visible question tokens;
* the **final answer** of every record (stage A's attribute answers, stage B's one-hop answers
  and the marginalised two-hop target `y`);
* the **decomposition itself** — that a two-hop question is answered by a LINK call followed by
  a terminal call. The marginal's form encodes that; the model is not asked to discover the
  program;
* in `frozen-terminal-6` only: **which identities are in this story**, read from visible rows.
  This is visible information, not a label, but it is information the other two arms do not
  get, and the arm must be read that way.

**NOT supplied, at any time, in any loss, or to build any record:**

* the intermediate entity `e` — no LINK record ever receives a target, in either stage;
* any supporting line / attention target — there is no evidence term anywhere
  (`evidence_lines_used = 0` in every batch's accounting);
* `row.gold`, `row.supplied`, `row.answer`, `row.hops`, `row.relation` — never read. The check
  suite poisons all five and asserts the batches, the losses and every gradient are identical,
  in both stages and for all three arms.

**Evaluator-only diagnostics.** The true middle person and the "wrong present person shares the
answer value" flag are labels. They are read only while the batch is built, stored in
`batch.diagnostics`, and read only by the diagnostic code path. The check suite scrambles them
and asserts every loss and every gradient is bit-identical, for every arm. `batch.present` is
deliberately **not** a diagnostic — `frozen-terminal-6` reads it in its loss — and the check
suite asserts that only that arm's loss changes when the mask is scrambled.

## What is measured

Every 100 updates, on the training batch, and on a **fixed held-out probe set** before the
first stage-B update and after the last: 512 fresh two-hop questions over six-person worlds
and 512 over sixteen-person worlds, built from the visible facts of fresh stories before
training starts, checked against the registered exclusion set (the run refuses to start on a
hit), never touched by any loss.

* **LINK accuracy** — argmax of the LINK call equals the true middle person (also reported
  restricted to the 16 entity tokens).
* **p_link mass** on the true person / wrong-but-present people / absent identities /
  non-entity tokens. These four partition the LINK softmax and sum to 1.
* **Terminal discriminability** — `p_term(y | true e)` against the mean `p_term(y | wrong
  present e)`, their difference, and how often the true person is the argmax among present
  people; plus the **shared-answer rate**: the fraction of questions where some wrong present
  person happens to have the same answer value (the "right answer through the wrong person"
  rate, ~27% in a six-person world, ~62% in a sixteen-person world at 16 values).
* **One-hop accuracy per relation (8, 9, 10)** of the trainable model — does LINK training
  damage the lookup stage A built?
* **Two-hop answer accuracy under real two-call execution** (`astra_canonical_operator.execute`,
  the same executor the registered panels use), split into **right-via-right-person** and
  **right-via-wrong-person**, with the aborted count (an early non-entity LINK output) kept
  separately.

`report` prints this **per seed, per arm**. Nothing is averaged across seeds.

## Pass marks and readings

**Pass mark, per seed:** `LINK accuracy >= 0.90` on the six-person held-out probe set.

Readings, decided in advance:

* **Only the frozen arms learn LINK** → terminal drift is implicated: the shared-weight
  movement of the terminal lookup is what prevents the marginal from teaching LINK.
* **Neither arm learns LINK** → terminal instability cannot be the whole explanation; the
  marginal's own signal is too weak or too flat, and the next experiment has to change the
  signal, not the sharing.
* **`shared` also learns LINK** → the earlier failures were about the monolithic records or
  the cold start, not interference, and `marg-full`'s result should be re-read that way.
* **`frozen-terminal-6` learns and `frozen-terminal` does not** → the 10 absent identities are
  the problem, and the fix is to restrict the sum, not to freeze anything.

Secondary readings, reported but not pass marks: a high right-via-wrong-person rate with high
answer accuracy means the model is scoring on the shared-answer coincidences rather than on the
link; a drop in one-hop accuracy per relation between the stage-A probe and the final probe
measures exactly how much LINK training costs the lookup.

## Cost

Measured single-process, `-B`, one torch thread, 3 warm-up + 8 timed updates at 16 visits,
with the **real** registered exclusion set loaded (6,656 entries, so the per-record overlap
sha256 is paid), on an idle Mac. `shared` carries the 16-way terminal expansion through the
backward; the frozen arms pay it as a forward-only `no_grad` pass through the frozen copy,
which is why they are ~1.6x faster.

| stage / arm | GFLOP/update | updates/s (1 process) | 3,000 updates |
| --- | --- | --- | --- |
| stage A | 0.623 | 25.7 | 117 s |
| stage B `shared` | 3.428 | 4.17 | 719 s |
| stage B `frozen-terminal` | 2.361 | 6.45 | 465 s |
| stage B `frozen-terminal-6` | 2.361 | 6.56 | 457 s |

Diagnostics on top: the every-100-update line costs 0.19 s (30 of them = 6 s per run); each
held-out probe pass costs 2.1 s (six-person, 512) + 3.4 s (sixteen-person, 512), run twice
per stage-B worker = 22 s; building both probe sets costs 0.6 s.

A wave is 3 seeds in parallel, one process each, one torch thread each. At the ~1.10
contention factor measured for three concurrent workers on this machine, the worst wave
(`shared`) projects to **~820 s ≈ 13.7 minutes**, the frozen arms to ~9 minutes, and stage A
to ~2.5 minutes — all inside the 25-minute rule.

Registered caps: `--stage-a-seconds 420` (work 660, terminate 690) and `--stage-b-seconds
1200` (work 1440, **terminate 1470 s = 24.5 min**). A worker that exceeds its training cap
raises and writes `failure.json` rather than silently producing a short run.

## Deviations and judgment calls

1. **Stage B runs at full story size throughout.** The curriculum's job is start-up and stage A
   finishes it (G2 = 1,500 < 3,000). Running stage B at fraction 1 also removes a confound
   between the arms.
2. **Stage B's lr restarts the rescaled v3r shape** (warm-up again over its first 50 updates)
   on top of stage A's restored optimizer moments. Each stage is a self-contained run of its
   own length; all three arms get the identical schedule, so it cannot confound the comparison.
3. **Stage A's loss has no .75/.25 split** — there is one record group.
4. **The monolithic records are gone in stage B**, as specified; their weight is dropped, not
   redistributed.
5. **The frozen copy is kept in all three arms**, including `shared`, so the three runs are
   structurally identical; in `shared` it is used only to report the frozen terminal margin.
6. **The probe sets are built before training starts** so an exclusion-set collision costs
   nothing instead of invalidating a finished run.
7. **This module does not monkeypatch `astra_canonical_operator`.** It runs its own two-stage
   worker, so the registered runner's ten-panel scoring is not part of this experiment; the
   result is read from the diagnostics and the held-out probes.

## Fable's predictions

Written 2026-09-20 by Fable before freeze. Known at this time: marg-staged-dense (shared weights, monolithic records kept, switch at 2,500)
gave LINK argmax accuracy 0.16 / 0.59 / 0.03 at update 6,000 in seeds 0/1/2, with seed 1's rise happening entirely in the last 1,000 updates;
seed 2's lookup never started. No run of this experiment exists. Pass mark: LINK accuracy ≥ 0.90 on the six-person probe, per seed.

| id | forecast | p | falsified by |
|---|---|---|---|
| P21 | stage A ends with one-hop probe accuracy ≥ 0.95 in 3/3 seeds | 0.65 | any seed < 0.95 (then stage B for that seed is uninterpretable, as the stop rule says) |
| P22 | `frozen-terminal` reaches the mark in ≥ 2/3 seeds | 0.45 | ≤ 1 seed |
| P23 | `frozen-terminal-6` reaches the mark in ≥ 2/3 seeds | 0.55 | ≤ 1 seed |
| P24 | `shared` reaches the mark in ≥ 2/3 seeds | 0.25 | ≥ 2 seeds |
| P25 | in every arm, "right answer through the wrong person" is ≥ 10 % of correct two-hop answers at some logged point before LINK accuracy passes 0.5 | 0.6 | never ≥ 10 % |

Reading I commit to in advance: if `shared` does as well as the frozen arms, mutual interference was NOT the cause of the earlier failures
(cold start / monolithic records / too few updates are then the suspects). If no arm learns LINK in 3,000 updates but LINK accuracy is still
rising at the end, the verdict is "slow, not impossible" and the follow-up is a longer stage B, not a new mechanism.
