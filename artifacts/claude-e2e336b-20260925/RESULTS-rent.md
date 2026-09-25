# RESULTS-rent.md: rent-336b, registered follow-up run 336b of Premonition 0.1 (bank B, 40 lives, rented Linux GPU)

Verdict: RAN COMPLETE. All four arms and the scorer exited 0 on the rental. No SEAL-MISMATCH, no SLEEP-NOT-LEARNING stop, no DUPLICATE. Counts only below; no judge/grammar/bank content opened or quoted.

## Scorer's printed line for each arm (verbatim)

{"arm": "G", "asks": {"ALL": {"ABSTAIN": 128, "CONFIRM_OTHER": 26, "RIGHT": 46, "RIGHT_CONFIRM": 29, "WRONG_CANDIDATE": 7}, "edit": {"ABSTAIN": 25, "CONFIRM_OTHER": 7, "RIGHT_CONFIRM": 5, "WRONG_CANDIDATE": 2}, "never_told": {"CONFIRM_OTHER": 1, "RIGHT": 36, "WRONG_CANDIDATE": 1}, "one_hop": {"ABSTAIN": 33, "CONFIRM_OTHER": 4, "RIGHT": 9, "RIGHT_CONFIRM": 17}, "partial": {"ABSTAIN": 13}, "reversal": {"ABSTAIN": 18, "CONFIRM_OTHER": 5, "RIGHT": 1, "RIGHT_CONFIRM": 4}, "two_hop": {"ABSTAIN": 25, "CONFIRM_OTHER": 6, "RIGHT_CONFIRM": 3, "WRONG_CANDIDATE": 3}, "yesno": {"ABSTAIN": 14, "CONFIRM_OTHER": 3, "WRONG_CANDIDATE": 1}}, "clarify_replies": 17, "confirm_rows": 180, "creative_turns": 38, "creative_turns_with_writes": 0, "day1_saved_facts": 90, "day1_saved_facts_kept_at_end": 87, "distinct_replies": 400, "facts_saved": 156, "facts_total": 333, "most_common_reply_count": 27, "ms_median": 755.7, "ms_p90": 1155.2, "new_triples": 181, "new_triples_owner_value_unsupported": 24, "nosave_turns_with_writes": 0, "user_rows": 619}
{"arm": "P", "asks": {"ALL": {"ABSTAIN": 128, "CONFIRM_OTHER": 26, "RIGHT": 46, "RIGHT_CONFIRM": 29, "WRONG_CANDIDATE": 7}, "edit": {"ABSTAIN": 25, "CONFIRM_OTHER": 7, "RIGHT_CONFIRM": 5, "WRONG_CANDIDATE": 2}, "never_told": {"CONFIRM_OTHER": 1, "RIGHT": 36, "WRONG_CANDIDATE": 1}, "one_hop": {"ABSTAIN": 33, "CONFIRM_OTHER": 4, "RIGHT": 9, "RIGHT_CONFIRM": 17}, "partial": {"ABSTAIN": 13}, "reversal": {"ABSTAIN": 18, "CONFIRM_OTHER": 5, "RIGHT": 1, "RIGHT_CONFIRM": 4}, "two_hop": {"ABSTAIN": 25, "CONFIRM_OTHER": 6, "RIGHT_CONFIRM": 3, "WRONG_CANDIDATE": 3}, "yesno": {"ABSTAIN": 14, "CONFIRM_OTHER": 3, "WRONG_CANDIDATE": 1}}, "clarify_replies": 17, "confirm_rows": 181, "creative_turns": 38, "creative_turns_with_writes": 0, "day1_saved_facts": 90, "day1_saved_facts_kept_at_end": 87, "distinct_replies": 400, "facts_saved": 156, "facts_total": 333, "most_common_reply_count": 27, "ms_median": 761.7, "ms_p90": 1150.4, "new_triples": 181, "new_triples_owner_value_unsupported": 24, "nosave_turns_with_writes": 0, "user_rows": 619}
{"arm": "T", "asks": {"ALL": {"ABSTAIN": 25, "RIGHT": 17, "WRONG_CANDIDATE": 194}, "edit": {"ABSTAIN": 6, "RIGHT": 3, "WRONG_CANDIDATE": 30}, "never_told": {"RIGHT": 7, "WRONG_CANDIDATE": 31}, "one_hop": {"ABSTAIN": 10, "RIGHT": 2, "WRONG_CANDIDATE": 51}, "partial": {"ABSTAIN": 1, "WRONG_CANDIDATE": 12}, "reversal": {"ABSTAIN": 3, "RIGHT": 2, "WRONG_CANDIDATE": 23}, "two_hop": {"ABSTAIN": 3, "RIGHT": 3, "WRONG_CANDIDATE": 31}, "yesno": {"ABSTAIN": 2, "WRONG_CANDIDATE": 16}}, "clarify_replies": 0, "confirm_rows": 0, "creative_turns": 38, "creative_turns_with_writes": 0, "day1_saved_facts": 0, "day1_saved_facts_kept_at_end": 0, "distinct_replies": 321, "facts_saved": 0, "facts_total": 333, "most_common_reply_count": 17, "ms_median": 346.1, "ms_p90": 696.0, "new_triples": 0, "new_triples_owner_value_unsupported": 0, "nosave_turns_with_writes": 0, "user_rows": 619}
{"arm": "B", "asks": {"ALL": {"ABSTAIN": 196, "RIGHT": 38, "WRONG_CANDIDATE": 2}, "edit": {"ABSTAIN": 37, "WRONG_CANDIDATE": 2}, "never_told": {"RIGHT": 38}, "one_hop": {"ABSTAIN": 63}, "partial": {"ABSTAIN": 13}, "reversal": {"ABSTAIN": 28}, "two_hop": {"ABSTAIN": 37}, "yesno": {"ABSTAIN": 18}}, "clarify_replies": 575, "confirm_rows": 0, "creative_turns": 38, "creative_turns_with_writes": 0, "day1_saved_facts": 0, "day1_saved_facts_kept_at_end": 0, "distinct_replies": 34, "facts_saved": 1, "facts_total": 333, "most_common_reply_count": 312, "ms_median": 7.9, "ms_p90": 15.9, "new_triples": 3, "new_triples_owner_value_unsupported": 2, "nosave_turns_with_writes": 0, "user_rows": 619}

