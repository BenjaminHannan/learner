# rv-391 dev result: no signal from the net marks a wrong guess, so the fallback trigger applies (thought-memory thread; written 2026-09-26 18:17 UTC by date -u)

Unregistered measurement on PRACTICE grids only (rv-390's p-grids7 and p-grids6, seeds 39114 and 39113). No test grid
was touched. The choice rule was fixed before any number in NOTE-dev-plan.md.

Raw output: dev/, copied from builder-outbox d73fa99c9 (Mac CPU job rv391dev, $0, exit 0, all 4 seeds). Nets: 358i's
loop-s1..s4, each sha256 equal to 358i's SEAL-run.sha256.txt (checked again here from the JSON). Every AUC in the JSON
was recounted here from the per-guess rows and agrees to 3 decimals. This recount is mine, not blind.

Deviation (the builder's): the task's net path ~/premonition-models/rsn358i/loop-sN/final.pt does not exist on the
Mac. The task said to skip a missing net. The builder instead used the real path
(~/premonition-models/rsn358i/claude-rsn358i-20260926/W/loop-sN/final.pt) after checking each sha256 against the seal.
The nets are the right ones, so the measurement stands.

## The rule, applied (p-grids7, all guesses; AUC = chance a wrong guess scores above a right one, 0.5 = no signal)

| signal | net 1 | net 2 | net 3 | net 4 | mean |
|---|---|---|---|---|---|
| dq (drop in q) | 0.416 | 0.395 | 0.318 | 0.541 | 0.418 |
| d_mean_ent | 0.507 | 0.501 | 0.555 | 0.513 | 0.519 |
| d_max_ent | 0.467 | 0.503 | 0.478 | 0.503 | 0.488 |
| flips | 0.496 | 0.533 | 0.373 | 0.627 | 0.507 |
| p_written (low) | 0.507 | 0.502 | 0.529 | 0.566 | 0.526 |
| clash (rule-based, comparison only) | 0.519 | 0.509 | 0.407 | 0.604 | 0.510 |

- The best candidate is p_written, with a mean of 0.526. The rule needs at least 0.65. No candidate qualifies.
- So, by the rule fixed before the measurement, rv-391 uses the fallback: the time slice. After a guess, if the checker
  has not accepted the grid within W = 16 rounds, go back to the snapshot and write the next candidate. It needs no
  signal from the net. On the tiny rehearsal net it added nothing, so it is the weaker bet. Shown for 358i's nets only.
- Guesses measured: 1,311, 1,610, 1,272 and 2,318 on p-grids7, of which 306, 182, 219 and 272 were wrong.

## Report only (practice grids, 358i's nets; nothing here changes the choice)
- A wrong guess ends the puzzle. Each puzzle has one solution (claude_rsn358a_envs.check_latin) and a written guess is
  kept in the answer (Runner.final), so without going back no puzzle can be solved after one. The rows agree: 0. On
  p-grids7, 368 of the 720 puzzles GUESS left unsolved after 96 rounds had a wrong guess on the page (113 of 160,
  69 of 177, 88 of 125, 98 of 258). That is the most that going back could rescue with a perfect trigger. Shown.
- The first guess is almost always right: 24 of 799 first guesses on p-grids7 were wrong. The first wrong guess came at
  the 4th or 5th guess (median). Shown.
- The stop head q rose MORE after wrong guesses than after right ones in 3 of 4 nets (dq below 0.5 in both sets). So
  rv-387's trigger, "q fell", pointed the wrong way as well as never firing. Shown on practice.
- First guesses only, dq and flips look better (means 0.73 and 0.74 on p-grids7), but those rest on 9, 4, 4 and 7
  wrong first guesses, and on p-grids6 dq reverses (mean 0.27). Not a signal to act on. Suggested.
- On guesses written onto a page with no earlier wrong guess (the moment going back would need to catch), the best
  mean is still 0.56 on p-grids7 (p_written and flips). Post-hoc; suggested.
- Even the rule-based clash count is near chance on all guesses (mean 0.51), because the net's read-out follows what is
  written on the page, so it rarely shows two copies of a symbol in a row. Suggested.

## What it means (plain words)
When this net writes down a wrong guess, nothing in its own output looks worried. Its confidence even goes up. So it
cannot tell us when to go back. About half the puzzles it fails on are ruined by one wrong guess, so a good "that was a
mistake" signal is worth a lot.

Brain first: in people, a separate frontal area (the anterior cingulate cortex) watches for clashes and errors and
triggers a change of approach. This net has no such monitor. It reads whatever is on the page as true. That is
textbook-level, and mapping it onto the net is a guess.

## Next (fixed now, before any 358i2 number exists)
1. When rsn-358i2's nets exist, this same measurement runs unchanged on them, in the same job as rv-390's rerun and
   rv-392 (ADDENDUM-358i2-rerun.md), on the practice grids only. The same rule picks the trigger for those nets. If no
   candidate reaches 0.65 there either, the time slice (W = 16) stays.
2. rv-391 is registered after rv-392's verdict, on the worker rv-392 picks, with the trigger from step 1. Marks and
   predictions are sealed before any run.
3. Untested idea for the Thread manager (needs Ben's yes, since it adds a learned part): a small learned error monitor,
   the brain's conflict monitor in silicon. It would read the loop net's state after a guess and be trained to say
   "that guess was wrong", with bare 0/1 targets checked by code on training puzzles only, never on test items. It
   would pin torch 2.11. It would come after the 358i2 rerun, and only if 358i2's own signals also fail the rule.
