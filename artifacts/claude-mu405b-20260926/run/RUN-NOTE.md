# mu-405b run note (written 2026-09-26 23:20:05 UTC by date -u)

- Registered run of arm U, sealed 774865c0d. Started 2026-09-26 22:39:09 UTC (run/started.txt, written by date -u at
  launch): torch 2.14.0+cpu, transformers 5.17.0, 4 threads.
- Machine: the "Making things up about you" thread's cloud container, CPU only, $0 (uptime 4:02 at 23:19:53 UTC; no
  restart since 19:17 UTC).
- Process: PID 10994 (python3 -B scripts/claude_mu405b_talk.py), launched by a tracked shell (PID 10982) that writes
  run/exits.txt when it ends.
- Command: HF_HUB_OFFLINE=1 PYTHONUTF8=1 python3 -B scripts/claude_mu405b_talk.py --panel
  artifacts/claude-mu405-20260926/panel/items.jsonl --facts artifacts/claude-mu405-20260926/facts.jsonl --model
  <MiniCPM5-1B snapshot 87179e5c> --out artifacts/claude-mu405b-20260926/run > run/logU.txt 2>&1
- Progress at 23:19:53 UTC: 55 of 60 chats (run/logU.txt progress lines; counts only).
- Next steps: exit line and talk_U.jsonl; RESULTS (rows, asks right, exit code) pushed BEFORE judging; gather N/W/H/U
  into judge/runs by sha256; prep 240 packets (seeds 4061-4063); two fresh blind Opus judges per packet, each in its
  own private folder; count; blind recount; VERIFY.md; verdict to the Thread manager and Month-end.
