---
name: model-comparison-0926
description: Ben switched the Thread manager to Fable 5.1 at 19:24 UTC 09-26 and asked which model did better; coordinator counts for both windows, the confounds, and the "no fair verdict" reading given to Ben
metadata:
  type: project
  modified: 2026-09-26T20:43:53.875Z
---
Ben 19:22 asked whether to switch the Thread manager to Fable 5.1; switched it himself 19:24-19:25 (get_session: user_switched_model = claude-fable-5-1). Ben 19:25:36: "In twenty minutes, look back at the work and tell me which model did a better job".

Criteria and full records: /mnt/project-files/thread-manager/model-comparison-2026-09-26.md.

Coordinator counts (read-only worker over the thread dump):
- Window A (Opus 5.5, 15:48-19:24): 63 replies to Ben, 14 corrected (22%); Ben caught 5 misses first; fix raised first: the autocast bug.
- Window B (Fable 5.1, 19:25-20:35): 7 replies (4 substantive), all 4 substantive needed corrections; 19 correction items, 18 caught by the coordinator, 1 by the Thread manager, 0 by Ben (silent since 19:28); 5 fixes raised first verified in commits + 1 draft; 4 clock slips; 3 unbatched replies; a payment ask withdrawn before sending.
- Confounds: 71 min vs ~3.5 h; every B report was spot-checked by a worker while 8 of A's 14 corrections predate spot-checks (began 18:41), so B's rate is inflated; ~9 more B draft faults were caught pre-send and not counted.
- Reading given to Ben (21:11 batch, 09-26): no fair verdict; the model cannot be separated from the checking; under equal checking both windows show the same slip kinds (dropped caveats, overstated headlines). A fair comparison needs the same pre-send and coordinator checks in both windows over a longer stretch.

**Why:** Ben will judge the switch on this; counts must come from the coordinator, not the Thread manager.
**How to apply:** if Ben asks again, give counts with the checker named per count and the confounds first; offer a longer equal-checking window rather than a verdict. Related: [[verify-before-ben]], [[thread-manager-adversarial-reviewer]], [[batch-results-for-ben]].

Update 21:17 UTC: the 21:08 batch (Fable) needed 4 in-place fixes from the coordinator's spot-check (wrong state word "nothing new released", an unsourced pace, dl-5s on the wrong machine, a dropped dev-use caveat); numbers all held. Window B running total: 5 of 5 substantive replies corrected.

23:29 UTC update: 23:18 batch needed 9 pre-send fixes and 7 more from the coordinator after send (finding-only reason, comparison baseline, dl-9 scope, unsourced recount, which prediction, two dropped caveats). Running total 7 of 7 Fable substantive replies corrected; coordinator post-send fixes on the last three batches: 4, 13, 7. Pattern: numbers right, framing words (finding only, unchanged, will test, blind) unsourced. Worker brief now asks for the file's own reason behind every label and the comparison behind every 'unchanged'.

00:17 UTC 09-27: Ben asked again at 00:08:58; answered with the coordinator's counts and no winner (cmsg_...4ZLbTM7A1vMcSLsNniyC5X), plus the Night Board artifact https://claude.ai/artifact/LKimjhXrdAkdim8qqbQEVQ. 00:09 batch sent before its pre-check (Ben waiting): 5 hard + ~12 fixes edited in at 00:15. Running total 8 of 8. Rule added to [[verify-before-ben]]: when Ben is waiting, a two-line headline first, the checked batch after.

00:24 UTC 09-27: Ben switched the Thread manager back to Opus 5.5 at ~00:22. Fable window B = 19:25-00:22, 8 of 8 substantive replies corrected under full checking. Window C (Opus, from 00:22) gets the same pre-send worker + coordinator spot-check, which makes it the first equal-checking comparison; count its corrections the same way.

00:31 UTC 09-27 window C (Opus): coordinator counted 2 of 2 substantive replies corrected after send (00:23 MoE 5 items, 00:25 358e3 10 items), numbers all right, framing/caveats wrong, same pattern as B. Both skipped the pre-send worker; do not skip it for result replies, even short ones.
00:35 UTC: window C clock slips 2 (the 00:30 stamp; a 00:36/00:37 stamp written before reading date -u 00:34:53). Run date -u in its own call, then write.
