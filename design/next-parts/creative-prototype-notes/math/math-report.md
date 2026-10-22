# Math report: target puzzles, chance floors and power (2026-10-03)

CPU-only analysis. No repo files edited, no training, no GPU, no money, no eval or reserved panels opened.
Every number carries a label: **[computed]** = produced by the scripts in this folder (exact enumeration, or
Monte Carlo where stated); **[assumed]** = an input I chose or the brief gave. Code facts quoted from
`../pipeline_code/` are marked **[code]**.

## Plain-language summary for Ben

- Puzzles like "use 7, 12 and 30 to make 25" are rare among random number/target pairs: only about 2% (2 numbers),
  4% (3 numbers) and 7% (4 numbers) of pairs have an answer [computed]. So the generator must pick targets that
  work, and it can: there are thousands to millions of different solvable puzzles [computed].
- Almost every solvable puzzle has exactly one real answer (one choice of which numbers get a plus or a minus),
  97 to 100% of the time [computed]. The many "different solutions" are mostly the same sum done in a different
  order. Counting call orders as different answers would fake creativity.
- A monkey pressing the calculator buttons at random solves a 2-number puzzle about 1 time in 20, a 3-number
  puzzle about 1 time in 200, and a 4-number puzzle about 1 time in 6,000 [computed]. With 32 tries per puzzle it
  reaches about 70%, 15% and 0.5% of puzzles [computed]. So 2 numbers is a warm-up, 3 is practice, and 4 is a real
  test where luck alone almost never wins.
- The strict checker (every number used once, answer comes out last) is the right one. The loose checker accepts
  a "make 40 from 5, 9, 23, 31" answer of 9 + 31, ignoring two numbers. About a quarter of 4-number puzzles that have no
  real answer still have such a loose answer it would accept [computed].
- For word problems with one correct call, random button-pressing gets the call exactly right 1 time in 6, and
  a random final number from the 27 "familiar" numbers is right 1 time in 27 (never, if the right answer is not one
  of the 27) [computed]. With 32 tries the call is almost always right by luck (99.7%) [computed], so call
  correctness with 32 samples is useless as a "luck" score.
- Power: with 256 fresh puzzles and a required gain of 10 points, two seeds per arm work if seeds differ by about
  3 points (false pass 1.0%, catches a real 15-point gain 87% of the time) [computed]. If seeds differ by about 5
  points, it catches it only 78% of the time; then use 3 seeds per arm and require each B seed to beat the control
  average (1.9% false pass, 85% catch) [computed]. A real 10-point gain is caught only about half the time
  [computed], so "not passed" will not mean "no effect".

---

## 0. Setup, assumptions and checks

**Tool rules used** [code]: 4 loops; each loop NONE, ADD or SUB; ADD/SUB take two references with different ids
(`DUPLICATE_REFERENCE` otherwise); references are the integer literals found mechanically in the question (max 8)
plus earlier OK results (max 3 prior results); ERROR and NONE add no reference.

**A1. Usable results 0..99** [assumed, from the brief]. Negative results and results of 100 or more are ERROR.
*Flag, found while checking* [computed, `tok_check.py`]: the runtime copy keeps a result only if
`tokenizer.encode(str(r))` is one token that decodes back to `str(r)` [code]. With the public
`LiquidAI/LFM2.5-1.2B-Instruct` `tokenizer.json` (downloaded from the Hugging Face main branch), **every integer
0..999 is one token, and no negative is** [computed]. So unless Ben's PC has another range check, results 100..999
would be OK, not ERROR. This must be checked on the PC (tokenizer revision and runtime). Part 1 reports the 0..999
case as a sensitivity.

**A2. The target is a reference** [assumed, follows from the code]. "to make 25" puts the literal 25 in the
question, and `build_registry` turns every integer literal into a reference [code]. So with k given numbers there
are k + 1 starting references. A checker must therefore reject any tree that uses the target literal as a leaf
(otherwise (25 + 12) - 12 "makes 25"). The question template must contain no other digits.

