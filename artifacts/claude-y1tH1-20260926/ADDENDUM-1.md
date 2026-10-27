# y1t-H1 addendum 1 (2026-09-26 17:23 UTC, `date -u`; before any y1t-H1 run, before y1t's job is released)

PASSMARKS-y1t-H1.md is unchanged: rows H1a-H1d, their bars, the INCONCLUSIVE rule and the judging stand as sealed.
This records how the run and scoring are wired, fixed before anything runs.

1. Config. PASSMARKS says both arms use "the layout, decoding, checks and fallback that y1t's PLAN registers for its
   own bank E test". Bank E's config is not sealed yet (Answering from memory, 17:20 UTC: rp1 waits for y1t), so the
   config is the one y1t's job runs in step 6b: scripts/claude_y1t_h1run.py (sealed by that thread in
   artifacts/claude-y1t-20260926/SEAL-y1tH1-runner.sha256.txt): every earlier user turn in time order, y1f's L1
   layout, one greedy answer, y1f's checks, "I don't know." when a check fails. A = plain MiniCPM5-1B, B = y1t merged,
   whatever y1t's DEV verdict is. Job: handoff/held/rent-0y1t.md step 6b (main 9971ac474); only panel/turns.jsonl goes
   to the rental, checked against SEAL-spare401.
2. Scoring adapter. The runner writes kind "ask"; the 336 scorer scores kind "user" and needs "ms" and
   "notebook_events". scripts/claude_y1tH1_score.py copies the rows to score/arm_A.jsonl and arm_B.jsonl with kind
   "user", ms 0.0 and notebook_events [] and runs the unchanged scorer (selftest on DEV: 71 asks per arm).
3. Judging and marks. scripts/claude_y1tH1_marks.py: prep = sf-401's packet prep with seed 4013; split = sf-401's;
   marks = H1a-H1d and the report rows exactly as PASSMARKS words them; score_ask gets no confirm row (there are
   none). Selftest runs sf-401's own rows through the whole pipeline with fake judges.
4. Order after the rows land: claude_y1tH1_score.py PANEL RUN SCORE -> marks prep -> two blind Opus judges with
   JUDGE-sf401.md verbatim, each given only a copy of asks.jsonl -> split -> third judge on splits -> marks ->
   blind recount agent (RECOUNT-sf401.md's method, rows H1a-H1d) -> VERIFY.
