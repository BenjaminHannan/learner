# dl-5s run note (Fix-sleep thread; written 2026-09-26T20:23:35Z, date -u)
- Where: this thread's cloud container CPU (no GPU, $0), repo checkout /home/user/learner at b72467bee (seal).
- Command: timeout 5400 python3 -B scripts/claude_dl5s_switch.py --model <local MiniCPM5-1B snapshot 87179e5c...>
  --out artifacts/claude-dl5s-20260926/cpu  (log: artifacts/claude-dl5s-20260926/cpu/log.txt)
- Started 2026-09-26 19:53 UTC, PID 6520; at 2026-09-26T20:23:35Z it had run 29 min 41 s.
- Last log line so far (written 20:19:23 UTC): the pool/positives summary, i.e. the base has written its quiz
  questions and the switch features are being computed. dl5s_results.json and the full log are committed when the
  run ends; a 90-minute timeout stops it otherwise.
