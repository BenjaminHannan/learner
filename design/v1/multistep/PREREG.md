# Multi-step creative puzzles: dream school (pre-registered 2026-10-23, before any run)

## The problem (dev numbers, `design/v1/results2/full/final_dev.json`)
Creative dev first try by kind (FULL W2): last_digit 98%, square 73%, double_add 2%, sq_plus 2%, affine 0%. `fits == first_try`, so on the
three hard kinds the model almost never writes a program that even fits the examples.

Why (from the code, not yet tested): the hard kinds need 3-5 B2 steps (`MANIFEST.json` `ref_steps`: affine 3-5, sq_plus 2-4, double_add 3-4),
because B, A must be built from the constants 1 2 10 100, and the parameter has to be worked out from the examples inside the network
(programs may not point at example numbers). Sleep trains only on the model's own fitting tries (W records), the search almost never fits
these kinds, so they get no records. PR #96's dreams stop at 2 steps and contain essentially none of these forms.

## The change (one change, in doses)
A **dream school**: before night 1, sleep on a large set of random B2 programs of 1..5 steps (DreamCoder fantasies), each written as a
C2 few-shot question labelled by execution, with every step's op and operand slots forced (step supervision). Same generator as
`creative/dream2.py`, `max_steps=5`. No answer key, no kind name. Nights then also get 1,000 dreams each.

## Setup (all arms identical except the arm's own lines)
Creative module only (no D, no bridge, no G1; G1 is off for every arm alike, disclosed). Parent B2_s200 (sha 94057436...).
Warm-up -> N' -> pool temperature on DEV exactly as `v1/creative_sleep.run_creative`; computed once per seed and shared by its arms.
Seeds 0 and 1. Nights: C2b W path (search 32 + 480, lr 1e-3, 32 visits).

| Arm | School before night 1 | Dreams per night |
|---|---|---|
| base | none | 0 |
| dream2 | none | 1,000, 1-2 steps (PR #96 as built) |
| school5 | 40,000 dreams, 1-5 steps balanced, 2 visits, lr 3e-4, skills + warm replay | 1,000, 1-5 steps |
| school5_strict | as school5, but every dream whose function equals any held-out kind's form (any parameters, on the whole input domain) is removed and redrawn | as school5, same filter |
| school5_curr | as school5, the same 40,000-dream budget in three phases: 1-2 steps, then 1-3, then 1-5 | as school5 |

oracle (report only): school = the pool questions' reference programs (uses the answer key's kind/params; an upper bound, not a candidate)

## Measure
Greedy first try (fits and right) by kind on creative `dev` (256) + `labelled` (512) = 768 held-out-kind questions, after night 2.
`test.jsonl` (sealed) is not opened. **Hard** = mean over affine, sq_plus, double_add. **Easy** = mean over square, last_digit.
Arm score = mean over the 2 seeds. Skills harm: pooled-5 skills (fastsleep.skills5) of W2 vs N' of the same seed.

## Pass marks (fixed now)
- **PASS**: some school arm has Hard >= 15% AND Hard >= base + 10 points, with Easy no more than 5 points below base and skills harm <= 2 points.
- **Not leakage**: school5_strict keeps at least half of school5's Hard gain over base. If not, the result is reported as
  "gain mostly from seeing held-out forms in dreams", not as generalisation.
