Renting a 5090 to run your three arms — starting checks and credit gate.
Worktree refs sorted — now reading the run spec and seals.
Credit gate passed (5.50), no duplicate — searching for a 5090.
Instance 52756154 created ($0.496/hr) — waiting for SSH.
First host failed with a Docker proxy error — destroying and trying the next host.
Second host has the same broken proxy — destroying and trying a third host.
The third create was rejected at scheduling (host full) — destroying the husk and making the final allowed attempt on a different host.
This host is pulling the image correctly — waiting for it to come online.
Rental is live — setting up SSH and streaming the tree.
scp -3 failed — using the one-mktemp-dir fallback.
Adapter verified — running kit setup (pip + model snapshots) detached.
All seals pass — checking how `--gen-model BASE` resolves before launching.
`--gen-model` takes the snapshot path — launching all three arms now.
Arms A and B crashed on a missing file — reading the full traceback before deciding.
V1 load lines are correct, but both 02c arms need a file missing from the tree spec — inspecting what it is before deciding.
The crash is in the sealed 02c stack's self127 novelty check — a committed runtime file missing from my tree spec. Checking exactly what it needs.
Output files are written at the end, so a clean relaunch is safe — preserving crash logs and streaming the missing committed dir.
Bytes verified — relaunching arms A and B with the exact specified commands.
Found it — my relaunch chained `&` wrong so B started in `/root` instead of `~/tree`. A is healthy; relaunching B from the right directory.
Both 02c arms running with V1 holding — polling progress.
A finished clean — waiting on B's last few conversations.
All three arms complete — running the sanctioned counts-only score.
Hashes all match — gathering timing and row counts for the report.
Everything verified — destroying the rental and confirming it's gone.
Verdict: RUN COMPLETE, V1 VALID — all three mu-402 arms finished 80/80 conversations on one rented RTX 5090. M1/M2/M3 PASS/FAIL is for the blind judges, not this run.

Integer counts:
- Credit at gate: 5.499236376269863 (balance 0). Task spend ~$0.36 of $1.00.
- Creates: 4 (3 live rentals + 1 success-False husk at $0). Two died of host-side docker-proxy failure (~$0.08 combined); the worker (52757517, $0.5037/hr) ran 14:03:48–14:36:01 UTC (~0.53h, ~$0.28). Zero rent-mu402 live after destroy (verified).
- Seals: SEAL.sha256 7/7 OK; SEAL-code 336 OK / 0 fail; selftest 7/7; route122 no raise. Adapter sha256 match (a33211dc…); self122_head.pt match (5ca02173…).
- Rows: A 402 rows/80 items; B 402/80; T 402/80. Progress lines 80/80/80. No traceback anywhere.
- Walls: T 6.0 min, A 10.3, B 12.4. Median ms/turn: A 1212.5, B 1104.1, T 926.1.
- V1: logA "adapter loaded = /root/adapter/adapter02c.pt"; logB "adapter loaded = none (B = 0, base 1B)". No "refusing to load".

Every deviation (all in RESULTS-rent.md, staged with run/ + ledger line for the watcher to push):
1. scp -3 failed → one mktemp dir fallback, removed by exact path (verified gone); only the 16.5 MB adapter touched the Mac.
2. 4 creates vs "(max 3)": 2 proxy-dead hosts + 1 $0 husk + 1 worker = 3 live rentals; kit allows 4.
3. Task tree list omitted artifacts/fable-self127-20260922, which the sealed 02c stack reads every turn — first A/B launch crashed turn 1 (FileNotFoundError deltas127.json). Streamed that one committed dir opaque from origin/main (hash-verified, never opened), kept crash logs, relaunched A/B with exact commands. No code touched.
4. My first B relaunch had a cwd chaining bug (died instantly, clear error); relaunched correctly from ~/tree.
5. Numeric exit codes uncaptured (detached launches); clean completion evidenced (80/80 lines, end-of-main outputs, no traceback). Score step exit 0.
6. Score file is summary_chat.json (runner convention), not "summary.json". Label rent-mu402 per task (not kit's claude- prefix).

Files staged (force-add, sha256-verified vs rental): run/chat_A/B/T.jsonl, summary_chat.json, logA/B/T.txt + crash logs, RESULTS-rent.md, ledger line. Adapter never on git.
