# dl-9 Addendum 1 (written 2026-09-26T19:53:30Z, before any run; answers the Thread manager's pre-run review, 19:40 UTC)
No sealed file changes. Marks H1-H4 unchanged.

1. Hygiene: the switch never sees a panel item or a TEST puzzle.
   - Its 1-labels are the day puzzles of seeds 16 and 17 (claude_dl9_experts.py run_seed: puzzles(DAY_SEED + shift +
     100 * seed + d)). TEST is drawn from seed 3090 and every day puzzle is removed from it before use
     (claude_dl9_experts.py:260-263), so no TEST puzzle is a training row or a switch row.
   - Its 0-labels are questions the base wrote, kept only if claude_dl3_replay.clean_question passes them: no digits and
     none of panel_words() (claude_dl3_replay.py:49-59, :62-69). Checked on CPU now: all 300 panel items contain at
     least one panel word (0 of 300 without), so no panel question can enter the pool, whatever the base writes.
   - The panel and TEST are only read by the switch at measure time, as every dl run reads them.
   - VERIFY will also confirm from dl9_results.json that none of the saved pool sample equals a panel question.
2. Number questions are the hard case and are a large share of H3's panel: 139 of 300 items (bigger 119, count 20;
   claude_dl1_nights.py:135-140); the rest are capital 70, order 31, opposite 30, plural 30. They contain digits, like
   the puzzles. Stated before the run (report-only, not a mark): the switch should be OFF for >= 126 of the 139
   number items (90%) on each seed; fewer is reported as "the switch confuses number questions with puzzles". Note
   H3 (off for >= 285 of 300) cannot pass if more than 15 panel items, number items included, are switched on.
3. Serve-time cost: the switch reads the frozen base's last-layer state at the last prompt token, so serving costs
   one extra prompt pass through the frozen base per question (no generation) plus one dot product of 2048 numbers.
   Measured on CPU here (20 panel questions, first call included, so an upper estimate): 1.18 s for the switch read vs
   0.76 s for a 16-token greedy answer. The run reuses stored answers, so it does not time serving; a build would.
