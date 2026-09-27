# mu-406 test panel (BASH-ONLY) RESULTS
- start: Sun Sep 27 10:01:23 UTC 2026
- uptime:  6:01  up 3 days, 19:54, 4 users, load averages: 17.52 27.84 32.61
- python: 3.12.14
- origin/main: 38ad6d0a3c5fe9fd992fc533e0246abbeb5ec36f
## SEAL
artifacts/claude-mu406-20260926/PASSMARKS.md: OK
artifacts/claude-mu406-20260926/JUDGE-pair406.md: OK
artifacts/claude-mu405-20260926/JUDGE-claims405.md: OK
artifacts/claude-mu407-20260927/JUDGE-fit407.md: OK
artifacts/claude-mu407-20260927/prep/frames.json: OK
scripts/claude_mu406_prep.py: OK
scripts/claude_mu406_teach.py: OK
scripts/claude_mu406_train.py: OK
scripts/claude_mu406_talk.py: OK
scripts/claude_mu406_judge.py: OK
scripts/claude_mu407_prep.py: OK
scripts/claude_mu407_prep_luna.py: OK
scripts/claude_mu405_facts.py: OK
scripts/claude_luna_codex.py: OK
scripts/claude_mu407_talk.py: OK
scripts/claude_mu405_talk.py: OK
scripts/claude_cre333_agent.py: OK
scripts/claude_e2e336_twin.py: OK
scripts/claude_y1f_layout.py: OK
scripts/claude_k1h_train.py: OK
scripts/claude_k1h_cre.py: OK
scripts/claude_chat338_agent.py: OK
scripts/claude_cre333d_agent.py: OK
scripts/claude_cre333b_agent.py: OK
scripts/claude_k1a_cre.py: OK
scripts/claude_k1f_cre.py: OK
scripts/claude_mu407_judge.py: OK
scripts/claude_mu402_judge.py: OK
scripts/claude_bm390.py: OK
scripts/claude_bm390_score.py: OK
## SELFTESTS
mu406 prep selftest 10/10 ok
  rc=0
{"ok": false, "attempts": 3, "error": "luna call failed after 3 tries: timeout after 300s"}
mu407 prep-luna selftest 11/11 ok
  rc=0
selftest ok: model gpt-6-luna, output-file True
  rc=0
  all 3 selftests ok
## FACTS
{"set": "test", "rows": 78, "smoke": 3}
  rc=0
## WRITE
- write started Sun Sep 27 10:01:48 UTC 2026, pid 74246
- write ended Sun Sep 27 10:22:50 UTC 2026, rc=0
- write.log last line: {"rows": 78, "ok": 78, "errors": {}, "stopped": "done", "minutes": 20.7}
## SELECT
{"set": "test", "panel": 60, "smoke": 3}
  rc=0
## SCAN
{"kept_chats": 78, "scan_hits": {"usage limit": 0, "rate limit": 0, "error:": 0, "as an ai": 0, "openai": 0, "codex": 0, "i can't help with": 0}, "repeated_messages": 25, "max_repeat": 12}
  rc=0
writer: Luna (gpt-6-luna), helper sha256 342a0fb7e15ebf22da763c21eddecb0c58cfcbd43c74481d8421b5709023024e
- copied facts_all.jsonl (      78 lines)
- copied raw.jsonl (      78 lines)
- copied write.log (       8 lines)
- copied items.jsonl (      63 lines)
- copied facts.jsonl (      63 lines)
- end: Sun Sep 27 10:22:50 UTC 2026
temp dir removed
rc=0
