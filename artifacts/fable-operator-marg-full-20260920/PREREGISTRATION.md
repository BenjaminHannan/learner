# Canonical-operator variant `marg-full` — full marginalisation on top of a start-up aid

Written 2026-09-20 EDT, before any `marg-full` run. Drafted by the build agent from Ben's
brief. **Review and amend before running `freeze`: `freeze` hashes this file and
`check_manifest` re-verifies the hash before every worker and every wave.**

## The question

`marg` — Ben's marginalisation over the sixteen intermediate entity tokens, no evidence
loss, no gold intermediate — never started on any of three seeds (3-16% one-hop). That is
exactly the pattern `e0` shows on 2 of 3 seeds, so the failure is consistent with the
start-up problem rather than with the marginal objective being wrong. `marg-full` tests
that directly: give the model a start-up aid on the **one-hop path only**, leave the
two-hop path fully marginalised at 16 of 16 visits, and see whether the composition
learns without any intermediate target at all.

## The change

**Two-hop path — no intermediate label, no supporting line, ever.** Each practised two-hop
question (asker x, terminal relation r) contributes

    -log P(y),   P(y) = sum_e p1[e] * P(y | S, e, r)

where `p1` is the softmax of the canonical LINK call `[4, x, 11, 5]` restricted to the
sixteen entity tokens 52..67 **without renormalisation** (mass on non-entity tokens is
lost and therefore penalised), and `P(y | S, e, r)` is the softmax of the canonical
terminal call `[4, e, r, 5]` on the same story. Gradients flow into both calls (checked).
All 16 visits are marginalised. Monolithic records carry answer CE only, as in `marg`.
Per-visit record accounting: 2 one-hop + 2 marginalised two-hop + 2 monolithic, weighted
as equal records (exactly 1/3, 1/3, 1/3 at 16 visits).

**Start-up aid — `--startup {hintwarm-onehop, grow, grow-blind}`.**

* `hintwarm-onehop`: the 0.5 supporting-line attention term is applied to the **two
  one-hop canonical records only**, and only for updates < H (`--hint-updates`, default
  1000). It is never applied to the LINK call, the terminal calls or the monolithic
  records. The one-hop records take their own forward while the hint is active.
* `grow`: the story-size curriculum of variant `grow` (chain lines + D distractors, grown
  back over [G1, G2)), with the chains derived from the **visible** facts of the full
  story rather than from `row.gold`.
* `grow-blind`: the label-free curriculum of variant `grow-blind`.

## HONESTY: what is and is not label-free

* **`row.gold`, `row.supplied`, `row.answer`, `row.hops` and `row.relation` are never read
  anywhere in this variant, for any startup base.** The check suite poisons all five and
  asserts the batch is bit-identical, for all three bases.
* **No intermediate entity is ever a target.** This is the one variant in the family that
  genuinely removes intermediate supervision.
* **The answer is still supervised**, as in every variant here.
* **`--startup grow` is not label-free in its curriculum.** Which lines are kept depends
  on the truth chain, derived from visible facts instead of from an annotation, but still
  chain-informed. `--startup grow-blind` is the label-free option.
* **`--startup hintwarm-onehop` uses the supporting-line annotation on the one-hop path**
  for the first H updates, via the same evidence mask v3r uses.

## Cost: what was measured, and the cheapest EXACT option

Measured single-process, 15 timed updates after 3 warm-up updates, `-B`, one torch thread,
on a machine already running six saturating processes. `base-e0` measured 766 s projected
for 6,000 updates in the same conditions while the live 3-process `balance` wave took
841 s, so these numbers run ~10% optimistic against a real 3-seed wave.

| marg-full option | GFLOP/update | updates/s | projected 6,000 |
| --- | --- | --- | --- |
| neither reduction | 7.54 | 2.64 | 2,269 s |
| terminal dedupe only | 6.94 | 3.06 | 1,958 s |
| single forward only | 5.13 | 3.01 | 1,994 s |
| **both (default)** | **4.37** | **3.69** | **1,625 s** |
| both, hint phase | 5.39 | 3.30 | 1,820 s |
| both, `--startup grow` at fraction 0 | 2.53 | 7.32 | 820 s |
| both, `--startup grow-blind` at fraction 0 | 2.45 | 7.11 | 844 s |

Both reductions are **exact** and are on by default:

* `--terminal-dedupe`: the 16 terminal calls are shared between the two two-hop records of
  a visit when the relation coincides (512 -> 448 calls, ~12.5%). The two records differ
  only in `where`; the merge is taken only after checking directly that no visible memory
  row lies between the two `where` values, i.e. that the two eligibility masks are
  identical. No entity is dropped and nothing is approximated. Checked against the
  un-deduped marginal to 0.0e+00.
* `--single-forward`: `TokenMemoryReasoner` already encodes the memory once per visit
  inside one forward and reuses the cached cross-attention key/value projections across
  every question of that visit, so packing the one-hop, LINK, 16-way terminal and
  monolithic queries into ONE forward encodes the story once per update instead of four
  times. Width-4 questions are right-padded to width 5 and masked out. Checked against 17
  separate forwards: max |diff| 1.5e-07.

The **only approximation** is `--marg-visits N` (marginalise the first N visits instead of
all 16); it is **OFF** (0 = all 16) and must be registered explicitly if ever used.

Wall-clock reading against the 30-minute wave rule (terminate = training cap + 270 s):

* `--startup grow` / `grow-blind`: ~1,460 s estimated for a 3-seed wave. Fits the standard
  1,500 s training cap.
* `--startup hintwarm-onehop`: ~1,820 s estimated. **Does NOT fit** the 1,500 s cap and
  sits on the 30-minute boundary. Register it with `--training-seconds 1530`
  (terminate 1,800 s) and accept the boundary, or reduce `--updates`, or run the
  grow-based bases first. Do not turn a reduction off to make it fit: they are exact.

## Base recipe

v3r, as `marg` is built. `--balance` is **OFF** by default (fresh seeds 3-5 showed the
relation-rebalanced one-hop records are not a net improvement); when set, the two one-hop
records are drawn with `balance`'s constructor. Same `random.Random(1101)` world stream,
v3r lr decay, 6,000 updates, 16 visits per update, same model/optimiser/clipping, same
overlap check against the full story, same ten panels, final-checkpoint-only scoring.
Extra randomness from `random.Random("fable-startup-marg-full:<seed>")`. FLOPs are counted
per forward with the module's own counter, so the sixteen-way expansion is charged in full.

## Pass marks

Astra's ten R cutoffs, **every seed separately, no averaging**:

| cells | cutoff (of 512) |
| --- | --- |
| c1, c2, p12-1, p12-2 | >= 487 |
| c3, c4, c5, c6, p12-3, s3 | >= 461 |

plus the R gate: every panel/side native LINK count >= 487, every terminal-oracle count >=
487, s3 native joint >= 461. Incomplete = failed. Wave 1 is seeds 0, 1, 2.

Reported alongside, descriptively: `mean_marginal_probability` and one-hop train accuracy
every 250 updates. A run whose one-hop accuracy starts but whose marginal probability
stays at chance is a *different* result from one that never starts, and must be reported
as such.

## Fable's predictions