**A3. Random policy** [assumed, from the brief]: each loop picks NONE, ADD, SUB with probability 1/3 each, then a
uniformly random ordered pair of *different* references among those available. Note [code]: the real runtime has
two independent pointer heads and uses argmax; no sampling exists today. If sampling is added as two independent
draws, left = right is possible and gives `DUPLICATE_REFERENCE`. That "independent pointers" variant is a
sensitivity.

**A4. Instances** [assumed]: k distinct numbers from 2..40 or 2..60, target 0..99. In Part 1a every (set, target)
pair is counted, including targets equal to a given number; the tiers in 1c exclude those.

**Checkers** (definitions from the brief, implemented by literal identity, not by value):
- STRICT: the OK calls form one tree; every given number is a leaf exactly once; the target literal is never a leaf;
  every intermediate result is used exactly once later; the last OK result equals the target. NONE or ERROR may fill
  the other loops. Any OK call after the tree is finished breaks it.
- STRICT-STOP (extra, for comparison): like STRICT, but loops after the finishing call are ignored.
- LENIENT: some OK result equals the target, and its tree uses each given number at most once, at least two
  numbers, and never the target literal.

**Checks that the math is right** [computed, `validate_tool.py`, `validate_tool.out`]: I drove the real
`execute_integer_call` from `calculator_tools.py` with the random policy (60,000 runs per case, 5 cases, both
pointer modes), scored them with checkers written separately from the main code (tree rebuilt from
`operand_references`), and compared with the exact formula. All agree within Monte Carlo noise, for example
(7, 12) to 19: real tool 0.0514 vs exact 0.0511; (11, 4, 20) to 27: 0.0038 vs 0.0041. On every Part 1 sample the
Monte Carlo STRICT mean differs from the exact mean by less than 1e-4 [computed].

---

## Part 1. Target puzzles

### 1a. How many puzzles have a solution, and how many solutions (STRICT, results 0..99)

Every k-subset of the range times every target 0..99 [computed, `part1_counts.py`, exact enumeration].

| k | numbers | number sets | (set, target) instances | solvable | solvable targets per set |
|---|---|---|---|---|---|
| 2 | 2..40 | 741 | 74,100 | 2.00% (1,482) | 2.00 |
| 2 | 2..60 | 1,711 | 171,100 | 1.94% (3,312) | 1.94 |
| 3 | 2..40 | 9,139 | 913,900 | 3.97% (36,319) | 3.97 |
| 3 | 2..60 | 32,509 | 3,250,900 | 3.56% (115,885) | 3.56 |
| 4 | 2..40 | 82,251 | 8,225,100 | 7.60% (624,746) | 7.60 |
| 4 | 2..60 | 455,126 | 45,512,600 | 6.57% (2,988,746) | 6.57 |

Every number set has at least one solvable target [computed]. Small targets are easier: for k = 4, 2..60 the
solvable share is 8.0% for targets 0..9, 7.8% for 10..49 and 5.3% for 50..99 [computed].

Number of distinct solutions per solvable instance [computed]. "Trajectories" = distinct ordered sequences of OK
calls (where the NONE/ERROR loops fall is ignored). "Trees" = distinct expression trees up to swapping the two
sides of an ADD. "Sign patterns" = which numbers are added and which subtracted, i.e. genuinely different
arithmetic.

| k | numbers | trajectories: mean, median, 10th to 90th pct, max | trees: mean, median, 10th to 90th, max | exactly one sign pattern |
|---|---|---|---|---|
| 2 | 2..40 | 1.50, 1.5, 1 to 2, 2 | 1.00, 1, 1 to 1, 1 | 100% |
| 2 | 2..60 | 1.48, 1, 1 to 2, 2 | 1.00, 1, 1 to 1, 1 | 100% |
| 3 | 2..40 | 6.75, 6, 4 to 12, 12 | 3.03, 3, 3 to 3, 6 | 99.1% |
| 3 | 2..60 | 6.07, 5, 4 to 12, 12 | 2.97, 3, 3 to 3, 6 | 99.3% |
| 4 | 2..40 | 59.6, 52, 34 to 108, 144 | 15.5, 15, 15 to 15, 36 | 97.1% |
| 4 | 2..60 | 48.4, 44, 32 to 72, 144 | 14.6, 15, 12 to 15, 36 | 97.8% |

