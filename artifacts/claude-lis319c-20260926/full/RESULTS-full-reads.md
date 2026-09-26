# lis-319c-full re-reads (BensPC): same reader, two sealed panels, whole-claim inputs

Builder run 2026-09-26 on BensPC (RTX 5070 Ti, CUDA). Sealed code run
unmodified. Each panel read ONCE with the lis-319 merged reader; reads are
greedy and deterministic. Category counts only; no panel text is quoted.
The reads/pairs files in this folder hold panel text (TEST-ONLY): only the
two blind same-claim judges and count-printing scripts may open them.

## Printed counts of every step

SEALS (BensPC tree root, git-bash sha256sum):
- artifacts/claude-lis319c-20260926/SEAL.sha256.txt: PASSMARKS.md OK (1/1)
- artifacts/claude-lis319c-20260926/SEAL-full.sha256.txt: 3/3 OK
  (PASSMARKS-full.md, full/JUDGE_SAME.md, scripts/claude_lis319_fullclaim.py)
- artifacts/claude-readpanel319c-20260926/SEAL.sha256.txt: 5/5 OK
- artifacts/claude-readpanel319-20260925/SEAL.sha256.txt: 4/4 OK
- READER C:/Users/benja/lis319/work/run/merged/model.safetensors sha256
  e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76: match.

PANEL 319c:
- rows: rows 239 with history 209
- read: read 239 rows on cuda
- check_A (0.995): rows 239, gold 424, R0 326, saved_right 138,
  held_right 188, saved_wrong 1, wrong_turns 1, parse_fail 1, ms_median 1532.4
- check_B (0.98): rows 239, gold 424, R0 326, saved_right 185,
  held_right 141, saved_wrong 2, wrong_turns 2, parse_fail 1, ms_median 1532.4
- pairs (0.995,0.98): A saved 139 (exact 81, needs_judge 57, nomatch 1);
  B saved 187 (exact 104, needs_judge 81, nomatch 2); pairs 81
  (pairs_319c.jsonl 81 lines, reads_319c.jsonl 239 lines)

PANEL 319 (diagnostic):
- rows: rows 240 with history 210
- read: read 240 rows on cuda
- check_319 (0.995): rows 240, gold 211, R0 197, saved_right 65,
  held_right 132, saved_wrong 1, wrong_turns 1, ms_median 1379.8
- pairs (0.995): saved 66 (exact 43, needs_judge 22, nomatch 1); pairs 22
  (pairs_319.jsonl 22 lines, reads_319.jsonl 240 lines)

## Reproduction checks (JSON compared key by key with a script)

- check_A.json vs 006e score_A.json: EQUAL on every key except ms_median
  (1532.4 here vs 1788.6 in 006e; run timing only).
- check_B.json vs 006e score_B.json: EQUAL on every key except ms_median
  (1532.4 here vs 1788.6 in 006e; run timing only).
- check_319.json vs origin/builder-outbox
  artifacts/claude-lis319-20260925/score_B.json: EQUAL on every key except
  ms_median (1379.8 here vs 1426.2 there; run timing only).

So this re-read reproduces 006e's counts exactly: F1-F3 inputs are valid.

## GPU, wall time per step (local EDT 2026-09-26)

- Device: BensPC NVIDIA GeForce RTX 5070 Ti, cuda, greedy decode.
- 006g was already done (results pushed 23:57); GPU idle (0%, 437 MiB) at start.
- Mac setup (fetch, full tree builder-outbox + main on top, 65 KB update
  pack over slow scp, extract on BensPC): ~00:10-00:14.
- Seals + READER sha: ~00:14-00:14:43.
- 319c rows (CPU): 00:14:43. 319c read (GPU): launched 00:14:52,
  done ~00:25 (~10 min).
- check_A 00:25:03, check_B 00:25:09, pairs_319c 00:25:14 (CPU).
- 319 rows (CPU): 00:25:33. 319 read (GPU): launched 00:25:38,
  done ~00:31:37 (~6 min).
- check_319 00:31:41, pairs_319 00:31:46 (CPU). Copy-back + compare ~00:32.
- Total ~22 min, inside the 50 min cap.

## Training, device, money, independence

- No training, no downloads, no rental, $0. Label lis-319c-full.
- One job at a time on the GPU; no other GPU job overlapped this run.
- Panel label files and reads/pairs files never opened, printed or quoted;
  scripts printed counts only. WORK scratch files holding panel text were
  deleted on BensPC (WORK empty at end); only the 7 PUSH files copied back.

## Deviations (env only; sealed code untouched)

1. Reused the lis-300 venv (torch +cu128) and the existing lis-319 merged
   reader; set PYTHONUTF8=1 (env only).
2. BensPC tree staged as the existing C:/Users/benja/lis319c/tree (from 006e)
   plus a 65 KB update (current scripts, lis319c + both readpanels) extracted
   on top; all seals re-checked after (1/1 + 3/3 + 5/5 + 4/4 OK). Content
   equals builder-outbox + main on top for every file this task uses.
3. Seals checked with git-bash sha256sum -c (shasum absent on BensPC).
4. Long GPU steps launched with nohup + disown in git-bash and the ssh
   session kept alive past launch (~100 s); native Windows paths to python.exe.
