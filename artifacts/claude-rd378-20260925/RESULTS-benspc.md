# rd-378 registered result (BensPC): FAIL on counted marks — notes don't move finding (N4 pending blind judge)

Builder run 2026-09-26 on BensPC (RTX 5070 Ti, CUDA). Sealed code imported and
run unmodified. Panel notepanel378 written over once; only scorer counts viewed.
No panel turn, question, or note is quoted anywhere in this file.

## Verdict: FAIL (N1, N2, N3 miss; N5 passes; N4 pending blind judge)

| Mark | Bar | Got (integers) | Verdict |
|---|---|---|---|
| N1 multi-turn questions: found@10 | B >= A + 10 | B 30/30 (A 30/30, diff 0) | FAIL |
| N2 time questions: found@10 | B >= A + 5 | B 30/30 (A 30/30, diff 0) | FAIL |
| N3 all questions: found@10 | B >= A + 5, and no type more than 3 below A | B 149/150 (A 150/150, diff -1); per-type diffs: latest -1, multi 0, preference 0, single 0, time 0 | FAIL (on the +5 clause; per-type clause holds) |
| N4 notes true to their turns (blind judge, unsupported) | <= 5% of B's notes | pending blind judge | PENDING |
| N5 notes parse | unparsed turns <= 2% | panel 0/324 (0.0%), dev 0/267 (0.0%) | PASS |

Proved-wrong clause (PASSMARKS): all-question found@10 B (149) <= A + 1 (151) is
TRUE, so notes don't help finding.

## score.json (verbatim counts; notes text never printed)

{
 "counts": {
  "turns_read": 324,
  "notes": 360,
  "unparsed": 0
 },
 "retriever": "bm25+minilm rrf",
 "A": {
  "all:allfound@10": 146,
  "all:allfound@5": 122,
  "all:found@10": 150,
  "all:found@5": 138,
  "all:n@10": 150,
  "all:n@5": 150,
  "latest:allfound@10": 28,
  "latest:allfound@5": 19,
  "latest:found@10": 30,
  "latest:found@5": 25,
  "latest:n@10": 30,
  "latest:n@5": 30,
  "multi:allfound@10": 28,
  "multi:allfound@5": 21,
  "multi:found@10": 30,
  "multi:found@5": 29,
  "multi:n@10": 30,
  "multi:n@5": 30,
  "preference:allfound@10": 30,
  "preference:allfound@5": 27,
  "preference:found@10": 30,
  "preference:found@5": 28,
  "preference:n@10": 30,
  "preference:n@5": 30,
  "single:allfound@10": 30,
  "single:allfound@5": 26,
  "single:found@10": 30,
  "single:found@5": 26,
  "single:n@10": 30,
  "single:n@5": 30,
  "time:allfound@10": 30,
  "time:allfound@5": 29,
  "time:found@10": 30,
  "time:found@5": 30,
  "time:n@10": 30,
  "time:n@5": 30
 },
 "B": {
  "all:allfound@10": 146,
  "all:allfound@5": 132,
  "all:found@10": 149,
  "all:found@5": 144,
  "all:n@10": 150,
  "all:n@5": 150,
  "latest:allfound@10": 28,
  "latest:allfound@5": 22,
  "latest:found@10": 29,
  "latest:found@5": 24,
  "latest:n@10": 30,
  "latest:n@5": 30,
  "multi:allfound@10": 29,
  "multi:allfound@5": 21,
  "multi:found@10": 30,
  "multi:found@5": 30,
  "multi:n@10": 30,
  "multi:n@5": 30,
  "preference:allfound@10": 29,
  "preference:allfound@5": 29,
  "preference:found@10": 30,
  "preference:found@5": 30,
  "preference:n@10": 30,
  "preference:n@5": 30,
  "single:allfound@10": 30,
  "single:allfound@5": 30,
  "single:found@10": 30,
  "single:found@5": 30,
  "single:n@10": 30,
  "single:n@5": 30,
  "time:allfound@10": 30,
  "time:allfound@5": 30,
  "time:found@10": 30,
  "time:found@5": 30,
  "time:n@10": 30,
  "time:n@5": 30
 }
}

(180 panel questions: 30 dialogs x 6; 30 "none" questions skipped by the scorer,
so n@k = 150 = 5 types x 30.)

## Report-only numbers

- found@5 per type: A all 138/150 (latest 25, multi 29, preference 28, single 26,
  time 30); B all 144/150 (latest 24, multi 30, preference 30, single 30,
  time 30).
- allfound@10 per type: A all 146 (latest 28, multi 28, preference 30, single 30,
  time 30); B all 146 (latest 28, multi 29, preference 29, single 30, time 30).
- allfound@5 per type: A all 122 (latest 19, multi 21, preference 27, single 26,
  time 29); B all 132 (latest 22, multi 21, preference 29, single 30, time 30).
- Notes per turn: panel 360 notes / 324 turns = 1.11; dev 277 notes / 267 turns
  = 1.04.
- Write ms per turn: dev median 908.4; panel median 1005.5, p90 1642.2,
  max 2752.9.
- Judge's other verdicts: pending blind judge (same judge as N4; panel_notes.jsonl
  pushed unquoted for the thread's blind read).

## Training, device, money

