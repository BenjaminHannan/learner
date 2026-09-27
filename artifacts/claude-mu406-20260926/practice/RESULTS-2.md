# mu-406 practice chats (BASH-ONLY) RESULTS
- start: Sun Sep 27 11:52:12 UTC 2026
- uptime:  7:52  up 3 days, 21:45, 4 users, load averages: 17.04 24.02 31.90
- python: 3.12.14
- origin/main: ed2bc55fabfc33bdae22caae51b02aa8e6d3e45b
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
- restart: seeded raw.jsonl from builder-outbox (     168 lines)
## FACTS
{"set": "practice", "rows": 260, "smoke": 0}
  rc=0
- writing the first      240 candidates in id order (select keeps the first 220 that pass, so later candidates could never be chosen)
## WRITE
- write started Sun Sep 27 11:52:29 UTC 2026, pid 28850
- write ended Sun Sep 27 12:11:30 UTC 2026, rc=0
- write-2.log last line: {"rows": 240, "ok": 238, "errors": {"value_in_chat2": 2}, "stopped": "done", "minutes": 18.7}
## SELECT
{"set": "practice", "train": 200, "heldout": 20}
  rc=0
## SCAN
{"kept_chats": 238, "scan_hits": {"usage limit": 0, "rate limit": 0, "error:": 0, "as an ai": 0, "openai": 0, "codex": 0, "i can't help with": 0}, "repeated_messages": 68, "max_repeat": 33}
  rc=0
writer: Luna (gpt-6-luna), helper sha256 342a0fb7e15ebf22da763c21eddecb0c58cfcbd43c74481d8421b5709023024e
- copied facts_all.jsonl (     260 lines)
- copied raw.jsonl (     240 lines)
- copied write-2.log (       7 lines)
- copied items.jsonl (     200 lines)
- copied facts.jsonl (     200 lines)
- copied heldout.jsonl (      20 lines)
- copied heldout_facts.jsonl (      20 lines)
- end: Sun Sep 27 12:11:30 UTC 2026
