---
name: revert-and-retry-verdicts
description: Finished verdicts of the "Memory for its own thoughts" thread (rv-385..rv-393), so no one reruns them
metadata:
  type: project
  modified: 2026-09-27T07:36:00.000Z
---
Verdicts from the thread "Memory for its own thoughts" (09-26). Each has a RESULTS or NOTE file, and each count was recounted.
- rv-385 REGISTERED FAIL (de654f66b): the 1B copies the failures it noted, so the 'not again' list stays in code. rv-386 WITHDRAWN, NOT RUN (487627d71).
- rv-387 (358i loop nets, 7x7): NO CLEAR RESULT (a6bf514b5). Going back on "q fell" never fired (0 in 2,400 runs). Report-only: GUESS beat KEEP by 11 to 17 of 300 at 48 rounds.
- rv-388 NO CLEAR RESULT (c3542bb56): END 34/28, JUDGE 42/35, PLACEBO 37/33, ORACLE 80/80. The judge's edge over random pruning is within chance.
- rv-390 worker (b804ca81b, about $0.37), 358i nets only, PROVISIONAL:
  - hard grids7 KEEP 5/1/11/0 vs RESTART 17/18/24/17, so H PROVED WRONG;
  - GUESS 24/34/32/14, so G PASS;
  - I PASS (wait at most 0.13 s).
  - Finds went to Sleep research.
- rv-391 dev (9d932498f, NOTE-dev-result.md; practice grids, 358i nets):
  - No net-made signal marks a wrong guess (best mean AUC 0.53 against the 0.65 needed), so the trigger is the time-slice fallback, W=16.
  - q rises MORE after wrong guesses.
  - 368 of 720 unsolved practice grids7 were ruined by one wrong guess.
- CAVEAT 2 (65ab0571a): an UNTRAINED net plus GUESS's code parts (row/col candidate skip + checker) solved 28 and 20 of 300 practice grids7, and 63 and 49 of 300 grids6. So G's margin may be partly code. rv-392 ADDENDUM-1 adds untrained-net (r0) rows plus per-puzzle day dumps to the 358i2 job.
- rv-391 dev 2 critic probe (14de0f17e, RESULTS-critic.md; 358i nets): PROVED WRONG. Mean AUC 0.776 vs count-only 0.777; margin 0.0016; blind recount agrees. Untrained critic 0.86 (within-k 0.82: it reads the page). Train 0.88-0.95 vs practice 0.68-0.79 = overfit. Then the same probe on 358i2:
- rv-391 dev 2 on rsn-358i2 (6eaee077a, RESULTS-critic-358i2.md): PROVED WRONG. Mean 0.763 vs count-only 0.794 (margin -0.031; bootstrap -0.068 to +0.005; pooled 0.788); blind recount agrees. Net 2 alone drives it (without it +0.013). Critic had only 1.4k-2.2k train states (stronger nets err less) = worse overfit. So time slice W=16 is rv-391's trigger; no more critic variants. Pencil-mark plan became rv-393 (no Ben yes needed, TM 22:29).
- rv-393 pencil marks (05d8edd50, artifacts/claude-rv393-20260926/RESULTS.md; BensPC job 175, 358i2 nets): PROVED WRONG, NO HARM holds, blind recount agrees. PENCIL overrules 6.9/21.1/9.2/6.3% of its own wrong marks (bar 60%); ORIG and CLEAN overrule 0. Page AUC 0.756 vs count-only 0.863 (bootstrap -0.154 to -0.058). Report-only: 7x7 practice (both arms) took grids7 test 173-241 -> 285-291 of 300. Suggested causes: replay memorised (~192k draws of 5-9k states); trained on the untouched net's mistakes, judged on its own. Going back -> Ben brainstorm (BRAINSTORM-going-back.md, sent to TM 07:35 UTC 09-27).
Caveat for all 358i results: the nets were probably undertrained (torch 2.8 autocast bug). Plans and next steps: [[revert-and-retry-line]].
