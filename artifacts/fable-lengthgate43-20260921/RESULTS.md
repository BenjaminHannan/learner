# Experiment 43A — length gate — RESULTS (registered; marks in PASSMARKS.md, sealed before the run)

Wave: 6 jobs, 10 min wall-clock, Mac CPU. All six runs valid (G0: lengths 4-8 >= 0.976).

Mean exact-match accuracy of the six OLD skills by input length (trained on lengths 4-8 only):

| Seed | Model | 4-8 | 9 | 10 | 12 | 16 |
|---|---|---|---|---|---|---|
| 4102 | control (registered base, probe) | 0.99 | 0.67 | 0.17 | 0.00 | — |
| 4102 | randpos | 1.000 | 0.807 | 0.520 | 0.000 | 0.000 |
| 4102 | randpos-loop | 0.988 | 0.455 | 0.103 | 0.000 | 0.000 |
| 4103 | control | 0.99 | 0.59 | 0.18 | 0.00 | — |
| 4103 | randpos | 0.993 | 0.573 | 0.398 | 0.033 | 0.000 |
| 4103 | randpos-loop | 0.985 | 0.768 | 0.470 | 0.013 | 0.000 |
| 4104 | control | 1.00 | 0.77 | 0.18 | 0.00 | — |
| 4104 | randpos | 0.978 | 0.648 | 0.435 | 0.032 | 0.000 |
| 4104 | randpos-loop | 0.976 | 0.658 | 0.420 | 0.013 | 0.000 |

| Mark | Verdict |
|---|---|
| G1 randpos length 10 >= 0.90, 3/3 | FAIL (0.52 / 0.40 / 0.44) |
| G2 randpos length 12 >= 0.80, 3/3 | FAIL (0.00 / 0.03 / 0.03) |
| G3 loop length 12 >= 0.80, 3/3 | FAIL |
| G4 loop beats separate blocks by 0.10 at length 12 | FAIL (no difference; loop has 1/4 the parameters and matched in 2 of 3 seeds at length 10, worse in seed 4102) |

What it means: randomised positions help a little one or two digits past training and not at all beyond. Sharing one block four times neither helped nor (in 2/3 seeds) hurt.
What it does not mean: it does not show looping is useless — these six skills do not need more steps for longer inputs, so looping had nothing to add here.

Probe after the run (no claim): at length 12 the first wrong answer digit is at place 1-3 in most cases and is almost never an early stop (<= 3 of 100). The model looks at the wrong input digit. Follow-up = Experiment 43C (segment-relative positions), marks in PASSMARKS-43C.md.

# Experiment 43C — segment-relative positions — RESULTS (marks in PASSMARKS-43C.md, sealed before the run)

Wave: 3 jobs, 10.5 min. Mean exact match of old skills (copy-like = ROTL1/INC3/SWAP; end-relative = REV/FOLD/REV+INC1):

| Seed | 4-8 (C0) | 9 all / copy / end | 10 all / copy / end | 12 | 16 |
|---|---|---|---|---|---|
| 4102 | 1.000 valid | 0.64 / 0.45 / 0.82 | 0.03 / 0.05 / 0.01 | 0.00 | 0.00 |
| 4103 | 0.656 INVALID | 0.05 / 0.00 / 0.10 | 0.00 | 0.00 | 0.00 |
| 4104 | 1.000 valid | 0.72 / 0.65 / 0.79 | 0.12 / 0.11 / 0.13 | 0.00 | 0.00 |

C1 FAIL, C2 FAIL, C3 FAIL, C4 FAIL (every valid seed 0.00 at length 12). Seed 4103 did not finish learning the trained lengths in 12,000 updates (invalid, shown, no claim).
It is WORSE than 43A's randomised positions at length 10 (0.03-0.12 vs 0.40-0.52).

Probe (no claim), skill "+3 to every digit", length 12: the model stops at the right place (end mark 100%), gets answer places 0-1 right, and places 2-11 at 10-40%. So it is NOT using "copy the digit with my number" even though that was made available. It learned some length-dependent way of finding the source digit, shared with the count-from-the-end skills, and that breaks at unseen lengths.

