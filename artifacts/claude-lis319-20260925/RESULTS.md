# lis-319 registered result (BensPC): PASS — the reader uses history from the prompt

Builder run 2026-09-25 on BensPC (RTX 5070 Ti, CUDA). Sealed code imported and
run unmodified. Panel readpanel319 run once per arm. Category counts only;
no panel turn is quoted.

## Verdict: PASS

| Mark | Bar | Got (integers) | Verdict |
|---|---|---|---|
| H1 back-references: B R0 on needs_history facts | >= 70% of them AND >= A + 40 (98 facts: >= 69 AND >= 41) | B 93/98 (94.9%), A 1/98 | PASS |
| H2 no loss elsewhere: B R0 on the other facts | >= A - 3 (= 99 of 113) | B 104/113 (A 102/113) | PASS |
| H3 safe: B wrong_turns at its T | <= 2 of 240 | 1 of 240 | PASS |
| H4 no invention: B nofact_rows_with_save | <= 1 | 0 | PASS |
| G1 single-turn dev (dev_single 1178 turns, 971 gold, each arm at its T) | B >= A - 3% (= 553 - 29 = 524) | B 577/971 (A 553/971) | PASS |

Proved-wrong clause (PASSMARKS): B's H1 (93) <= A's H1 + 10 (11) is FALSE,
so the reader DOES use history from the prompt; no redirect to a different
mechanism.

## score_A.json (verbatim; arm A = lis-318 reader at T_A 0.995)

{
 "rows": 240,
 "gold": 211,
 "R0": 103,
 "held_right": 45,
 "saved_wrong": 12,
 "wrong_turns": 11,
 "saved_right": 58,
 "threshold": 0.995,
 "ms_median": 1400.3,
 "per_kind": {
  "all:R0": 103,
  "all:gold": 211,
  "all:saved_right": 58,
  "all:wrong_turns": 11
 },
 "gold_hist": 98,
 "R0_hist": 1,
 "gold_local": 113,
 "R0_local": 102
}

## score_B.json (verbatim; arm B = lis-319 reader with history at T_B 0.995)

{
 "rows": 240,
 "gold": 211,
 "R0": 197,
 "saved_right": 65,
 "held_right": 132,
 "saved_wrong": 1,
 "wrong_turns": 1,
 "threshold": 0.995,
 "ms_median": 1426.2,
 "per_kind": {
  "all:R0": 197,
  "all:gold": 211,
  "all:saved_right": 65,
  "all:wrong_turns": 1
 },
 "gold_hist": 98,
 "R0_hist": 93,
 "gold_local": 113,
 "R0_local": 104
}

(nofact_rows_with_save and parse_fail keys are absent from both files because
both counts are 0: the scorer only emits nonzero counters. So H4 = 0 for A
and 0 for B.)

## Length check (LENGTHS.json verbatim, max-len 512)

{
 "train": {
  "rows": 50044,
  "max": 491,
  "p99": 321,
  "over": 0,
  "over_by_src": {}
 },
 "dev": {
  "rows": 1311,
  "max": 382,
  "p99": 318,
  "over": 0,
  "over_by_src": {}
 }
}

Exit code 0 (0% of train rows over 512 tokens; bar to stop was > 1%).

## Threshold and dev sweep (T_B = 0.995, T_A = 0.995)

No sweep grid value reached 0 wrong-save dev turns (minimum 3 at
t=0.980/0.990/0.995), so T_B = 0.995 by the sealed rule. T_A = 0.995 from
origin/builder-outbox:artifacts/claude-lis318-20260925/THRESHOLD.txt.
Full sweep (1311 dev turns, 1053 gold writes):

- t=0.000 wrong_turns=28 recall=1002/1053 ask=131/140 we=19/19
- t=0.300 wrong_turns=27 recall=1001/1053 ask=131/140 we=19/19
- t=0.500 wrong_turns=24 recall=987/1053 ask=131/140 we=19/19
- t=0.600 wrong_turns=21 recall=970/1053 ask=131/140 we=19/19
- t=0.700 wrong_turns=18 recall=961/1053 ask=131/140 we=19/19
- t=0.800 wrong_turns=14 recall=938/1053 ask=131/140 we=19/19
- t=0.850 wrong_turns=13 recall=932/1053 ask=131/140 we=19/19
- t=0.900 wrong_turns=10 recall=896/1053 ask=131/140 we=19/19
- t=0.930 wrong_turns=6 recall=864/1053 ask=131/140 we=19/19
- t=0.950 wrong_turns=5 recall=837/1053 ask=131/140 we=19/19
- t=0.970 wrong_turns=4 recall=802/1053 ask=131/140 we=19/19
- t=0.980 wrong_turns=3 recall=771/1053 ask=131/140 we=19/19
- t=0.990 wrong_turns=3 recall=703/1053 ask=131/140 we=19/19
- t=0.995 wrong_turns=3 recall=611/1053 ask=131/140 we=19/19

