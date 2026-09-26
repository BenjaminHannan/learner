# rd-371b registered result (BensPC): FAIL on counted marks — dev bar keeps almost nothing

Builder run 2026-09-26 on BensPC (RTX 5070 Ti, CUDA). Sealed code run unmodified.
Panel notepanel371b scored ONCE at the dev bar; only scorer counts viewed.
No panel turn, note, or dialog text is quoted anywhere in this file.

## Verdict: FAIL (C1 passes on n=1, C2 misses, C3 passes; proved-wrong clause TRUE)

| Mark | Bar | Got (integers) | Verdict |
|---|---|---|---|
| C1 untrue notes stored: unsupported share of accepted (key ok + unsupported) | <= 5% | 0/1 accepted unsupported (0.0%) | PASS |
| C2 good notes kept: key-ok notes accepted | >= 80% | 1/132 (0.8%) | FAIL |
| C3 no kind left behind: chat vs overheard C2 | gap <= 10 points | chat 1/68 (1.5%), overheard 0/64 (0.0%), gap 1.5 points | PASS |
| Proved wrong: at its dev bar the checker keeps < 50% of key-ok notes | report | 1/132 (0.8%) < 50% | TRUE |

## score.json (verbatim counts; note text never printed)

{
 "accepted": 1,
 "chat:excluded_total": 19,
 "chat:ok_kept": 1,
 "chat:ok_total": 68,
 "chat:unsupported_total": 61,
 "excluded_total": 37,
 "ok_kept": 1,
 "ok_total": 132,
 "overheard:excluded_total": 18,
 "overheard:ok_total": 64,
 "overheard:unsupported_total": 84,
 "unsupported_total": 145,
 "threshold": 0.98,
 "C1_unsupported_share_of_accepted": 0.0,
 "C2_ok_kept_share": 0.0076,
 "ms_median": 24.2
}

Keyed panel notes: 277 (132 ok + 145 unsupported); excluded 37 (19 chat + 18 overheard).
Panel check ran once: 314 notes checked.

## Dev bar (THRESHOLD.json)

- T = 0.98 (rule: lowest grid value with dev unsupported/accepted <= 0.04, accepted > 0).
- Dev row at T: accepted 6, unsupported 0, ok_kept 6/167, rate 0.0.
- Dev sweep notes: 277; verdicts ok 167, bad_cite 7, unsupported 96, bad_when 2, bad_form 5.
- Grid near the bar: t=0.9 accepted 78 unsupported 6 ok_kept 69 rate 0.0769 (fail);
  t=0.95 accepted 37 unsupported 3 ok_kept 34 rate 0.0811 (fail);
  t=0.98 accepted 6 unsupported 0 ok_kept 6 rate 0.0 (pass, first pass);
  t=0.99 and above accepted 0 (empty, rule skips).
- Dev check: 277 notes checked, device cuda, median ms per note 24.0.

## Training, device, money

- Device: BensPC NVIDIA GeForce RTX 5070 Ti, cuda. No rental, $0.
- Training: 284/284 steps, 2 epochs, 3.25 minutes, 3955.3 tok/s, dev loss 0.1978,
  LoRA trainable 22,413,312 of 1,103,046,144 params, batch 16 (no OOM, no batch-8
  fallback), lr 2e-4, rank 32, seed 300, max-len 512, max-minutes 60 cap never bound.
- Train rows 2257, dev rows 218 (ck/summary.json).
- Base model: C:/Users/benja/lis300/model (reused lis-300 download),
  model-00000-of-00001.safetensors sha256
  7ab8fd86563125929be78aeec8cb3969c7ed2ead3be1ab9d3ec0a9fa69c8660d
  (re-verified before training; commit 87179e5c as in lis-300 RESULTS.md).
- No downloads. Venv C:/Users/benja/lis300/venv (torch 2.11.0+cu128).
- Merged checker sha256
  f54dbe63dff7963cb1fbd2db0b79dcdf79055f3c7b276ba536453cc07ce284a1,
  kept on BensPC at C:/Users/benja/rd371b/run/merged (sha verified after copy)
  and at C:/Users/benja/rd371b/tree/WORK/run/merged. Never in git.
