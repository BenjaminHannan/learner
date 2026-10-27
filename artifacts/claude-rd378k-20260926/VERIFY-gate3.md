# rd-378k label gate 3 = NO VERDICT: the run was hit by OpenRouter's 402s (Trustworthy notes thread, 2026-09-26 19:29 UTC)

Source: origin/builder-outbox runs/rd378k-gate3 (rc=0) and artifacts/claude-rd378k-20260926/gate3/teacher-log.txt.
As fixed in PASSMARKS-F.md before this output landed, only these counts were read from gate3 (by a script that prints
nothing else); its labels, grade counts and agreement lines were not read and are never used:

- log lines "try N failed: HTTPError HTTP Error 402": 298 (no other HTTP error code)
- failed calls: 71
- usable dialogs: 18 of 38 (chat 12 of 23, overheard 6 of 15)

The OpenRouter account ran out of funds at about 18:29-18:33 UTC; gate3 started at about 18:32 UTC. So gate3 measured
the account, not the grader, and does not count either way (agreed with the Thread manager, 19:00 UTC). Next, per
PASSMARKS-F.md: the same labeller on the same 38 dialogs through Ben's opencode route (rd378k-gate3oc).
