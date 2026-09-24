# RESULTS-rent: rent-330c-dev2 (DEV dress rehearsal of joined 330c, 2026-09-24)

REPORT ONLY. DEV bank only (artifacts/claude-e2e331-dev-20260924, 10 lives,
194 user turns, 131 truth facts). No panel opened, read, tuned on, or quoted.
Counts only; no reply text quoted.

## Pre-run checks (rental, tree root)

- `sha256sum -c SEAL.sha256.txt` inside artifacts/claude-e2e331-dev-20260924: 3/3 OK
  (turns.jsonl, truth.jsonl, README.md).
- `python -B scripts/claude_chat338b_test.py`: `338b tests: 3/3 OK`.
- `python -B scripts/claude_cre333b_test.py`:
  `333b/c tests: 2/2 OK (own look-alikes routed: 333 13/20, 333c 0/20)`.
- `fable_self122.route122('what is your name?')`: returned, no raise.
- READER model.safetensors sha256: b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890 (match).
- self122_head.pt sha256: 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25 (match).

## Arm (1 arm, twinb-wrapped)

Command: `python -B scripts/claude_twinb_wrap.py scripts/claude_e2e336_run.py
--bank artifacts/claude-e2e331-dev-20260924 --arm claude_e2e330c:build_330c
--name P330c --model /root/reader
--gen-model /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
--out artifacts/claude-e2e330c-dev2-20260924/run`

- First printed line: `twinb: the plain twin is Twin336b (enable_thinking=False)` (match).
- Output: run/arm_P330c.jsonl, 248 rows = 194 user + 54 confirm_answer, 10/10 lives.
- Wall time: start ~17:47Z, wrote 17:50:53Z, ~3-4 min (~210 s).
- Tracebacks in arm log: 0.

## Scorer printed line (verbatim)

Command: `python -B scripts/claude_e2e336_score.py
--bank artifacts/claude-e2e331-dev-20260924
--runs artifacts/claude-e2e330c-dev2-20260924/run/arm_*.jsonl
--out artifacts/claude-e2e330c-dev2-20260924/score`

`{"arm": "P330c", "asks": {"ALL": {"ABSTAIN": 44, "CONFIRM_OTHER": 9, "RIGHT": 11, "RIGHT_CONFIRM": 5, "WRONG_CANDIDATE": 2}, "edit": {"ABSTAIN": 3, "CONFIRM_OTHER": 4, "RIGHT_CONFIRM": 3}, "never_told": {"RIGHT": 10}, "one_hop": {"ABSTAIN": 12, "RIGHT": 1, "RIGHT_CONFIRM": 2, "WRONG_CANDIDATE": 1}, "partial": {"ABSTAIN": 4, "CONFIRM_OTHER": 1}, "reversal": {"ABSTAIN": 9, "CONFIRM_OTHER": 1}, "two_hop": {"ABSTAIN": 8, "CONFIRM_OTHER": 2, "WRONG_CANDIDATE": 1}, "yesno": {"ABSTAIN": 8, "CONFIRM_OTHER": 1}}, "clarify_replies": 13, "confirm_rows": 54, "creative_turns": 10, "creative_turns_with_writes": 0, "day1_saved_facts": 30, "day1_saved_facts_kept_at_end": 30, "distinct_replies": 117, "facts_saved": 49, "facts_total": 131, "most_common_reply_count": 50, "ms_median": 797.7, "ms_p90": 1174.4, "new_triples": 53, "new_triples_owner_value_unsupported": 3, "nosave_turns_with_writes": 0, "user_rows": 194}`

Score dir: grammar_P330c.jsonl, judge_asks_P330c.jsonl (2 rows),
judge_saves_P330c.jsonl, mechanical.json. Scorer exit 0. Tracebacks in score log: 0.

## Machine and money

- GPU: 1x RTX 5090 (vast.ai offer 52190830, KR, 16 vCPU, 80 GB disk,
  image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime, torch 2.8.0+cu128, CUDA True).
- Instance: 52456341, label rent-330c-dev2. Rented 2026-09-24T17:21:34Z,
  running ~17:23Z, destroyed 2026-09-24T17:54:05Z, confirmed gone
  (`vastai show instances` lists 0 rent-330c-dev2 after).
- Hours: ~0.54. dph: $0.4690. Dollars: ~$0.25 of $1.00 budget.
- Credit at start: $5.52.
- Rentals used for this task: 1 of 4 allowed. No re-rents, no watchdog kills.

## Models

- BASE (gen): openbmb/MiniCPM5-1B snapshot commit 87179e5c1f455ef22e6223592d2d61351b525bfc
  (matches expected 87179e5c1f455ef22e6223592d2d61351b525bfc).
- READER: lis-301 merged, model.safetensors b4fd93a2 (match, never pushed).
- No other model downloaded.

## Tracebacks

None. `grep -c traceback` on arm log = 0, on score log = 0.
(No traceback to reproduce in full.)

## Files for PUSH

- artifacts/claude-e2e330c-dev2-20260924/RESULTS-rent.md (this file)
- artifacts/claude-e2e330c-dev2-20260924/run (arm_P330c.jsonl, 248 rows)
- artifacts/claude-e2e330c-dev2-20260924/score (4 files)
- artifacts/fable-predictions-ledger.md (appended 1 line)