G vs P: identical on every count except confirm_rows (G 180, P 181). Arm file rows: G 799, P 800, T 619, B 619 (G/P row files include confirm_answer rows).

## Seal checks (step 1, on the rental before anything else)

- `sha256sum -c artifacts/claude-e2e336b-20260925/SEAL-code.sha256.txt` from tree root: 229/229 OK, 0 failures.
- `sha256sum -c SEAL.sha256.txt` from inside artifacts/claude-e2e331-bankB-20260925: 3/3 OK (turns.jsonl, truth.jsonl, README.md).
- Tree: git archive origin/builder-outbox + git archive origin/main on top + self122_head.pt copy (sha256 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25, match).
- READER model.safetensors sha256 b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890 (match). Route122 smoke check passed.

## Step 2 (sleep base checkpoint rebuild)

- Printed JSON line: {"stage": "base", "seed": 4102, "seconds": 14.4, "fresh_hop1to3": 1.0, "fresh_depth10": 1.0, "big_depth10": 1.0, "unknown_rate": 1.0}
- Copied /tmp/r44/base-seed4102.pt to artifacts/fable-reasoner44-20260921/runs/base-seed4102.pt (cp only; runs/ .json files untouched).
- .pt sha256: 1dfd95f5e6917cb5a5a73a408456555e27f4706a5bfae752cd0b0b632db63c86 (2969 bytes).

## Sleep logs (rows with checkpoint_exists true / attempted true)

- sleep_G.jsonl: 120 rows, 120 checkpoint_exists true, 0 attempted true.
- sleep_P.jsonl: 120 rows, 120 checkpoint_exists true, 0 attempted true.
- sleep_B.jsonl: 120 rows, 120 checkpoint_exists true, 0 attempted true.
- sleep_T.jsonl: absent (expected; T has no sleep).
- Every row: accepted true, reason "0 word episodes (< 8); kept queued, nothing to gate". No SLEEP-NOT-LEARNING stop on any arm (checkpoint present on all 360 rows; stop triggers only on missing checkpoint or "no base checkpoint" reason, neither seen).