Trajectory-count buckets [computed]: k = 2: exactly 1 (a SUB) about 50%, exactly 2 (an ADD, either order) about
50%. k = 3, 2..40: 3 to 4 trajectories 24%, 5 to 10 51%, more than 10 25% (2..60: 32%, 52%, 16%). k = 4: always
more than 10.

What this means: a typical sign pattern has 3 valid trees (k = 3) or 15 (k = 4) [computed], and each tree can be
run in several call orders. These are re-orderings of one answer. A diversity score should count sign patterns (or
trees at most), never call trajectories, in the same way the v6 doc says multiple spellings of one number are
artificial diversity.

Results 0..999 instead of 0..99 [computed]: the solvable instances are exactly the same for all six rows (no
solution needs an intermediate of 100 or more that cannot be reordered). Trajectory counts rise slightly (k = 4,
2..60: mean 48.4 to 51.5; k = 3, 2..60: 6.07 to 6.17).

### 1b. Random policy: chance of an accepted trajectory in 4 loops

2000 instances drawn uniformly from the STRICT-solvable (set, target) pairs (all 1,482 for k = 2, 2..40)
[assumed sampling]. STRICT and STRICT-STOP are exact per instance; LENIENT is Monte Carlo with 4,096 runs per
instance [computed, `part1_random.py`]. pass@k = mean over instances of 1 - (1 - p)^k.

| k | numbers | STRICT mean p | median | 10th to 90th pct | pass@1 | pass@8 | pass@32 |
|---|---|---|---|---|---|---|---|
| 2 | 2..40 | 4.39% | 3.8% | 2.6% to 6.0% | 4.39% | 28.8% | 70.1% |
| 2 | 2..60 | 6.42% | 4.7% | 2.6% to 18% | 6.42% | 36.7% | 74.5% |
| 3 | 2..40 | 0.510% | 0.38% | 0.27% to 0.94% | 0.510% | 3.98% | 14.7% |
| 3 | 2..60 | 0.529% | 0.41% | 0.27% to 1.1% | 0.529% | 4.13% | 15.2% |
| 4 | 2..40 | 0.0180% | 0.015% | 0.0099% to 0.042% | 0.0180% | 0.147% | 0.587% |
| 4 | 2..60 | 0.0160% | 0.014% | 0.010% to 0.023% | 0.0160% | 0.128% | 0.511% |

| k | numbers | STRICT-STOP mean | pass@8 | pass@32 | LENIENT mean | pass@8 | pass@32 |
|---|---|---|---|---|---|---|---|
| 2 | 2..40 | 15.9% | 71.9% | 98.5% | 21.8% | 82.7% | 99.7% |
| 2 | 2..60 | 17.2% | 73.3% | 98.5% | 22.4% | 83.1% | 99.7% |
| 3 | 2..40 | 0.885% | 6.81% | 24.0% | 1.91% | 13.0% | 37.5% |
| 3 | 2..60 | 0.851% | 6.56% | 23.3% | 1.73% | 11.8% | 34.8% |
| 4 | 2..40 | 0.0230% | 0.180% | 0.717% | 0.911% | 5.66% | 12.4% |
| 4 | 2..60 | 0.0190% | 0.153% | 0.610% | 0.604% | 3.81% | 8.67% |

No solvable instance has p = 0 under STRICT [computed]. (For LENIENT at k = 4, 24% and 32% of instances had no hit
in 4,096 runs, but LENIENT always accepts whatever STRICT accepts, so their true p is small, not zero.)

Why STRICT is so much lower than STRICT-STOP at k = 2: after the answer is made, the random policy keeps calling
on 2 of every 3 loops, and any further OK call breaks the "last OK result" rule. A trained worker is taught to
choose NONE after success (v6 supervision), so this gap measures stopping, not finding.

