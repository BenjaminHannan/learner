# RESULTS-rent: rent-sf401 (registered run of sf-401, stale-fact guard)

## Credit / gates
- `vastai show user --raw` credit at start: **4.536206896269867** (balance 0). Above the Director's $3.00 rental floor: rented.
- DUPLICATE gate: no `artifacts/claude-sf401-20260926/run` or `RESULTS-rent.md` on origin/main or origin/builder-outbox, no live `claude-wrongfact-sf401` instance: passed, proceeded.

## Seals and tests (rental ~/tree)
- `sha256sum -c artifacts/claude-e2e02c-20260926/SEAL-code.sha256.txt`: all OK (364 `: OK` lines, 0 FAILED).
- `sha256sum -c artifacts/claude-sf401-20260926/SEAL-sf401.sha256.txt`: all OK (17/17, incl. panel turns/truth/decoys/corrections/README).
- `python -B scripts/claude_readersha_wrap.py --selftest`: `readersha selftest 9/9`.
- `python -B scripts/claude_sf401_test.py`: `sf401 tests: 14/14 passed` (task text said 13/13; PASSMARKS-addendum-2 added CPU test s14, so 14/14 is the current sealed expectation).
- `python -B scripts/claude_sleep02c.py --selftest`: `claude_sleep02c selftest: 9/9 OK`.

