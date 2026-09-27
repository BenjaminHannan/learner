COMMON RULES: follow the first 14 lines of origin/main:handoff/queue/lis-302-gpu.md. The "Trustworthy notes" thread (Claude) wrote this task on 2026-09-27 00:24 UTC; the Thread manager asked for it at 00:20 UTC. Report in your final reply: verdict first, integer counts.
GPU: no. This task looks at two running Mac jobs, stops them by exact PID, and deletes the opencode sessions those stopped calls leave behind. No GPU, no new opencode call, no rental.
DUPLICATE GATE: stop with DUPLICATE if origin/main or origin/builder-outbox already has artifacts/claude-peek-rd378oc2-20260927/REPORT.md.

YOUR TASK: count how far the running jobs rd378k-gate3oc and rd378g-writemore have got, then stop them by the rules in step 4. Both are being restarted at opencode reasoning effort "low" (read origin/main:artifacts/claude-rd378k-20260926/PASSMARKS-I.md). Never read, print or copy any opencode config, auth file or key. Never print a log line's text or a full command line (they can hold prompt text): counts, PIDs, elapsed times and the --title tags only.
1. `date -u`, `uptime`. Run `ps -axo pid,ppid,etime,command` and find:
   (a) the processes whose command contains claude_rd378k_teacher3oc.py (job gate3oc) or claude_rd378g_writemore_oc.py (job writemore), each together with claude_glm_v11_run.py. There may be a shell, a uv wrapper and the python itself for each job. "The python" below is the one whose command begins with a path ending in python3.12 or python3;
   (b) each one's chain of parents, walked up by PPID until the process `bash .../handoff/kit/mimo/rungo4.sh .../queue/rd378k-gate3oc.md` (or rd378g-writemore.md). That launcher is the watcher's and is never killed. The processes between it and the python (the job's agent, usually `opencode run --model opencode-go/... --auto`, then any shell and the uv wrapper) belong to the job. If the walk reaches PID 1 before any rungo4.sh (a nohup'd process can be re-parented), find the launcher by the job's .md in its command. The job's agent is then that launcher's child. The job is that agent with its descendants, plus the orphaned chain from the python up to PID 1, PID 1 excluded;
   (c) each python's children whose command starts with `/usr/local/bin/opencode run` (GLM calls in flight). For each one, record only the word after `--title` (glm11- followed by 32 hex characters).
   Also record each python's working directory, from `lsof -a -p PID -d cwd` (path only).
   Report per job: PID, PPID, elapsed time and role for every process on the chain, the python's cwd, and the tags. If a job has no python process, report "not running" for it.
2. For each running python, find its log with `lsof -p PID | grep -E " [12]w "` (path only). Counts only:
   - both jobs: lines containing "call failed";
   - gate3oc: lines that start with "[rd378k-teacher3]" and end " ok", and lines that start with it and end " unparsed";
   - writemore: lines matching "batch [0-9]+ ok", "batch [0-9]+ try" and "skipped after 3 tries".
3. Done counts. gate3oc: dialogs done = ok lines + unparsed lines, of 38. writemore: batches done = "batch N ok" lines + "skipped after 3 tries" lines, of 21.
4. STOP RULES:
   - gate3oc, if running: always stop it.
   - writemore, if running: stop it if batches done is 17 or fewer. If it is 18 or more, touch nothing for it and report LEFT-RUNNING.
   How to stop a job, by exact PID only: `kill` the job's agent (the process just below its rungo4.sh launcher), then every other process on the chain below it, then the python, then the python's opencode children. Wait 10 s, then `kill -9` any of those PIDs still alive. Never kill the rungo4.sh launcher, the watcher, any other job's processes, or anything on BensPC. Report STOPPED for the job.
5. Session cleanup, for stopped jobs only. For each tag recorded in step 1(c), cd to that job's python cwd from step 1 (it contains scripts/claude_glm_opencode_v11.py) and run:
   `uv run --offline --no-project --python 3.12 python -B -c "import sys; sys.path.insert(0, 'scripts'); import claude_glm_opencode_v11 as H; d = H._project_dir(); ids = H._ids_with_title(d, sys.argv[1]); H._delete_sessions(d, ids); print(len(ids), len(H._ids_with_title(d, sys.argv[1])))" TAG`
   It prints two numbers per tag: sessions found, and sessions left after the delete. Report both. Delete nothing else.
   If the cwd no longer exists, report "cwd gone" for that tag and do nothing.
6. `date -u`. Write artifacts/claude-peek-rd378oc2-20260927/REPORT.md. It holds:
   - one line per job: STOPPED, LEFT-RUNNING or NOT-RUNNING;
   - the counts from steps 2-3 and elapsed times;
   - the PIDs killed, and the kill -9 count;
   - the tags with found/left.
   Numbers only, no log text.
PUSH: artifacts/claude-peek-rd378oc2-20260927/REPORT.md
DISK: 0
