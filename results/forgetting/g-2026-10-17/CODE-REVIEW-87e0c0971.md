# Code review of commit 87e0c0971 (Claude Code built-in /code-review, level high), Oct 20

Scope: domain/far/learn_probe.py and its tests (the --replay-priority draft, arm H1), plus results/forgetting/e0/e0_score.py.
**Verdict: CHANGES NEEDED before the draft code is merged. 9 findings, none of which touches the G1 or G3 results.**
G1 and G3 ran with --replay-priority off. On that path the draw is the original `randint` and the trainer is bit-identical to
62cf9ac36 (final checkpoint sha 60ad8d75 on both).

Spot-checked by the lead against the code: findings 1, 3 and 4 are confirmed (line 24 of e0_score.py; `max(nan, 0.0)` returns nan; line 1974
sets an explicit uniform `p`, so line 2002 takes the `choice` branch from update 1).

| # | where | finding | affects |
|---|---|---|---|
| 1 | e0_score.py:24 | the 6,800-DEV identity check is always true (`[...] is not None`), and the big DEV's sha is never asserted; any 6,800-row file passes | E0 (not yet run): fix before running |
| 2 | learn_probe.py:1663 | diary_families has no sha check on train.jsonl and no count of '?' (unlabelled) rows; priority can silently collapse | H1 only |
| 3 | learn_probe.py:1673/1708 | a NaN KL passes `max(x, 0.0)`, so p becomes all-NaN and `choice` raises, killing the run | H1 only |
| 4 | learn_probe.py:1974 | priority ON uses `choice(p=uniform)` from update 1, not `randint`, so the replay stream differs from the control before any KL measurement (two changes, not one) | H1 only; H1's FAIL stands (its mechanism check failed independently), but its paired contrasts carry this confound |
| 5 | learn_probe.py:2041 | `extra.update(... replay_priority_measures ...)` after the loop is dead code; never reaches a record | H1 records |
| 6 | learn_probe.py:1666 | no minimum family size; a 1-row family can take a large share of replay | H1 only |
| 7 | test_learn_probe_replay.py:1003 | diary_families is stubbed in every test, so the real label lookup is untested | tests |
| 8 | e0_score.py:39 | final-checkpoint fallback is a partial copy of analyze.py (bare KeyError, no "path differs" note) | E0 |
| 9 | learn_probe.py:1706 | per-family KL forwards in tiny batches (speed only) | H1 wall time |

Next (drafts, for the coordinator): fix 1 and 8 before E0 runs; fix 3, 4, 2 (in that order) before any further use of
--replay-priority, or drop the flag, since H1 failed.
