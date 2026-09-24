Cache pin and deleter hunt — verifying snapshot and tracing the wipe.
Snapshot is present and backed up — now hunting for the deleter.
Pin saved. Now digging into logs around the 22:00 ET window for the deletion culprit.
No system cleanup jobs found. Now examining the prime suspects from that night.
Builders look clean — checking system-level cleaners and disk pressure next.
System cleaners look unrelated. Checking for hidden cache-purge commands and second deletion traces.
Investigation complete — doing a final verification of the pinned copy.
Snapshot present (not MISSING-CACHE):
- `~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41/` with config.json, model.safetensors, vocab.txt, mtime Sep 23 22:17 ET.
- Copied via `cp -R` (not move) to `~/premonition-models/minilm/models--sentence-transformers--all-MiniLM-L6-v2/`, sha256 source==dest verified:
  - config.json 953f9c0d463486b10a6871cc2fd59f223b2c70184f49815e7efbcab5d8908b41
  - model.safetensors 53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db
  - vocab.txt 07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3
- Recorded in `runs/000-cache-pin/pin.txt` (2.6KB, pushable). Changed nothing else, deleted nothing, stopped no processes.

Deleter hunt (read-only greps):
- `~/premonition-watch/watch.log`: zero hits for huggingface/MiniLM/self122/.cache/rm -rf/cache purge/hf cache. Relevant window (log times = local ET): 21:36-21:49 "disk 2 GB free, holding new launches"; 21:51 launch 274-build, lis-302-gpu, mut0-build, rsn-296-guard, rsn-296-train; 22:20 pushed lis-302-gpu; 22:22 pushed 274-build; 22:24 launch lis-313-f0; 22:56 pushed mut0-build. So tasks running at ~22:00 ET = those 5 launched 21:51.
- `274-build.go1.reply.md`: documents it: "second actor deleted ~/.cache/huggingface/hub at ~22:02 (dir mtime) and restored full MiniLM snapshot at ~22:17", run-2 VOID with 14-29 CRASH/arm FileNotFoundError in route122, run-3 clean 0 CRASH/450 turns.
- `274-build.go1.err.txt`: FileNotFoundError hub/snapshots, `ls hub/` = No such file, later restored 22:17 with hashed files. Only `rm -rf` is scoped to `artifacts/claude-loop274-20260924/run274/...`; attempted `rm -rf ~*` was blocked by opencode permission rule (line 2838). Not the deleter.
- `mut0-build.go1.reply.md` D2 + `mut0-build.go1.err.txt` 1592-1821: same missing hub/, HF_HOME empty, then mut0 itself re-downloaded 3 files from huggingface.co main rev 1110a24 to ~/.cache and verified. Mut0 is the 22:17 restorer, not deleter. No cache rm in its log (only blocked rm by policy).
- All queue `*.err.txt` greps for `rm -rf.*cache|huggingface|~/|$HOME`: no hits except this task's own investigation lines and blocked-by-policy errors. Builders' rms are only artifacts/, /tmp/smoke*, scripts/__pycache__.
- Worktree `scripts/`: `fable_self122_train.py:63-71` resolve_snapshot is read-only listdir; no delete. Other hits are read-only SNAP path refs or snapshot_download imports. No `delete-cache/hf cache purge/rmtree hub` code. `runs/` in worktree has no deleter strings (only new pin.txt).
- `~/premonition-watch/watcher.sh`, `watcher.new`, `handoff/kit/mimo/rungo4.sh`, `diskguard.sh`: no HF deletions; diskguard only prunes DB sessions, rungo4 only waits on low disk.
- `crontab -l`: polymarket collectors only, no cleanup/purge jobs, no .cache lines.
- `launchctl list` + LaunchAgents/Daemons: no cleaners; only `com.valvesoftware.steamclean` scoped to SteamApps, plus Apple/Google/Zoom/Docker. No HF job.
- Disk context: 274 err df shows Available 15GB (start) -> 28GB (mid) -> 73GB (end); now 52GB free. ~58GB freed during window by unknown actor. Deletion was selective: hub/ gone, but datasets/ (Sep 9) and xet/ logs remained.
- Exoneration: lis-302-gpu runs on BensPC Windows (can't delete Mac ~/.cache); rsn-296-train rents VastAI (Mac side only orchestrates); rsn-296-guard only `vastai show/destroy rsn-296*` + ledger append.

Likely culprit: UNKNOWN among builder tasks — evidence points to external disk-pressure reclaim (2GB-free event + 58GB freed coinciding with selective hub/ removal), not a builder `rm -rf`/`hf cache` command. No builder, cron, or launchd deleter found.

PINNED ~/premonition-models/minilm/models--sentence-transformers--all-MiniLM-L6-v2 and CULPRIT UNKNOWN