- SEAL-run.sha256.txt seals THRESHOLD.json (7a64090e...) + merged model.safetensors
  (f54dbe63...), written BEFORE the panel run.

## Report-only numbers

- No-checker baseline (accept all 277 keyed): unsupported share 145/277 (52.3%),
  ok kept 132/132 (100%).
- Excluded notes: 37 (19 chat, 18 overheard).
- Median ms per note: panel 24.2, dev 24.0.
- C3 detail: chat ok 1/68 kept, overheard ok 0/64 kept.

## Data / seals (BensPC tree, counts only)

- SEAL.sha256.txt 1/1 OK, SEAL-data.sha256.txt 6/6 OK, SEAL-train.sha256.txt 7/7 OK,
  key/SEAL.sha256.txt 6/6 OK, notepanel371b SEAL.sha256.txt 2/2 OK.
- Sealed panel/key/panel_notes files were never opened, printed or quoted; panel
  scored once; only scorer counts and ms were viewed.

## Wall time per step (UTC 2026-09-26; BensPC local = UTC-4)

- Setup (fetch, tree build builder-outbox + main on top, 6-chunk scp, reassemble sha
  match, extract, BASE sha + GPU idle checks): 04:35-04:49.
- Seals: 04:47-04:49 (all OK).
- Train: launched 04:49:47, done ~04:56 (3.25 min per summary).
- Dev check (277 notes) + sweep (T=0.98) + seal-run: ~04:57-04:58.
- Panel check once (314 notes) + score at 0.98: ~04:58-04:59.
- Model keep-copy (sha verified) + 6 small-file copy-backs: ~04:59-05:01.
- Total ~26 min, inside the 90 min cap (training 3.25 min < 60 min cap).

## Deviations (env only; sealed code untouched)

1. Reused the lis-300 venv and the downloaded base-model snapshot (sha re-verified)
   instead of a new venv and re-download; new work dir C:/Users/benja/rd371b/tree
   with WORK/run inside, then kept merged at C:/Users/benja/rd371b/run/merged.
2. Set PYTHONUTF8=1 (env var only), as in lis-300/lis-301/lis-318/rd-378.
3. shasum is absent on BensPC; seals checked with git-bash sha256sum -c. The key
   seal lists bare filenames, so it was run from inside
   artifacts/claude-rd371b-20260926/key (6/6 OK) rather than the tree root
   (where the paths don't resolve); same env-only pattern as the rd-378 deviation.
4. No OOM at batch 16, so the batch-8 fallback was not used.
5. First training launch died silently (no log, GPU idle); relaunched with the ssh
   session held open ~100 s per the lis-318/006g pattern and it survived (launch ssh
   calls time out locally with no output even on success; verified via separate ssh).
6. Whole-file scp stalls on the flaky link; tree.tgz (177M) moved in 6 split chunks
   and reassembled with matching sha256.
7. One GPU job at a time throughout; GPU 0% before and after each step (training drew
   ~223W, real compute, no VRAM-spill signature).

## What it means (plain high-school English)

- The checker learned to say no to almost everything. At the bar picked on dev
  (0.98), it keeps 1 of 132 good panel notes and accepts 1 note total, so the
  untrue-share looks perfect (0%) only because it stores almost nothing.
- It does not mean the idea is dead, only that this trained checker at its
  registered bar fails the good-notes-kept mark (C2 0.8% vs 80% needed) and trips
  the proved-wrong clause (keeps far under half the good notes).
- It does not mean the test leaked: seals passed first, the panel ran once, and no
  dialog or note text is quoted anywhere.

PUSH: artifacts/claude-rd371b-20260926/RESULTS.md artifacts/claude-rd371b-20260926/train_summary.json artifacts/claude-rd371b-20260926/dev_pred.jsonl artifacts/claude-rd371b-20260926/THRESHOLD.json artifacts/claude-rd371b-20260926/SEAL-run.sha256.txt artifacts/claude-rd371b-20260926/panel_pred.jsonl artifacts/claude-rd371b-20260926/score.json
