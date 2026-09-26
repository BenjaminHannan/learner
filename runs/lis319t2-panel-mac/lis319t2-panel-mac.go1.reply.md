Sealed single-read task locked in — checking common rules, passmarks, and prior jobs before touching the panel.
Common-rules file is stale-dated versus the task header — substance matches, so I'm proceeding and noting the discrepancy.
Passmarks confirmed and prerequisites mapped — verifying the two blocking reader jobs are done.
Both blockers are finished and no reader is running — building the sealed tree.
Seals pass and reader hash matches — compiling panel rows.
Single read complete — computing timing stats without opening the sealed content.
Cleanup verified — confirming the push files are staged for the watcher.
VERDICT: DONE — lis-319t2 one-read complete with the lis-319f reader. B1-B3 pending judges. Label: lis319t2-panel.

Marks table (integer counts; this read decides no bars itself):

| Mark | Bar (0.98 vs 0.995, same reads) | Result here |
|---|---|---|
| B1 | saved_right_full: 0.98 >= 0.995 + 10 | pending judges (reads done, 240 lines) |
| B2 | saved_wrong_full: 0.98 <= 0.995 + 2 | pending judges |
| B3 | nofact_rows_with_save: 0.98 <= 0.995 + 1 | pending judges |
| INCONCLUSIVE gate | read covers >= 230 rows | PASS: 240 rows read |

Every move:
1. `git fetch -q origin main` (plus one `git fetch -q origin` to confirm origin/main current at 5f44229bb). No checkout, merge, or push.
2. Read first 13 lines of origin/main:handoff/queue/lis-302-gpu.md via `git archive` (additive-only, fictional-names, TEST-ONLY-never-read, report-in-final-reply rules). Read origin/main:artifacts/claude-lis319t2-20260926/PASSMARKS.md via `git archive`.
3. Gate check: lis319k-panel-mac RESULTS-read.md present (240 rows on mps) and lis319k-devbank-mac-r2 devbank/RESULTS.md present (69 rows); no `claude_lis319_read.py` process running. Ran alone.
4. TREE: D=/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.K79Pnp3WPE; `git archive origin/main scripts design/v3/60-listener artifacts/claude-lis319t2-20260926 artifacts/claude-readpanel319k-20260926 | tar -x -C $D`. 25 MB-scale single tree.
5. Seals: t2 SEAL all 4 OK; readpanel319k SEAL all 8 OK. Reader `~/premonition-models/lis319f-merged/model.safetensors` sha256 970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b = match, not READER-FAIL.
6. Rows: `claude_lis319_rows.py` printed verbatim `rows 240 with history 210` (as expected).
7. Read (ONCE): `claude_lis319_read.py` printed verbatim `read 240 rows on mps`. Device mps. Wall 424 s (2026-09-26 15:29:54 UTC to 15:36:58 UTC). Median 1610.9 ms over 240 per-row ms values (counts-only aggregation). Env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1 with the specified uv offline Python 3.12 torch/numpy/transformers/safetensors invocation. Code never edited.
8. Copied reads_panel_319f.jsonl (240 lines, `wc -l` only) to artifacts/claude-lis319t2-20260926/; wrote RESULTS-read.md (new files only). Never opened, printed, or quoted panel.jsonl, label_B.jsonl, adjudication.jsonl, or the reads file content.
9. `rm -rf` exact temp path; `ls` confirms "No such file or directory". Gone.

Every miss: none. No failures, no retries, no missing rows.

Deviations:
- One header note: the task preamble describes the common-rules file as the "Fix: reading facts from chat" thread 2026-09-26, but origin/main:handoff/queue/lis-302-gpu.md lines 1-13 actually read "(the listener thread, Claude, wrote this task on 2026-09-23)". Substance (additive-only, fictional names, TEST-ONLY never read item-by-item, report in final reply) matches, so I followed the on-disk rules. No other deviation: GPU no (mps), DISK 1, TIME CAP 60 min (used ~7 min), $0.

What it means / doesn't mean (plain high-school English): the sealed 240-question test was read exactly once by the new lis-319f reader and the answers are saved unread for blind judges. This says nothing yet about whether the 0.98 bar passes — B1/B2/B3 are scored later from this same file. It also doesn't prove anything about other readers.

PUSH (left in worktree for the watcher; never pushed by me): artifacts/claude-lis319t2-20260926/RESULTS-read.md, artifacts/claude-lis319t2-20260926/reads_panel_319f.jsonl.
