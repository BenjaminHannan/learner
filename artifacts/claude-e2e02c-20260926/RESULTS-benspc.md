# 02c-benspc RESULTS: Premonition 0.2c registered run on BensPC (COMPLETE, 4b not measured)

Verdict: COMPLETE. Every registered step 1, 2, 3 (DEV GATE PASS), 4 (sleep 3/3 nights),
4a (activation pass=true), 5 (bank D X/G/T + score), 6 (chat X/T/G, creative X/T + scores),
7a (params) ran once each to exit 0 with no traceback. All GPU work finished 10:47 UTC,
inside the 10:50 UTC cap: NOT partial. Step 4b (GSM8K/MMLU lanes) NOT run: step 6 ended
10:44 UTC, past the 09:30 UTC cutoff, so H5/H6 are "not measured" (open, not a pass).
Blind-judge rows (H1-H4, C1, C2, K1, S1) are pending off-box judging; only script counts
are reported below. No reply is quoted; no bank/panel item opened.

Machine: BensPC, NVIDIA GeForce RTX 5070 Ti 16303 MiB, driver 591.86, CUDA 13.1.
Dollars: $0, no rental. BACKUP condition held: no rent-02c run on origin/builder-outbox
(no run/, no RESULTS-rent.md) and no live rent-02c rental (only rent-bm391) at launch.
VRAM peak observed: 9151 MiB (creative X tail); sleep 5935, bank X 5645, bank G 5679,
bank T 5697, chat X 6005, chat T 3579, chat G 6221 MiB. Idle baseline 423 MiB.

## Step 1: seals + selftests (tree C:/Users/benja/lis301/work/e2e02c/tree)
- SEAL-code.sha256.txt: 347/347 OK (git-bash sha256sum -c, exit 0).
- Bank D SEAL.sha256.txt: 3/3 OK (turns.jsonl, truth.jsonl, README.md).
- Panel02c SEAL.sha256.txt: 2/2 OK (chat/items.jsonl, creative/items.jsonl).
- claude_e2e382_test.py: 10/10 OK. claude_e2e383_test.py: 13/13 OK.
- claude_sleep02c.py --selftest: 9/9 OK. claude_fix02c_test.py: 12/12 OK.
- claude_params02c.py --selftest: 1/1 OK.
- READER C:/Users/benja/lis301/work/run/merged model.safetensors sha256
  b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890 (match).
- READER319 C:/Users/benja/lis319/work/run/merged model.safetensors sha256
  e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76 (match).
- MiniLM present; route122 check printed a route (D8, conf 0.9732).
- W CHECK: `W scripts/claude_winnl2_test.py probe` -> "ok": true, "crlf": 0.

## Step 2: sleep base checkpoint
- {"stage": "base", "seed": 4102, "seconds": 12.9, "fresh_hop1to3": 1.0,
  "fresh_depth10": 1.0, "big_depth10": 1.0, "unknown_rate": 1.0}
- runs/base-seed4102.pt sha256 4655b7610b50e91b57dbb6a780f1935dba8863e3810c4877408d901f1be5edb3.

## Step 3: DEV GATE (PASS)
- Dev sleep (1 night, 10 day, 10 test, 3 chat): exit 0, no traceback; 1 night,
  tries=310 > 0; adapter saved (16,568,145 bytes dev adapter, not pushed).
- Dev bank X: exit 0, no traceback; wrote arm_X.jsonl rows=276 lives=10.
- Dev chat X: exit 0, no traceback; chat_X.jsonl 10 rows (3/3 items).
- Dev sleep_X.jsonl: 30 rows, checkpoint_exists true 30/30.

## Step 4: sleep (registered, 3 nights, 150 day, TEST 100, chat 40)
- Base: lucky 74, reached 39, greedy 5, harm_right 201, chat_solved 0.
- Night 1: tries 4650, day 150, day_greedy_right 1, day_reached 66, examples 66,
  optimizer_steps 27, weight_change_l2 2.609708, test lucky/reached/greedy 116/47/7,
  harm lost/gained/net 7/29/-22 right 223, kl 0.03273, chat_solved 0, minutes 11.1,
  adapter_saved true, sha256 92ca438cf0fcd2c68cf324b678e8914f6740b059501faf610812efa3b5496ca9,
  check_greedy_right 0, active_after_reload true.
- Night 2: tries 4650, day_greedy_right 11, day_reached 83, examples 83, steps 33,
  weight_change_l2 2.080267, test 140/57/11, harm 10/48/-38 right 239, kl 0.05355,
  chat_solved 0, minutes 8.1, adapter_saved true,
  sha256 533bb7220101238d32c3cc62841b85c063d8dd8d950ed4f25f96aacbe13a81a3,
  check_greedy_right 2, active_after_reload true.
