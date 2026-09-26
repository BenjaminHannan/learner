Firing up the two-bar read — verifying seals and building the code tree.
I've got the marks and scoring plan — now tracking down how to reach the GPU machine.
The GPU box needs Windows-style commands — adjusting the approach.
Another job is on the GPU — I'll build the code tree while waiting for it to clear.
Disk is tight but workable — building the full code tree now.
Tree is packed — copying it to the GPU machine.
The copy is stalling — checking what's arriving and trying a different transfer.
Full transfer is too slow — reusing the existing on-machine tree and updating just the new files.
Copy is running in the background — waiting for it to finish.
GPU is still busy with the other experiment — waiting for the copy to finish and the GPU to free.
Staging is done — now verifying the seals and reader.
Seals pass and the reader hash matches — running the history build and waiting on the GPU for the read.
History built: 239 rows — now waiting for the GPU to clear for the read.
GPU is free — launching the panel read.
Read is running — polling until it completes.
Progress is slow with GPU contention — checking if the read is still alive.
Read finished: 239 rows — scoring at both bars now.
Both bars scored and panel text wiped — copying the counts back.
Results written — doing final checks before handoff.
Verdict: PASS — lis-319c bar 0.98 saves more with safety held. No code edited, no failures.

Marks (integers, same 239-row / 424-fact reads scored at both bars):

| Mark | Bar | Got | Verdict |
|---|---|---|---|
| S1 more saved: B saved_right | >= 138 + 25 = 163 | B 185 (A 138), +47 | PASS |
| S2 no less safe: B wrong_turns | <= 1 + 1 = 2 AND <= 3 of 239 | B 2 (A 1) | PASS |
| S3 no invention: B nofact_rows_with_save | <= 1 | 0 (key absent = 0, both arms) | PASS |

Proved-wrong clause: B wrong_turns (2) >= A (1) + 3 (= 4) is FALSE — 0.98 does not let in hidden real errors.

Report-only: held_right A 188, B 141 (of R0 326); per-kind saved_right A→B: backref 2→3/59, long_multi 101→140/291, short 35→42/74; greedy R0 split (bar-independent): needs_history 37/57, other 289/367; ms median 1788.6 both arms; parse_fail 1 both arms (same read).

Every move:
- Fetched origin main + builder-outbox; read PASSMARKS (239 rows / 424 facts, S2 "3 of 239").
- Built tree (builder-outbox + main on top); 164 MB upload stalled (~1 MB/min), so staged BensPC tree as local copy of lis-319/tree + 40 KB update (current scripts, lis319c + readpanel319c) on top; seals re-checked.
- Seals (git-bash sha256sum): PASSMARKS 1/1 OK; readpanel319c 5/5 OK. READER C:/Users/benja/lis319/work/run/merged sha256 e688…6a76 match.
- Rows (CPU): 239 rows, 209 with history. Read ONCE (GPU): 239 rows on cuda (~11 min). Scored same reads at 0.995 and 0.98 (CPU, counts only).
- Deleted WORK/panel_reads.jsonl, panel_hist.jsonl, read.log on BensPC; copied back only score_A.json (550 B), score_B.json (549 B); wrote RESULTS.md. Panel label files never opened/printed/quoted.
- Misses: none. No training, no downloads, no rental, $0. Label lis-319c-bar. GPU BensPC RTX 5070 Ti, cuda.

Deviations (env only): venv reuse + PYTHONUTF8=1; git-bash sha256sum; nohup+disown launch; Windows paths; local-copy staging (content-equal for all used files); Mac disk dipped to ~1 GB mid-stage (continued; only byte-size scores needed Mac disk); a second GPU job started mid-read — shared GPU, no errors.

What it means (high-school English): dropping the bar to 0.98 banks 47 more facts with only 1 extra wrong save (2 vs limit 3) and zero inventions. It doesn't mean the gate is solved (141 found facts still held back), and it doesn't mean leakage (read once, sealed first, same reads both bars, counts only).

PUSH: artifacts/claude-lis319c-20260926/RESULTS.md artifacts/claude-lis319c-20260926/score_A.json artifacts/claude-lis319c-20260926/score_B.json