## Step 4 reasoner base
- `fable_reasoner44.py --stage base --seed 4102` (17.8 s) -> `artifacts/fable-reasoner44-20260921/runs/base-seed4102.pt`
- sha256: `bc44f9196f5d7982caaaed90233164951ab86b2f40348b4bfe37726ba4d8d93a` (DIFFERS from 0.2c's 4655b7610b50e91b57dbb6a780f1935dba8863e3810c4877408d901f1be5edb3; reported, not a stop; both arms used this file).

## Step 5 arm A (first two output lines)
- `readersha: reader weights sha256 e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76 match READER_SHA`
- `sleepcheck: logging every sleep to artifacts/claude-sf401-20260926/run/sleep_A.jsonl; stop on missing checkpoint = True`
- Result: `wrote arm_A.jsonl rows=747 lives=24`, exit 0.

## Step 6 arm B (first two output lines)
- `readersha: reader weights sha256 e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76 match READER_SHA`
- `sleepcheck: logging every sleep to artifacts/claude-sf401-20260926/run/sleep_B.jsonl; stop on missing checkpoint = True`
- Result: `wrote arm_B.jsonl rows=759 lives=24`, exit 0.

## Step 7 scorer printed lines (mechanical counts only)
- A: asks ALL ABSTAIN 95, CONFIRM_OTHER 27, RIGHT 57, RIGHT_CONFIRM 29, WRONG_CANDIDATE 23; edit ABSTAIN 28, CONFIRM_OTHER 16, RIGHT 5, RIGHT_CONFIRM 16, WRONG_CANDIDATE 9; never_told RIGHT 20; one_hop ABSTAIN 17, CONFIRM_OTHER 4, RIGHT 29, RIGHT_CONFIRM 11, WRONG_CANDIDATE 7; reversal ABSTAIN 18, CONFIRM_OTHER 1, WRONG_CANDIDATE 1; two_hop ABSTAIN 15, CONFIRM_OTHER 3, RIGHT 3, RIGHT_CONFIRM 2, WRONG_CANDIDATE 2; yesno ABSTAIN 17, CONFIRM_OTHER 3, WRONG_CANDIDATE 4. clarify_replies 40, confirm_rows 137, creative_turns 0, day1_saved_facts 201 (kept 196), distinct_replies 411, facts_saved 295, facts_total 468, most_common_reply_count 19, ms_median 807.8, ms_p90 1284.4, new_triples 311 (owner_value_unsupported 14), nosave_turns_with_writes 2, user_rows 610.
- B: asks ALL ABSTAIN 96, CONFIRM_OTHER 26, RIGHT 54, RIGHT_CONFIRM 42, WRONG_CANDIDATE 13; edit ABSTAIN 28, CONFIRM_OTHER 11, RIGHT 5, RIGHT_CONFIRM 27, WRONG_CANDIDATE 3; never_told RIGHT 20; one_hop ABSTAIN 18, CONFIRM_OTHER 8, RIGHT 26, RIGHT_CONFIRM 12, WRONG_CANDIDATE 4; reversal ABSTAIN 18, CONFIRM_OTHER 1, RIGHT 1; two_hop ABSTAIN 16, CONFIRM_OTHER 3, RIGHT 1, RIGHT_CONFIRM 3, WRONG_CANDIDATE 2; yesno ABSTAIN 16, CONFIRM_OTHER 3, RIGHT 1, WRONG_CANDIDATE 4. clarify_replies 41, confirm_rows 149, creative_turns 0, day1_saved_facts 200 (kept 192), distinct_replies 413, facts_saved 305, facts_total 468, most_common_reply_count 19, ms_median 811.6, ms_p90 1293.0, new_triples 322 (owner_value_unsupported 15), nosave_turns_with_writes 2, user_rows 610.

## Guard counters (OUT/sf401_counts_B.jsonl summed per key, counts only)
- cleared_no 1, cleared_repeat 2, doubt_a 25, doubt_b 8, doubt_c 0, doubts_live 61, explained_skip 0, fired 17, fired_confirm 17, fired_hedge 0, offer_no 1, offer_yes 16, question_turns 242, reads_seen 610, turns 759.
- OUT/sf401_events_B.jsonl line count: 759.

## ms per turn
- A median 807.8, p90 1284.4. B median 811.6, p90 1293.0.

## How READER319 and the adapter reached the rental
- READER319 (~/old/lis319-merged): Director's depot route per RELEASE. Depot REPORT.md found on origin/builder-outbox at ~14:18 UTC (DEPOT READY, depot id 52755827, /root/reader319 sha e688e1b2...776a76). `vastai copy 52755827:/root/reader319 52762309:/root/reader319` rental-to-rental (~14:40-14:53 UTC); landed nested one level (reader319/reader319), fixed with `mv` to ~/old/lis319-merged. Rental sha256 e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76 MATCH. Depot never written to, never stopped. Nothing staged on the Mac.
- ADAPTER: streamed from BensPC `C:/Users/benja/lis301/work/e2e02c/tree/.../run/sleep/adapter02c.pt` via bsdtar over ssh piped through the Mac straight to the rental (no Mac copy kept) into `tree/artifacts/claude-e2e02c-20260926/run/sleep/`. Rental sha256 a33211dc9bdb4e26bc7161b62147cb4dfc04fb605ba1aecbb26948f86e7936f5 MATCH (adapter02c.json came with the builder-outbox tree).

## Rental / money
- GPU: NVIDIA GeForce RTX 5090. Instance id 52762309 (label claude-wrongfact-sf401), dph $0.4944. Running 2026-09-26 14:37:13 UTC, destroyed 15:58:07 UTC: 2.35 h x $0.4944 = $1.16.
- Two starter rentals destroyed under the 6-min rule (never reached running): 52760159 (~0.13 h x $0.406 = $0.05) and 52761301 (~0.11 h x $0.4722 = $0.05). Whole-task running total ~$1.27: below the $1.40 BUDGET-STOP tripwire and the $1.50 budget.
- BASE (kit C): /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc (commit 87179e5c1f455ef22e6223592d2d61351b525bfc, matches expected). MiniLM snapshot 1110a243fdf4706b3f48f1d95db1a4f5529b4d41. route122 check passed. Image torch 2.2.1+cu121 was unusable (transformers 5.17 needs torch>=2.5; RTX 5090 needs newer CUDA): upgraded to torch 2.11.0+cu128 (+ torchvision/torchaudio to match) inside the container; no code touched.

## Wall time per step (UTC 2026-09-26)
- Depot poll 14:13-14:18 (REPORT FOUND on poll 2). Rent #1 create 14:19:00, destroyed 14:27 (6-min rule, stayed loading). Rent #2 create 14:26:36, destroyed 14:33 (6-min rule). Rent #3 (52762309) running 14:37:13.
- Tree stream 14:37:50-14:39:08 (32 M; self122_head.pt sha 5ca02173...ee25 OK). vastai reader copy ~14:40-14:53. Adapter stream ~14:41-14:44. Kit C (pip + 2 snapshots + route122) done ~14:47.
- Extra data streams + seals/tests ~14:48-14:52 (seals OK, readersha 9/9, sf401 14/14, sleep02c 9/9 OK). Step 4 reasoner base ~14:53 (17.8 s).
- Torch upgrade 15:02-15:11. Arm A 15:30-15:40 (~10 min). Arm B 15:40-15:53 (~13 min). Score 15:54. Copy-back + verify 15:56-15:58. Destroy 15:58:07, confirmed gone.
- TIME CAP 2 h 30 min on rental (14:37-17:07): not reached.

## Deviations (code never edited)
1. `--bank P`: literal "P" resolves to `P/turns.jsonl` (missing). P is the panel-path variable, so ran with `--bank artifacts/claude-sf401-20260926/panel` for run (A, B) and score. Two crashed A attempts wrote nothing (OUT stayed empty; partial 7 KB/352 B logs deleted before the valid run). Each arm measured ONCE.
2. Tree list omitted runtime data the sealed code reads; streamed read-only extras from origin/main (no code touched): artifacts/claude-relationtable-20260922, design/v3/60-listener/relation-names.txt, artifacts/fable-abstain76-20260921, artifacts/claude-table237-20260922, artifacts/fable-nameval171b-20260922, and ~95 small fable-*-2026092x component config dirs (no *panel*/*bank* dirs streamed; tree 32 M -> 452 M).
3. sf401 test prints 14/14 (addendum-2 s14), not 13/13 as the task text says.
4. Container torch upgraded 2.2.1+cu121 -> 2.11.0+cu128 (+torchvision/torchaudio) to satisfy transformers>=5 and the RTX 5090.
5. 3 rentals total (<= 4 allowed); 2 destroyed under the 6-min rule.
6. EP382_LOG was set for both arms but no ep382_A/B.jsonl was written by the runner (nothing to copy back).
7. Step 4 sha differs from 0.2c (reported, not a stop).

## Tracebacks seen (full)
T1 (A attempt 1, bank path): FileNotFoundError: [Errno 2] No such file or directory: 'P/turns.jsonl' (claude_e2e336_run.py line 221 in main, via load(bank / "turns.jsonl")).
T2 (A attempt 2): ImportError: AutoModelForCausalLM requires the PyTorch library but it was not found (transformers 5.17 vs torch 2.2.1).
T3 (A attempt 3): ModuleNotFoundError: Could not import module 'LlamaConfig', caused by RuntimeError: operator torchvision::nms does not exist (torchvision 0.17.1 vs torch 2.11).
T4 (A attempt 4): FileNotFoundError: [Errno 2] No such file or directory: '/root/tree/artifacts/fable-self127-20260922/deltas127.json' (fable_self127.py load_deltas).
T5 (sf401 test, before extra data): FileNotFoundError artifacts/claude-relationtable-20260922/relation_table_v1.json, then design/v3/60-listener/relation-names.txt, then artifacts/fable-abstain76-20260921/ltt_summary.json, then artifacts/claude-table237-20260922/relation_table_v1_1.json, then artifacts/fable-nameval171b-20260922/closedlist171b.txt; after streaming, 14/14 passed.

## Verdict
M1-M6 pending judges (blind judging runs after this job). No verdict computed here. No reply or panel text quoted; judge_*/grammar_*/arm_* contents never opened (counts only via runner/scorer printouts).