- Night 3: tries 4650, day_greedy_right 14, day_reached 95, examples 95, steps 36,
  weight_change_l2 2.173805, test 192/61/12, harm 10/47/-37 right 238, kl 0.06264,
  chat_solved 0, minutes 8.2, adapter_saved true,
  sha256 a33211dc9bdb4e26bc7161b62147cb4dfc04fb605ba1aecbb26948f86e7936f5,
  check_greedy_right 0, active_after_reload true.
- Adapter (NOT pushed): run/sleep/adapter02c.pt 16,568,145 bytes,
  sha256 a33211dc9bdb4e26bc7161b62147cb4dfc04fb605ba1aecbb26948f86e7936f5.
  run/sleep/adapter02c.json 395 bytes,
  sha256 07d3c41eecc6f29f9e1df24c4612456c7406971befacba9bef739bebb5afb73a (pushed).

## Step 4a: activation check (fresh process)
- {"check_activation": {"night": 3, "puzzles": 10, "on_equals_saved": 10,
  "on_differs_from_off": 10, "on_again_equals_on": 10, "pass": true}}.

## Step 5: bank D (40/40 lives each) + score
- X: wrote arm_X.jsonl rows=953 lives=40. First lines: sleepcheck line then
  "twinb: the plain twin is Twin336b (enable_thinking=False)". No refusing-to-load error.
- G: wrote arm_G.jsonl rows=860 lives=40. Same first two lines.
- T: wrote arm_T.jsonl rows=658 lives=40. Same first two lines. sleep_T.jsonl absent (expected).
- Scorer mechanical per arm (asks ALL / user_rows 658 each):
  X: ABSTAIN 94, CONFIRM_OTHER 69, RIGHT 29, RIGHT_CONFIRM 34, WRONG_CANDIDATE 18;
    edit: ABSTAIN 8, CONFIRM_OTHER 10, RIGHT 1, RIGHT_CONFIRM 2, WRONG_CANDIDATE 9;
    never_told: CONFIRM_OTHER 16, RIGHT 18, WRONG_CANDIDATE 2;
    one_hop RIGHT 6 RIGHT_CONFIRM 27; two_hop RIGHT 1 RIGHT_CONFIRM 3;
    confirm_rows 295, facts_saved 224/369, distinct_replies 477,
    ms_median 1877.2, ms_p90 2768.6.
  G: ABSTAIN 109, CONFIRM_OTHER 41, RIGHT 53, RIGHT_CONFIRM 24, WRONG_CANDIDATE 17;
    edit: ABSTAIN 11, CONFIRM_OTHER 6, RIGHT 3, RIGHT_CONFIRM 1, WRONG_CANDIDATE 9;
    never_told: CONFIRM_OTHER 3, RIGHT 33;
    confirm_rows 202, facts_saved 219/369, distinct_replies 468,
    ms_median 1515.5, ms_p90 2491.7.
  T: ABSTAIN 42, RIGHT 28, WRONG_CANDIDATE 174;
    edit: ABSTAIN 8, RIGHT 3, WRONG_CANDIDATE 19;
    never_told: RIGHT 12, WRONG_CANDIDATE 24;
    confirm_rows 0, facts_saved 0/369, distinct_replies 312,
    ms_median 906.5, ms_p90 1318.6.
- Sleep logs: sleep_X.jsonl 120 rows, checkpoint_exists true 120, attempted true 0;
  sleep_G.jsonl 120 rows, true 120, attempted true 0.
- EP382 logs: none written (OUT/ep382_X.jsonl, ep382_chat_X.jsonl,
  ep382_creative_X.jsonl all absent, 0 rows). Expected: sealed build_02c has
  MEM02C=0 (382b memory frozen out), so no ep382_stats exist. GRAM360 logs present
  (gram360_parts_X.jsonl 295,743 bytes; gram360_parts_G.jsonl 283,716 bytes).

## Step 6: panels (60/60 items each) + scores
- Chat X (--model READER319): 60/60 conversations, exit 0, no traceback.
- Chat T: 60/60, exit 0, no traceback.
- Chat G: 60/60, exit 0, no traceback.
- Creative X (--model READER319): 60/60 items, exit 0, no traceback.
- Creative T: 60/60 items, exit 0, no traceback.
- Chat panel summary (items 60): X messages 335, distinct_replies 271,
  think_turns 33, think_numeric 27, think_numeric_right 10, ask_known 8
  (ask_known_right 3), ask_unknown 6 (dont_know 6), ms_median 3084.0;
  T think_numeric_right 11, ask_known_right 0, ask_unknown_dont_know 4, ms_median 3026.5;
  G think_numeric_right 12, ask_known_right 2, ask_unknown_dont_know 6, ms_median 2384.3.
- Creative panel summary (items 60): X messages 92, distinct_replies 81,
  puzzles 10, puzzles_solved 0, ms_median 3566.8;
  T messages 92, distinct_replies 90, puzzles_solved 0, ms_median 1519.9.