What it means: giving the model convenient position numbers is not enough; gradient descent on lengths 4-8 does not choose the length-general way of addressing. Sealed reading rule applies: next rung = relative-position ATTENTION (the attention score itself depends on distance), which removes the length-dependent option instead of merely offering a better one.
What it does not mean: nothing here is about sleep. Two quick position changes failing does not show the length goal is unreachable; published results reach 2-5x length on copy/reverse/addition, but with relative attention, index hints and many seeds.

# Experiment 43D — relative-position attention — RESULTS (marks in PASSMARKS-43D.md, sealed before the run)

Wave: 6 jobs, 11.5 min. All six runs valid (D0: lengths 4-8 >= 0.993). Exact match per skill, seeds 4102 / 4103 / 4104.

rel-both (start + end index differences):

| Length | INC3 | ROTL1 | REV | REV+INC1 | SWAP | FOLD |
|---|---|---|---|---|---|---|
| 10 | 0.99 / 1.00 / 1.00 | 0.12 / 0.47 / 0.57 | 1.00 / 0.64 / 1.00 | 0.98 / 0.72 / 1.00 | <= 0.09 | <= 0.01 |
| 12 | 0.91 / 0.90 / 0.82 | 0.01 / 0.01 / 0.55 | 0.93 / 0.37 / 0.95 | 0.94 / 0.44 / 0.99 | <= 0.02 | 0.00 |
| 16 | 0.56 / 0.32 / 0.02 | 0.00 | 0.31 / 0.02 / 0.19 | 0.30 / 0.05 / 0.45 | 0.00 | 0.00 |

rel-start (start index differences only):

| Length | INC3 | ROTL1 | REV | REV+INC1 | SWAP | FOLD |
|---|---|---|---|---|---|---|
| 10 | 1.00 / 1.00 / 1.00 | 0.96 / 0.87 / 0.98 | 0.08 / 0.18 / 0.62 | 0.38 / 0.11 / 0.26 | <= 0.16 | 0.00 |
| 12 | 0.53 / 0.99 / 1.00 | 0.55 / 0.41 / 0.80 | 0.00 | 0.00 | <= 0.05 | 0.00 |
| 16 | 0.01 / 0.89 / 0.97 | 0.05 / 0.04 / 0.10 | 0.00 | 0.00 | 0.00 | 0.00 |

| Mark | Verdict |
|---|---|
| D1 rel-both INC3+ROTL1 >= 0.90 at 12 and 16, 3/3 | FAIL |
| D2 rel-both REV+REV/INC1 >= 0.90 at 12 and 16, 3/3 | FAIL (length 12 reached 0.93-0.99 in 2 of 3 seeds) |
| D3 rel-start INC3+ROTL1 >= 0.90 at 12 and 16, 3/3 | FAIL (INC3 alone: 2 of 3 seeds at 0.89-1.00 even at length 16) |
| D4 all-six mean >= 0.80 at 12 | FAIL (0.47 / 0.29 / 0.56) |

Sealed reading rule: "D1 fail -> stop position work and wait for the outside review." That rule is followed.

What it means: every registered mark failed, so no claim. But this is the first change that moved length 12 off zero: before it, all six skills were 0.00-0.03 at length 12 in every model; now reverse is 0.93-0.95 and +3 is 0.82-1.00 in most seeds. As predicted in advance, reverse needs the end-index signal (0.00 without it), and SWAP / FOLD stay at zero (a capped distance carries no odd/even or halving information).
Probe (no claim), rel-both seed 4104, length 16, each answer place judged with the correct prefix: +3 skill is 0.93-1.00 at places 0-13 and fails only at the LAST TWO places (0.08, 0.24); reverse is 0.77-1.00 at places 0-13 and 0.29 at place 14. So the per-digit procedure carries to 2x length; what breaks is the handling near the end of the answer, and it is seed-fragile.
What it does not mean: not a pass, not robust (three seeds disagree), nothing about sleep, toy only.
