# Code review of claude/forgetting-round-g vs 62cf9ac36 at 080c9bdba (Claude Code built-in /code-review, level high), Oct 20

Second review, run after fix round 1 (FIX-ROUND-1.md).
**Verdict: CHANGES NEEDED, 8 findings. Three are about the fix round itself (rows 1, 2, 5); the rest are new.**
None affects the G1 or G3 numbers. Both ran with --guard kfsoft and the flag off, and 3-update G1 and G3 runs gave final checkpoints
identical to 62cf9ac36's. Not fixed here: the coordinator's instruction was to re-run the review, record it, push and stop. A further
fix round needs a new GO.

Spot-checked by the lead: findings 1 and 3 are confirmed. For 1, after a measurement prio['p'] is the uniform array that
replay_priority_probs returns, never None. For 3, the 87e0c0971 diff moves frozen_copy and adds parent= to setup_replay_arm, and the
off-path old-vs-new check covered only kfsoft configs.

| # | where | finding | affects |
|---|---|---|---|
| 1 | learn_probe.py:2050 | fix 4 is partial: after a measurement that yields S <= 0, p is a uniform array (not None), so the draw stays `choice`, not the control's `randint` | --replay-priority only (H1, not re-run) |
| 2 | learn_probe.py:1672 | fix 2 is partial: the label file's sha is recorded but never compared to the pinned train sha / dcmp, so a superset build passes | --replay-priority only |
| 3 | learn_probe.py:1951 | the off-path bit-identity check covered only kfsoft; the --guard replay path (A1F, replay-kl) moved code (frozen_copy before load_guard, parent=) and was not compared old vs new | replay arm with the flag off; G1 / G3 unaffected |
| 4 | e0_score.py:83 | runs are checked one at a time and e0.json is written only at the end, so a bad later run throws away earlier scoring | E0 (not yet run) |
| 5 | e0_score.py:39 | fix 8 is still a copy of analyze.py's rule: it drops the "nights after nights_run ignored" note; better to share one function | E0 |
| 6 | learn_probe.py:2055 | the "@u top families by KL" log recomputes S including negatives, so its percentages can disagree with the draw (even exceed 100%) | log only |
| 7 | learn_probe.py:1666 | prompts listed under two families take the first label silently; conflicts are not counted | --replay-priority only |
| 8 | e0_score.py:14 | duplicates existing helpers and constants (DEV sha, file sha, night_checkpoints); import them instead | E0 maintenance |

Suggested order for a next round (if GO): 3 (old-vs-new check on the replay paths), 4 and 5 (before E0 runs), then 1, 2, 7, 6, 8.
