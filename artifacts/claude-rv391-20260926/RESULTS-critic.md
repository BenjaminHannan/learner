# rv-391 dev 2 results: the learned critic on 358i's nets (thought-memory thread; written 2026-09-26 21:15 UTC by date -u)

Raw output: critic/run/, copied from builder-outbox (Mac CPU job rv391critic, 20:27 to 21:06 UTC, $0, no GLM). The seal
checked 14 of 14. Nets: 358i's loop-s1..s4, each sha256 equal to 358i's SEAL-run (critic/run/SOURCES.txt), plus r0, an
untrained net. Marks: NOTE-critic-plan.md, sealed at 8ec8392fe. Addendum 1 (25fcae183) adds one report row.
Blind recount: a separate agent recounted from the rows files only, before seeing this write-up. Its scripts are in
critic/verify/. It agrees on every count and on the verdict, and no value differs by more than 0.00005 (rounding).

## Verdict (358i's nets only): PROVED WRONG

| p-grids7 (practice) | net 1 | net 2 | net 3 | net 4 | mean |
|---|---|---|---|---|---|
| critic AUC (dead vs live page) | 0.755 | 0.773 | 0.780 | 0.794 | 0.776 |
| count-only AUC (number of guesses written) | 0.792 | 0.779 | 0.796 | 0.742 | 0.777 |

- GOOD ENOUGH TO USE needed three things. A mean of at least 0.65 was met, and every net above 0.5 was met. Beating
  count-only by 0.05 was not: the margin is -0.002. Not good enough.
- PROVED WRONG holds by its second clause, "a mean no better than the count-only baseline": 0.776 against 0.777.
- How firm this is (the blind recount's own checks, report only):
  - "Good enough" is firmly ruled out. In a puzzle-level bootstrap of 1,000 resamples, the critic's margin over
    count-only ranged from -0.020 to +0.018 (95% range) and never reached +0.05.
  - "No better than" rests on a margin of 0.0016, so the critic ties with counting rather than being worse.
  - The note compares means of per-net AUCs. One other reading of the baseline would change the label: one
    count-only AUC over all four nets' states pooled is 0.754. Against that, the critic is ahead by 0.022, which gives
    no clear result. The per-net mean is used here because the critic's own number is a per-net mean. The note did not
    spell this out, so the reading is disclosed rather than hidden.
- p-grids6 check (report once a verdict exists): the cut flags a larger share of dead states than live ones in 4 of 4
  nets (dead 262/335, 138/272, 126/205, 197/468; live 214/615, 187/780, 144/428, 354/1647).
- So the time slice (W = 16) stays as the go-back trigger for 358i's nets. P391c.1 (GOOD ENOUGH) was WRONG.

## The Thread manager's two questions (21:12 UTC)
1. What does the untrained net's critic read? Its AUC was 0.858 on p-grids7 and 0.852 on p-grids6.
   - It is not just the dead share. AUC is a ranking measure, so a high dead share alone does not raise it.
   - Within groups of states that have the same number of written guesses, r0's critic still scores 0.816 and 0.824.
     So it reads something about the page beyond the count.
   - The trained nets' critics score only 0.535, 0.617, 0.610 and 0.703 within those groups on p-grids7 (mean 0.616).
     This is computed from the rows; it is post-hoc and report only.
   - The likely reason is the state mix. The untrained net guesses almost at random: 42% of its states with one guess
     written are already dead, and 75% of its states are dead. Its dead pages differ from live ones in ways that are easy to see
     from the page itself. The trained nets make fewer mistakes, and their mistakes look like right answers. That is a
     harder task. So "untrained scores higher" does not show that the untrained state holds more. The two critics
     faced different tasks. Suggested; untested.
   - This probe answers "can a critic predict dead ends from page plus state?" (Addendum 1). It cannot answer whether
     the trained state carries the signal.
2. Overfit: yes. On the training puzzles the critic scores 0.88 to 0.95. On practice puzzles from the same generator it
   scores 0.68 to 0.79. Count-only has no fitting and scores about the same on both (0.73 to 0.80 on training, 0.70 to
   0.80 on practice). So the critic's drop is overfitting: 1,025 inputs fitted on 7,538 to 16,100 training states that come in
   bunches of about 9 from the same puzzle. Shown.

## Report-only rows
- Addendum 1's row (trained nets' mean minus r0): -0.082 on p-grids7, -0.141 on p-grids6. It is not a clean answer to
  the second question, for the reasons above. P391c.2 (r0 within 0.10 of the trained mean) held on p-grids7 and failed
  on p-grids6.
- The cut flags at most 20% of live TRAINING states. On practice it flagged 22% to 35% of live states in the trained
  nets: that is the overfit again.
- The two machines give r0 different starting weights for the same seed: weights hash a23da0b8... here and 05f28704... on
  the Mac. So r0's rows belong to the Mac copy.

## What it means (plain words)
A small add-on that watches the reasoner's state was trained to shout "this page can't be finished any more". On these
old, under-trained nets it did no better than a much simpler rule: the more guesses are written, the more likely one is
wrong. It also learned its training puzzles too well and did worse on new ones.

## Next (fixed in ADDENDUM-critic-2-358i2.md before any 358i2 number)
- The same probe, unchanged, runs on the retrained rsn-358i2 nets (Mac CPU job rv391critic2, $0). rv-391 will run on
  those nets, so their verdict decides rv-391's trigger.
- If it is not GOOD ENOUGH there either, the time slice stays. The next plain fix goes to the Thread manager as a
  proposal: train the reasoner on its own search traces, dead ends and backtracks included (Stream of Search), rather
  than bolting a critic on. More critic variants are not the plan.