Whole dev at T_B: 611/1053 hits (58.0%), 3 wrong turns
(check_so 1 on opus_dev nosave turn, o0a2 1 on nosave turn, teach_multi 1 on
chat318_dev), ask 131/140, we 19/19, turn_exact 429, held_back 438,
ms median 1505.0, p90 2335.0, max 4245.4.

## Dev numbers per src at T_B = 0.995

- o0b_l2: 240/352 hits (68.2%), 0 wrong turns, ask 59/59
- opus_dev: 39/74 hits (52.7%), 1 wrong turn (check_so, nosave turn), ask 14/17, we 4/4
- o0a2: 158/238 hits (66.4%), 1 wrong turn (nosave turn), we 8/8
- opus301_dev: 55/97 hits (56.7%), 0 wrong turns, ask 5/5, we 1/1
- chat318_dev: 85/210 hits (40.5%), 1 wrong turn (teach_multi), ask 43/45, we 3/3
- hist319_dev: 34/82 hits (41.5%), 0 wrong turns, ask 10/14, we 3/3

## G1 (single-turn dev: dev_single 1178 turns, 971 gold writes, lis-300 scorer)

- Arm A (lis-318 dev_pred.jsonl at 0.995): 553/971 hits, 1 wrong turn
  (o0a2, nosave turn), ask 118/126, we 16/16, turn_exact 403.
- Arm B (new reader dev_pred at T_B=0.995): 577/971 hits, 3 wrong turns
  (check_so, o0a2, teach_multi), ask 121/126, we 16/16, turn_exact 408.
- G1: 577 >= 553 - 29 (= 524, 3% of 971). PASS (no forgetting; B is +24).

## B on lis-317 e2e DEV rows (report only, 194 rows with history built)

- reads_e2edev_B.jsonl: 194 rows read on cuda with the lis-319 reader
  (194 rows in, 194 reads out). No bar; file pushed for the record.

## Per-kind panel counts (report only)

Arm A saved_right by kind: all 58/211. Arm B saved_right by kind: all 65/211.
Held_right (what confirm-at-use could still recover): A 45, B 132.
Greedy R0 split: needs_history A 1/98 vs B 93/98; other facts A 102/113
vs B 104/113.

## Training, device, money

- Device: BensPC NVIDIA GeForce RTX 5070 Ti, cuda, greedy decode. No rental, $0.
- Training: 6256/6256 steps, 2 epochs, 76.47 minutes, 2946.3 tok/s,
  dev loss 0.0416, LoRA trainable 22,413,312 of 1,103,046,144 params,
  batch 16 (no OOM, no batch-8 fallback), lr 2e-4, rank 32, seed 300,
  max-len 512, max-minutes 150 cap never bound.
- Base model: C:/Users/benja/lis300/model (reused lis-300 download),
  model-00000-of-00001.safetensors sha256
  7ab8fd86563125929be78aeec8cb3969c7ed2ead3be1ab9d3ec0a9fa69c8660d
  (verified before training; commit 87179e5c as in lis-300 RESULTS.md).
- Merged reader sha256 e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76,
  kept at C:/Users/benja/lis319/work/run/merged (BensPC) and
  ~/premonition-models/lis319-merged/ (Mac, hash verified). Never in git.
- Panel read ms (240 turns): A median 1400.3; B median 1426.2.
- Dev read ms (1311 turns, new reader): median 1505.0, p90 2335.0, max 4245.4.

## Data built (recorded counts)

- Seals from the BensPC tree root before building: lis-300 14/14 OK,
  lis-301 13/13 OK, lis-318 data 14/14 OK, lis-319 data 16/16 OK,
  readpanel319 4/4 OK (git-bash sha256sum -c, same file format).