On average p rises with the number of solution trajectories [computed]: k = 3, 2..40: 0.27% (3 to 4
trajectories), 0.39% (5 to 8), 1.03% (9 to 12); k = 4, 2..60: 0.0096% (13 to 32), 0.015% (33 to 64), 0.034%
(65 to 144).

Sensitivities, first 500 instances of each sample, STRICT mean p [computed]:

| k | numbers | main | results 0..999 | independent pointers | target not a reference |
|---|---|---|---|---|---|
| 2 | 2..40 | 4.54% | 3.81% | 6.20% | 13.2% |
| 2 | 2..60 | 6.34% | 3.74% | 7.37% | 15.7% |
| 3 | 2..40 | 0.505% | 0.453% | 0.427% | 1.59% |
| 3 | 2..60 | 0.528% | 0.422% | 0.427% | 1.62% |
| 4 | 2..40 | 0.0178% | 0.0170% | 0.0117% | 0.0607% |
| 4 | 2..60 | 0.0156% | 0.0151% | 0.0101% | 0.0528% |

The target literal costs the random policy a factor of 2.5 to 3.4 [computed], because it is one more thing to point
at and any OK call that touches it is a failure. The 0..999 question lowers k = 2 by up to about 40% and k = 3, 4 by
3% to 20% [computed].

### 1c. Which checker: STRICT

1. STRICT is the puzzle as written ("each exactly once"). LENIENT is a different, easier puzzle (subset sums).
   Over all instances, LENIENT-solvable vs STRICT-solvable is 9.7% vs 4.0% (k = 3, 2..40) and 28.9% vs 6.6%
   (k = 4, 2..60) [computed; all 9,139 sets for k = 3, 20,000 sampled sets for k = 4]. Among instances with **no** STRICT solution, 5.9% (k = 3)
   and 23.9% (k = 4) are LENIENT-solvable, and the random policy gets a LENIENT accept on them 11.9% and 4.4% of the
   time [computed]. Those accepts are answers to a puzzle that was not asked.
2. At k = 4, LENIENT raises the random hit rate from 0.016% to 0.60% (2..60) [computed], almost all through
   shortcuts: when instances with a proper-subset shortcut are removed (tier T below), LENIENT is 0.025% vs STRICT
   0.016% [computed]. So LENIENT mostly rewards ignoring numbers.
3. STRICT is checkable mechanically from the trace (literal ids and `operand_references`), needs no answer key
   beyond the target in the question, and is the natural "goal predicate" the v6 doc allows for restricted formal
   tasks.

Use STRICT to accept TRAIN experiences and to score. Report STRICT-STOP next to it as a diagnostic ("found it but
kept calling"). LENIENT is at most a near-miss or relabelling signal (a LENIENT hit is a correct answer to the
*smaller* puzzle it actually solved, which is how Hindsight Experience Replay would relabel it), never acceptance.

### 1d. Difficulty knob

What moves the random hit rate [computed, tables above]:
- **k is the main knob.** STRICT mean p: about 5% (k = 2), 0.5% (k = 3), 0.017% (k = 4): each extra number divides
  it by about 10 and then about 30.
- **Range hardly matters for STRICT** (k = 3: 0.51% vs 0.53%; k = 4: 0.018% vs 0.016%), but a wider range gives
  more instances and a lower solvable share.
- **Within a tier**, more solution trajectories means easier (up to about 4x, see 1b).
- **Shortcut filter** (no proper subset of 2 or more numbers reaches the target) makes LENIENT and STRICT nearly
  agree and removes "stop early" hits.
- **Order-forced filter** (fewer valid trees than the same sign pattern allows with no upper cap, i.e. some
  orderings of the one answer pass 99, so the order must be planned; for k = 4 this slightly undercounts, because
  a few sign patterns allow 18 trees instead of 15 [computed]): 0% of tier P (k = 3, 2..40, where no sum can pass
  99), 5% of P' (2..60) and 25% of T (k = 4, 2..60) [computed]. It barely changes the random rate
  (0.0161% to 0.0153% at k = 4) [computed], so it is a "planning" flavour, not a difficulty dial.

