COMMON RULES: follow the first 14 lines of origin/main:handoff/queue/lis-302-gpu.md. The "Trustworthy notes" thread (Claude) wrote this task on 2026-09-27 03:58 UTC. Report in your final reply: verdict first, integer counts.
GPU: no. This task stops two stuck Mac jobs by exact PID and deletes the opencode sessions of the GLM calls it cuts off. No GPU, no model call, no rental.
DUPLICATE GATE: stop with DUPLICATE if origin/main or origin/builder-outbox already has artifacts/claude-stop-rd378low-20260927/REPORT.md.

YOUR TASK: stop 004-rd378k-gate3low and 005-rd378g-writelow. Ben's opencode Go plan hit its weekly limit at about 00:57 UTC, and both jobs have been stuck since. Their output is dropped unread (artifacts/claude-rd378k-20260926/PASSMARKS-K.md). Never read, print or copy any opencode config, auth file or key. Never read or print any log line, output file or full command line of these jobs. Report PIDs, elapsed times, roles and --title tags only.
1. `date -u`. Run `ps -axo pid,ppid,etime,command` and find, for each job:
   (a) the processes whose command contains claude_glm_low_run.py together with claude_rd378k_teacher3oc.py (job 004) or claude_rd378g_writemore_oc.py (job 005). There may be a shell, a uv wrapper and the python. "The python" is the one whose command begins with a path ending in python3.12 or python3. None is also possible, if the python already finished.
   (b) the job's launcher `bash .../handoff/kit/mimo/rungo4.sh .../queue/004-rd378k-gate3low.md` (or 005-rd378g-writelow.md), which is never killed. Its child is the job's agent. The job is that agent with all its descendants, plus any orphaned chain from the python up to PID 1 (PID 1 excluded).
   (c) each python's children whose command starts with `/usr/local/bin/opencode run`. For each, record only the word after `--title` (glm11- followed by 32 hex characters), and record the python's working directory from `lsof -a -p PID -d cwd` (path only).
2. Stop each job, by exact PID only. `kill` the agent first, then every other process of the job, then the opencode children. Wait 10 s, then `kill -9` any of those PIDs still alive. Never kill a rungo4.sh launcher, the watcher, any other job's processes (anything with claude_luna_run.py included), or anything on BensPC. If a job has no agent and no python left, report NOT-RUNNING for it.
3. For each tag from 1(c): cd to that python's cwd (it contains scripts/claude_glm_opencode_v11.py) and run `uv run --offline --no-project --python 3.12 python -B -c "import sys; sys.path.insert(0, 'scripts'); import claude_glm_opencode_v11 as H; d = H._project_dir(); ids = H._ids_with_title(d, sys.argv[1]); H._delete_sessions(d, ids); print(len(ids), len(H._ids_with_title(d, sys.argv[1])))" TAG`. Report the two numbers (found, left) per tag. If the cwd is gone, report "cwd gone". Delete nothing else.
4. `date -u`. Write artifacts/claude-stop-rd378low-20260927/REPORT.md with only:
   - one line per job: STOPPED or NOT-RUNNING;
   - the PIDs killed with their roles, and the kill -9 count;
   - the tags with their found/left numbers.
PUSH: artifacts/claude-stop-rd378low-20260927/REPORT.md
DISK: 0
