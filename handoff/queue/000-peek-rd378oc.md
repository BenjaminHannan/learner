COMMON RULES: follow the first 14 lines of origin/main:handoff/queue/lis-302-gpu.md (the "Trustworthy notes" thread, Claude, wrote this task on 2026-09-26 20:33 UTC; the Thread manager asked for it at 20:33 UTC). Report in your final reply: verdict first, integer counts.
GPU: no (a read-only look at two running Mac jobs; no GPU, no opencode call, no rental).
DUPLICATE GATE: stop with DUPLICATE if origin/main or origin/builder-outbox already has artifacts/claude-peek-rd378oc-20260926/REPORT.md.

YOUR TASK: check whether the opencode route is failing inside the running jobs rd378k-gate3oc and rd378g-writemore, and stop a job only by the rule in step 4. Never read, print or copy any opencode config, auth file or key. Never print a log line's text: counts only.
1. `ps -axo pid,ppid,etime,command | grep -E "claude_rd378k_teacher3oc|claude_rd378g_writemore_oc" | grep -v grep`: report PID, elapsed time and which job (teacher3oc = gate3oc, writemore_oc = writemore). No process for a job: report "not running" for it (it may have stopped at its LEAK or ROUTE-FAIL check, or finished).
2. For each PID: its log file from `lsof -p PID | grep -E " [12]w "` (report the path only).
3. From each log, counts only: lines containing "call failed"; for gate3oc, lines ending " ok" and lines ending " unparsed" that start with "[rd378k-teacher3]"; for writemore, lines matching "batch [0-9]+ ok", "batch [0-9]+ try" and "skipped after 3 tries".
4. STOP RULE (route failing): if a job's log has at least 8 "call failed" lines and 0 ok lines (gate3oc: dialog ok lines; writemore: batch ok lines), stop that job with `kill <PID>` (that exact python PID only; nothing else) and report STOPPED-ROUTE for it. Otherwise touch nothing and report RUNNING-OK.
5. `date -u`. Write artifacts/claude-peek-rd378oc-20260926/REPORT.md with those numbers only.
PUSH: artifacts/claude-peek-rd378oc-20260926/REPORT.md
DISK: 0