Proposed tiers (generation rules) with counts and random-policy floors, 2000 instances drawn per tier, STRICT
exact, LENIENT Monte Carlo [computed, `part1_tiers.py`]:

| Tier | Rule | distinct instances (canonical) | number sets | STRICT mean | pass@8 | pass@32 | STOP mean | LENIENT mean |
|---|---|---|---|---|---|---|---|---|
| W warm-up | k = 2, distinct numbers 2..60, target = a + b (if at most 99) or larger minus smaller, target not equal to a given number | 3,283 | 1,711 | 6.51% | 37.1% | 75.0% | 17.3% | 22.6% |
| P practice | k = 3, distinct 2..40, STRICT-solvable target 0..99, target not a given number, no 2-number shortcut | 33,670 | 9,139 | 0.544% | 4.24% | 15.6% | 0.933% | 1.40% |
| P' (wider) | same with 2..60 | 109,597 | 32,501 | 0.547% | 4.27% | 15.7% | 0.872% | 1.26% |
| T transfer | k = 4, distinct 2..60, STRICT-solvable target, target not a given number, no shortcut of 2 or 3 numbers | 2,318,380 | 454,597 | 0.0161% | 0.128% | 0.513% | 0.0191% | 0.0253% |
| T+ (harder) | T plus order-forced | 569,345 | 253,832 | 0.0153% | 0.122% | 0.488% | 0.0175% | 0.0225% |

Practical rules for all tiers [assumed, design advice]: enumerate the whole pool, shuffle once with a fixed seed,
split by canonical form; show the numbers in a random order; template "Use A, B and C, each exactly once, adding or
subtracting, to make T." with no other digits; keep at most 8 literals (k at most 7). If TRAIN uses W and P only,
T tests a deeper composition (3 calls) that was never trained, and luck alone reaches only about 0.5% of T
puzzles in 32 tries [computed], so plain sampling gives almost no cold-start signal there.

### 1e. How many distinct instances per tier

Canonical form = sorted multiset of numbers plus target. Pool sizes [computed]: W 3,283; P 33,670; P' 109,597;
T 2,318,380; T+ 569,345. W is the only tight pool: with a TRAIN of 1,000 W instances, 2,283 remain, about 8
disjoint fresh sets of 256 [computed]. For extra room, W with numbers 2..99 gives 7,009 instances, 10..99 gives
5,565 [computed]. If "disjoint" should also mean "no shared number set" (stricter, since each W number pair has up
to two targets), the W pool is 1,711 pairs [computed]. The W pool also overlaps in spirit with the queued
512-numeric-pair curriculum, so the canonical check should run across both.

---

## Part 2. Word problems with one correct call

Two literals in the question; the right call is a fixed op with a fixed order [assumed]. Random policy as in A3.
Exact fractions [computed, `part2_word.py`].

| Event (random policy) | distinct pointers (brief) | independent pointers |
|---|---|---|
| Loop-1 call exactly right (action and ordered references) | 1/6 = 16.7% | 1/12 = 8.3% |
| Loop-1 right value, ADD problem (either order works) | 1/3 = 33.3% | 1/6 = 16.7% |
| Loop-1 right value, SUB problem | 1/6 = 16.7% | 1/12 = 8.3% |
| First non-NONE call is exactly right (within 4 loops) | 20/81 = 24.7% | 10/81 = 12.3% |
| Exactly right call in any of the 4 loops, ADD / SUB | 37.7% / 44.6% | 25.6% / 27.0% |
| Right value from some OK call in 4 loops, ADD / SUB | 69.1% / 44.9% | 48.5% / 27.1% |

The "any loop" rows use an assumed operand mix (a, b in 10..89, answer 10..99, 60 problems per op) [assumed]; the
other rows do not depend on the numbers.

Final number drawn at random [computed]:

