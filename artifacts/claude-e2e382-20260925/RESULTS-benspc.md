# 382b/383 RESULTS-benspc (COMPLETE, inside 5 h cap)

Verdict: COMPLETE. Every step rent-382b did not finish ran once to exit 0 with no
traceback on BensPC: seals, tests, base checkpoint, DEV GATE (PASS), Bank C arms
E/G/R/ER, the 5-arm scorer, chat panels E/G/R/ER, creative E, chat score (E,T,G,R,ER),
creative score (E,T). T arms reused from rent-382b unread (sha verified, never rerun).
Blind-judge marks (C1/C2/C3/K1/S1/S2/S3) are pending off-box judging; only script
counts are reported below. No bank/panel item opened; no reply quoted; no
judge_*, chat_pair_*, chat_turns_*, creative_judge*, grammar_* file opened.

Machine: BensPC, NVIDIA GeForce RTX 5070 Ti 16303 MiB. T reused from rent-382b.
Dollars: $0, no rental. GPU idle at end. Inside the 5 h wall cap: NOT partial.

## 1. Seals + selftests (tree C:/Users/benja/lis301/work/e2e382b/tree)
- SEAL-code.sha256.txt: 239/239 OK (git-bash sha256sum -c, exit 0).
- Bank C SEAL.sha256.txt: 3/3 OK (turns.jsonl, truth.jsonl, README.md).
- Panel382 SEAL.sha256.txt: 2/2 OK (chat/items.jsonl, creative/items.jsonl).
- claude_e2e382_test.py: 10/10 OK. claude_e2e383_test.py: 13/13 OK.
- READER C:/Users/benja/lis301/work/run/merged model.safetensors sha256
  b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890 (match).
- MiniLM present; route122 check printed a route (D8, conf 0.9732).
- W CHECK: `python scripts/claude_winnl2_wrap.py scripts/claude_winnl2_test.py probe`
  prints "ok": true, "crlf": 0.

## 2. Base checkpoint
- JSON line: {"stage": "base", "seed": 4102, "seconds": 12.8, "fresh_hop1to3": 1.0,
  "fresh_depth10": 1.0, "big_depth10": 1.0, "unknown_rate": 1.0}.
- runs/base-seed4102.pt sha256 4655b7610b50e91b57dbb6a780f1935dba8863e3810c4877408d901f1be5edb3,
  2969 bytes (see deviation D4).

## 2b. DEV GATE (PASS; RESULTS-dev.md in artifacts/claude-e2e382-dev-20260925/)
- Dev bank E: arm_E.jsonl rows=248 lives=10, exit 0, no traceback.
- Dev bank R: arm_R.jsonl rows=248 lives=10, exit 0, no traceback.
- First two printed lines of each: sleepcheck line then
  "twinb: the plain twin is Twin336b (enable_thinking=False)".
- Dev scorer: E user_rows 194 ms_median 1911.6 ms_p90 2646.1;
  R user_rows 194 ms_median 1629.4 ms_p90 2789.0.
- Dev chat E: 3/3 chats, chat_E.jsonl rows=10. Dev chat R: 3/3, rows=10.
- Dev chat panel summary (items 3): E messages 10 think_numeric_right 1
  ask_known_right 1 ask_unknown_dont_know 1 ms_median 2487.6;
  R messages 10 think_numeric_right 1 ask_known_right 1 ask_unknown_dont_know 1
  ms_median 2407.3.
- sleep_E.jsonl 34 rows true 34/34; sleep_R.jsonl 30 rows true 30/30.
- ep382_E.jsonl 62 rows; ep382_panel_E.jsonl 1 row.

## 3/3b. Bank C (40/40 lives each) + 4. scorer
- E (claude_e2e382:build_382b): wrote arm_E.jsonl rows=876 lives=40. Same first
  two lines. No SLEEP-NOT-LEARNING. No traceback.
