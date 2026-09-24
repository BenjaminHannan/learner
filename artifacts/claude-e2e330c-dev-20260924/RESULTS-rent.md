# rent-330c-dev: DEV dress rehearsal of 330c vs plain twin b on rented Linux GPU (REPORT ONLY, 2026-09-24)

Verdict: PASS (rehearsal). The joined Premonition 0.1 agent (scripts/claude_e2e330c.py, arm P330c)
and the fixed plain twin b (arm twinb) each ran 10/10 DEV lives end to end on the rental,
and the scorer ran clean. Dev data only; no registered marks; no TEST-ONLY panel touched
(judge_*.jsonl and grammar_*.jsonl written by the scorer were never opened).

## What ran where

- Rental: vast.ai contract 52455952, NVIDIA GeForce RTX 5090, 32607 MiB, offer 49024471,
  16 vCPU, image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime (image torch 2.8.0+cu128,
  CUDA True, no torch upgrade needed).
- Window: 2026-09-24 17:18:38Z (rent) to 17:46:25Z (destroyed, confirmed 0 rent-330c-dev
  live after; sibling labels untouched).
- Hours alive: 1677 s = 0.47 h. dph $0.469. Dollars ~$0.22. Budget $1.50: respected.
  Whole-task spend incl. dead attempts ~$0.27 (see Deviations). Credit $6.13 at start.
- BASE model commit hash: 87179e5c1f455ef22e6223592d2d61351b525bfc (matches expected).
- READER safetensors sha256: b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890 (match).
- self122_head.pt sha256: 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25 (match).
- DEV bank seal on the rental (step 1, from inside artifacts/claude-e2e331-dev-20260924):
  3/3 OK (turns.jsonl OK, truth.jsonl OK, README.md OK).
- 338b unit tests on the rental: "338b tests: 3/3 OK".
- Tree: git archive origin/builder-outbox + git archive origin/main on top, plus the
  self122_head.pt copy. Month-end code never edited.
- Both arms wrapped with scripts/claude_twinb_wrap.py; the first printed line of each arm
  log is "twinb: the plain twin is Twin336b (enable_thinking=False)" (2/2).

## Wall time per arm (seconds, container clock, exit 0 both)

- P330c: 184 s, wrote arm_P330c.jsonl rows=248 lives=10 (194 user + 54 confirm_answer).
- twinb: 69 s, wrote arm_twinb.jsonl rows=194 lives=10 (194 user + 0 confirm_answer).
- Scorer: exit 0. Copied back: 2 run files + 7 score files, byte sizes match the box.

## Scorer's printed line for each arm (verbatim, counts only)

{"arm": "P330c", "asks": {"ALL": {"ABSTAIN": 44, "CONFIRM_OTHER": 9, "RIGHT": 11, "RIGHT_CONFIRM": 5, "WRONG_CANDIDATE": 2}, "edit": {"ABSTAIN": 3, "CONFIRM_OTHER": 4, "RIGHT_CONFIRM": 3}, "never_told": {"RIGHT": 10}, "one_hop": {"ABSTAIN": 12, "RIGHT": 1, "RIGHT_CONFIRM": 2, "WRONG_CANDIDATE": 1}, "partial": {"ABSTAIN": 4, "CONFIRM_OTHER": 1}, "reversal": {"ABSTAIN": 9, "CONFIRM_OTHER": 1}, "two_hop": {"ABSTAIN": 8, "CONFIRM_OTHER": 2, "WRONG_CANDIDATE": 1}, "yesno": {"ABSTAIN": 8, "CONFIRM_OTHER": 1}}, "clarify_replies": 13, "confirm_rows": 54, "creative_turns": 10, "creative_turns_with_writes": 0, "day1_saved_facts": 30, "day1_saved_facts_kept_at_end": 30, "distinct_replies": 109, "facts_saved": 49, "facts_total": 131, "most_common_reply_count": 48, "ms_median": 790.9, "ms_p90": 1167.4, "new_triples": 53, "new_triples_owner_value_unsupported": 3, "nosave_turns_with_writes": 0, "user_rows": 194}
{"arm": "twinb", "asks": {"ALL": {"ABSTAIN": 12, "RIGHT": 3, "WRONG_CANDIDATE": 56}, "edit": {"ABSTAIN": 2, "WRONG_CANDIDATE": 8}, "never_told": {"RIGHT": 2, "WRONG_CANDIDATE": 8}, "one_hop": {"ABSTAIN": 2, "WRONG_CANDIDATE": 14}, "partial": {"ABSTAIN": 2, "WRONG_CANDIDATE": 3}, "reversal": {"ABSTAIN": 2, "WRONG_CANDIDATE": 8}, "two_hop": {"ABSTAIN": 2, "RIGHT": 1, "WRONG_CANDIDATE": 8}, "yesno": {"ABSTAIN": 2, "WRONG_CANDIDATE": 7}}, "clarify_replies": 0, "confirm_rows": 0, "creative_turns": 10, "creative_turns_with_writes": 0, "day1_saved_facts": 0, "day1_saved_facts_kept_at_end": 0, "distinct_replies": 66, "facts_saved": 0, "facts_total": 131, "most_common_reply_count": 20, "ms_median": 331.8, "ms_p90": 538.9, "new_triples": 0, "new_triples_owner_value_unsupported": 0, "nosave_turns_with_writes": 0, "user_rows": 194}

## think-tag check

- Rows in arm_twinb.jsonl whose reply contains "<think": 0 (expected 0).
- Rows in arm_P330c.jsonl whose reply contains "<think": 0.

## Tracebacks

- None. Both arm logs contain 0 lines matching "traceback"; scorer exited 0.

## Deviations (3 dead rentals, 0 code edits, panel never touched)

1. Contract 52453726 (offer 50232264, $0.4676/h): stuck "loading" past the 6-min mark,
   destroyed per rule, $0.00.
2. Contract 52454797 (offer 40999534, $0.469/h): reached "running" in ~2 min but the ssh
   proxy refused connections for 6+ min; one reboot did not fix it; destroyed, ~$0.05.
3. Contract 52455934: create returned success:false (offer just taken); destroyed the
   stub, $0.00.
4. Contract 52455952 (offer 49024471, $0.469/h): rented 17:18:38Z, running 17:21:18Z,
   all steps green, destroyed 17:46:25Z. 4 rentals total = the allowed maximum.

## What it means (plain high-school English)

- The 330c dress rehearsal runs end to end on Linux: 2/2 arms finished, 194 user turns
  each, scorer lines above. The joined agent saves 49/131 facts with 54 follow-up
  confirmations; the plain twin saves 0 and never asks back. This says the harness,
  the reader, and the DEV bank work together; it says nothing about any registered
  TEST-ONLY panel.
- The twin-b swap printed its banner line first in both arms, so both arms really ran
  against Twin336b.

## What it doesn't mean

- It doesn't mean the agent passes anything registered: this is DEV data with
  mechanical counts only; the blind judges never ran here (their packets are filed
  unopened for later).
