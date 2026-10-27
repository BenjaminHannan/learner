# dl-5s RESULTS (FINDING ONLY; Fix-sleep thread, 2026-09-26T22:55:28Z, date -u)

**Finding: a small learned switch kept dl-5's grid add-ons completely off the general panel and fully on for grids.**
Served through the switch, the panel lost 0 of the base's 200 right items on both seeds (always-on add-on: 98 and 61),
and the grid score stays exactly the add-on's own (715 and 712 of 762 states), because the switch was on for all 762
grid test states. All three expectations fixed in PASSMARKS.md hold; "shown wrong" is not triggered. A blind recount
(separate read-only agent) agrees on every number.

| | seed 8 | seed 9 |
|---|---|---|
| panel lost, add-on always on (S) | 98 | 61 |
| panel lost, served by the switch (X) | 0 | 0 |
| panel right S / X (base 200) | 120 / 200 | 153 / 200 |
| grid test states right, S = X (of 762) | 715 | 712 |

Switch: on for 762 of 762 grid test states; off for 300 of 300 panel items (bigger 0/119, capital 0/70, count 0/20,
opposite 0/30, order 0/31, plural 0/30); off for 104 of 104 held-out base questions. Fit loss 0.0 on 600 practice
states + 412 base questions. The recount found 0 of the 762 test states among the 9,571 practice states and no panel
question among either, and the switch's scaling came from the fit set only.

What it means (plain): the old skills were never overwritten in the base; the add-on just answered everything. A
switch that sends only grid-looking questions to the add-on removes all of the measured forgetting here.
What it does NOT mean: the task was very easy to tell apart (fit loss 0). Grid states all share Claude's fixed grid
wording, and the base's questions have no digits and all end in "?". The switch most likely keys on that wording, not
on "puzzle vs question". It says nothing yet about reworded or blended questions; dl-9's GLM rewording row tests that.
Reused saved answers, not live serving; grid bounds rest on dl5_results' night-5 scores belonging to the same adapters
as the carry row (the recount did not trace that through the adapters' sha256).

Correction (found by the recount): PASSMARKS.md's 19:41 addendum says the 139 number items "contain digits". Only the
119 "bigger" items contain digits; the 20 "count" items ("How many legs does a spider have?") do not. No expectation
changes.
Deviations: try 1 was stopped by my own 90-minute wrapper before any result (RUN-NOTE.md). Try 2's console log was lost:
my commit step removed cpu/log.txt from git, and the rebase that followed deleted the file on disk while the run was
still writing to it. dl5s_results.json is the whole output (the script prints the same JSON). Try 2: 88.9 min on CPU, $0.
