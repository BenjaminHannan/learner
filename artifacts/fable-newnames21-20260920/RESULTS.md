# Experiment 21 / M1 "new names" — results

Fable (coordinator) · 20 September 2026 · run once under FREEZE-NOTE.md (sha f0358218…). Six runs
(control and treatment × seeds 2100/2101/2102), 6,000 updates each, 660–682 s per run, no failures.
Source tables: `report.txt` (sha 020f248c…), `gates.json` (sha 6fa21952…), `runs/*/training.json`.

## Registered verdict: FAIL, 0/3 treatment seeds. Control 3/3.

Control (fixed name table, the frozen grow-blind recipe): 512/512 on all ten cells in all three seeds, so the
recipe reproduced and the run is not VOID.

## Every seed, every cell (R = fixed loop, correct out of 512; cutoffs 487 or 461)

| Cell | Cutoff | Control 2100/2101/2102 | Treatment, reserved codes 2100/2101/2102 |
|---|---|---|---|
| c1 | 487 | 512/512/512 | 149 / 79 / 30 |
| c2 | 487 | 512/512/512 | 145 / 59 / 33 |
| c3 | 461 | 512/512/512 | 126 / 89 / 25 |
| c4 | 461 | 512/512/512 | 0 / 0 / 0 |
| c5 | 461 | 512/512/512 | 0 / 0 / 0 |
| c6 | 461 | 512/512/512 | 149 / 84 / 38 |
| p12-1 | 487 | 512/512/512 | 109 / 53 / 29 |
| p12-2 | 487 | 512/512/512 | 95 / 59 / 32 |
| p12-3 | 461 | 512/512/512 | 132 / 67 / 32 |
| s3 | 461 | 512/512/512 | 139 / 77 / 30 |

All three scorings:
1. **Reserved codes (the gated one):** table above.
2. **Training-pool codes:** identical counts on every cell and seed.
3. **Paired, reserved minus training-pool (mark ≥ −13):** exactly +0 on all 30 cells.

Two-sided warning line (added by hand, condition 11): the paired mark is one-sided; a large *positive*
difference would also have been a warning sign. It does not trigger — every difference is 0.

## Pre-named failure signatures

| Seed | never_started | attributes_fine_link_at_chance | One-call attribute accuracy | First-stage LINK accuracy |
|---|---|---|---|---|
| 2100 | no | no | 0.19–0.29 | 0.06–0.10 |
| 2101 | no | no | 0.08–0.20 | 0.05–0.07 |
| 2102 | **yes** | no | 0.04–0.09 | 0.04–0.06 |

Chance is 1/16 = 0.0625. LINK is at chance in all three seeds. Seeds 2100 and 2101 match neither pre-named
signature ("unnamed failure"): their attributes are far from fine.

## scale_trace (treatment; one sample per 500 updates; start value 0.13856)

| Seed | code_scale at 500, 1000, …, 6000 | entity_output_bias first → last |
|---|---|---|
| 2100 | 0.005, −0.005, −0.007, −0.017, 0.013, 0.012, 0.000, 0.006, 0.009, 0.003, 0.002, 0.004 | 0.249 → −1.069 |
| 2101 | 0.016, −0.002, 0.009, −0.004, −0.002, 0.001, 0.008, −0.001, 0.003, −0.004, −0.000, 0.001 | 0.226 → −1.448 |
| 2102 | 0.015, −0.003, −0.004, −0.003, 0.004, 0.003, 0.004, 0.005, −0.002, −0.005, 0.002, 0.003 | 0.268 → −2.444 |

**Speed-limit flag** (≥ 0.50 at update 500 or ≥ 0.90 at update 1,000): not tripped in any seed. The scale did
the opposite of what the ruling worried about: instead of climbing too slowly, it fell to ≈ 0 inside the first
500 updates and stayed there.

## Descriptive extra, not gated: 64-person worlds, reserved codes

| Seed | wide64-attr /256 | wide64-link /128 | wide64-two /128 |
|---|---|---|---|
| 2100 | 26 | 1 | 14 |
| 2101 | 25 | 2 | 10 |
| 2102 | 13 | 0 | 9 |

## What it means

- The model given freshly drawn random name codes every world did not learn to bind them. It learned to
  **switch the names off**: the single number that scales every name code went to ≈ 0 in all three seeds, and
  the output bias for "answer with a name" went negative. With names invisible, a trained code and a
  never-trained code look the same — which is exactly why the two scorings agree to the unit on all 30 cells.
- What is left is a name-blind guesser: chance on anything that needs a name (LINK), a little above chance on
  attributes in two seeds.
- The same recipe with a fixed name table is perfect, so the training recipe, panels and scorer are sound. The
  difference is the name scheme alone.

## What it does not mean

- Not evidence that new-name binding is impossible for this operator — only that this tied-random-code design,
  at this learning rate and initial scale, falls into an "ignore the names" solution early.
- Not a test of new names at all, in effect: the model never used names, so reserved-vs-trained says nothing
  about generalisation to unseen codes.
- Not a cause: the trace shows *that* the scale collapsed, not *why*. The pre-named follow-up (7× learning
  rate on the scalar) targets the opposite problem and is not supported by this trace.
- Q1 limitation, verbatim: "The three seeds differ in the model's starting weights, the blind-curriculum stream
  and (treatment only) the name stream. They do not differ in the training worlds. The result is therefore
  conditional on one world stream; it says nothing about other world streams."

## Predictions (hashed before the run; full rows in `artifacts/fable-predictions-ledger.md`)

| Forecast of "treatment passes 3/3" | p | Outcome |
|---|---|---|
| Coordinator P94 | 0.25 | FALSE |
| Reviewer R21-P1 | 0.35 | FALSE |
| GPT-6 Pro | 0.45 | FALSE |

Other scored rows: control 3/3 TRUE (P97 0.80, R21-P4 0.85); never_started in ≥ 1 seed TRUE (P98 0.40,
R21-P5 0.30); unnamed failure in ≥ 1 seed TRUE (R21-P7 0.35); speed-limit flag FALSE (P99 0.10, R21-P8 0.25);
code_scale below its start value at update 500 in 3/3 TRUE (P100 0.65). P101 and R21-P9..P13 are not scorable
(they condition on a passing seed). Nobody forecast a scale collapse to zero.

## Next

No amendment, no rerun of this registration. The follow-up design goes to a Fable reviewer with this trace,
ruling 21b's M1c option and GPT-6 Pro's staged row-copy proposal (corrected by adjudication 25b to a
token-pointer copy head), one change at a time.
