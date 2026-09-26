Starting rd-378 sealed run — fetching fresh sources and verifying the tree.
Confirmed rd-378 on BensPC — now tracking down the connection details.
BensPC is reachable — now checking GPU availability and prior state.
GPU is idle and the base model is in place — verifying hashes and snapshots.
Base and MiniLM verified — now building the code tree for BensPC.
Tree assembled — compressing and shipping it to BensPC.
Tree is ready on BensPC — running seal checks and building training data.
Data matches the dry run exactly — launching the 60-minute training run.
Training is running on the GPU — polling progress while preparing artifacts.
Training finished cleanly — now generating dev notes and sealing the model.
Dev notes clean — sealing the run and executing the one-time panel.
Panel scored — pulling the full counts to grade the marks.
Model transfer hit a snag — retrying with a sturdier copy.
First chunk arrived intact — fetching the remaining three.
Three chunks secured — grabbing the last one.
All chunks arrived — reassembling and verifying the model hash.
Disk space recovered — reassembling the model now.
Model verified on both machines — copying result artifacts back to the Mac.
All evidence in hand — writing the final results and ledger entry.
Ledger appended — final verification and cleanup.
Verdict: FAIL on the counted marks (N1, N2, N3 miss; N5 passes; N4 pending the blind judge). The note writer's notes do not help evidence-finding with this retriever.

Marks table (integers, B = turns+notes, A = turns only, found@10):

| Mark | Bar | Got | Verdict |
|---|---|---|---|
| N1 multi found@10 | B >= A + 10 | B 30/30 vs A 30/30 (diff 0) | FAIL |
| N2 time found@10 | B >= A + 5 | B 30/30 vs A 30/30 (diff 0) | FAIL |
| N3 all found@10 | B >= A + 5 and no type worse than A - 3 | B 149/150 vs A 150/150 (diff -1); per-type diffs latest -1, multi 0, preference 0, single 0, time 0 | FAIL on the +5 clause (per-type clause holds) |
| N4 notes true to turns | <= 5% unsupported | pending blind judge (panel_notes.jsonl pushed unquoted for the thread's read) | PENDING |
| N5 notes parse | unparsed <= 2% | panel 0/324 (0%), dev 0/267 (0%) | PASS |

Proved-wrong clause tripped: B all-found@10 149 <= A + 1 = 151 is TRUE.

Every move, in order (BensPC RTX 5070 Ti, venv C:/Users/benja/lis300/venv, BASE MiniCPM5-1B sha 7ab8fd86 re-verified, MiniLM snapshot 1110a243 present, no downloads, PYTHONUTF8=1, one GPU job at a time, label rd-378-train, $0, sealed code never edited):
1. Tree: git archive builder-outbox then main on top, scp 163M tree.tgz to C:/Users/benja/rd378, extracted. Seals: rd378-data 16/16 OK, notepanel378 7/7 OK (git-bash sha256sum; data seal run from inside its data dir since it lists bare filenames).
2. DATA: printed {dev_dialogs 31, dev_rows 255, dropped 232, kept_dev 255, kept_train 2550, notes_kept 2797, train_rows 7650, turns 3037} = README dry run exactly; recorded in DATA.json.
3. TRAIN: 958/958 steps, 2 epochs, 11.57 min, 4071.9 tok/s, dev loss 0.5286, batch 16 with no OOM (no batch-8 fallback), 60-min cap never bound.
4. DEV: 267 turns, 277 notes (1.04/turn), 0 unparsed, median 908.4 ms.
5. SEAL (merged sha dbcc8db5…) written BEFORE panel; panel written over exactly once (324 turns, 360 notes, 1.11/turn, 0 unparsed, median 1005.5 ms, p90 1642.2, max 2752.9); eval bm25+minilm rrf, counts only.
6. Model kept both ends with matching sha256 (BensPC WORK/nrun/merged + ~/premonition-models/rd378-notes-merged/); summary.json copied to train_summary.json; weights never in git; ledger line appended (1 insertion).
7. RESULTS-benspc.md written with the tables above plus report-only found@5/allfound@k per type. Panel files only ever passed as CLI args; I saw counts and ms, never text. Total wall ~1h00 inside the 3h cap.

Misses/deviations: N1/N2/N3 miss by 10/5/6 points respectively; A already finds 150/150 at top-10 so there was almost no headroom. Env-only deviations: reused venv+BASE snapshot; winshim unneeded; foreground ssh for short steps; model ferried in 4 split chunks after two whole-file scp drops (sha matches); Mac disk hit 0B free mid-copy, freed only my own temp files (final 5G free). No data lost, panel untouched after its single run.

What it means in plain English: sticking auto-written notes next to chat turns didn't help find answers — the plain-turns search already finds everything (150/150) and notes even lost one (149). It doesn't mean the writer is broken (zero parse failures, ~1 note per turn) — whether the notes are truthful is still ungraded (N4). It doesn't mean the test leaked — seals passed first, single panel run, nothing quoted. Per the registered proved-wrong rule, for finding evidence with this retriever, notes beside raw turns don't help.

PUSH (on disk, watcher pushes): artifacts/claude-rd378-20260925/RESULTS-benspc.md, DATA.json, SEAL-run.sha256.txt, score.json, panel_notes.jsonl, dev_notes.jsonl, train_summary.json, artifacts/fable-predictions-ledger.md.
