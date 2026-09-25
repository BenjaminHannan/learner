# lis-318 registered result (BensPC): FAIL — chatty rows are not the lever

Builder run 2026-09-25 on BensPC (RTX 5070 Ti, CUDA). Sealed code imported and
run unmodified. Panel readpanel318 run once per arm. Category counts only;
no panel turn is quoted.

## Verdict: FAIL

| Mark | Bar | Got (integers) | Verdict |
|---|---|---|---|
| Q1 reads chat: B R0 | >= 217/255 AND >= A R0 + 38 (= 277) | B 237/255 (A 239/255) | FAIL |
| Q2 saves more: B saved_right at its T | >= A saved_right + 40 (= 151) | B 132 (A 111) | FAIL |
| Q3 safe: B wrong_turns at its T | <= 2 of 240 | 0 of 240 | PASS |
| Q4 no invention: B nofact_rows_with_save | <= 1 | 0 | PASS |
| G1 no forgetting: lis-301 dev hits, each arm at its T | B >= A - 23 (= 439) | B 484/761 (A 462/761) | PASS |
| G2 speed: B median read ms on BensPC | <= A median + 200 (= 1697.9) | B 1545.6 (A 1497.9) | PASS |

Proved-wrong clause (PASSMARKS): B's R0 (237) <= A's R0 + 13 (252) is TRUE,
so chat rows are not the lever; the next step is a different mechanism
(more context, open relations, or a learned checker), not more rows.

## score_A.json (verbatim; arm A = lis-301 reader at T 0.995)

{
 "rows": 240,
 "gold": 255,
 "R0": 239,
 "saved_right": 111,
 "held_right": 128,
 "saved_wrong": 0,
 "wrong_turns": 0,
 "threshold": 0.995,
 "ms_median": 1497.9,
 "per_kind": {
  "correct:R0": 20,
  "correct:gold": 21,
  "short_answer:R0": 14,
  "short_answer:gold": 15,
  "short_answer:saved_right": 3,
  "teach_multi:R0": 142,
  "teach_multi:gold": 147,
  "teach_multi:saved_right": 84,
  "teach_passing:R0": 23,
  "teach_passing:gold": 32,
  "teach_passing:saved_right": 1,
  "teach_single:R0": 40,
  "teach_single:gold": 40,
  "teach_single:saved_right": 23
 }
}

## score_B.json (verbatim; arm B = lis-318 reader at its dev T = 0.995)

{
 "rows": 240,
 "gold": 255,
 "R0": 237,
 "saved_right": 132,
 "held_right": 105,
 "saved_wrong": 0,
 "wrong_turns": 0,
 "threshold": 0.995,
 "ms_median": 1545.6,
 "per_kind": {
  "correct:R0": 21,
  "correct:gold": 21,
  "correct:saved_right": 3,
  "short_answer:R0": 14,
  "short_answer:gold": 15,
  "short_answer:saved_right": 3,
  "teach_multi:R0": 140,
  "teach_multi:gold": 147,
  "teach_multi:saved_right": 90,
  "teach_passing:R0": 24,
  "teach_passing:gold": 32,
  "teach_passing:saved_right": 12,
  "teach_single:R0": 38,
  "teach_single:gold": 40,
  "teach_single:saved_right": 24
 }
}

(nofact_rows_with_save and parse_fail keys are absent from both files because
both counts are 0: the scorer only emits nonzero counters. So Q4 = 0 for A
and 0 for B.)

## Threshold and dev sweep (T = 0.995)

No sweep grid value reached 0 wrong-save dev turns (minimum 1 at t=0.995),
so T = 0.995 by the sealed rule. Full sweep (1181 dev turns, 971 gold writes):

