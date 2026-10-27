# Canonical-operator variant `marg-staged-dense` — delayed marginal plus restored single-call practice

Written 2026-09-20 EDT, before any `marg-staged-dense` run. Drafted by the build agent from
Ben's brief. **Review and amend before running `freeze`: `freeze` hashes this file and
`check_manifest` re-verifies the hash before every worker and every wave.**

## The question

`grow-blind` learns a perfect one-hop lookup in 3/3 seeds (train accuracy 1.00 at update
6,000, reached around 1,500–3,000). `marg-full --startup grow-blind` — the same curriculum
with the gold intermediates removed and the two-hop path trained only through the exact
marginal — fails in 3/3 seeds (one-hop train accuracy 0.156 / 0.188 / 0.125, mean marginal
probability 0.220 / 0.238 / 0.213). Two things changed at once between those two runs, and
each is a candidate explanation:

* **(i)** the marginal term is pure noise until the terminal attribute lookup is sharp, and
  it dominates the shared weights from update 0;
* **(ii)** **single-call practice collapsed.** `grow-blind` gives the model **6** single-call
  records per visit (2 one-hop + 2 LINK + 2 terminal, all with direct targets).
  `marg-full` gives it **2** — only the generator's two one-hop questions carry a direct
  gradient on a single call; the sixteen terminal calls appear only inside the marginal,
  where each one is weighted by a near-uniform `p1` and none is individually supervised.
  The attribute lookup simply gets a third of the practice it needs.

`marg-staged` (the companion arm) tests (i) alone. **`marg-staged-dense` tests (i) and (ii)
together**: it is `marg-staged` plus K extra label-free one-hop attribute records per visit,
restoring the 6-single-call-records-per-visit density of `grow-blind` without restoring a
single intermediate label.

Read the two arms together. If `marg-staged` passes, (i) was sufficient. If only
`marg-staged-dense` passes, the density mattered. If neither passes, the marginal objective
itself is the problem, not its schedule.

## The change

**Change 1 (shared with `marg-staged`): the staged switch.** The marginal two-hop term
carries weight **exactly 0** for updates `< M` (`--marg-start`, default **2500**) and its
normal weight from `M` on. Hard switch, no ramp. Before `M` the loss is `marg-full`'s loss
with the marginal term removed (the other two groups keep the weights they had); from `M`
on the step is `marg-full`'s step verbatim. Before `M` the LINK call and the 16-way
terminal expansion are not forwarded during training; FLOPs count only the forwards
actually performed.

**Change 2 (this arm only): K extra label-free one-hop records per visit.**
`--extra-onehop`, default **K = 4**, applied **before and after** `M` alike. Each extra
record is built from **that visit's own kept visible facts** with the existing `balance`
one-hop constructor (`fable_operator_startup._one_hop_record`): entity uniform over the
world's six people, **relation uniform over (8, 9, 10)**, rejecting draws whose fact line is
not in the kept subset. The answer is read off the kept visible fact row; the record's
causal eligibility is the first question line of the visit, and the suite asserts directly
that every kept fact precedes it. With K = 4 the visit carries **6** single-call attribute
records, matching `grow-blind`.

**A LINK question is NEVER constructed.** A synthesised `[4, x, 11, 5]` record paired with
its entity answer would be exactly the intermediate label this whole family exists to
remove. This is asserted per record at construction *and* on the packed question tensor
(`no one-hop question may carry relation 11`), and checked again in the test suite.

**Weights.** `marg_weights` gives every *record* equal weight — the rule already in use
(`grow-blind` weights its 6 canonical records .75 and its 2 monolithic records .25, i.e.
.125 each). Adding K records to the one-hop group therefore re-divides the groups from
(1/3, 1/3, 1/3) to `(2+K, 2, 2)/(6+K)` = **(0.6, 0.2, 0.2)** at K = 4. This is a consequence
of the added records under the existing rule, not a separate design choice, but it does mean
**the marginal term's weight is 0.2 here versus 1/3 in `marg-staged`.** If the two arms
disagree, that difference is a candidate explanation and must be named in the write-up.

**Everything else is `marg-full --startup grow-blind` unchanged**: same runner, model, init,
AdamW, clipping, v3r lr decay, `random.Random(1101)` world stream, 6,000 updates, 16 visits
per update, `--blind-lines 16` of the 24 fact lines grown back over [1500, 3000), both EXACT
reductions on, `--marg-visits 0`, `--balance` off, the same ten panels and cutoffs,
final-checkpoint-only scoring.

