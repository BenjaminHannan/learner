# sf-401 blind recount brief (fixed 2026-09-26 ~14:30 UTC, before any run)

Given verbatim to one recount agent after the judges and scripts/claude_sf401_judges.py marks have run. It must not
read or run scripts/claude_sf401_judges.py or claude_sf401_diag.py, and must not see the builder's mark table.

---
Never use WebFetch or any web access in this task. Do not call any mcp__hearthbot__ tools.

You recount a registered result from its files, with your own code. Files (all under artifacts/claude-sf401-20260926/):
panel/turns.jsonl (asks have kind "ask", ask_type, gold), run/arm_A.jsonl and run/arm_B.jsonl (one row per user
turn; kind "user" or "confirm_answer"), score/judge_asks_A.jsonl and judge_asks_B.jsonl (every ask the mechanical
rules call wrong), judges/asks.jsonl + judges/key_asks.json (packet id -> arm) + judges/j1.jsonl, j2.jsonl, j3.jsonl
(verdicts; j3 only on ids where j1 and j2 differ; final = j1 when j1 = j2, else j3). The mechanical class of each
ask comes from scripts/claude_e2e336_score.py's score_ask(turn, row, confirm_row) (import it; you may read that file).
Recompute, per arm A and B, and print one table: judged wrong on all asks, on control asks (ask_type not edit and not
never_told) and on edit asks; RIGHT + RIGHT_CONFIRM on control asks and on edit asks; ABSTAIN on control asks; RIGHT
on never_told asks. Then check these marks: M1 wrong B <= A - 4; M2 control right B >= A - 2; M3 edit right B >= A;
M4 control abstain B <= A + 2; M5 control wrong B <= A + 1; M6 never-told right B >= A - 1; INCONCLUSIVE if A's
judged-wrong edit asks < 5. Print counts only: never any user text, reply text, names or facts.
---
