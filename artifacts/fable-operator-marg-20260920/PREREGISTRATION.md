# Canonical-operator variant `marg` — marginalised two-hop, no intermediate labels

Written 2026-09-20 EDT, before any `marg` run. Drafted by the build agent from Ben's
brief. **Review and amend before running `freeze`: `freeze` hashes this file and
`check_manifest` re-verifies the hash before every worker and every wave.**
**Also settle the timing decision in the "Time budget" section before freezing.**

## Question (Ben's proposal)

Every canonical-operator result so far hands the model the gold intermediate entity: the
LINK record's answer target *is* the friend, and the terminal record's subject *is* the
friend. The two-hop composition is therefore never learned from the two-hop question — it
is assembled from two separately supervised one-hop lookups. Can the composition be
learned with no intermediate label and no supporting line at all, by marginalising over
the intermediate?

## The two-hop training signal

For each practised two-hop question (asker `x`, terminal relation `r` in {8, 9}, final
answer `y`) on story `S`:

1. one canonical LINK call `[4, x, 11, 5]` on `S`; `p1 = softmax` over the full 68-token
   output; `P(e) = p1[e]` for the sixteen entity tokens 52..67, taken **as-is and not
   renormalised** — mass the LINK call puts on non-entity tokens contributes nothing to
   `P(y)` and is therefore penalised;
2. sixteen canonical terminal calls `[4, e, r, 5]` on the same story, one per entity
   token, batched, giving `P(y | S, e, r)`;
3. `P(y) = sum_e P(e) * P(y | S, e, r)`; loss `= -log(max(P(y), 1e-12))`.

Gradients flow into both calls. No gold intermediate entity and no supporting line is
read anywhere in this variant — `row.gold` and `row.supplied` are never touched, which
the test suite verifies by poisoning them and checking the batch and loss are unchanged.

## Record accounting and weighting

Per visit: 2 one-hop canonical records (answer CE only) + 2 marginalised two-hop records
(each costing 1 + 16 canonical forwards) + 2 monolithic records. **Deviation, noted
explicitly:** the monolithic records here carry answer cross-entropy only. v3r gives them
the evidence-bearing `loss_for`; keeping that would reintroduce supporting-line
supervision on exactly the two-hop questions this variant is trying to learn without it.

The three groups are weighted as equal records — the plain mean over the six per-visit
losses, i.e. (1/3, 1/3, 1/3) over the three group means. (v3r's .75/.25 is the same
device: it is exactly the eight-record mean.)

FLOPs are counted per forward with the module's own counter over all four input groups,
so the sixteen-way expansion is charged in full: measured 7.54e9 FLOPs per update versus
2.85e9 for a v3r-shaped update, a factor of 2.6.

## Everything else is identical to v3r

Model, init, AdamW settings, clipping, lr-decay schedule, 6,000 updates, 16 visits per
update, `random.Random(1101)` consumed identically for world generation, the semantic
overlap `forbidden` check (applied to every one of the sixteen expanded terminal calls),
the two monolithic records per visit, zero three-hop / 12-person / held-out-composition
training, final-checkpoint-only scoring on the same ten panels with the same cutoffs.

**Evaluation is unchanged.** The R policy passes actual discrete argmax tokens between
calls; the marginalisation exists only in training. Averaged predictions never count.

## Time budget — DECIDE BEFORE FREEZING

Measured single-process on the Mac on 2026-09-20 with six other registered workers
running (`balance`/`e0` measured 7.1-7.3 updates/s in the same conditions, versus 6.7
updates/s for the v3r workers actually running, so these numbers are not optimistic):

| marginalised visits per update | updates/s | projected 6,000 updates | peak RSS |
|---|---|---|---|
| 16 (default, flag OFF) | 2.25 | 2,667 s | 1.28 GB |
| 8  (`--marg-visits 8`) | 3.18 | 1,886 s | 1.39 GB |
| 6  (`--marg-visits 6`) | 3.43 | 1,748 s | 0.99 GB |
| 4  (`--marg-visits 4`) | 3.85 | 1,558 s | 0.73 GB |

The registered 1,500 s training cap is not reachable at 16 visits, and not reachable at
8 either. Two options, smallest first; the registered update count (6,000) is not
changed by either:

* **(a) raise only the wall-clock cap.** `freeze --training-seconds 3000` keeps every
  6,000 updates x 16 visits exactly as designed and changes no computation at all; the
  work/terminate deadlines follow automatically at 3,240/3,270 s. Cost: ~45 min per wave
  instead of ~25.
* **(b) keep the 1,500 s cap and reduce the marginalised fan-out** to `--marg-visits 4`
  (one-hop and monolithic records still cover all 16 visits). This changes the
  experiment: the marginalised term sees a quarter of the visits per update.

The flag defaults OFF (all 16 visits marginalised). Recorded in the launch manifest as
`marg_visits`.

## Predictions (score as written)

1. `marg` is the hardest of the three variants. The marginal is a soft mixture over 16
   entities at initialization, so early gradients are diffuse; the LINK call has no
   direct target at all.
2. If the LINK call sharpens onto the true friend by the end of training, R on c2 (own
   practised two-hop) meets its cutoff and the native LINK diagnostics are high. That
   would be the first evidence in this line that the composition is learnable without
   intermediate labels.
3. Most likely failure mode: the LINK call spreads mass over entities that happen to
   share the answer value for relation `r`, since any such entity gives the same `P(y)`.
   Watch `native_links` in the panel diagnostics, not just the answer counts.
4. M stays below 128/512 on c3-c6 and s3 in every seed.

Success = R meets all ten cutoffs in every seed of wave 1 (seeds 0, 1, 2). A failure is
informative and will be reported as written, not re-cut.

## Fable's amendments before freeze (2026-09-20 ~09:20 EDT, before any run)
Timing decision: the full design (16 visits of marginalised two-hop per update) projects to ~2,670 s, beyond Ben's 30-minute wave rule. This first screen therefore uses `--marg-visits 4` (the marginalised term sees 4 of the 16 visits per update; one-hop and monolithic records still use all 16) with a 1,700 s training cap. This weakens the two-hop signal fourfold and is a disclosed limitation: a failure here cannot by itself reject Ben's proposal at full strength; a success is conservative evidence for it.
Roster: seeds 0,1,2. Pass marks (Ben's): Astra's ten cutoffs for R with ACTUAL discrete tokens passed between calls, plus the runner's native-path diagnostics (every autonomous LINK stage >= 487/512), in every seed. Averaged predictions never count.
Predictions: I expect FAIL in all three seeds (~70%), mainly because this variant also removes the supporting-line loss, which e0 tests separately at the same time; if e0 fails too, the next marg run should keep the evidence-free question open but restore only what e0 shows is necessary. If marg passes, intermediate labels are not needed on this toy and problem 1 on Ben's list moves from "unresolved" to "shown on the toy".
