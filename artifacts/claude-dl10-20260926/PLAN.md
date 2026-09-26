# dl-10 PLAN (not sealed, not queued; Fix-sleep thread, 2026-09-26T20:15:30Z). Replay + a learned switch together.

Does dl-9 include replay? No. dl-9 trains exactly dl-2's night (no anchor, no replay); only how the adapter is served
changes (claude_dl9_experts.py docstring and run_seed).

Why both: the brain does both, replay in sleep and partly separate circuits gated by task. They guard different
things. The switch keeps the add-on away from questions that are not its kind, so it cannot protect anything the
switch sends TO the add-on: the add-on's own older skills, and any general question the switch mistakes for its kind
(dl-9's report row on the 139 number questions shows how many). Replay (dl-7b's shaky-fact anchor) protects what the
add-on itself answers, at a cost in learning (dl-7b kept 76% of the gain, FAIL on 80%).

When: only after dl-9 reports, and only if dl-9 shows a gap the switch alone leaves: panel items switched on and
then lost, or reworded / near-kind questions the switch sends to the add-on and gets wrong. If dl-9 PASSes with no
such gap, dl-10 is not needed for the panel and waits for a test with blended questions or many experts.

Shape (one change from dl-9): the add-on is trained with dl-7b's anchor (claude_dl4_anchor.train_anchor on the base's
shaky short facts, GLM suffix), served through dl-9's switch; compare with dl-9's plain night + switch on the same
seeds. Marks to fix before any run: lost among switched-on panel items, gain kept vs dl-9 (the anchor's cost),
switch on-rates unchanged. BensPC, $0.