- Built set: train 50,044 (o0b 27000 + opus 5012 + opus301 4960 + chat318 7936
  + hist319 5136), dev 1311 (o0b_l2 428 + opus_dev 131 + o0a2 263 +
  opus301_dev 137 + chat318_dev 219 + hist319_dev 133),
  hist319 agreed 1417, dropped chat318 UNCLEAR 216 train + 3 dev.
- The panel label files were never opened, printed or quoted. Panel ran once
  per arm (A 240 rows, B 240 hist rows); only scorer counts were viewed.

## Wall time per step (UTC 2026-09-25)

- Setup (fetch, tree build builder-outbox + main on top, scp 169 MB,
  extract, BASE/READER_A sha + GPU idle checks): 17:45-17:51.
- Step 1 seals (BensPC tree root, git-bash sha256sum): 17:47-17:50.
- Step 2 data: 17:50-17:51 (< 1 min); lencheck 17:51 (exit 0, 0 over).
- Step 3 train: 17:51-19:09 (76.5 min).
- Step 4 dev read 19:10-19:46 (~36 min) + sweep + persrc + THRESHOLD + G1
  devsplit/read/score: 19:46-19:48.
- Step 5 seal (THRESHOLD + merged sha, both OK): 19:48 (before panel).
- Step 6 panel A read 19:48-20:00 (~12 min), panel hist build + panel B read
  20:00-20:11 (~11 min), scores 20:11, e2edev hist + read 20:12-20:20
  (~8 min, 194/194 rows).
- Step 7 model copy (2.16 GB scp, both-sha check match) + artifacts
  copy-back: 20:20-20:35.
- Total ~2 h 50 min, inside the 4 h cap.

## Deviations (env only; sealed code untouched)

1. Reused the lis-300 venv (torch 2.11.0+cu128) and the downloaded base-model
   snapshot (safetensors sha256 re-verified) instead of a new venv and
   re-download; new work dir C:/Users/benja/lis319 used throughout.
2. Set PYTHONUTF8=1 (env var only), as in lis-300/lis-301/lis-318.
3. No `resource`-module failure occurred, so scripts/winshim was not needed.
4. No OOM at batch 16, so the batch-8 fallback was not used.
5. shasum is absent on BensPC; seals were checked with git-bash sha256sum -c
   (same file format), all OK counts as above.
6. Background GPU jobs were launched with nohup + disown (no setsid in
   git-bash) with the ssh session kept alive ~100 s after each launch per the
   lis-318 fix; launches that outlived the ssh timeout still survived and
   completed (train 6256/6256, dev 1311/1311, panel A/B 240/240, e2e 194/194).
7. Per-src dev numbers were computed by splitting dev gold/pred by src and
   running the sealed scorer per subset at T_B (same scorer, no edits).
8. rsync is absent on BensPC (Windows OpenSSH has no rsync server), so the
   model was copied back with per-file scp instead of rsync --partial
   (same bytes; safetensors 2,161,290,944 B both ends, sha256 verified match).
9. PowerShell `>` redirect wrote LENGTHS.json as UTF-16; converted to UTF-8
   on copy-back (content identical, exit-0 counts unchanged).
10. THRESHOLD.txt assembled from the sealed sweep output and sealed scorer
    JSONs (whole + 6 persrc + G1 both arms); SEAL-run uses the artifact
    relative path plus the BensPC merged absolute path (both OK under
    sha256sum -c on BensPC), matching the lis-301 precedent.

## What it means (plain high-school English)

- The history prompt fixes back-references. On the blind history panel the
  new reader greedily finds 93 of 98 history-needing facts vs 1 for the old
  reader, with no loss elsewhere (104 vs 102) and safety held (1 wrong turn,
  0 invented saves on nosave rows). Old single-turn dev recall even rose
  553 to 577.
- It doesn't mean the gate is solved: at the live gate the new reader still
  holds back 132 of 197 found panel facts to stay safe (saves 65 vs 58),
  same story as lis-300/lis-301/lis-318.
- It doesn't mean the test leaked: panel run once per arm, seals checked
  first (14/14 + 13/13 + 14/14 + 16/16, key dir 4/4, run sealed pre-panel).
- Per PASSMARKS, the proved-wrong clause did NOT trip (93 is not <= 11):
  the next step is not a different mechanism; history in the prompt works.