- t=0.000 wrong_turns=18 recall=927/971 ask=118/126 we=16/16
- t=0.300 wrong_turns=16 recall=927/971 ask=118/126 we=16/16
- t=0.500 wrong_turns=16 recall=923/971 ask=118/126 we=16/16
- t=0.600 wrong_turns=15 recall=906/971 ask=118/126 we=16/16
- t=0.700 wrong_turns=13 recall=887/971 ask=118/126 we=16/16
- t=0.800 wrong_turns=11 recall=873/971 ask=118/126 we=16/16
- t=0.850 wrong_turns=11 recall=857/971 ask=118/126 we=16/16
- t=0.900 wrong_turns=7 recall=828/971 ask=118/126 we=16/16
- t=0.930 wrong_turns=6 recall=800/971 ask=118/126 we=16/16
- t=0.950 wrong_turns=5 recall=769/971 ask=118/126 we=16/16
- t=0.970 wrong_turns=4 recall=723/971 ask=118/126 we=16/16
- t=0.980 wrong_turns=3 recall=682/971 ask=118/126 we=16/16
- t=0.990 wrong_turns=2 recall=618/971 ask=118/126 we=16/16
- t=0.995 wrong_turns=1 recall=553/971 ask=118/126 we=16/16

Whole dev at T: 553/971 hits (57.0%), 1 wrong turn (o0a2 family, nosave turn),
ask 118/126, we 16/16, turn_exact 403, held_back 410, ms median 1498.4.

## Dev numbers per src at T = 0.995

- o0b_l2: 231/352 hits (65.6%), 0 wrong turns, ask 59/59
- opus_dev: 41/74 hits (55.4%), 0 wrong turns, ask 15/17, we 4/4
- o0a2: 146/238 hits (61.3%), 1 wrong turn (nosave turn), we 8/8
- opus301_dev: 66/97 hits (68.0%), 0 wrong turns, ask 5/5, we 1/1
- chat318_dev: 69/210 hits (32.9%), 0 wrong turns, ask 39/45, we 3/3

## G1 (lis-301 original dev, 959 turns, 761 gold writes, lis-300 scorer)

- Arm A (lis-301 dev_pred.jsonl at 0.995): 462/761 hits, 2 wrong turns
  (both o0a2), ask 77/81, we 13/13. Reproduces the published lis-301 numbers.
- Arm B (new reader on lis-301 dev_rows.jsonl at T_B=0.995): 484/761 hits,
  1 wrong turn (o0a2, nosave turn), ask 79/81, we 13/13.
- G1: 484 >= 462 - 23 = 439. PASS (no forgetting; B is +22 on old dev).

## B on the lis-317 DEV rows (report only, claude_lis317_score.py counts)

- R0 88/131 (lis-301 reader: 89/131), saved at T (RT) 33 (lis-301: 20),
  RT_and_check_ok 32, W0 18, ask act ASK on 60/71 ask turns.

## Per-kind panel counts (report only)

Arm A saved_right by kind: teach_multi 84/147, teach_single 23/40,
teach_passing 1/32, correct 0/21, short_answer 3/15.
Arm B saved_right by kind: teach_multi 90/147, teach_single 24/40,
teach_passing 12/32, correct 3/21, short_answer 3/15.
Held_right (what confirm-at-use could still recover): A 128, B 105.

## Training, device, money

- Device: BensPC NVIDIA GeForce RTX 5070 Ti, cuda, greedy decode. No rental, $0.
- Training: 5642/5642 steps, 2 epochs, 40.51 minutes, 3866.7 tok/s,
  dev loss 0.0453, LoRA trainable 22,413,312 of 1,103,046,144 params,
  batch 16 (no OOM, no batch-8 fallback), lr 2e-4, rank 32, seed 300,
  max-minutes 150 cap never bound.
- Base model: C:/Users/benja/lis300/model (reused lis-300 download),
  model-00000-of-00001.safetensors sha256
  7ab8fd86563125929be78aeec8cb3969c7ed2ead3be1ab9d3ec0a9fa69c8660d
  (verified before training; commit 87179e5c as in lis-300 RESULTS.md).
