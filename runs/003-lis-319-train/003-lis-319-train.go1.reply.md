Starting lis-319 — fetching branches and reading the handoff.
Found the registered test spec — now tracking down BensPC access.
BensPC is reachable — checking GPU status and disk space.
GPU is free and venv works — pulling the full run procedure.
Preflight looks good — verifying model hashes and building the code tree.
Local seals pass (14/14, 13/13, 14/14, 16/16, 4/4) — transferring to BensPC.
Step 1 seals pass on BensPC — running the data build.
Data build matches (50,044 train / 1,311 dev, 0 over length) — launching training.
Training is running (200/6256 steps) — waiting for completion.
Training at 75% (4740/6256) — continuing to monitor.
Training complete (6256/6256 steps, 76.5 min) — starting dev reads.
Dev read complete (1311 rows) — running threshold sweep.
Sweep shows no zero-wrong grid value (T_B=0.995) — computing per-source numbers.
Per-source dev done — running G1 single-turn comparison.
Scoring files saved — assembling the threshold record.
Threshold record ready — sealing the run before the panel.
Run sealed and GPU free — running the registered panel once per arm.
Arm A complete (240 rows) — launching Arm B with history.
Panel scores are in (counts only) — running the e2e dev check and verifying marks.
Panel and e2e reads done — copying the model back to Mac.
Small model files copied — transferring the 2.1GB weights.
All artifacts copied back — writing the results report.
All counts verified — writing RESULTS.md and the ledger line.
Report and ledger done — final verification of the push set.
Verdict: PASS — lis-319, the reader reads the conversation. All five registered marks pass on BensPC.

Marks (integers, panel 240 rows / 211 gold: 98 needs_history + 113 other; dev_single 1178 turns / 971 gold):

| Mark | Bar | Got | Verdict |
|---|---|---|---|
| H1 back-references: B R0 on needs_history | >= 69/98 (70%) AND >= 1+40 = 41 | B 93/98 (94.9%), A 1/98 | PASS |
| H2 no loss elsewhere: B R0 on other facts | >= 102-3 = 99/113 | B 104/113, A 102/113 | PASS |
| H3 safe: B wrong_turns at its T | <= 2 of 240 | 1 of 240 | PASS |
| H4 no invention: B nofact_rows_with_save | <= 1 | 0 | PASS |
| G1 single-turn dev at each arm's T | B >= 553-29 = 524/971 | B 577/971, A 553/971 | PASS |

Proved-wrong clause: B H1 (93) <= A H1 + 10 (11)? FALSE — not triggered. The reader uses history from the prompt.