- Device: BensPC NVIDIA GeForce RTX 5070 Ti, cuda, greedy decode. No rental, $0.
- Training: 958/958 steps, 2 epochs, 11.57 minutes, 4071.9 tok/s,
  dev loss 0.5286, LoRA trainable 22,413,312 of 1,103,046,144 params,
  batch 16 (no OOM, no batch-8 fallback), lr 2e-4, rank 32, seed 300,
  max-len 512, max-minutes 60 cap never bound.
- Base model: C:/Users/benja/lis300/model (reused lis-300 download),
  model-00000-of-00001.safetensors sha256
  7ab8fd86563125929be78aeec8cb3969c7ed2ead3be1ab9d3ec0a9fa69c8660d
  (verified before training; commit 87179e5c as in lis-300 RESULTS.md).
- MiniLM: snapshot already on BensPC
  (C:/Users/benja/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41,
  the snapshot scripts/fable_self122_train.resolve_snapshot(None) returns);
  eval retriever bm25+minilm rrf. No downloads.
- Merged note-writer sha256
  dbcc8db5a5840d839fe049f720bdfeacf094deb78f2652984c28c53f8c388510,
  kept at C:/Users/benja/rd378/tree/WORK/nrun/merged (BensPC) and
  ~/premonition-models/rd378-notes-merged/ (Mac, hash verified). Never in git.
- Panel write: 324 turns, 360 notes, 0 unparsed. Dev write: 267 turns,
  277 notes, 0 unparsed.

## Data built (recorded counts = DATA.json = data/README.md dry run)

- Seals from the BensPC tree before building: rd378 data 16/16 OK,
  notepanel378 7/7 OK.
- Built set: { "dev_dialogs": 31, "dev_rows": 255, "dropped": 232,
  "kept_dev": 255, "kept_train": 2550, "notes_kept": 2797, "train_rows": 7650,
  "turns": 3037 } (train_rows = 2550 kept x3 repeat; dev rows carry notes+kind).
- The sealed panel files were never opened, printed or quoted. Panel written
  over once; only scorer counts and ms were viewed.

## Wall time per step (UTC 2026-09-26; BensPC local = UTC-4)

- Setup (fetch, tree build builder-outbox + main on top, scp, extract,
  BASE sha + GPU idle checks): 00:07-00:13.
- Step 1 seals: 00:13 (data 16/16, panel 7/7).
- Step 2 data: 00:13 (< 1 min; counts match dry run exactly).
- Step 3 train: ~00:14-00:26 (11.57 min per summary; merged saved 20:25 local).
- Step 4 dev write: 00:28-00:33 (~5 min, 267 turns).
- Step 5 seal 00:33 (before panel); panel write 00:33-00:39 (~6 min,
  324 turns, once); eval ~00:39-00:41.
- Step 6 model copy + both-sha check + artifacts copy-back: 00:41-01:07
  (2.1G model moved in 4 split chunks after two whole-file scp drops; sha
  matches on both ends; small files direct).
- Total ~1 h 00 min, inside the 3 h cap (training 11.57 min < 60 min cap).

## Deviations (env only; sealed code untouched)

1. Reused the lis-300 venv (torch 2.11.0+cu128) and the downloaded base-model
   snapshot (safetensors sha256 re-verified) instead of a new venv and
   re-download; new work dir C:/Users/benja/rd378 used throughout.
2. Set PYTHONUTF8=1 (env var only), as in lis-300/lis-301/lis-318.
3. No `resource`-module failure occurred, so scripts/winshim was not needed.
4. No OOM at batch 16, so the batch-8 fallback was not used.
5. shasum is absent on BensPC; seals were checked with git-bash sha256sum -c
   (same file format). The rd378 data seal lists bare filenames, so it was run
   from inside artifacts/claude-rd378-20260925/data (16/16 OK) rather than the
   tree root (where the paths don't resolve); the panel seal was run from
   inside artifacts/claude-notepanel378-20260925 (7/7 OK), as written.
6. Training was launched with nohup + disown per the lis-318 pattern; the
   shorter write/eval steps ran foreground over the steady ssh link (one GPU
   job at a time throughout; GPU 0% before and after each step).
7. The 2.1G merged safetensors was ferried to the Mac in 4 split chunks
   (two whole-file scp attempts dropped mid-transfer on the flaky link) and
   reassembled; shasum matches the BensPC SEAL on both ends.
8. Mac disk hit 0 bytes free mid-copy (other agents active on the shared Mac);
   freed only my own temp files (tree.tgz 163M + build tree 1.9G) and stale
   partial copies; final 5G free. No data lost, panel untouched (single run).

## What it means (plain high-school English)

- Adding machine-written notes next to the chat turns did not help find answers.
  Without notes the retriever already finds 150 of 150 evidences in the top 10;
  with notes it finds 149. Every question type stays flat (multi 30 to 30, time
  30 to 30), far short of the +10/+5 bars.
- It doesn't mean the writer failed to write: it wrote 360 notes over 324 turns
  with zero parse failures, about one note per turn. The blind judge still has
  to say whether those notes are true to their turns (N4 pending) — that part
  is ungraded here.
- It doesn't mean the test leaked: seals checked first (16/16 + 7/7), panel
  written over exactly once, and the panel's turns, questions and notes were
  never opened or quoted — only counts left the machine.
- Per PASSMARKS, the proved-wrong clause tripped (149 <= 150 + 1): for finding
  evidence, notes beside raw turns don't help, at least with this retriever.
