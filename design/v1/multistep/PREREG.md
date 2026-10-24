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

## Round 4 result (BensPC, 2026-10-24, 2 seeds, 49 min)
Hard: base 10.2, nights4 16.9 (+6.6); Easy 80.2 vs 82.0; harm 1.75 vs 1.25 pts. **NO PASS** (+8 needed), not proved wrong (> +2).
Curve, nights4: 6.2 / 11.3 / 13.4 / 16.9 after nights 1-4, still rising; affine ~0 in every arm and night.

# Round 5: eight nights (pre-registered 2026-10-24, before the run)
One change from nights4: 8 nights. Same seeds, run in round 4's OUT dir (base and nights4 reused). Marks: PASS if nights8 Hard >= base + 12
AND >= nights4 + 4, Easy within 5 of base, harm <= 2. Plateau: nights8 Hard <= nights4 + 1.5. Reported: the 8-night curve, affine separately.

# Round 6: hindsight records mixed into the nights (pre-registered 2026-10-24, before the run)
Source: GPT's second opinion on the dream-school results (ranked #1). It differs from C2b's H arm: C2b slept on H records instead of W
records; here W records stay as they are and hindsight records are added on top.
One change from nights4: arm `hind4`. Each night, for pool questions where search found NO fitting try, take up to 2 distinct tries
that run on every example, rewrite the prompt's example outputs to what each try computes (`fewshot.relabel_prompt`), and answer with
the try's own output. Multi-step tries (>= 2 steps) are preferred. The total is capped at the night's W record count, so W stays at
least half of the puzzle records. Reads no key and no kind. Same seeds (0, 1), 4 nights, round 4's OUT dir (base and nights4 reused).
Marks: PASS if hind4 Hard >= nights4 + 4 points, Easy within 5 of base, harm <= 2. Proved wrong: hind4 Hard <= nights4 + 1.
Reported: per-night curve; per-night W records by kind (does hindsight raise real fits on the hard kinds?); step-1 op entropy on 200
pool puzzles after N' and after each night.

Loss check (from the code, 2026-10-24): the oracle's "below 0" school loss is a logging offset, not a training bug. In
`custom_io/models/ledger.py` the pointer loss for a commutative op is `-logaddexp(lab, lba)`. When both operands are the same slot
(x*x, 2+2, x+x) then lab == lba, so the term is `-(lab + log 2)`: it can reach -0.69 per such step, while its gradient is unchanged.
Oracle programs use these steps often, so the logged loss goes below 0 once the rest is near 0.

# Round 7: composition dreams (pre-registered 2026-10-24, before any round 5/6 number was seen)
Source: GPT's #2, ranked #3 by the literature note (reviews/multistep-literature-2026-10-24.md). The affine diagnosis
(reviews/multistep-affine-diagnosis-2026-10-24.md) shows the 3 examples pin each rule down (ambiguity is not the cause), and affine
spends ~2.6 of its ~4 steps building A and B. Affine and double_add are compositions of the practised skills (mult then add, add then mult).
One change from nights4: arm `comp4`. Each night, add composition dreams: draw two programs P1, P2 from the model's own programs (the
warm-up's add/mult records and that night's W records), chain them (P1's answer becomes P2's input), execute on pool-like inputs (x in
3..29, every output 0..999), and train on (puzzle -> chained program) as forced-label records. Count capped at half the night's W records.
No answer key or kind of a held-out question is read. Same seeds (0, 1), 4 nights, same OUT dir as rounds 4-6.
Marks: PASS if comp4 Hard >= nights4 + 4 points AND affine >= 5%, Easy within 5 of base, harm <= 2. Proved wrong: comp4 Hard <= nights4 + 1.
sq_plus is the control kind (x*x is not a practised skill): report it separately. A pass is "learning by composing practised skills",
not zero-shot transfer to an unseen structure.

## Round 5 result (BensPC, 2026-10-24, 2 seeds; base and nights4 reused from round 4)
Hard: nights8 26.0 vs base 10.2 (+15.8) and nights4 16.9 (+9.1); Easy 83.8 vs 80.2; harm 2.25 pts (seeds 2.0, 2.5).
**NO PASS, on the harm mark only**: the Hard marks passed (+12 over base and +4 over nights4 both met), but harm was 2.25 against a limit of 2.
Not a plateau. Mean Hard by night: 4.7 / 12.1 / 16.6 / 20.4 / 24.1 / 26.0 / 25.8 / 26.0. It levels off after night 6.
Per kind after night 8: sq_plus 48.7, double_add 28.4, affine 1.0. Noise note: nights8's own night-4 score (20.4) differs from the
nights4 arm's (16.9) at the same settings and seeds (GPU nondeterminism), so differences of ~3-4 points between runs are within noise.

## Round 6 result (BensPC, 2026-10-24, 2 seeds; base and nights4 reused; raw files on branch claude/multistep-r6-pc-results @ 88cb479ef9d1)
Hard: hind4 18.2 vs nights4 16.9 (+1.3); Easy 80.6 vs base 80.2; harm 2.0. **NO PASS, between the marks** (pass needs +4, proved wrong
needs <= +1). This is within run-to-run noise (~3-4 points, see round 5). Curve: 4.2 / 9.9 / 15.7 / 18.2. Hindsight records were all
multi-step and shrank by night (seed 0: 813, 670, 532, 472). By night 4 ~70% of them came from affine questions, yet affine stayed at 0.6.
Reading (suggested): practice on puzzles the wrong tries happen to solve does not teach how to solve the real affine ones.