Every move (UTC 2026-09-25, worktree card-experiment-handoff-7c5b27, BensPC RTX 5070 Ti):
- Fetched origin main + builder-outbox. Read PASSMARKS, rent-kit §A, lis-302-gpu first 13 lines, lis-318 RESULTS-benspc + THRESHOLD (T_A = 0.995).
- Built tree (builder-outbox archive, then main on top; no self122/MiniLM/route122 per task). Tree.tgz 169,322,074 B scp'd to C:/Users/benja/lis319/, extracted to tree/.
- Step 1 seals from BensPC tree root (git-bash sha256sum -c): lis-300 14/14 OK, lis-301 13/13 OK, lis-318 data 14/14 OK, lis-319 data 16/16 OK, readpanel319 4/4 OK. BASE C:/Users/benja/lis300/model sha 7ab8fd86…66d0d match; READER_A C:/Users/benja/lis318/work/run/merged sha 8b3fdbda…3e6d match (no READER-FAIL). GPU free.
- Step 2 DATA on BensPC: train 50,044 (o0b 27000 + opus 5012 + opus301 4960 + chat318 7936 + hist319 5136), dev 1,311 (428+131+263+137+219+133), hist319 agreed 1417, dropped UNCLEAR 216 train + 3 dev — matches CPU dry run. Lencheck max-len 512: train max 491 p99 321 over 0; dev max 382 p99 318 over 0; exit 0 (stop bar was exit 3).
- Step 3 TRAIN: 6256/6256 steps, 2 epochs, 76.47 min, 2946.3 tok/s, dev loss 0.0416, LoRA 22,413,312/1,103,046,144, batch 16 (no OOM, no batch-8), lr 2e-4 rank 32 seed 300 max-len 512, --max-minutes 150 never bound, --merge. Merged sha e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76.
- Step 4 DEV: dev read 1311/1311 rows on cuda; sweep min 3 wrong turns (no 0 grid) so T_B = 0.995. Whole dev at T_B: 611/1053 hits, 3 wrong turns, ask 131/140, we 19/19, turn_exact 429, held_back 438, ms 1505.0/2335.0/4245.4. Per src at T_B: o0b_l2 240/352 0 wrong; opus_dev 39/74 1 wrong; o0a2 158/238 1 wrong; opus301_dev 55/97 0 wrong; chat318_dev 85/210 1 wrong; hist319_dev 34/82 0 wrong. G1 devsplit (single 1178 / hist 133): B 577/971 3 wrong vs A 553/971 1 wrong — PASS (+24, bar 524).
- Step 5 SEAL before panel: SEAL-run.sha256.txt both lines OK under sha256sum -c on BensPC.
- Step 6 PANEL once per arm, counts only: A 240 rows (R0 103, saved_right 58, saved_wrong 12, wrong_turns 11, ms 1400.3; hist 1/98, local 102/113). Hist build 240 rows (210 with history). B 240 rows (R0 197, saved_right 65, saved_wrong 1, wrong_turns 1, ms 1426.2; hist 93/98, local 104/113). Scores written. E2E dev (report only): 194 hist rows built, 194/194 read to reads_e2edev_B.jsonl.
- Step 7: model scp'd file-by-file to ~/premonition-models/lis319-merged/ (2,161,290,944 B safetensors both ends); Mac sha matches BensPC. Never in git. dev_pred.jsonl (1311 rows) copied to artifacts dev/. Ledger line appended via cat >>.
- Step 8 RESULTS.md written (scores verbatim, LENGTHS, sweep, per-src, training, GPU, wall times, sha; no panel text).
- Misses: none. Panel files never opened/printed/quoted (only scorer counts seen); code never edited (one encoding conversion on my own new LENGTHS.json, content identical — see deviations).

Deviations (env only): reused lis-300 venv + base snapshot; PYTHONUTF8=1; no resource error so no winshim; no OOM; git-bash sha256sum for seals; nohup+disown launches (survived ssh timeouts, all completed); persrc via split + sealed scorer; scp instead of rsync (no rsync on Windows, hash-verified); LENGTHS.json UTF-16→UTF-8 on copy-back; THRESHOLD assembled from sealed outputs; SEAL-run uses artifact-relative + BensPC-absolute paths (both OK on BensPC, lis-301 precedent).

Common-rules report: additive only (new files in artifacts/claude-lis319-20260925/ + ledger append; .gitignore keeps artifacts/ untracked — files on disk ready for watcher PUSH); fictional names only; TEST-ONLY panel run once per arm, counts only, never quoted.

What it means (plain high-school English): giving the reader the earlier chat fixes back-references — it finds 93 of 98 history-needing facts where the old reader found 1, without losing anything elsewhere or inventing saves. It doesn't mean the job is done: at the live safety gate it still holds back most found facts (saves 65 of 197) to stay safe. It doesn't mean the test leaked: seals passed first and each panel ran exactly once.

PUSH (on disk, ready): artifacts/claude-lis319-20260925/RESULTS.md, LENGTHS.json, THRESHOLD.txt, SEAL-run.sha256.txt, score_A.json, score_B.json, reads_e2edev_B.jsonl, train_summary.json, dev/dev_pred.jsonl, artifacts/fable-predictions-ledger.md.