## Machine, money, model, wall time

- GPU: NVIDIA GeForce RTX 5090, 32607 MiB. Image torch 2.8.0+cu128 with CUDA True.
- BASE model commit hash: 87179e5c1f455ef22e6223592d2d61351b525bfc (HF snapshot dir, matches expected).
- Rental 1: contract 52513837, offer 43982841 (machine 142842, ip 180.189.55.38), dph $0.4944, rented 01:46:33Z, ssh key auth refused for 10+ min, destroyed ~01:58Z, ~0.19 h = ~$0.09, outcome SSH-FAIL.
- Rental 2: contract 52514776, offer 48989566 (machine 148839, ip 180.189.55.43 KR), dph $0.4944, rented ~01:56:30Z, running 02:01:19Z, destroyed 03:05:47Z, ~1.15 h = ~$0.57.
- Combined ~$0.66 of $4.00 budget. Account credit at start $1.90. No DUPLICATE (no live rent-336b at start; no run/ on origin/builder-outbox).
- Wall time per arm (rental 2, UTC 2026-09-25): G 02:27:56 to 02:37:10 = 554 s; P ~02:38:35 to 02:48:55 ~= 620 s (approximate start); T ~02:50:50 to 02:55:52 ~= 300 s (approximate); B ~02:55:50 to 02:57:12 ~= 80 s (approximate); scorer ~02:57:30 to ~03:01 ~= 200 s (approximate). All exits 0.
- First two stdout lines of every arm: "sleepcheck: ..." then "twinb: the plain twin is Twin336b (enable_thinking=False)" (verified in each arm log).

## Tracebacks

- No traceback in any completed arm run or the scorer run.
- One traceback in the superseded FIRST G launch (died < 2 min, wrote no arm file; relaunched after mkdir, see deviations). Captured tail:
  run_life(builder, args, lid, by[lid], truth_by.get(lid, []), rows)
    File "scripts/claude_e2e336_run.py", line 176, in run_life
      reply, ms, new = one(agent, text)
  File "scripts/claude_e2e336_run.py", line 158, in one
    parts = agent.turn(text)
  File "/root/tree/scripts/claude_nb323_turnlog.py", line 323, in _turn323
    said = self._orig_turn323(text)
  File "/root/tree/scripts/claude_gram360.py", line 333, in turn_gram
    with open(path, "a", encoding="utf-8") as f:
  FileNotFoundError: [Errno 2] No such file or directory: 'artifacts/claude-e2e336b-20260925/run/gram360_parts_G.jsonl'
  EXIT=1

## Copy-back verification

- run/ (8 files: arm_G/P/T/B.jsonl, sleep_G/P/B.jsonl, gram360_parts_G.jsonl) + score/ (13 files: grammar_G/P/T/B, judge_asks_G/P/T/B, judge_saves_G/P/T/B, mechanical.json): 21/21 sha256 match between rental and Mac.
- sleep_T.jsonl correctly absent on both sides.

## Deviations (all reported, code never edited)

1. Rental 1 unreachable via ssh (proxy key auth refused incl. a fresh registered key) -> destroyed, re-rented another host (rental 2 of max 4). Costed ~$0.09, inside budget.
2. First G launch died on missing run/ dir (gram360 opens GRAM360_LOG for append; dir did not exist yet) -> created the dir with mkdir, relaunched G once. Dead process confirmed gone before relaunch; first launch wrote no arm file.
3. First P launch missed the SLEEPCHECK env vars (log said "(no log)", stop False) -> killed before any output (no arm_P.jsonl on disk), relaunched correctly with SLEEPCHECK_STOP=1 + SLEEPCHECK_LOG. One live P process at all times (verified via ps).
4. Sleep attempted=true on 0/360 rows (sleeper gated on < 8 word episodes each time); checkpoint present on 360/360 rows so no stop. B2 evaluation is the director's call.
