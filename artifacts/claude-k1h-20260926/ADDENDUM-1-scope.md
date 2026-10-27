# k1h ADDENDUM 1: what a k1h PASS means (Creative answers in chat thread, written 2026-09-26 19:50 UTC)

Written before any k1h chat, answer, training or run exists, at the Thread manager's review (19:36 UTC). It changes no
mark, arm, data rule or code; it only states the scope of the result. Registered FAILs stay FAILs.

## A k1h PASS is a finding about LFM, not a 0.2d part
0.2d has one talker path for every message and no creative route: Ben chose "Remove" for the hand-written creative
rule at 18:39:38 UTC (design/v3/30-modes/02d-gates-ADDENDUM-27.md:1-9). k1h, like k1f, runs on 0.2c's build, where
is_creative333c still sends creative turns to a separate writer. So an adapted LFM writer cannot join 0.2d as a
creative-only part. It could matter to the build only if Ben decides that LFM becomes the whole talker (his call, after
k1f; ADDENDUM-27:11-12). Until then a k1h PASS means: teaching the LFM writer from GLM's answers makes its creative
replies more useful than the plain LFM writer on this panel. It is not a build win, and the K1 line and 0.2d-row
readings reported beside it are readings on 0.2c's build, not 0.2d's.

## Citation corrected
PASSMARKS-k1h.md cites scripts/claude_e2e02c.py:59-72 for "the build's MiniCPM writer shares the model that carries the
sleep adapter". That file is 0.2c's build (the build k1a, k1f and k1h run on), not 0.2d's. The reason for choosing the
LFM writer is unchanged: in the build k1h is tested on, an adapter on MiniCPM's writer would be a second change.