| Per-sample chance | p | pass@8 | pass@32 |
|---|---|---|---|
| Call exactly right (loop 1) | 16.7% | 76.7% | 99.7% |
| Final from the 27-number shelf, right answer on the shelf | 1/27 = 3.70% | 26.1% | 70.1% |
| Final from the shelf, right answer off the shelf | 0 | 0 | 0 |
| Final from the shelf, set where half the answers are off the shelf (like F1: 64 of 128) | 1.85% | 13.0% | 35.1% |
| Final uniform on 0..99 | 1.00% | 7.7% | 27.5% |
| Call right AND final right (shelf, on shelf), independent | 0.62% | 4.8% | 18.0% |
| Call right AND final right (0..99), independent | 0.17% | 1.3% | 5.2% |

Notes. (1) The calls are chosen before the LM decodes and today by argmax [code], so if only LM temperature is
sampled, the call is the same in all k samples and the call rows do not apply; only the final-number rows do.
(2) Any luck metric built on the call alone saturates at 32 samples (99.7% by chance) [computed]; a luck metric
should use the final number, or STRICT puzzles with k of 3 or more.

---

## Part 3. Power of the two-seed rule

**Rule tested** (from the brief): PASS if mean(B) - mean(control) >= M points AND every B seed scores above every
control seed. Two seeds per arm unless stated.

**Noise model** [assumed]: each seed's true rate = base + gain (B only) + a seed effect drawn from Normal(0, SD),
SD = 3 or 5 points, clipped to 0..100%; its score on n fresh puzzles is Binomial(n, rate) / n. The four models are
scored independently. In reality they share the same puzzles, and shared puzzle difficulty cancels part of the
noise in B minus control, so these numbers are on the cautious side (untested how much). 200,000 simulated
experiments per cell [computed, `part3_power.py`]. "False pass" = pass rate when the true gain is 0 (worst of
base 10%, 30%, 50%); "power" = pass rate at a true gain (worst of the three bases).

### 3a. Greedy score, 2 seeds per arm [computed]

| n | M | SD 3: false pass | power +5 | +10 | +15 | SD 5: false pass | power +5 | +10 | +15 |
|---|---|---|---|---|---|---|---|---|---|
| 128 | 8 | 5.7% | 22% | 60% | 87% | 8.9% | 26% | 53% | 78% |
| 128 | 10 | 2.9% | 11% | 48% | 81% | 5.9% | 18% | 46% | 73% |
| 128 | 12 | 1.2% | 5% | 33% | 71% | 3.4% | 11% | 36% | 66% |
| 192 | 8 | 4.1% | 21% | 64% | 92% | 8.0% | 26% | 56% | 82% |
| 192 | 10 | 1.6% | 9% | 49% | 85% | 4.6% | 17% | 47% | 76% |
| 192 | 12 | 0.5% | 3% | 30% | 73% | 2.3% | 9% | 35% | 67% |
| 256 | 8 | 3.1% | 21% | 67% | 94% | 7.3% | 26% | 57% | 84% |
| 256 | 10 | 1.0% | 8% | 49% | 87% | 4.0% | 16% | 47% | 78% |
| 256 | 12 | 0.3% | 3% | 29% | 76% | 2.0% | 9% | 35% | 68% |

Per-base values (base 10%, 30%, 50% separately) are in `part3_tables.out` [computed]. In every row shown, the worst
base is 50% for false pass and 30% or 50% for power [computed].

What the table says:
- **Seed SD 3:** (n = 192, M = 8), (n = 192, M = 10), (n = 256, M = 8) and (n = 256, M = 10) all meet "false pass
  at most 5% and power at least 80% at +15" [computed]; (n = 128, M = 10) just does (2.9%, 81%).
- **Seed SD 5:** nothing with n up to 256 meets both under this rule [computed]. M = 8 lets noise pass 7% to 9% of
  the time; M = 10 has 73% to 78% power. The seed noise, not the puzzle count, is the limit: even n = 512 gives
  only 80% at M = 10 [computed]. Extra cells [computed, `part3_extra.py`]: n = 256, M = 9: 5.4% and 81% (fails
  false pass by a hair); n = 384, M = 9: 4.8% and 83% (meets both).
