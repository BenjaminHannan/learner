# mu-406 teaching replies (BASH-ONLY) RESULTS
- start: Sun Sep 27 15:37:28 UTC 2026
- uptime: 11:37  up 4 days,  1:30, 4 users, load averages: 36.99 39.62 49.32
- launch 2 leftovers removed: yes
- python: 3.12.14
- origin/main: bcef721d7b59022db8fe84673cd9c81812821bf4
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
panel/items.jsonl: OK
panel/facts.jsonl: OK
panel/facts_all.jsonl: OK
panel/raw.jsonl: OK
## SELFTESTS
[mu406t] 1/1 chats, 1 whole in this batch
mu406 teach selftest 9/9 ok
  rc=0
selftest ok: model gpt-6-luna, output-file True
  rc=0
  both selftests ok
- chats to teach:      220 (held-out first), facts rows      220
- restart: seeded teach.jsonl from builder-outbox (      92 chats)
## WRITE
- write started Sun Sep 27 15:38:29 UTC 2026, pid 8862
- write ended Sun Sep 27 16:31:01 UTC 2026, rc=0
- teach-3.log last line: {"chats": 160, "whole": 160, "turns": 800, "first_try": 799, "fails": {"too_long": 1}, "stops_by_reason_and_turn_kind": {}, "median_chat_seconds": 57.9, "stopped": "time", "minutes": 52.1}
## STATS
{"chats": 160, "whole": 160, "turns": 800, "first_try": 799, "fails": {"too_long": 1}, "stops_by_reason_and_turn_kind": {}, "median_chat_seconds": 57.9}
  rc=0
writer: Luna (gpt-6-luna), helper sha256 342a0fb7e15ebf22da763c21eddecb0c58cfcbd43c74481d8421b5709023024e
- copied teach.jsonl (     160 lines)
- copied teach-3.log (      18 lines)
- end: Sun Sep 27 16:31:01 UTC 2026
temp dir removed
rc=0
