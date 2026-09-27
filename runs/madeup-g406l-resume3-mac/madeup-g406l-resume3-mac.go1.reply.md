# g406b-L resume3 (BASH-ONLY) RESULTS
- start: Sun Sep 27 08:44:42 UTC 2026
- uptime:  4:44  up 3 days, 18:37, 4 users, load averages: 40.80 35.28 34.95
- python: 3.12.14
- origin/main: e1903e7af4c250fc9782648dc709602593c07a8b
- copied run/luna_b.jsonl to run2/
- luna_b.jsonl lines now:      220
- sha256 of its first 220 lines: 19889ed299570f1adc3fecb5576246156dc98bdd4759f706e87f46f8e414f910
## SEAL
artifacts/claude-g406l-20260927/PASSMARKS.md: OK
artifacts/claude-mu405-20260926/JUDGE-claims405.md: OK
artifacts/claude-mu405b-20260926/judge/keys/claims_key.json: OK
artifacts/claude-mu405b-20260926/judge/out/claims_j1.jsonl: OK
artifacts/claude-mu405b-20260926/judge/out/claims_j2.jsonl: OK
artifacts/claude-mu405b-20260926/judge/out/claims_j3.jsonl: OK
artifacts/claude-mu405b-20260926/judge/out/claims_j4.jsonl: OK
artifacts/claude-mu405b-20260926/judge/out/claims_j5.jsonl: OK
artifacts/claude-mu405b-20260926/judge/out/claims_j6.jsonl: OK
artifacts/claude-mu405b-20260926/judge/out/claims_j7.jsonl: OK
artifacts/claude-mu405b-20260926/judge/out/claims_j8.jsonl: OK
artifacts/claude-mu405b-20260926/judge/packets/claims_j1.jsonl: OK
artifacts/claude-mu405b-20260926/judge/packets/claims_j2.jsonl: OK
artifacts/claude-mu405b-20260926/judge/packets/claims_j3.jsonl: OK
artifacts/claude-mu405b-20260926/judge/packets/claims_j4.jsonl: OK
artifacts/claude-mu405b-20260926/judge/packets/claims_j5.jsonl: OK
artifacts/claude-mu405b-20260926/judge/packets/claims_j6.jsonl: OK
artifacts/claude-mu405b-20260926/judge/packets/claims_j7.jsonl: OK
artifacts/claude-mu405b-20260926/judge/packets/claims_j8.jsonl: OK
scripts/claude_g406l_luna.py: OK
scripts/claude_luna_codex.py: OK
scripts/claude_g406_2_glm.py: OK
scripts/claude_g406_glm.py: OK
scripts/claude_g406_count.py: OK
## SELFTESTS
[g406-2/two] pass 1: 2 written this run, 0 failed
g406l luna selftest 7/7 ok
  rc=0
[g406-2/two] pass 2: 5 written this run, 2 failed
g406-2 selftest 7/7 ok
  rc=0
g406 count selftest 5/5 ok
  rc=0
selftest ok: model gpt-6-luna, output-file True
  rc=0
  all 4 selftests ok
## RESUME
- resume started Sun Sep 27 08:44:51 UTC 2026, pid 89979
- resume ended Sun Sep 27 08:50:21 UTC 2026, rc=0
- log last line: {"mode": "two", "packets": 240, "usable_before": 220, "written": 20, "failed_this_run": 0, "usable_now": 240, "minutes": 5.2, "stopped": "done"}
- luna_b.jsonl lines:      240
- error prefixes (first 60 chars, counts):
   240 ''
## COUNT
{"packets": 240, "usable": 240}
  rc=0
{"packets": 240, "usable_packets": 240, "replies": 1200, "judge_either": 168, "judge_both": 131, "glm_flags": 394, "glm_catches_both": 130, "glm_catches_either": 158, "glm_clean": 806, "either_in_glm_clean": 10, "recall_both": 0.992, "recall_either": 0.94, "base_either_rate": 0.14, "either_rate_in_glm_clean": 0.0124, "either_rate_in_glm_flagged": 0.401, "yield_clean": 0.672, "kappa_vs_either": 0.455, "V": true, "G1": true, "G2": true, "G3": true, "proved_wrong": false, "verdict": "PASS", "per_source": {"claude-mu405b-20260926": {"replies": 1200, "either": 168, "both": 131, "glm_flags": 394, "glm_catches_both": 130}}}
  rc=0
  rc=0
labeller: Luna (gpt-6-luna), helper sha256 342a0fb7e15ebf22da763c21eddecb0c58cfcbd43c74481d8421b5709023024e
- copied luna_b.jsonl (     240 lines)
- copied luna_b.log (       2 lines)
- copied best_b.jsonl (     240 lines)
- copied verdict_b.json (      34 lines)
- copied arms_b.json (       1 lines)
- end: Sun Sep 27 08:50:22 UTC 2026
temp dir removed
rc=0
