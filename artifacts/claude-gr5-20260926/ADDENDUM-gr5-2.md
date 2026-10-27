# ADDENDUM gr-5 #2: where the registered run happens (2026-09-26 20:29 UTC)

Owner: Plain-English puzzles thread. The time comes from `date -u`. Written before the adapter was trained and before
any gr-5 run (the BensPC job has not started). PASSMARKS-gr5.md is not edited. The marks, bars, arms, the training
recipe and rows, the dev stop rule, the panel and the code are all unchanged.

PASSMARKS-gr5.md's "Where it runs" section says the training is on this container's CPU unless one timed step is too
slow, and that the run and the score are on this container's CPU. Both are replaced. Everything now runs on BensPC
(RTX 5070 Ti, free) as one job, handoff/queue/250-gr5-benspc.md: training, the dev gate, the addendum-1 report line,
each registered task launched once (L on squares, lookalikes, unseen, general; P0 on squares, lookalikes, unseen), and
the score. Only run files, counts and logs come back.

Why:
- A two-step smoke on this CPU took about 14 seconds per training example, so 3 epochs of 739 rows would take hours.
- The Thread manager's review (20:04 UTC) asked for a BensPC slot at once rather than after CPU timing.
- The adapter is about 16 MB of weights, and weights stay off git, so the adapter never leaves BensPC. The run
  therefore has to happen where the adapter is. Its sha256 is logged on BensPC before the dev gate.

The same review condition was written into the job file (16e4f2e38), but the PASSMARKS text was not changed with it.
The Thread manager found the mismatch at 20:28 UTC, and this addendum fixes it.
