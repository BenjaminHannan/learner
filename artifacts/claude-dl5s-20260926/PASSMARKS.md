# dl-5s (FINDING ONLY): could a small learned switch have kept dl-5's grid adapters off the general panel?
# (Fix-sleep thread. Expectations fixed when this file is committed, before the run. Step (1) of the Thread manager's
# 19:25 UTC plan after Ben's 19:20 "just put the old skills somewhere where they don't get overridden".)
Code: scripts/claude_dl5s_switch.py (the docstring is the method); the switch is claude_dl9_experts.fit_switch.

## Why a finding, not a result
dl-5's training rows carry Claude-written grid wording and a Claude-written answer prefix (rv-385), so under Ben's
16:39 "Use GLM" nothing here can be a registered result. The clean registered test is dl-9 (ebe89c7a0).

## What it does
The base 1B was frozen in every dl run; only the add-on learned. dl-5's carry row saved the base's and each S adapter's
greedy answers to the 300 panel items (S lost 98 on seed 8 and 61 on seed 9 of the base's 200 right items). A switch
is fitted on the frozen base's last-layer state at the last prompt token, with code-made labels: 1 = states along the
true solution of dl-5's own practice grids (seed 8, days 1-5, 600 sampled); 0 = short quiz questions the base wrote
itself (dl-7's recipe, panel topics dropped, pool seed 3391; 80% fit, 20% held out; half carry GLM's "Answer only, no
explanation."). X = the adapter's saved answer where the switch is on, the base's where it is off. Nothing is trained
into the 1B; no adapter is loaded.

## Expected (fixed now)
- X lost <= 5 on each seed.
- The switch is on for >= 95% of dl-5's 762 grid test states (seed 38990, never used to fit).
- The switch is off for >= 95% of the 300 panel items.
Shown wrong: X lost > 0.5 x S lost on either seed.

## Reported
On-rate by panel kind (count and bigger are number questions), on the held-out base questions; S's lost items the
switch turned on; X's grid score as bounds (S's saved grid score minus / plus the test states the switch turned off,
since per-state grid answers were not saved).

## Added after the Thread manager's review (19:41 UTC), before the run
- Reported: the held-out 20% base questions' accuracy (switched off = right), and the on-rate per panel kind, with
  the number questions named as the hard case: 139 of 300 items (bigger 119, count 20) contain digits, as grid
  states do.
- The positives carry Claude's grid wording (rv-385), so the switch may learn that wording rather than "puzzle vs
  question". dl-9's GLM rewording row is what tests that.
- The grid bound errs both ways: X's grid score lies between S's saved score minus the switched-off test states (if
  the base were wrong on all of them) and S's score plus them (if the base were right where S was wrong). If every
  test state is switched on, X's grid score equals S's exactly.

## Limits
Reuses saved answers instead of serving live (exact for the greedy panel; a bound for grids). One adapter per seed,
distinct kinds of question. The plumbing rehearsal used shifted grid and pool seeds, never the test grids.
