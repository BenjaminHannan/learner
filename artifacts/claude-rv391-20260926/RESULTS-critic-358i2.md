# rv-391 dev 2 results on the retrained nets: the learned critic on rsn-358i2 (thought-memory thread; written about 22:10 UTC and committed 22:11:15 UTC. Time fix at 22:12 UTC by date -u: the first stamp here said 22:14, which was typed without running date -u and was ahead of the real time)

Raw output: critic/run-358i2/, committed at 39b867609 (Mac CPU job rv391critic2, 21:45 to 21:56 UTC, $0, no GLM). The
seal checked 14 of 14 and the code was not edited. Nets: rsn-358i2 loop-s1..s4, each sha256 equal to its line in
../claude-rv390-20260926/NETS-358i2.sha256.txt (critic/run-358i2/SOURCES.txt). There was no untrained net this time.
Marks: NOTE-critic-plan.md (sealed at 8ec8392fe), unchanged. How this run is read: ADDENDUM-critic-2-358i2.md, which
was fixed before any 358i2 number.
Blind recount: a separate agent recounted from the rows files only, before seeing this write-up. Its scripts are in
critic/verify-358i2/. It agrees with the JSON files and the logs on every count and on the verdict, and no value
differs by more than 0.001.

## Verdict (rsn-358i2's nets): PROVED WRONG

| p-grids7 (practice) | net 1 | net 2 | net 3 | net 4 | mean |
|---|---|---|---|---|---|
| critic AUC (dead vs live page) | 0.800 | 0.620 | 0.785 | 0.847 | 0.763 |
| count-only AUC (number of guesses written) | 0.779 | 0.783 | 0.793 | 0.821 | 0.794 |
| margin | +0.021 | -0.163 | -0.008 | +0.027 | -0.031 |

- GOOD ENOUGH TO USE needed three things:
  - a mean of at least 0.65: met;
  - every net above 0.5: met (the lowest is net 2 at 0.620);
  - beating count-only by 0.05: not met, since the margin is -0.031.
- PROVED WRONG holds by its second clause, "a mean no better than the count-only baseline": 0.763 against 0.794.
  The other clause (mean at most 0.55) does not fire.
- As fixed in addendum 2, rv-391's trigger comes from this verdict. So the time slice (W = 16) stays as the go-back
  trigger for rv-391. P391c.1 (GOOD ENOUGH) was WRONG again.

## The three readings (ADDENDUM-critic-2, like for like with RESULTS-critic.md)

| reading | 358i's nets | rsn-358i2's nets |
|---|---|---|
| per-net-mean margin (the one the mark uses) | -0.002 | -0.031 |
| puzzle-level bootstrap, 95% range of that margin (1,000 resamples) | -0.020 to +0.018 | -0.068 to +0.005 |
| share of resamples above 0 / at least +0.05 | not recorded / 0 | 0.053 / 0.000 |
| critic mean minus one pooled count-only AUC | +0.022 (pooled 0.754) | -0.025 (pooled 0.788) |

- On 358i's nets the pooled reading would have given no clear result. Here all three readings point the same way.
  The critic trails counting on the mark's reading and on the pooled reading, and "good enough" is outside the
  bootstrap range.
- Sensitivity, report only: net 2 alone drives the negative mean. Without it the margin is +0.013. That still misses
  GOOD ENOUGH, but it would read as no clear result rather than PROVED WRONG. The mark covers all four nets, so this
  does not change the verdict.
- The bootstrap resamples only puzzles that have states (80, 43, 75, 79), as critic/verify/extra.py did for 358i.
  Drawing from all unfinished puzzles instead gives -0.068 to +0.007. Seeds 1 to 5 give a share above 0 of 0.036
  to 0.053.

## Report-only rows
- Within-k AUC (the critic's ranking inside groups of states that have the same number of written guesses; dead/live
  pairs with equal k, pooled over k): 0.661, 0.444, 0.650, 0.698 (mean 0.613). 358i's nets: 0.535, 0.617, 0.610,
  0.703 (mean 0.616). The same script (critic/verify-358i2/withink.py) reproduces 358i's four numbers exactly, so
  the two rows are defined the same way. The critic knows a little beyond the count in three nets and nothing in
  net 2, the same as before.
- p-grids6 check: the cut flags a larger share of dead states than live ones in 4 of 4 nets (dead 6/7, 25/26,
  15/20, 3/3; live 1/9, 1/7, 1/19, 12/22). But the retrained nets leave only 4 to 12 of the 300 practice 6x6 grids
  unfinished, so there are 16 to 39 states per net from 4 to 6 puzzles. Net 1's 7 dead states and net 4's 3 all come
  from one puzzle. This check says very little.
- Overfit, worse than on 358i. The retrained nets make far fewer wrong guesses, so the critic had only 1,356 to 2,196
  training states, against 7,538 to 16,100 on 358i, for the same 1,025 inputs. It scores 0.974 to 0.992 on its training
  states and 0.972 to 0.991 on the training puzzles (t-grids7), against 0.620 to 0.847 on practice. Count-only scores
  0.764 to 0.851 on the training puzzles and about the same on practice. Shown.
- The cut flags at most 20% of live training states. On practice it flags 32%, 59%, 48% and 40% of live states. That
  is the overfit again.
- The retrained nets are much stronger at this task. Unfinished practice 7x7 grids: 97, 52, 110, 105 of 300 (358i:
  194, 219, 166, 277). Unfinished practice 6x6: 6, 4, 12, 11 (358i: 124, 151, 88, 246). These are the probe's own GUESS
  runs at 96 rounds, not a registered test.

## What it means (plain words)
The add-on that watches the reasoner and says "this page can't be finished any more" was tried again on the
retrained, much stronger nets. It still did no better than simply counting how many guesses are written, and on one
of the four nets it did clearly worse. Because the stronger nets make fewer mistakes, the add-on had fewer examples
to learn from, and it memorised them. Two tries with the same result are enough: no more versions of this add-on.

## Next (fixed in ADDENDUM-critic-2-358i2.md before this number)
- The time slice (W = 16) stays as rv-391's go-back trigger.
- The next plain fix goes to the Thread manager as a proposal that needs Ben's yes: train the reasoner on its own
  guessing, wrong guesses included, with guesses written in pencil (PLAN-own-traces.md). More critic variants are
  not the plan.
