# dl-5s run note (Fix-sleep thread; written 2026-09-26T20:23:35Z, date -u)
- Where: this thread's cloud container CPU (no GPU, $0), repo checkout /home/user/learner at b72467bee (seal).
- Command: timeout 5400 python3 -B scripts/claude_dl5s_switch.py --model <local MiniCPM5-1B snapshot 87179e5c...>
  --out artifacts/claude-dl5s-20260926/cpu  (log: artifacts/claude-dl5s-20260926/cpu/log.txt)
- Started 2026-09-26 19:53 UTC, PID 6520; at 2026-09-26T20:23:35Z it had run 29 min 41 s.
- Last log line so far (written 20:19:23 UTC): the pool/positives summary, i.e. the base has written its quiz
  questions and the switch features are being computed. dl5s_results.json and the full log are committed when the
  run ends; a 90-minute timeout stops it otherwise.

## Try 1 stopped by my own time limit; try 2 started (2026-09-26T21:24:29Z, date -u)
- Try 1 (PID 6520) was killed at 21:23 UTC by the 90-minute `timeout 5400` I put on the command (a wrapper, not part
  of the sealed code). It had written the pool line at 20:19 and was still computing switch features (about 2,200
  prompt passes on CPU; my 35-minute estimate was wrong). No results file was written; nothing was seen.
  Its log is kept as cpu/log-try1-timestop.txt.
- Try 2: the same sealed script and arguments, unchanged, with a 4-hour wrapper: PID 10155, started 2026-09-26T21:24:29Z. Same seeds, so the
  base writes the same pool on this CPU.
