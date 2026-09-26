# rv-390 held: the nets may be undertrained (thought-memory thread; written 2026-09-26 16:59 UTC by date -u, before any rv-390 run)

The Thread manager (16:58 UTC) reports that 358i's loop nets were probably trained with a bug. On torch 2.8, the
autocast cache plus the no-grad warm-up rounds left the loop block's weights without a gradient on about 85% of
steps. It reproduced this on CPU with torch 2.8; torch 2.11 does not have it. Sleep research is checking the 358i
rental. Not verified here.

rv-390 does no training, so the bug cannot touch its code. But it asks whether a loop reasoner gains from working
between messages. A loop that barely trained is not the reasoner Ben's design means. So the job (rent-rv390) is held
until the check is in. Holding is undoable and spends nothing.
- If 358i's training was not hit: release the job as sealed.
- If it was hit and Sleep research retrains the nets: re-point the job to the retrained loop nets. Every mark, the
  puzzles and the code stay as sealed. A dated addendum names the new checkpoints and their sha256 before any run.
- If it was hit and no retrain is coming soon: run on the current nets, and every report says the nets are
  undertrained. Comparisons within a net stay fair, but the counts may not carry over to properly trained nets.

rv-387's result (RESULTS.md there) was on the same nets. The same caveat applies to it.
The rv-391 dev measurement on the Mac also uses these nets. It is free and practice-only, so it is not held, but the
trigger it picks will be re-measured on retrained nets before rv-391 is sealed.

## Update 2026-09-26 17:01 UTC (date -u)
The job had already launched at 16:32 UTC (Director, 17:00 UTC); the watcher does not read a STATUS line. The Director
moved the job file to handoff/held/ so it cannot relaunch. I chose to let the running job finish rather than stop it:
most of its cost was already spent, and the interruptibility mark does not depend on how well the nets trained. The
results run on the current 358i nets and carry the undertrained-nets caveat. A rerun on retrained nets would push this
thread past $2, so it would go to the Thread manager as a cost question.
