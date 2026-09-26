Firing up the full re-read — fetching seals and building the code tree.
Seals confirmed — now tracking down the BensPC access route.
Found the task spec — now digging up the SSH details.
SSH works — now checking GPU status and prior staging method.
Tree exists on BensPC with all panels — building the update pack now.
Staged — now verifying seals and reader.
All seals pass — starting the panel reads.
Read is running — polling progress and prepping reference counts.
319c read done (239 rows) — scoring at both bars.
319c scored — now the 319 diagnostic panel.
319 read launched — waiting for completion.
319 read done (240 rows) — scoring and pairing.
All runs complete — copying results back and comparing.
All comparisons match (ms_median aside) — cleaning scratch and writing results.
Files are in place (artifacts/ is gitignored, so staging explicitly like sibling tasks).
Verdict: DONE — lis-319c-full re-reads complete. Both sealed panels re-read once each with the same reader; all reproduction checks pass (F1-F3 inputs valid). No code edited, no failures.

Marks table (integers; greedy re-reads on BensPC):

| Check | Got | Verdict |
|---|---|---|
| check_A vs 006e score_A.json (239 rows / 424 gold) | equal on every key except ms_median | REPRODUCED (A saved_right 138, wrong_turns 1) |
| check_B vs 006e score_B.json (same reads, T 0.98) | equal on every key except ms_median | REPRODUCED (B saved_right 185, wrong_turns 2) |
| check_319 vs builder-outbox lis-319 score_B.json (240 rows / 211 gold) | equal on every key except ms_median | REPRODUCED (saved_right 65, wrong_turns 1) |
| pairs_319c (T 0.995 + 0.98) | 81 pairs (A: exact 81 / judged 57 / nomatch 1; B: exact 104 / judged 81 / nomatch 2) | WRITTEN UNREAD |
| pairs_319 (T 0.995) | 22 pairs (exact 43 / judged 22 / nomatch 1) | WRITTEN UNREAD |

The only differing key in all three comparisons is ms_median (run timing: 1532.4 vs 1788.6; 1532.4 vs 1788.6; 1379.8 vs 1426.2). Every count that matters for F1-F3 matches exactly.

Every move:
- Fetched origin main + builder-outbox; read PASSMARKS-full.md and the queue task via git show (worktree not touched beyond new files).
- 006g already finished (results pushed 23:57), so no wait needed; GPU idle at start (0%, 437 MiB, RTX 5070 Ti).
- Built full code tree on Mac (builder-outbox, then main on top); staged BensPC as existing lis319c/tree + 65 KB update (current scripts, lis319c seals, both readpanels) on top.
- Seals on BensPC (git-bash sha256sum): PASSMARKS 1/1 OK, SEAL-full 3/3 OK, readpanel319c 5/5 OK, readpanel319 4/4 OK. READER safetensors sha256 e688…6a76 match.
- 319c: rows 239 (history 209) → read 239 rows on cuda (~10 min) → check_A / check_B (CPU) → pairs_319c (81 lines).
- 319: rows 240 (history 210) → read 240 rows on cuda (~6 min) → check_319 (CPU) → pairs_319 (22 lines).
- Copied back only the 7 PUSH data files + wrote RESULTS-full-reads.md (8 files staged with git add -f; artifacts/ is gitignored). Panel/label/reads/pairs contents never opened, printed, or quoted — counts only. WORK scratch deleted on BensPC (0 files left).
- Misses: none. No training, no downloads, no rental, $0. Label lis-319c-full. Total ~22 min, inside the 50 min cap.

Deviations (env only): venv reuse + PYTHONUTF8=1; git-bash sha256sum; nohup+disown launches with ssh held ~100 s past launch; native Windows paths; local-copy staging (content-equal for all used files).

What it means (plain high-school English): the same reader, run fresh on both sealed panels, produced exactly the same counts as the registered runs — so the whole-claim F1-F3 judging starts from solid, reproduced numbers. It doesn't mean F1-F3 pass yet: that needs the two blind judges to rule on the 81 + 22 pairs. It doesn't mean leakage either: each panel read once, seals checked first, files pushed unread.

PUSH: artifacts/claude-lis319c-20260926/full/RESULTS-full-reads.md, check_A.json, check_B.json, check_319.json, reads_319c.jsonl, reads_319.jsonl, pairs_319c.jsonl, pairs_319.jsonl
