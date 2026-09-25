# rent-360-gram RESULTS-rent (registered gram-360 run on bank G, rented Linux GPU)

## Pre-run checks (rental, tree root)
- `sha256sum -c SEAL.sha256.txt` in artifacts/claude-gram360-bankG-20260925: turns.jsonl OK, truth.jsonl OK, README.md OK (3/3 OK).
- `python -B scripts/claude_gram360_test.py`: gram360 tests: 16/16 OK.
- `python -B scripts/claude_chat338b_test.py`: 338b tests: 3/3 OK.
- `python -B scripts/claude_cre333d_test.py`: 333d tests: 2/2 OK.
- `python -B scripts/claude_vary330c_test.py`: vary330c tests: 2/2 OK.
- Sidecar `gram360_parts.jsonl` absent before Step 2 (verified).
- Twinb banner first printed line on both arms: `twinb: the plain twin is Twin336b (enable_thinking=False)`.

## Scorer printed lines (scripts/claude_e2e336_score.py, counts only, no reply text)
- P330c: {"arm": "P330c", "user_rows": 194, "confirm_rows": 55, "clarify_replies": 15, "creative_turns": 10, "creative_turns_with_writes": 0, "facts_total": 134, "facts_saved": 71, "day1_saved_facts": 52, "day1_saved_facts_kept_at_end": 52, "new_triples": 81, "new_triples_owner_value_unsupported": 9, "nosave_turns_with_writes": 0, "distinct_replies": 140, "most_common_reply_count": 8, "ms_median": 771.1, "ms_p90": 1226.2, "asks_ALL": {"ABSTAIN": 36, "CONFIRM_OTHER": 10, "RIGHT": 16, "RIGHT_CONFIRM": 6, "WRONG_CANDIDATE": 3}}
- P360: {"arm": "P360", "user_rows": 194, "confirm_rows": 56, "clarify_replies": 15, "creative_turns": 10, "creative_turns_with_writes": 0, "facts_total": 134, "facts_saved": 71, "day1_saved_facts": 52, "day1_saved_facts_kept_at_end": 52, "new_triples": 80, "new_triples_owner_value_unsupported": 9, "nosave_turns_with_writes": 0, "distinct_replies": 142, "most_common_reply_count": 8, "ms_median": 768.0, "ms_p90": 1235.6, "asks_ALL": {"ABSTAIN": 34, "CONFIRM_OTHER": 10, "RIGHT": 17, "RIGHT_CONFIRM": 6, "WRONG_CANDIDATE": 4}}
- Run rows: arm_P360.jsonl 250 rows / 10 lives; arm_P330c.jsonl 249 rows / 10 lives (from runner `wrote` lines).

## Checker printed line (scripts/claude_gram360_check.py, counts only)
- {"P360.3": "PASS", "P360.3_ask_class": 0, "P360.3_confirm_answer": 0, "P360.3_confirm_flag": 0, "P360.4": "PASS", "P360.4_word_losses": 0, "distinct_all_final": 193, "distinct_rule_final": 154, "distinct_rule_raw": 154, "nonrule_changed": 0, "nonrule_parts": 103, "replies_changed": 62, "rows": 250, "rule_parts": 183, "rule_parts_changed": 68}

## Machine / money / models
- GPU: 1x NVIDIA GeForce RTX 5090 (vast.ai).
- Instance: 52513907, label rent-360-gram, offer 45669186, image pytorch/pytorch:2.8.0-cuda12.9-cudnn9-runtime, 8 vCPU / 80 GB disk request.
- dph: $0.5037037037037037.
- Alive: rented 2026-09-25 ~01:48Z, running ~01:52Z-02:23Z, destroyed 2026-09-25 ~02:25Z; billed duration ~0.60 h x $0.5037/h = ~$0.30 (budget $1.50 respected; credit $1.90 at start).
- BASE (openbmb/MiniCPM5-1B snapshot): 87179e5c1f455ef22e6223592d2d61351b525bfc (matches expected).
- READER (/root/reader = ~/premonition-models/lis301-merged): model.safetensors sha256 b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890 (match).
- self122_head.pt sha256 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25 (match).
- HF second snapshot (sentence-transformers/all-MiniLM-L6-v2): 1110a243fdf4706b3f48f1d95db1a4f5529b4d41.

## Wall time per arm (UTC 2026-09-25)
- P360: start 02:13:51Z, end 02:17:01Z = 190 s.
- P330c: start 02:17:01Z, end 02:20:05Z = 184 s.
- Score + check: ~02:20Z, exits 0/0.

## Tracebacks
- None. grep Traceback over rent360.log = 0. Step exits: P360_EXIT:0, P330c_EXIT:0, SCORE_EXIT:0, CHECK_EXIT:0.

## Independence notes
- Bank turns/truth never opened, printed or quoted (runner/scorer/checker read them).
- grammar_*.jsonl, judge_*.jsonl and check/*.jsonl never opened.
- No reply or turn text quoted in this file (counts only).
- Month-end code run unedited (tree from git archive origin/builder-outbox + origin/main, main on top).
- run/, score/, check/ copied back and row/file-checked before destroy; instance confirmed gone via `vastai show instances`.