## Step 7a: params (CPU)
- {"generator": {"params": 1080632832, "bytes": 2161265664, "files": 1},
  "reader_X": {"params": 1080632832, "bytes": 2161265664, "files": 1},
  "reader_G": {"params": 1080632832, "bytes": 2161265664, "files": 1},
  "adapter": {"params": 0, "bytes": 0}, "total_params": 3241898496}.
  (Adapter 0/0: script reads file headers only; the LoRA adapter's 16,568,145 bytes
  are reported in step 4 above, not counted here.) Joined assistant is ~2B resident
  per arm (generator + reader), ~3.24B total across the three model files.

## Step 4b: Benchmarks lanes (NOT MEASURED)
- Not run: step 6 ended 10:44 UTC, past the 09:30 UTC cutoff. H5/H6 open, not a pass.
  No FETCH line, no run02c/ outputs.

## Script-mechanical mark readings (judge rows pending)
- L1 (3/3 nights tries>0, examples>0, weight change>0, reload exact): 3/3 PASS.
- L2 (TEST right after night 3 >= 1.5x before): greedy 12 vs 5 = 2.4x PASS
  (reached 61 vs 39 = 1.56x; lucky 192 vs 74).
- L3 (drops >15% vs prior night, <= 1 of 3): greedy 5->7->11->12, no drops PASS.
- L4 (dl-1 300-item net flips <= 5 every night and <= 0 after night 3):
  net -22/-38/-37 PASS (lost 7/10/10).
- L5 (TEST reached after night 3 >= before): 61 >= 39 PASS.
- L6 (items lost after night 3 <= 20): 10 PASS.
- Q1 (chat think-numeric right X-G >= +3): 10-12 = -2 (count; bar not met).
- Q2 (X-T >= 0): 10-11 = -1 (count; bar not met).
- K2 (creative puzzles solved X >= T): 0 vs 0 (count; tie).
- ME1 (bank edit asks right X >= G): X 1+2=3, G 3+1=4 (count).
- Y1 mechanical (bank ALL RIGHT+RIGHT_CONFIRM X-G): X 63, G 77, diff -14 (count).
- H1/H2/H3/H4, C1/C2, K1, S1: pending blind judges (packets in score/).

## Integrity
- CRLF ("\r\n") byte count: run/ 0 (14 files), score/ 0 (26 files), dev 0 (5 files).
- No traceback in any registered log. One non-registered first attempt (dev sleep
  without W) crashed with TurnLog323Corrupt; disclosed under Deviations, full text
  in the BensPC dev_sleep.log (overwritten by the registered attempt's log).
- Copied back and hash-checked on the Mac (sha256 table in repo command log):
  run/ 14 files, score/ 26 files, dev 5 files; adapter02c.pt named above, never pushed.

## Wall time per step (UTC 2026-09-26)
- Seals+tests 07:11; base checkpoint 07:11:50-07:12:05; dev sleep 07:20:22-~07:26;
  dev bank X 07:27:09-~07:36; dev panel X 07:36:15-~07:41;
  sleep reg 07:41:50-08:21:23; 4a 08:21:34-08:24:58;
  bank X 08:25:21-08:49:57; bank G 08:50:07-~09:13; bank T 09:13:20-09:25:44;
  bank score 09:25:56-09:28; chat X 09:28:24-09:50:36; chat T 09:50:53-10:04:13;
  chat G 10:04:22-10:22:35; creative X 10:22:52-10:38:32; creative T 10:39:05-10:44:32;
  chat score ~10:39-10:41 (concurrent, CPU-only); creative score + 7a 10:44:44-10:46:50;
  copy-back 10:47-10:49. GPU idle at 10:47. Inside the 10:50 cap.

## Deviations (all disclosed; code never edited)
- D1 WINNL: every python runner command was prefixed with sealed
  scripts/claude_winnl2_wrap.py (W), the repo's tested Windows-newline shim
  (precedent: gram-364-benspc VERIFY-364). Without it the registered run is
  impossible on Windows: the first attempt (dev sleep, exact rent-02c command)
  loaded both models then crashed at the first turnlog append with
  "TurnLog323Corrupt: turnlog323: read-back mismatch" (text-mode \r\n vs binary
  read-back). W makes Windows writes byte-identical to Linux (CRLF count 0 above).
- D2 LAUNCH: long steps were launched via Win32_Process Create (survives SSH exit;
  git-bash nohup/background procs are killed when the SSH session closes on this
  box) with PID recorded per step; each step ran alone on the GPU; polls only read
  log tails and nvidia-smi. Stop-by-exact-PID was available throughout, never needed.
- D3 CONCURRENCY: chat --score (CPU-only, no model) ran concurrently with creative T
  to fit the 10:50 cap; GPU stayed on creative T throughout (2953 MiB, single python).
- Bank X used --model READER and chat/creative X used --model READER319 exactly as
  rent-02c steps 5-6 specify (arm build_02c selects the r319 loop internally).