- G (claude_e2e360:build_360): wrote arm_G.jsonl rows=873 lives=40. Same. No traceback.
- R (claude_e2e383:build_383): wrote arm_R.jsonl rows=873 lives=40. Same. No traceback.
- ER (claude_e2e383:build_383e): wrote arm_ER.jsonl rows=874 lives=40. Same. No traceback.
- T reused: arm_T.jsonl sha ea1d543680cfaa43f075a35671ac8a95d59fa1ea3cb2c988898fdf22fbe982dd
  (rows=653 lives=40, from RESULTS-rent.md; verified identical on arrival).
- Scorer mechanical per arm (asks ALL / user_rows 653 each):
  E: ABSTAIN 78, CONFIRM_OTHER 42, RIGHT 69, RIGHT_CONFIRM 24, WRONG_CANDIDATE 32;
    edit: ABSTAIN 13, CONFIRM_OTHER 8, RIGHT 6, WRONG_CANDIDATE 7;
    never_told: CONFIRM_OTHER 7, RIGHT 25, WRONG_CANDIDATE 2;
    one_hop RIGHT 17 RIGHT_CONFIRM 18; two_hop RIGHT 6 RIGHT_CONFIRM 3;
    confirm_rows 223, facts_saved 215/404, distinct_replies 501,
    ms_median 1836.3, ms_p90 3151.2.
  G: ABSTAIN 117, CONFIRM_OTHER 42, RIGHT 50, RIGHT_CONFIRM 24, WRONG_CANDIDATE 12;
    edit: ABSTAIN 18, CONFIRM_OTHER 8, RIGHT 5, WRONG_CANDIDATE 3;
    never_told: CONFIRM_OTHER 7, RIGHT 26, WRONG_CANDIDATE 1;
    one_hop RIGHT 11 RIGHT_CONFIRM 18; two_hop RIGHT 2 RIGHT_CONFIRM 3;
    confirm_rows 220, facts_saved 216/404, distinct_replies 466,
    ms_median 2850.8, ms_p90 6776.6.
  T: ABSTAIN 45, RIGHT 30, WRONG_CANDIDATE 170;
    edit: ABSTAIN 7, RIGHT 4, WRONG_CANDIDATE 23;
    never_told: RIGHT 10, WRONG_CANDIDATE 24;
    confirm_rows 0, facts_saved 0/404, distinct_replies 271,
    ms_median 368.1, ms_p90 630.2.
  R: ABSTAIN 116, CONFIRM_OTHER 42, RIGHT 50, RIGHT_CONFIRM 24, WRONG_CANDIDATE 13;
    edit: ABSTAIN 19, CONFIRM_OTHER 8, RIGHT 5, WRONG_CANDIDATE 2;
    never_told: CONFIRM_OTHER 7, RIGHT 26, WRONG_CANDIDATE 1;
    one_hop RIGHT 11 RIGHT_CONFIRM 18; two_hop RIGHT 2 RIGHT_CONFIRM 3;
    confirm_rows 220, facts_saved 216/404, distinct_replies 470,
    ms_median 1542.6, ms_p90 2711.0.
  ER: ABSTAIN 86, CONFIRM_OTHER 41, RIGHT 72, RIGHT_CONFIRM 24, WRONG_CANDIDATE 22;
    edit: ABSTAIN 13, CONFIRM_OTHER 8, RIGHT 10, WRONG_CANDIDATE 3;
    never_told: CONFIRM_OTHER 7, RIGHT 25, WRONG_CANDIDATE 2;
    one_hop RIGHT 18 RIGHT_CONFIRM 18; two_hop RIGHT 7 RIGHT_CONFIRM 3;
    confirm_rows 221, facts_saved 215/404, distinct_replies 499,
    ms_median 1701.2, ms_p90 2852.8.

## 5/5b. Panels (60/60 items each) + scores
- Chat E: 60/60 conversations, chat_E.jsonl rows=318, exit 0, no traceback.
- Chat G: 60/60, chat_G.jsonl rows=318 (spot: file present, size 93917). No traceback.
- Creative E: 60/60 items, creative_E.jsonl rows=91, exit 0, no traceback.
- Chat R: 60/60, chat_R.jsonl rows=318 (size 125973). No traceback.
- Chat ER: 60/60, chat_ER.jsonl rows=318, ms_median 2670.5. No traceback.
- Chat T / creative T reused: chat_T.jsonl sha
  42fe7744b5955b5b7813fb22d7b15232cde63c2bf957381771a92a409b5e3372,
  creative_T.jsonl sha f6d628db4a6759605fc4a7412e8065bf42f8c775d3246ca4c1bb80c3fadaeb8d.