- Merged reader sha256 8b3fdbda0868277303f1fac893de3b1a88448957ebf3aedbd79e570e0c883e6d,
  kept at C:/Users/benja/lis318/work/run/merged (BensPC) and
  ~/premonition-models/lis318-merged/ (Mac, hash verified). Never in git.
- Panel read ms (240 turns): A median 1497.9; B median 1545.6 (G2 PASS).
- Dev read ms (1181 turns, new reader): median 1498.4, p90 2332.6, max 4564.8.

## Data built (recorded counts)

- Seals from the BensPC tree root before building: lis-300 14/14 OK,
  lis-301 13/13 OK, lis-318 data 14/14 OK, readpanel318 4/4 OK.
- Built set: train 45124 (o0b 27000 + opus 5012 + opus301 4960 + chat318 8152
  = 2038 agreed non-dev rows x4), dev 1181 (o0b_l2 428 + opus_dev 131 +
  o0a2 263 + opus301_dev 137 + chat318_dev 222), chat318 agreed 2260,
  chat318 dev dialogs rows 222.
- The panel label files were never opened, printed or quoted. Panel ran once
  per arm; only scorer counts were viewed.

## Wall time per step (UTC 2026-09-25)

- Setup (fetch, tree build builder-outbox + main on top, scp, extract,
  BASE/READER sha + GPU idle checks): 06:45-06:52.
- Step 1 seals: 06:52.
- Step 2 data: 06:52-06:53 (< 1 min).
- Step 3 train: 06:54-07:38 (40.5 min).
- Step 4 dev read + sweep + persrc + THRESHOLD + G1 read/score: 07:40-08:56.
- Step 5 seal: 08:56 (before panel).
- Step 6 panel A read 08:57-09:07, panel B read 09:08-09:18, scores 09:19,
  e2edev read 09:20-09:28.
- Step 7 model copy + both-sha check + artifacts copy-back: 09:28-09:35.
- Total ~2 h 50 min, inside the 4 h cap.

## Deviations (env only; sealed code untouched)

1. Reused the lis-300 venv (torch 2.11.0+cu128) and the downloaded base-model
   snapshot (safetensors sha256 re-verified) instead of a new venv and
   re-download; new work dir C:/Users/benja/lis318 used throughout.
2. Set PYTHONUTF8=1 (env var only), as in lis-300/lis-301.
3. No `resource`-module failure occurred, so scripts/winshim was not needed.
4. No OOM at batch 16, so the batch-8 fallback was not used.
5. shasum is absent on BensPC; seals were checked with git-bash sha256sum -c
   (same file format), all OK counts as above.
6. Background GPU jobs were launched with nohup + disown (no setsid in
   git-bash) with the ssh session kept alive ~100 s after each launch; one
   G1 launch without that wait died silently and was relaunched (no data lost,
   panel untouched).
7. Per-src dev numbers were computed by splitting dev gold/pred by src and
   running the sealed scorer per subset at T (same scorer, no edits).

## What it means (plain high-school English)

- The chatty training rows did not move the needle. On the blind chatty panel
  the new reader greedily finds 237 of 255 facts vs 239 for the old reader,
  and at the live gate it saves 132 vs 111 — far short of the +38/+40 bars.
  Safety held (0 wrong turns, 0 invented saves on nosave rows), and old-dev
  recall even rose 462 to 484, but the registered question was whether chat
  rows fix chat reading, and the answer is no.
- It doesn't mean the reader can't read chat at all: with no gate it already
  finds ~93% of panel facts (both arms), same story as lis-300/lis-301. The
  gate still throws away over half the true facts to stay safe.
- It doesn't mean the test leaked: panel run once per arm, seals checked
  first (14/14 + 13/13 + 14/14, key dir 4/4, run sealed pre-panel at 08:56).
- Per PASSMARKS, the proved-wrong clause tripped: next step is a different
  mechanism (more context, open relations, or a learned checker), not more rows.