- **Curriculum helps**: school5_curr Hard >= school5 Hard + 5 points (otherwise: no shown effect of ordering).
- **Proved wrong**: every school arm has Hard <= base + 3 points.
- dream2 vs base is reported only (PR #96's expectation: no Hard gain, since 2-step dreams cannot write these forms).

Noise: ~150 questions per kind per seed, two seeds; a 10-point gap is about 3 standard errors on a pooled Hard mean of ~450 x 2.

## Result of round 1 (2026-10-23, Vast RTX 3090, $0.40) — `results/results.json`
Hard (affine, sq_plus, double_add) / Easy, mean of 2 seeds, dev + labelled (768): base 11.1 / 79.4; dream2 12.3 / 84.8; school5 1.2 / 78.7;
school5_strict 1.5 / 81.1; school5_curr 1.5 / 81.3; oracle (report only) 45.5 / 99.0. Verdict by the marks above: **PROVED WRONG** (every school arm
<= base + 3; in fact about 10 points below base). The school's own loss stayed at ~7.0 after 2,500 updates (oracle school: below 0), i.e. the model
did not learn the random dreams at all. Reading (suggested, not tested): a uniformly random program is a noisy label, because many programs fit
the same 3 examples and the label is whichever one was drawn; the oracle's labels are the SHORTEST program (breadth-first search), which is
consistent across questions, and it reaches 45.5%.

# Round 2: Occam dreams (pre-registered 2026-10-23, before the run)
One change: every school dream is RE-LABELLED with the shortest program that fits its own shown examples and query
(`fewshot.find_reference` on the dream row, the same search that labels the oracle; dreams with no program within 5 steps are dropped).
The label never comes from a held-out kind's key; strict filtering as before. Everything else as round 1, school lr 1e-3 (round 1's 3e-4 left the
school loss flat), 4 visits, 40,000 dreams, 1,000 Occam dreams per night.

| Arm | |
|---|---|
| base | as round 1 (re-run, same seeds) |
| occam5 | Occam-labelled school, 1-5 step functions |
| occam5_strict | as occam5, held-out forms removed (same filter as round 1) |
| oracle | as round 1 (report only) |

Marks: **PASS** if occam5_strict Hard >= base + 10 points AND >= 20%, Easy within 5 of base, skills harm <= 2 points.
**Not leakage**: occam5_strict keeps >= half of occam5's gain. **Proved wrong**: occam5_strict Hard <= base + 3.
Mechanism check (reported): school loss after the school must fall below 2.0, otherwise the arm "did not learn its dreams".

# Round 3: depth-balanced Occam dreams (pre-registered 2026-10-23, before round 2's result was seen)
Found while building round 2: after Occam relabelling the school is mostly short (2,000-dream sample: found length 1: 53%, 2: 32%, 3: 12%,
4: 3%, 5: 0.1%), because most random 4-5 step programs equal a shorter one. The hard kinds need 3-5 steps. One change from occam5: the 40,000
school dreams are dealt by FOUND (shortest) length, 1-4 steps, 10,000 each (5 is too rare to fill; dropped). Nightly dreams as occam5.

| Arm | |
|---|---|
| occam_deep | depth-balanced Occam school, strict filter ON (held-out forms removed) |

Run with the same seeds against round 2's base (same code path, same seeds; base is re-run on the box for a same-box comparison).
Marks: PASS if occam_deep Hard >= base + 10 AND >= 20%, Easy within 5, harm <= 2. Depth helps: occam_deep Hard >= occam5_strict Hard + 5.
Proved wrong: occam_deep Hard <= base + 3. Mechanism: school loss < 2.0.

## Reduced run on the Mac (2026-10-24, before any round-2/3 number was seen)
The Vast budget was cut to ~$9 shared until Sunday, so both boxes were stopped. Neither had finished an arm: Occam generation of 40,000
dreams took 96 min on the box, mostly rejection-sampling 5-step draws, which accept 0.14%. Fallback on Ben's Mac (CPU), one seed (0),
arms base, occam5_strict and occam_deep, `--reduced` (school 8,000 dreams, nightly 300, drawn programs <= 4 steps), every arm alike.
The same marks apply, read as one-seed evidence ("suggested", not "shown").

# Round 4: more nights (pre-registered 2026-10-24, before the run)
Read first: C2b's sealed H arm (hindsight relabelling of near-miss tries) already tested "near-miss practice" and stayed at N's level on
the hard kinds (s200: double_add first try H 1% vs W 17%; `creative/results/c2b/`), so that idea is not re-run. Only real fitting
tries (W records) have raised the hard kinds, and they grow night over night (base Hard ~1% before nights, 11-12% after two).
One change: 4 nights instead of 2 (night k samples with night k-1's model, same search, lr, visits). Arm `nights4` vs `base`,
seeds 0 and 1, full sizes, on Ben's PC. Marks: PASS if nights4 Hard >= base + 8 points with Easy within 5 and skills harm <= 2.
Proved wrong: nights4 Hard <= base + 2. Reported: Hard after nights 1, 2, 3, 4 (the curve).
