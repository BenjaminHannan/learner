# rsn-358i recount and exit-rule reading (sleep research thread, 2026-09-26 15:57 UTC)

Recounted from runs/*/tests.json (builder commit e75ef5be8 on builder-outbox, copied to main unchanged). Every count and mark matches the builder's RESULTS.md.

**Verdict: INCONCLUSIVE.** G0 is missed because loop seed 4 is right on only 122/300 of practised-size grids5. G1 FAIL, G2 FAIL, G3 PASS. The proved-wrong clause does not apply, because it needs G0.

4-seed means, loop - plain (300 per test):

| test | plain | loop | loop - plain | seeds with loop ahead |
|---|---|---|---|---|
| sums4 (practised) | 300 | 299 | -1 | |
| sums6 (bigger) | 197.75 | 239 | +41.25 | 4/4 |
| sums8 | 115 | 184.75 | +69.75 | 4/4 |
| sums10 | 73 | 161 | +88 | 4/4 |
| sums12 | 51.25 | 127.25 | +76 | 4/4 |
| grids5 (practised) | 299 | 221.5 | -77.5 | 0/4 |
| grids6 (bigger) | 237.75 | 154.75 | -83 | 0/4 |
| grids7 | 139.25 | 80.25 | -59 | 0/4 |
| numbers4 / numbers5 | ~1 / ~0.5 | ~1 / 0 | ~0 | (both memorise the 24 game, as predicted) |

## Exit rule (EXIT-RULE.md 50745425c plus ADDENDUM-1 ac7eacbbd), read literally
- STOP needs G0 met, so there is no STOP.
- EXIT-RULE.md says: "An INCONCLUSIVE 358i ... decides nothing; rerun first."
- The CONTINUE counts are met on the numbers: the loop lead is +88 on sums10 and +76 on sums12, against a bar of >= +20. But an inconclusive run decides nothing, so this is reported, not used.
- The loop line therefore continues. A plain rerun of this recipe (358m stage 1, seeds 5-8, about $1) is the rule's next step. 358t, which is running, changes the loop in two ways at once and so is not that rerun.

## What the counts show (my reading, labelled)
- **Sums (shown):** the width fix worked. The loop beats plain on every seed at every bigger size, and the lead grows with size. But the loop's sums answers hardly change after round 1 (seed 1 sums6: 211 at 1 round, 222 at 48). So the sums win comes from the net's design, not from thinking longer.
- **Grids (shown):** the loop really does use its rounds here (seed 1 grids6: 34 at 1 round, 121 at 4, 177 at 16, 182 at 48). But it learns grids slowly. Seed 4 stalled at about 35% exact on grids5 in training. Its own stop needs 13-45 rounds, more than the 16 rounds it ever trained on.
- **Suggested:** grids are where more thinking helps and where under-training hurts. 358t (the TRM schedule, which trains on its own long rollouts, plus Ben's looped 8-layer net) is aimed at exactly that.
- **Untested:** whether the half-narrow heads (only 4 of 8 heads see a whole row) cost the 2-layer loop more on grids than the 8-layer plain.
