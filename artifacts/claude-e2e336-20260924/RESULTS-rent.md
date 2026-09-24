# rent-336-registered: REGISTERED end-to-end run 336 of Premonition 0.1 (2026-09-24)

Verdict: RAN (registered run executed once; marks left to the month-end thread's judges).
Bank A (TEST-ONLY) was read only by the sealed runner and scorer, once. No judge_*.jsonl,
grammar_*.jsonl or bank file was opened here; no reply is quoted.

## What ran where

- Rental: vast.ai contract 52466807, NVIDIA GeForce RTX 5090, offer 45669065,
  16 vCPU, image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime (image torch 2.8.0+cu128,
  CUDA True, no torch upgrade needed).
- Window: 2026-09-24 18:44:05Z (rent) to 19:48:35Z (destroyed, confirmed 0
  rent-336-registered live after; sibling labels untouched).
- Hours alive: 3870 s = 1.075 h. dph $0.5037. Dollars ~$0.54. Budget $4.00: respected.
  1 rental total (allowed maximum 4). Credit $7.61 at start.
- BASE model commit hash: 87179e5c1f455ef22e6223592d2d61351b525bfc (matches expected).
- READER safetensors sha256: b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890 (match).
- self122_head.pt sha256: 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25 (match).
- Tree: git archive origin/builder-outbox + git archive origin/main on top, plus the
  self122_head.pt copy. Month-end code never edited.
- Seal checks on the rental BEFORE anything else: SEAL-code 223/223 OK (0 failures),
  bank SEAL 3/3 OK (turns.jsonl OK, truth.jsonl OK, README.md OK).
- All three arms wrapped with scripts/claude_twinb_wrap.py; the first printed line of each
  arm log is "twinb: the plain twin is Twin336b (enable_thinking=False)" (3/3).

## Wall time per arm (seconds, container clock, exit 0 all)

- P (claude_e2e330c:build_330c, READER + BASE): 602 s, wrote arm_P.jsonl rows=850 lives=40.
- T (twin b, BASE): ~200 s, wrote arm_T.jsonl rows=663 lives=40.
- B (292t, READER): 8 s, wrote arm_B.jsonl rows=663 lives=40.
- Scorer: exit 0 in ~20 s. Copied back: 3 run files + 10 score files, sizes and sha256
  match the box for all 13 files before destroy.

## Scorer's printed line for each arm (verbatim, counts only)

{"arm": "P", "asks": {"ALL": {"ABSTAIN": 126, "CONFIRM_OTHER": 25, "RIGHT": 56, "RIGHT_CONFIRM": 16, "WRONG_CANDIDATE": 19}, "edit": {"ABSTAIN": 21, "CONFIRM_OTHER": 5, "RIGHT": 1, "RIGHT_CONFIRM": 6, "WRONG_CANDIDATE": 2}, "never_told": {"CONFIRM_OTHER": 6, "RIGHT": 30}, "one_hop": {"ABSTAIN": 28, "CONFIRM_OTHER": 3, "RIGHT": 18, "RIGHT_CONFIRM": 7, "WRONG_CANDIDATE": 7}, "partial": {"ABSTAIN": 10, "CONFIRM_OTHER": 2, "WRONG_CANDIDATE": 1}, "reversal": {"ABSTAIN": 23, "RIGHT": 2, "WRONG_CANDIDATE": 4}, "two_hop": {"ABSTAIN": 19, "CONFIRM_OTHER": 8, "RIGHT": 5, "RIGHT_CONFIRM": 3, "WRONG_CANDIDATE": 2}, "yesno": {"ABSTAIN": 25, "CONFIRM_OTHER": 1, "WRONG_CANDIDATE": 3}}, "clarify_replies": 34, "confirm_rows": 187, "creative_turns": 40, "creative_turns_with_writes": 0, "day1_saved_facts": 125, "day1_saved_facts_kept_at_end": 121, "distinct_replies": 449, "facts_saved": 182, "facts_total": 318, "most_common_reply_count": 23, "ms_median": 770.3, "ms_p90": 1200.4, "new_triples": 200, "new_triples_owner_value_unsupported": 16, "nosave_turns_with_writes": 0, "user_rows": 663}
{"arm": "T", "asks": {"ALL": {"ABSTAIN": 39, "RIGHT": 16, "WRONG_CANDIDATE": 187}, "edit": {"ABSTAIN": 9, "RIGHT": 1, "WRONG_CANDIDATE": 25}, "never_told": {"RIGHT": 8, "WRONG_CANDIDATE": 28}, "one_hop": {"ABSTAIN": 8, "RIGHT": 5, "WRONG_CANDIDATE": 50}, "partial": {"ABSTAIN": 2, "WRONG_CANDIDATE": 11}, "reversal": {"ABSTAIN": 7, "RIGHT": 1, "WRONG_CANDIDATE": 21}, "two_hop": {"ABSTAIN": 8, "RIGHT": 1, "WRONG_CANDIDATE": 28}, "yesno": {"ABSTAIN": 5, "WRONG_CANDIDATE": 24}}, "clarify_replies": 0, "confirm_rows": 0, "creative_turns": 40, "creative_turns_with_writes": 0, "day1_saved_facts": 0, "day1_saved_facts_kept_at_end": 0, "distinct_replies": 211, "facts_saved": 0, "facts_total": 318, "most_common_reply_count": 115, "ms_median": 275.5, "ms_p90": 511.1, "new_triples": 0, "new_triples_owner_value_unsupported": 0, "nosave_turns_with_writes": 0, "user_rows": 663}
{"arm": "B", "asks": {"ALL": {"ABSTAIN": 201, "RIGHT": 36, "WRONG_CANDIDATE": 5}, "edit": {"ABSTAIN": 35}, "never_told": {"RIGHT": 36}, "one_hop": {"ABSTAIN": 62, "WRONG_CANDIDATE": 1}, "partial": {"ABSTAIN": 13}, "reversal": {"ABSTAIN": 25, "WRONG_CANDIDATE": 4}, "two_hop": {"ABSTAIN": 37}, "yesno": {"ABSTAIN": 29}}, "clarify_replies": 523, "confirm_rows": 0, "creative_turns": 40, "creative_turns_with_writes": 0, "day1_saved_facts": 2, "day1_saved_facts_kept_at_end": 2, "distinct_replies": 73, "facts_saved": 2, "facts_total": 318, "most_common_reply_count": 280, "ms_median": 8.2, "ms_p90": 16.5, "new_triples": 7, "new_triples_owner_value_unsupported": 5, "nosave_turns_with_writes": 0, "user_rows": 663}

## Tracebacks

- None. Arm logs contain 0 lines matching "traceback" (P 0, T 0, B 0); scorer exited 0.

## Deviations (1 duplicate process, 1 slow upload, 0 code edits, panel never touched)

1. The first arm-P launch ssh call timed out locally but had actually started the run on
   the box, and the retry started a second identical P process (PIDs 794 + 836, same out
   dir). The unintended older process (794) was killed within ~5 min; the confirmed run
   (836, banner first line) completed 40/40 lives alone. No two different arms ever ran
   at once; T and B each ran once, sequentially after P finished.
2. The 2 GB READER upload needed two scp passes (first timed out at ~1.5 GB); the final
   file sha256 matches b4fd93a2 before any run.
3. Code unedited, bank read only by runner/scorer, judge/grammar files never opened,
   no reply quoted.
