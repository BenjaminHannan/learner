COMMON RULES: follow the first 14 lines of origin/main:handoff/queue/lis-302-gpu.md. The "Trustworthy notes" thread (Claude) wrote this task on 2026-09-27 07:30 UTC. Report in your final reply: verdict first, integer counts.
GPU: no. Short plumbing job: find two running python processes, count their log lines, start one detached finisher script. No model call, no GPU, no rental, never kill anything.
LOAD-LIGHT: yes
DUPLICATE GATE: stop with DUPLICATE if origin/main or origin/builder-outbox already has artifacts/claude-rescue-rd378-20260927/REPORT.md.

WHY: the job agents of 006-rd378k-gate3luna and 008-rd378g-writeluna2 died on their own model's "Rate limit exceeded". Their nohup'd python runs (a Luna label gate and a Luna practice-batch write) kept going in the jobs' temp dirs, and nothing will copy their results out. This task starts scripts/claude_rd378_finish.sh (read its header) detached. It waits for each python to exit, runs the next steps with the same sealed code, and copies the outputs into this worktree. A later job pushes them.
RULES: never read, print or copy anything under ~/.codex or any Codex / ChatGPT / opencode config, auth file or key. Never print a log line's text, a row, or a full command line: counts, PIDs, elapsed times and directory paths only. Never kill or restart any process.

1. `date -u`. Run `ps -axo pid,etime,command` and find:
   - the GATE python: command begins with a path ending in python3.12 and contains claude_luna_run.py, claude_rd378k_teacher3oc.py and gate3luna;
   - the WRITER python: command begins with a path ending in python3.12 and contains claude_luna_run2.py, claude_rd378g_writemore_oc.py and glm2N.
   For each, report PID and elapsed time, and its cwd from `lsof -a -p PID -d cwd` (path only). If one is missing, report "not running" for it and use PID 0.
2. GATE_DIR is the gate python's cwd if it is running, else /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/opencode/rd378k-gate3luna-tmp. It must contain scripts/claude_rd378k_teacher.py; if not, report GATE-DIR-MISSING and use it anyway.
   WRITER_DIR is the writer python's cwd if it is running, else the directory matching /tmp/rd378g-luna2-* that contains write-run.log. Report every match.
3. Counts only:
   - gate log: the file under GATE_DIR (not *.jsonl) found by `grep -rl --exclude='*.jsonl' '\[rd378k-teacher3\] td-' GATE_DIR`. Report its path and its count of lines that end " ok", end " unparsed", and contain "call failed".
   - writer log WRITER_DIR/write-run.log: its count of lines matching "batch [0-9]+ ok", "batch [0-9]+ try", "skipped after 3 tries" and "call failed".
4. From your worktree root:
   - mkdir -p artifacts/claude-rescue-rd378-20260927;
   - `git show origin/main:scripts/claude_rd378_finish.sh > artifacts/claude-rescue-rd378-20260927/finish.sh`. `shasum -a 256` of it must be 6e01bfaf7d4ba6ea7ee5576012030a3cd961f7c75addf33fc9f26b1b8b21ad77; if not, stop with SEAL-MISMATCH;
   - `nohup bash artifacts/claude-rescue-rd378-20260927/finish.sh "$(pwd)" "GATE_DIR" GATE_PID "WRITER_DIR" WRITER_PID > artifacts/claude-rescue-rd378-20260927/finisher.log 2>&1 & disown`, then report the finisher's PID.
   - Wait 20 s, then report finisher.log's lines. They hold timestamps, START and counts only.
   The finisher must keep running after you finish. Never wait for it.
5. `date -u`. Write artifacts/claude-rescue-rd378-20260927/REPORT.md with the PIDs, elapsed times, dirs, counts, the finisher PID and finisher.log's lines.
PUSH: artifacts/claude-rescue-rd378-20260927/REPORT.md artifacts/claude-rescue-rd378-20260927/finisher.log
DISK: 0
