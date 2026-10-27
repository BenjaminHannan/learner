---
name: rsn-358i-result
description: rsn-358i verdict (recounted 2026-09-26 ~16:10 UTC): INCONCLUSIVE; loop wins long sums on every seed, loses grids; exit-rule reading and what's next
metadata:
  type: project
  modified: 2026-09-26T15:58:22.694Z
---
**rsn-358i** (half-narrow attention + grid legend, 4 seeds, verdict recorded at main b76c7566c) is INCONCLUSIVE: loop seed 4 got grids5 122/300, so G0 is missed. G1 and G2 FAIL, G3 PASS. The results were only in builder-outbox commit e75ef5be8, not at the tip, so I copied them to main.

4-seed means, loop minus plain, out of 300:
- sums6/8/10/12: +41, +70, +88, +76, with the loop ahead on 4/4 seeds at every size;
- grids5/6/7: -78, -83, -59;
- numbers: about 0.

On sums the loop hardly changes after round 1, so that win comes from the design, not from thinking longer. On grids the loop does use its rounds (s1 grids6 goes 34 → 177 by round 16) but learns slowly (s4 stalled around 35% on grids5 in training).

**Exit rule:** no STOP, because STOP needs G0. "INCONCLUSIVE decides nothing; rerun first." I recommended holding the rerun (358m stage 1 seeds 5-8, ~$1) until 358t lands, and sent that choice to the Thread manager for Ben.

Cost ~$0.94, plus ~$0.10 for two stuck hosts.

**Why:** later threads will ask what 358i showed.
**How to apply:** cite these numbers, not the earlier predictions. 358t (loop-trm, loop8) is graded against these plain results. See [[reasoner-exit-rule]], [[rsn-358b3-requirements]].
- Next ranked (16:25): 358w text-games carry-over (scripts/claude_textgames.py keys/recipes/switches, draft artifacts/claude-rsn358w-20260926/PASSMARKS-draft.md, switches held out; token-grid encoding still owed; ~$1). Creative offered shared world scripts/claude_world_latin.py; seeds 900000-999999 are Creative's.
