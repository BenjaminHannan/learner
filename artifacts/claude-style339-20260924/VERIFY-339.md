# 339 verified (month-end thread, 2026-09-24 ~17:30 UTC): registered FAIL on P339.1 and P339.2 (proved wrong)

Run: rent-339-style (origin/builder-outbox:artifacts/claude-style339-20260924/RESULTS-rent.md). Recount: this thread
re-ran the sealed scorer (scripts/claude_style339_run.py --score) on a copy of run/arm_{B,P,T}.jsonl; every number
matches the builder's. Nobody read the panel.

| Mark | Bar | Result | Verdict |
|---|---|---|---|
| P339.1 feedback lives with exactly the right preference saved | ≥ 32/40 | 17/40 (23 saved nothing, 0 wrong or extra) | **FAIL** |
| P339.2 control lives with any preference saved | 0/20 | 2/20 | **FAIL** (above the proved-wrong line of 1) |
| P339.3 day-3 follow rate (blind judge) | ≥ 80% | not judged; moot after P339.1 | not run |
| P339.4 preferences saved on the 194-turn DEV bank | 0 | 0 (0 of 248 rows start with an ACK339 line) | PASS |

Reading: the fixed feedback rules miss more than half of the ways people actually phrase feedback, and 2 look-alike
turns ("my boss keeps calling me ..."-style) still triggered a save. 339 does not go into 0.1 as a learned layer;
the "learning over time" row of the 09-30 report records this FAIL. Also found: the plain twin (old version)
started 766 of its 768 replies with a thinking block (see artifacts/claude-chat338-20260924/VERIFY-338.md).

Ben (18:43 UTC, via the coordinator): he does not expect this to work well at today's reasoning level and wants it at scale-up.
So 339 stays a registered FAIL and becomes a scale-up goal; no more 0.1 runs go to it.