The curriculum RNG is `random.Random("fable-startup-marg-full:<seed>")` — `marg-full`'s own
namespace — and the K extra records draw from a **separate** stream,
`random.Random("fable-staged-extra-marg-staged-dense:<seed>")`, so that adding them does not
shift the curriculum by a single draw. The check suite verifies that the stories, the
generator's own records, the LINK/terminal/monolithic groups and the final world-RNG state
match `marg-full --startup grow-blind` exactly over the first 20 batches.

## HONESTY: what is and is not supplied

**Supplied to the model during training:**

* the visible story (a random subset of fact lines early, the full story from update 3,000);
* the visible question tokens;
* **the final answer** of every record — the 2 generator one-hop questions, the K extra
  one-hop questions, the monolithic two-hop question, and the marginalised two-hop target;
* **the decomposition itself** — that a two-hop question is answered by a LINK call followed
  by a terminal call, encoded in the marginal's form;
* **more attribute-lookup practice**, which is the point of this arm. The extra records are
  ordinary final-answer questions about facts that are visible in that visit's story. They
  contain no intermediate, no chain and no annotation.

**NOT supplied, at any time, in any loss, or to build any record:**

* the intermediate entity — no LINK record ever receives a target, and no LINK question is
  ever constructed. The LINK call is learned only through the marginal, and only from `M` on;
* any supporting line / attention target (`evidence_lines_used = 0` in every batch);
* `row.gold`, `row.supplied`, `row.answer`, `row.hops`, `row.relation` — never read. The
  check suite poisons all five and asserts the batch, the losses and every gradient are
  identical, at a pre-`M` step and at a post-`M` step.

**Evaluator-only diagnostics.** As in `marg-staged`: LINK argmax accuracy and
terminal-given-true accuracy are logged every 250 updates from `batch.diagnostics`, which no
loss reads; the suite scrambles that field and asserts every loss and gradient is unchanged.

## Cost

Measured single-process, `-B`, one torch thread, 3 warm-up + 8 timed updates at each
curriculum point, with the **real** registered exclusion set loaded, on a Mac already
running three registered training workers.

| phase | updates | fraction | marginal | GFLOP/update | updates/s |
| --- | --- | --- | --- | --- | --- |
| A: 0–1,499 | 1,500 | 0 | off | 0.87 | 16.7 |
| B: 1,500–2,499 | 1,000 | 0 → 0.67 | off | 1.27 → 1.56 | 12.6 → 10.1 |
| C: 2,500–2,999 | 500 | 0.67 → 1 | **on** | ~4.4 | ~3.3 |
| D: 3,000–5,999 | 3,000 | 1 | on | 4.69 | 3.18–3.27 |

Projected single-process 6,000-update wall time: **~1,254 s** (A 90 s + B 80 s + C 152 s +
D 930 s + probes). With the ×1.10 contention factor measured for a real 3-seed wave:
**~1,379 s**, against the registered 1,500 s training cap — **fits, but with only ~8%
margin.**

If more margin is wanted, the smallest EXACT change (nothing about the experiment moves) is
to register this arm with `--training-seconds 1530`, i.e. `terminate_seconds = 1800`, which
sits exactly on the 30-minute wave boundary and gives ~151 s of headroom. Do **not** turn
off `--terminal-dedupe` or `--single-forward` to buy time: they are exact and they are what
makes the 16-way expansion affordable at all.

## Pass marks

Astra's ten R cutoffs, on the recursive arm **R** with actual discrete tokens passed between
calls, **every seed separately, no averaging**:

| cells | cutoff (of 512) |
| --- | --- |
| c1, c2, p12-1, p12-2 | >= 487 |
| c3, c4, c5, c6, p12-3, s3 | >= 461 |

plus the R gate: **every autonomous LINK stage >= 487/512 in every seed** (every panel,
every side), every terminal-oracle count >= 487, s3 native joint >= 461. Incomplete =
failed. Averaged results never count. Wave 1 is seeds 0, 1, 2.

Reported alongside, descriptively, never as a pass mark: one-hop train accuracy, mean
marginal probability, LINK argmax accuracy and terminal-given-true accuracy, every 250
updates; and the comparison against `marg-staged` on the same seeds, which is the only way
to separate hypothesis (i) from hypothesis (ii).

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
