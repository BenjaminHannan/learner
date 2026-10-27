CACHE PIN + FIND THE DELETER (director, 2026-09-24 03:58 UTC). Small CPU task on the Mac. Never print secrets. Never delete anything. Stop processes only by exact PID, and only if the director says so (here: don't).
Context: ~/.cache/huggingface/hub (the MiniLM router snapshot used by the self122 router) vanished twice on 2026-09-23 (~22:02 ET during 274, again during mut-0).
1. Check the snapshot is present now (ls ~/.cache/huggingface/hub). If missing, report MISSING-CACHE and stop.
2. Copy (cp -R, not move) the MiniLM snapshot directory to ~/premonition-models/minilm/ and record its file sha256s in runs/000-cache-pin/pin.txt.
3. Find what deleted it: grep the watcher log (~/premonition-watch/watch.log) and every runs/*/ reply and script in the worktree and ~/premonition-watch for "huggingface", "rm -rf", ".cache", "cache purge", "hf cache", and list the tasks running at ~22:00 ET on 2026-09-23. Also check crontab -l and launchctl list for cleanup jobs. Report the likely culprit(s) with evidence; change nothing.
Final line: PINNED <path> and CULPRIT <best guess or UNKNOWN>.
PUSH: runs/000-cache-pin/pin.txt
