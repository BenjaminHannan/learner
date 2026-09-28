---
name: rsn-358i3-pass
description: 2026-09-27 00:53 UTC: the bug-fixed 358i loop beats its same-size plain twin on fresh seeds, one machine (rsn-358i3 PASS, recount 23dbe806b); problem #5 shown at small scale
metadata:
  type: project
  modified: 2026-09-27T00:54:10.701Z
---
**rsn-358i3 PASS** (BensPC, torch 2.11, seeds 5-8, both arms trained there; my recount 23dbe806b agrees with the builder, c06390585 on builder-outbox).
- Loop 2x512 vs plain 8x256, about 6.4M weights each, same data and steps (60k).
- Mean loop minus plain, of 300: sums6 +124.00 and grids6 +52.00 (ahead on 4 of 4 seeds); grids7 +67.75; sums8 +185.75; sums10 +160.75; sums12 +129.50.
- Practised sizes are level. Number puzzles: neither net learns them (0-5 of 300).
- The loop's own stop works (G3).
- The fix was the autocast cache (see [[autocast-cache-bug]]); rsn-358i2 confirmed it, 358i3 replicated it.
- Machine check: BensPC plain vs rental plain differ by at most 10 per test, so the 358i2 gaps also stand.

**Why:** this is the first demo goal ("beats same-size models side by side") shown for the reasoner at small scale. Before it, every loop result on a rental had been hit by the bug.
**How to apply:**
- Cite 358i3 (not 358i or 358d) for loop vs plain.
- The 358i2/358i3 checkpoints are the net for 358b3 (chat-puzzle gate), the 358x rerun and rv-390.
- The next goal item is scaling (a bigger loop still beats plain of its size); the draft marks are 358s at 442bf2d3b.
- Supersedes the loss rows in [[rsn-358i-result]]. See [[reasoner-exit-rule]].