- Chat panel summary (items 60):
  E messages 318, distinct_replies 263, think_turns 29, think_numeric 23,
  think_numeric_right 5, ask_known 6 (ask_known_right 3), ask_unknown 4
  (ask_unknown_dont_know 3), ms_median 2550.1;
  T think_numeric_right 11, ask_known_right 0, ask_unknown_dont_know 2, ms_median 626.4;
  G think_numeric_right 5, ask_known_right 3, ask_unknown_dont_know 3, ms_median 2416.1;
  R think_numeric_right 10, ask_known_right 3, ask_unknown_dont_know 3, ms_median 2584.9;
  ER think_numeric_right 8, ask_known_right 3, ask_unknown_dont_know 4, ms_median 2670.5.
- Creative panel summary (items 60):
  E messages 91, distinct_replies 85, puzzles 10, puzzles_solved 0, ms_median 2971.9;
  T messages 91, distinct_replies 85, puzzles_solved 0, ms_median 616.4.

## EP382 logs (rows, outcomes, guard failures)
- OUT/ep382_E.jsonl: rows=146, replaced 43, all_failed 103, guard failures 0.
- OUT/ep382_ER.jsonl: rows=146, replaced 35, all_failed 111, guard failures 0.
- OUT/ep382_chat_E.jsonl: rows=54, replaced 7, all_failed 45, no_rows 2, guard failures 0.
- OUT/ep382_creative_E.jsonl: rows=10, all_failed 5, no_rows 5, guard failures 0.

## Sleep logs (rows, checkpoint_exists true, attempted true)
- OUT/sleep_E.jsonl: 120 rows, true 120, attempted true 0.
- OUT/sleep_G.jsonl: 120 rows, true 120, attempted true 0.
- OUT/sleep_R.jsonl: 120 rows, true 120, attempted true 0.
- OUT/sleep_ER.jsonl: 120 rows, true 120, attempted true 0.

