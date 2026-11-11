# Code review of claude/forgetting-round-g vs 62cf9ac36 at 950a7d2e2 (Claude Code built-in /code-review, level high), Oct 20

Third review, after fix round 2 (FIX-ROUND-2.md).
**Verdict: CHANGES NEEDED, 10 findings. None touches the flag-off path:** the reviewer confirms the off path is the old `randint`
draw, matching the four old-vs-new checkpoint identities (G1 exact, replay KL, A1F, replay CE). So the G1 numbers and the code E0
would run on are unaffected. The round-1/2 fixes it re-checked hold: the zero-KL draw, the labels sha comparison and the conflict count.
Not fixed here (the coordinator's instruction: review, record, push, stop).

Lead's note on #1: the reviewer's machine had no torch or pytest, so it read the code without running it. The tests do run and pass
in this repo's venv (55/55). Its point stands on the wording, though: FIX-ROUND-2's "refusal tests run without the torch stack" holds
only for the check_devs tests, because the final_checkpoint / resolve_runs tests import domain.score (torch).

| # | where | finding | affects |
|---|---|---|---|
| 1 | test_e0_score.py:55 | final_checkpoint / resolve_runs tests import domain.score (torch); FIX-ROUND-2's "without the torch stack" claim holds only for check_devs | E0 tests; wording |
| 2 | learn_probe.py:2006 | the --replay-priority label checks refuse only after the parent load, diary build and first K-FAC measure; check them with the other input checks | --replay-priority only |
| 3 | learn_probe.py:2058 | if --replay-priority-every >= --updates (or a futility stop comes first), priority never applies, yet the records say replay_priority=FRAC; refuse or flag it | --replay-priority only (H1 ran 16k with every 500: not this case) |
| 4 | learn_probe.py:2066 | the "no priority mass" rule lives in two places (the loop's S and replay_priority_probs' fallback); make it one | --replay-priority only |
| 5 | learn_probe.py:2067 | the shares on the step-u record are the distribution for updates after u, not the one that produced the step-u weights | --replay-priority records |
| 6 | e0_score.py:38 | nights_run 0 or a missing nights_run key gives a bare KeyError, not a named refusal | E0 |
| 7 | e0_score.py:119 | e0.json is rewritten in place (no temp file + rename) and a stale e0.json survives a failure before the first run | E0 |
| 8 | test_e0_score.py:80 | the wording test checks analyze.py's source against fixed strings, never e0's own messages | E0 tests |
| 9 | learn_probe.py:2059 | priority measuring time lands in the next segment's s/update log line (t_train is right) | log only |
| 10 | learn_probe.py:1740 | measure_family_kl re-collates the same fixed batches each measurement | speed only |
