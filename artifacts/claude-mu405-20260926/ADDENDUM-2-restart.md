# mu-405 ADDENDUM-2: the CPU run was cut off; the same run restarts in run2/ (written 2026-09-26 19:18:43 UTC by date -u, before any reply is read)

- The registered CPU run (ADDENDUM-1, launched 18:48:43 UTC) stopped at 19:02:05 UTC during arm N, after chat 20 of
  60, because this cloud container was reclaimed while the thread was idle (uptime 0 min at 19:17 UTC). Arm N writes
  its replies only when all 60 chats finish, so no reply from this attempt exists; its only file besides
  run/started.txt is run/logN.txt, which holds progress lines only. Both stay in run/ as a record and are never scored.
- The restart is the same run: sealed code, panel, facts and marks unchanged from 132260303 (sha256 -c 13/13 OK and
  selftest 6/6 at 19:18 UTC), same machine type, torch 2.14.0+cpu, transformers 5.17.0, MiniCPM5-1B 87179e5c, arms
  N, K, W, H in that order. Its output goes to artifacts/claude-mu405-20260926/run2/, and run2/ is the one registered
  run. Greedy decoding on the same machine, so nothing about the replies depends on which attempt ran.
- To stop another cut-off, the thread keeps a tracked watcher open while the run goes, and checks the run every hour.
  If the container is reclaimed again, the fallback is BensPC through the queue (free), recorded in a further addendum
  before any output is read.
- Correction to ADDENDUM-1: the duplicate rental was vast instance 52800315, not 52799415 (Director, 19:17 UTC). It
  ran 0.056 h at $0.494/h, about $0.03, wrote no output, and was destroyed; its builder was killed at 18:53 UTC
  (artifacts/claude-stop-mu405-20260926/REPORT.md on builder-outbox).
