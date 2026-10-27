# ADDENDUM gr-5 #3: the whole job moves to this container's CPU (2026-09-26 22:43 UTC)

Owner: Plain-English puzzles thread. The time comes from `date -u`. Written before the adapter was trained and before
any gr-5 run. PASSMARKS-gr5.md, ADDENDUM-gr5-1 and ADDENDUM-gr5-2 are not edited. The marks, bars, arms, panel,
training rows, recipe (seed 4990), code, the dev stop rule and the report lines are all unchanged. Only the machine
changes.

- Decision: the Thread manager chose this container's CPU at 22:41 UTC. On BensPC, gr-5 was behind 358i3 (running),
  dl-9 (cap 4 h) and rv390 (cap 2.5 h). The BensPC job 250-gr5-benspc.md was taken out of the queue in 5a917abbe,
  before it had run anywhere (no gr-5 file on builder-outbox), so gr-5 cannot run twice.
- One machine: training, the dev gate, the ADDENDUM-1 dev split line, every registered task (L on squares, lookalikes,
  unseen, general; P0 on squares, lookalikes, unseen) and the score all run on this one CPU container, in that order,
  by artifacts/claude-gr5-20260926/cpu/chain.sh (sealed below). ADDENDUM-gr5-2's rule that everything runs on one
  machine still holds, with this machine in BensPC's place.
- Machine: this container's CPU, 4 threads (OMP_NUM_THREADS=4, torch.get_num_threads() = 4), fp32, torch 2.14.0+cpu,
  transformers 5.17.0, Python 3.11.15. The chain prints the versions again at its start.
- Measured before this addendum: 8 training steps at 3.05 seconds per example. An estimate, not a promise, is about
  1.9 hours to train and about 3.5 hours for the whole job.
- Cap: 6 hours from the chain's first STEP line. At the cap, the chain is stopped by exact PID. What exists is
  committed, and the report is PARTIAL with no verdict. Any continuation needs a new addendum.
- The adapter stays off git. It is written outside the repo, in the session scratch folder, and its sha256 and size go
  into the chain log before the dev gate.
- If the container is reclaimed mid-run, the run restarts from the start under the same seal. Any partial run files
  are moved, not deleted, to run-aborted-N/, and the restart is recorded as a line in run/RUN-NOTE.md, not in a new
  addendum. The sealed scripts do not checkpoint.
- Progress files (logs and each task's run file) are committed as they land. Times come from `date -u`.
