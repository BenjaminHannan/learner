# V1 re-run status (2026-10-22 ~02:40 UTC)

FLOOR re-run: DONE, clean. D dev 68.4% (W1-dev mark 18.95%: pass); creative dev first-try 34.0% (W2-dev mark 20%: pass); bridge-off 2.3%; KL share 12-22% (A3 line 50%). Box 57128113 pulled (sha ok) and destroyed. Dev only.

FULL re-run (box 57124461): log froze at step 4,150 (00:04 UTC), box kept billing past expected finish; stopped ~02:17 UTC; pull of out.tar.gz returned nothing for 25+ min (dead-host pattern, as in Gate S). Spend so far ~$1.45.

Waiting on: OK to `destroy --abandon` 57124461, and OK for one A5 relaunch of FULL from scratch (needs Ben's rental click; total re-run ~ $3.9 vs $4.50 cap).
Nothing launched or destroyed since. Seal stays shut; floor-vs-full and D5 need the FULL result.