## Round 7 result (BensPC, 2026-10-24, 2 seeds; raw files on branch claude/multistep-r7-pc-results @ c641f51eaed8)
Hard: comp4 14.8 vs nights4 16.9 (-2.1); affine 2.3 (nights4 0.0; mark 5); Easy 80.1; harm 1.2. **PROVED WRONG** (Hard <= nights4 + 1).
sq_plus control 25.2 vs 28.1; double_add 17.0 vs 22.5. Caveat: the warm-up programs are long reference programs, so most composed
records were 6-7 steps (seed 0: 406, 651, 770, 836 per night). Composition from short programs only is untested.

# Round 8: a friendlier constant (pre-registered 2026-10-24, before the run)
Source: the affine diagnosis. ~2.6 of affine's ~4 steps only build A and B from {1, 2, 10, 100}, and 100 is almost never needed by C2
(B <= 30, A <= 9, outputs <= 999). One change: the constant set becomes {1, 2, 10, K}, replacing 100, so the slot count and the model's
shapes stay the same. Constant slots are value-coded, so the new slot's embedding follows from its value. K is 3 or 5, picked BEFORE
training by this rule: whichever gives the lower mean shortest-program length on the pool's affine questions (tie: 5).
Arm `const_nights4` = nights4 with the new constant set, everything else equal, seeds 0 and 1. It is compared with round 4's nights4
(16.9 Hard, affine 0.0), and base is re-run with the new set too (`const_base`).
Marks: PASS if const_nights4 Hard >= nights4 + 4 AND affine >= 5%, Easy within 5 of base, harm <= 2.
Proved wrong: affine <= 1% AND Hard <= nights4 + 1. Reported: shortest-length distribution per kind under each set, and the per-night curve.

## Round 8 constant pick (computed 2026-10-24, before any run; BFS shortest programs, `creative/rules_real.reference`, each set in a fresh subprocess with PREMO_CONSTS)
Shortest program length (steps) per question, held-out kinds on pool.jsonl (1,024 questions), add/mult on warm.jsonl. Length depends on the rule's parameters only (the canonical program is checked on the whole input domain); nothing was unrepresentable under any set.

| set | affine (n=205) mean | sq_plus mean | double_add mean | square | last_digit | warm add mean | warm mult mean |
|---|---|---|---|---|---|---|---|
| {1,2,10,100} (old) | 4.005 | 3.410 | 2.897 | 1.0 | 1.0 | 2.889 | 2.292 |
| {1,2,10,3} | **3.332** | 2.844 | 2.784 | 1.0 | 1.0 | 2.477 | 1.857 |
| {1,2,10,5} | 3.454 | 2.898 | 2.897 | 1.0 | 1.0 | 2.581 | 1.861 |

Length distributions (steps: count). Pool affine: old 3:32, 4:140, 5:33; K=3 2:14, 3:109, 4:82; K=5 2:9, 3:94, 4:102. Pool sq_plus: old 3:121, 4:84; K=3 2:32, 3:173; K=5 2:21, 3:184.
Pool double_add: old 2:21, 3:183; K=3 2:44, 3:160; K=5 2:21, 3:183 (same as old). Square and last_digit: 1 step for all 205, every set.
Warm add (1,024): old 1:34, 2:291, 3:454, 4:245; K=3 1:68, 2:400, 3:556; K=5 1:59, 2:399, 3:478, 4:88. Warm mult (1,024): old 2:725, 3:299; K=3 1:146, 2:878; K=5 1:142, 2:882.
Dev and labelled give the same picture (affine mean old 4.15 / 4.03, K=3 3.31 / 3.38, K=5 3.52 / 3.54).
**Rule result: K = 3** (affine 3.332 < 3.454; no tie). The constant set for Round 8 is {1, 2, 10, 3}.
Checks: the B2 checkpoint stores no constants (keys: model, name, cfg {copy: True}, chars, step), and the constant slots are value-coded, so B2 loads unchanged. Prompt numbers 3 and 5 now sit next to a constant slot; the data files are unchanged (rules_real still only excludes 2 and 10 as inputs), so a pool number can equal slot 19's value: the pointer then has two correct candidates, which the supervision already allows.
Skills replay (2,000-row sample of the skills train set; 136 dev in_dist rows): 16 train rows (0.8%) and 1 dev row need the constant 100 (percent rows, `x * p / 100`). Under the swap those rows lose their program; the run skips them from replay and counts them in train.json (`replay_skipped`) instead of training them program-less. Warm records: none fail (0 skipped). Dream caches and the shared setup (warm-up, N', setup.json, dev floors) of the new set live in OUT/s<seed>/const3/, never the old files. The dev/labelled questions all stay representable.
Kaggle repeat of round 6 (same-box base/nights4/hind4, 2 seeds, T4 shared with another job; files in /mnt/project-files/multistep/round6-kaggle/):
hind4 20.8 vs nights4 17.1 (+3.7), Easy 81.4 vs 77.8, harm 3.2 (fails <= 2). Also NO PASS, between the marks. Two machines: +1.3 and +3.7,
both short of +4, and harm was higher on Kaggle. Hindsight is at most a small gain at some cost to old skills.
