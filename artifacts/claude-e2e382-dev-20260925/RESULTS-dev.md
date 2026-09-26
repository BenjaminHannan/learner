# 382b/383 DEV GATE RESULTS-dev (BensPC, registered, PASS)

Verdict: PASS. Every DEV command exited 0 with no traceback. Both sleep logs have rows
with checkpoint_exists true. DOUT/ep382_E.jsonl has rows. Proceeding to Bank C.
Counts only; no bank/panel item opened; no reply quoted.

Machine: BensPC, NVIDIA GeForce RTX 5070 Ti. DOUT = artifacts/claude-e2e382-dev-20260925/run.

## DEV bank (dev bank, 10/10 lives each)
- E (claude_e2e382:build_382b): wrote arm_E.jsonl rows=248 lives=10. No traceback.
- R (claude_e2e383:build_383): wrote arm_R.jsonl rows=248 lives=10. No traceback.
- First two printed lines of each: "sleepcheck: ..." and
  "twinb: the plain twin is Twin336b (enable_thinking=False)".

## DEV scorer (dev bank, --runs arm_E arm_R)
- E: user_rows 194, ms_median 1911.6, ms_p90 2646.1.
- R: user_rows 194, ms_median 1629.4, ms_p90 2789.0.
- Full per-arm scorer JSON lines are in devScore.log (mechanical counts only).

## DEV chat panel (dev panel, 3/3 items each)
- chat E: 3/3 chats, chat_E.jsonl rows=10. No traceback.
- chat R: 3/3 chats, chat_R.jsonl rows=10. No traceback.
- Panel summary (--score DOUT --names E,R): items 3.
- E: messages 10, distinct_replies 10, think_turns 1, think_numeric 1,
  think_numeric_right 1, ask_known 1 (ask_known_right 1), ask_unknown 1
  (ask_unknown_dont_know 1), ms_median 2487.6.
- R: messages 10, distinct_replies 10, think_turns 1, think_numeric 1,
  think_numeric_right 1, ask_known 1 (ask_known_right 1), ask_unknown 1
  (ask_unknown_dont_know 1), ms_median 2407.3.

## EP382 logs
- DOUT/ep382_E.jsonl: rows=62, outcomes replaced=17, all_failed=45, guard failures 0.
- DOUT/ep382_panel_E.jsonl: rows=1, outcomes all_failed=1, guard failures 0.

## Sleep logs
- DOUT/sleep_E.jsonl: rows=34, checkpoint_exists true 34/34, attempted true 0.
- DOUT/sleep_R.jsonl: rows=30, checkpoint_exists true 30/30, attempted true 0.

## ms per turn (median / slowest over numeric ms values in run outputs)
- arm_E.jsonl: median 1659.5, slowest 8461.5 (n=248).
- arm_R.jsonl: median 1418.0, slowest 8463.4 (n=248).
- chat_E.jsonl: median 2487.6, slowest 12326.4 (n=10).
- chat_R.jsonl: median 2407.3, slowest 11785.2 (n=10).

## Wall time per step (UTC 2026-09-26)
- dev bank E 11:24:33-~11:33 (~9 min, successful run; two earlier launches died at
  import on missing slim-tree data files, zero rows written, disclosed in RESULTS-benspc).
- dev bank R 11:33:34-~11:41 (~8 min).
- dev score 11:42:12-~11:43 (<1 min).
- dev chat E 11:43:27-~11:47 (~4 min).
- dev chat R 11:47:08-~11:50 (~3 min).
- dev chat score 11:51:28-~11:52 (<1 min).