- **A real +10 gain passes only about half the time, and +5 rarely (3% to 26%)** [computed]. The rule is built to
  confirm big gains only. A smaller real effect will usually read "not passed", which is not "no effect".

### 3b. More seeds: the "every B seed beats every control seed" clause works against you

With 3 or 4 seeds per arm and the brief's clause, power at +15 *drops* (SD 5, n = 256, M = 10: 78% with 2 seeds,
74% with 3, 67% with 4) [computed, `part3_extra.py`], because more pairs must all go the right way. If more seeds
are used, the clause should be loosened. Tested alternative [computed, `part3_rules.py`; the rule change itself is
a suggestion, untested in practice]: **"mean(B) - mean(control) >= M AND every B seed beats the control mean"**.

| Seeds per arm | n | M | Clause | SD 3: false / power +15 | SD 5: false / power +15 |
|---|---|---|---|---|---|
| 2 | 256 | 10 | brief (every B > every control) | 1.0% / 87% | 4.0% / 78% |
| 2 | 384 | 9 | brief | 1.0% / 93% | 4.8% / 83% |
| 3 | 192 | 10 | every B > control mean | 0.4% / 91% | 2.3% / 83% |
| 3 | 256 | 10 | every B > control mean | 0.2% / 92% | 1.9% / 85% |
| 4 | 256 | 10 | every B > control mean | 0.1% / 95% | 0.8% / 87% |

(Under no real gain, the brief's clause alone holds by luck 1 time in 6 with 2 seeds, 1 in 20 with 3 and 1 in 70
with 4 [computed: S!S!/(2S)!]; it gets very strict as seeds are added. In the alternative clause the mark M does
the work of keeping false passes low, as the table shows.)

### 3c. pass@8 luck metric (32 samples per puzzle, puzzle is the unit)

Each puzzle gets one number, the unbiased pass@8 estimate from its 32 samples; the arm score is the mean over n
puzzles. The puzzle, not the sample, is the unit: 32 x n samples are not 32 x n independent tries.
- Upper bound [computed, exact]: any per-puzzle score between 0 and 1 with mean L has variance at most L(1 - L), the
  same as a greedy right/wrong. So, with the same base and gain in pass@8 points, pass@8 is never noisier per
  puzzle than greedy, and the greedy table above is a safe stand-in (the "bound" model reproduces it within 1 point
  [computed]).
- With an assumed spread of puzzle difficulty (each puzzle's per-sample success ~ Beta with total weight 1, "beta1",
  or 4, "beta4") [assumed], the per-puzzle variance is 0.74 to 0.80 (beta1) or 0.54 to 0.64 (beta4) times the bound
  for levels 10% to 65% [computed]. A full per-puzzle simulation (32 samples each, 4,000 experiments) matches the
  quick normal model within 0.7 points in 3 test cells [computed].

pass@8, beta1 model, 2 seeds per arm, worst of base 10/30/50 [computed]:

| n | M | SD 3: false pass | power +5 | +10 | +15 | SD 5: false pass | power +5 | +10 | +15 |
|---|---|---|---|---|---|---|---|---|---|
| 128 | 8 | 4.6% | 22% | 63% | 91% | 8.3% | 26% | 56% | 82% |
| 128 | 10 | 2.0% | 10% | 49% | 84% | 5.1% | 17% | 47% | 76% |
| 128 | 12 | 0.7% | 4% | 31% | 73% | 2.7% | 10% | 35% | 67% |
| 192 | 8 | 3.1% | 20% | 66% | 94% | 7.4% | 26% | 58% | 84% |
| 192 | 10 | 1.0% | 9% | 49% | 88% | 4.2% | 17% | 47% | 78% |
| 192 | 12 | 0.3% | 3% | 30% | 76% | 2.0% | 9% | 35% | 68% |
| 256 | 8 | 2.3% | 19% | 68% | 95% | 6.8% | 26% | 59% | 85% |
| 256 | 10 | 0.6% | 8% | 50% | 89% | 3.6% | 16% | 48% | 79% |
| 256 | 12 | 0.1% | 2% | 29% | 77% | 1.7% | 9% | 35% | 69% |