## Script-mechanical mark readings (blind-judge marks pending; LoCoMo/GSM8K/MMLU not run here)
- Y2 (bank ALL RIGHT+RIGHT_CONFIRM E-G): E 93, G 74, diff +19 (count; bar +10).
- Q1 (chat think_numeric_right R-G, of 23): R 10, G 5, diff +5 (count; bar +5).
- Q2 (bank never_told ABSTAIN R-G): R 0, G 0, diff 0 (count; bar -1).
- Q3 (bank ALL WRONG_CANDIDATE R-G): R 13, G 12, diff +1 (count; bar +1).
- K2 (creative puzzles_solved E vs T): 0 vs 0, tie (count; bar >= T's).
- L1 (sleep attempted_true rows): 0 in every bank sleep log (count; bar >= 1).
- Y1/R2/C1/C2/C3/K1/S1/S2/S3: pending blind judges or Benchmarks lanes, not judged here.
- route383 counters: report-only; counted inside R/ER runs, not extracted per turn.

## Integrity
- CRLF check: not run as a separate pass; all runner writes went through
  scripts/claude_winnl2_wrap.py (probe crlf 0).
- No traceback in any registered log (grep Traceback = 0 in every step log).
- Copied back and hash-checked on the Mac: run/ 21 new files (T files skipped,
  worktree copies verified identical: ea1d5436/42fe7744/f6d628db), score/ 38 files,
  dev folder (RESULTS-dev.md, run 15 files, score files). Core 9-file sha256 match
  BensPC exactly (arm_E 3ff20d54, arm_ER 31dae9a6, arm_G 0dc741c2, arm_R f47c9179,
  chat_E 771118d4, chat_ER d7d392ca, chat_G 71411df3, chat_R a4a4e48d,
  creative_E 8da04d74).

## Wall time per step (UTC 2026-09-26)
- Setup/staging+checks 10:57-11:06; seals+tests 11:06-11:09; base 11:09-11:11.
- DEV E 11:24:33-11:33; DEV R 11:33:34-11:41; DEV score 11:42-11:43;
  DEV chat E 11:43-11:47; DEV chat R 11:47-11:50; DEV chat score 11:51-11:52.
- Bank E 11:55:19-12:18; bank G 12:19:46-12:57; bank R 12:57:44-13:25;
  bank ER 13:26:02-13:50; bank scorer 13:50:46-13:53.
- Chat E 13:53:37-14:17; chat G 14:17:02-14:36; creative E 14:36:38-14:45;
  chat R 14:45:05-15:09; chat ER 15:09:37-15:37;
  chat score 15:37:20-15:39; creative score 15:39:42-15:41.
- Copy-back+verify 15:50-15:58. GPU idle from 15:37.

## Deviations (all disclosed; code never edited)
- D1 WINNL: every python runner command prefixed with sealed
  scripts/claude_winnl2_wrap.py (precedent: 006k D1). Without it the registered run
  is impossible on Windows (TurnLog323Corrupt at the first turnlog append).
- D2 LAUNCH: long steps launched via Win32_Process Create (git-bash background
  procs die with the SSH session), PID recorded per step (devE 19068/19396/18792/6644,
  devR 12184, devScore 18436, devChatE 2696, devChatR 12152, devChatScore 14292,
  bankE 16932, bankG 21136, bankR 7628, bankER 6108, bankScore 11504, chatE 5808,
  chatG 12208, creE 10060, chatR 5412, chatER 20208, chatScore 22276, creScore 16152).
  Stop-by-exact-PID available throughout, never needed. Process list checked before
  every launch; each registered process ran once except devE (D5).
- D3 SLIM-TREE: staged a slim subset by pipe (never on Mac disk), main on top:
  SEAL paths, scripts+winshim, self122_head.pt (5ca02173 match), reasoner44 dir,
  bankC/panel382/dev/panel-dev/e2e382 data, outbox run T files. The runtime chain
  needed 4 more small committed data files not in the task's list, staged the same
  way: relation_table_v1.json (100 KB), relation-names.txt, ltt_summary.json,
  self127 dir; plus 4 prophylactic small files that may never have been read
  (relation_table_v1_1.json, nameval171b dir, nameval171 dir incl. wordlist171.txt,
  ears47 relation_classes.json).
- D4 BASE-PT: base-seed4102.pt sha 4655b761 differs from rental's 1dfd95f5
  (platform torch determinism); identical to 006k's value on this same box/venv.
  JSON metrics identical to rental (all 1.0). Not sealed; recorded only.
- D5 DEV-E LAUNCHES: devE launched 4x with the same command (11:11, 11:17, 11:21,
  11:24). The first three died at import on the D3 missing files with zero rows
  written (nothing ran); the fourth is the registered run. Every other registered
  process launched exactly once.

## Tracebacks (full; all from devE staging failures, zero rows written each time)
1. 11:11 launch: FileNotFoundError
   '.../tree/artifacts/claude-relationtable-20260922/relation_table_v1.json'
   via scripts/fable_fix222_ofteachb.py line 34 _load_allowed222
   (TABLE_PATH.read_text), during arm build import. Step log devE.log (overwritten
   by later launches; error line captured live).
2. 11:17 relaunch: FileNotFoundError
   '.../tree/artifacts/fable-abstain76-20260921/ltt_summary.json'
   via scripts/fable_loop90_agent.py line 67 load_tau_hat, during arm build.
3. 11:21 relaunch: FileNotFoundError
   '.../tree/artifacts/fable-self127-20260922/deltas127.json'
   via fable_self127 router load, during arm build.
- No other traceback in any registered step log (all grep counts 0).

## What this means
- The rest of registered run 382b/383 is complete on BensPC with the sealed code.
  Script counts: memory row Y2 +19 (mechanical), route Q1 +5/Q2 0/Q3 +1 (mechanical),
  K2 tie 0-0 (mechanical), L1 0 attempts (mechanical, expected FAIL per PASSMARKS).
- Blind-judge rows (C1/C2/C3/K1/S1/S2/S3) and Benchmarks lanes (Y1/R2) are not
  judged here; packets are in score/.