Same story as greedy: fine at seed SD 3 from n = 128 (M = 10); at seed SD 5 no n up to 256 passes both marks with
2 seeds (n = 384, M = 10: 3.2% and 80%) [computed]. Assumption to flag [assumed]: the seed SD of pass@8 is taken
equal to greedy's; it is unknown. Also remember the chance floor inside pass@8: on tier P puzzles the random policy
alone has pass@8 = 4.2%, on W 37% [computed, Part 1].

### 3d. Recommendation

- **Recommended: n = 256 fresh puzzles, M = 10 points** [computed basis above]. With 2 seeds per arm it keeps the
  false-pass rate at or below 4.0% for both seed SDs and has 87% power at +15 if the seed SD is about 3; at seed SD 5
  power is 78%, just short.
- **If the seed SD is near 5** (plausible: the old blurt-2 gain moved from +11 to +6 on a repeat), 2 seeds cannot
  reach the marks at n up to 256. What is needed: **3 seeds per arm with the clause "every B seed beats the control
  mean"**, n = 256, M = 10: 1.9% false pass and 85% power at SD 5 (0.2% and 92% at SD 3) [computed]. Or, keeping 2
  seeds and the brief's clause, n = 384 with M = 9 (4.8% and 83%) [computed].
- **Measure the seed SD first, before fixing the mark**: the control arm's two seeds plus the existing checkpoints
  give a rough value. Fix (n, M, seeds, clause) in writing before any arm is scored.
- What would prove the plan wrong: if the two control seeds differ by more than about 16 points on 256 puzzles
  (2 standard deviations of that difference at seed SD 5 plus binomial noise, which is 7.5 to 8.3 points
  [computed]), the seed SD is probably above 5 and none of these marks hold. One pair is weak evidence, so treat it
  as a warning, not a measurement.

---

## What this means for the creative experiment (suggested, not tested)

- Score target puzzles with STRICT by literal identity; never by value alone (the target literal is pointable).
- Count diversity by sign pattern. At k = 3 and 4 nearly every puzzle has one sign pattern [computed], so on these
  puzzles "creativity" can only mean finding the one answer more often, not finding new answers to one puzzle.
- Tier W is solved by chance 75% of the time in 32 tries [computed]: useful as warm-up, useless as evidence. Tier P
  gives a usable cold-start signal (16% of puzzles reached in 32 random tries) [computed]. Tier T is where luck is
  near zero (0.5%) [computed], so a T gain is hard to explain by sampling alone.
- Before any of this: check on the PC whether results 100..999 are accepted (A1), and add head sampling, since
  argmax calls cannot produce pass@k at all [code].

## Files (all in this folder)

| File | What it does |
|---|---|
| `common.py` | tree enumeration, exact STRICT/STOP recursion, vectorised Monte Carlo of the random policy |
| `tok_check.py` | which integers are one LFM2.5 token (public tokenizer file in `tok/`) |
| `validate_tool.py`, `validate_tool.out` | real `execute_integer_call` + independent checkers vs exact values |
| `sanity.py` | tree counts (k = 2, 3, 4: 4, 48, 1152 trajectories; 3, 27, 405 trees; 3, 7, 15 sign patterns) and small checks |
| `part1_counts.py`, `part1_counts.json`, `counts_*.npz` | Part 1a, all instances |
| `part1_random.py`, `part1_random.json` | Part 1b, random policy, sensitivities, LENIENT vs STRICT |
| `part1_tiers.py`, `part1_tiers.json` | Part 1c/1d tiers |
| `part2_word.py`, `part2_word.json` | Part 2 |
| `part3_power.py`, `part3_power.json`, `part3_tables.py`, `part3_tables.out`, `part3_compact.py`, `part3_compact.out` | Part 3 main grid |
| `part3_extra.py`, `part3_extra.json`, `part3_rules.py`, `part3_rules.json` | Part 3 extra cells and alternative clause |

Python 3.11 with numpy 2.4.6, scipy 1.17.1, tokenizers in a scratch venv (`venv/`). Random seeds are fixed in each
script.
