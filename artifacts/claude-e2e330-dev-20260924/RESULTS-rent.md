# rent-330-dev: DEV dress rehearsal on rented Linux GPU (REPORT ONLY, 2026-09-24)

Verdict: PASS (rehearsal). All 5 arms ran to completion and the scorer ran clean on the
rental, where the Windows run (RESULTS-dev.md) stopped at the preflight with 0 arms run.
Dev data only; no registered marks; no TEST-ONLY panel touched.

## What ran where

- Rental: vast.ai contract 52415640, NVIDIA GeForce RTX 5090, 32607 MiB, offer 49337314.
- Window: 2026-09-24 12:38:26Z (rent) to 13:37:18Z (destroyed, confirmed 0 live after).
- Hours alive: 3532 s = 0.98 h. dph $0.4944. Dollars ~$0.49. Budget $2.00: respected.
- BASE model commit hash: 87179e5c1f455ef22e6223592d2d61351b525bfc (downloaded once on the box).
- READER safetensors sha256: b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890 (match).
- self122_head.pt sha256: 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25 (match).
- DEV bank seal on the rental (step 1, from inside the bank folder): 3/3 OK
  (turns.jsonl OK, truth.jsonl OK, README.md OK).
- Tree: git archive origin/builder-outbox + git archive origin/main on top, plus the
  self122_head.pt copy. Month-end code never edited.

## Wall time per arm (seconds, from the rental log)

- G: 163 s, exit 0, wrote arm_G.jsonl rows=226 lives=10
- 330a: 163 s, exit 0, wrote arm_330a.jsonl rows=226 lives=10
- 330a_cre: 173 s, exit 0, wrote arm_330a_cre.jsonl rows=247 lives=10
- 330a_chat: 193 s, exit 0, wrote arm_330a_chat.jsonl rows=247 lives=10
- twin: 257 s, exit 0, wrote arm_twin.jsonl rows=194 lives=10
- Scorer: exit 0. Copied back: 5 run files + 16 score files, byte sizes match the box.

## Scorer's printed line for every arm (verbatim, counts only)

{"arm": "G", "asks": {"ALL": {"ABSTAIN": 44, "CONFIRM_OTHER": 7, "RIGHT": 12, "RIGHT_CONFIRM": 3, "WRONG_CANDIDATE": 5}, "edit": {"ABSTAIN": 3, "CONFIRM_OTHER": 4, "RIGHT": 1, "RIGHT_CONFIRM": 1, "WRONG_CANDIDATE": 1}, "never_told": {"RIGHT": 10}, "one_hop": {"ABSTAIN": 12, "RIGHT": 1, "RIGHT_CONFIRM": 2, "WRONG_CANDIDATE": 1}, "partial": {"ABSTAIN": 4, "CONFIRM_OTHER": 1}, "reversal": {"ABSTAIN": 9, "CONFIRM_OTHER": 1}, "two_hop": {"ABSTAIN": 7, "CONFIRM_OTHER": 1, "WRONG_CANDIDATE": 3}, "yesno": {"ABSTAIN": 9}}, "clarify_replies": 98, "confirm_rows": 32, "creative_turns": 10, "creative_turns_with_writes": 0, "day1_saved_facts": 18, "day1_saved_facts_kept_at_end": 18, "distinct_replies": 66, "facts_saved": 33, "facts_total": 131, "most_common_reply_count": 49, "ms_median": 725.2, "ms_p90": 995.0, "new_triples": 34, "new_triples_owner_value_unsupported": 0, "nosave_turns_with_writes": 0, "user_rows": 194}
{"arm": "330a", "asks": {"ALL": {"ABSTAIN": 44, "CONFIRM_OTHER": 7, "RIGHT": 12, "RIGHT_CONFIRM": 3, "WRONG_CANDIDATE": 5}, "edit": {"ABSTAIN": 3, "CONFIRM_OTHER": 4, "RIGHT": 1, "RIGHT_CONFIRM": 1, "WRONG_CANDIDATE": 1}, "never_told": {"RIGHT": 10}, "one_hop": {"ABSTAIN": 12, "RIGHT": 1, "RIGHT_CONFIRM": 2, "WRONG_CANDIDATE": 1}, "partial": {"ABSTAIN": 4, "CONFIRM_OTHER": 1}, "reversal": {"ABSTAIN": 9, "CONFIRM_OTHER": 1}, "two_hop": {"ABSTAIN": 7, "CONFIRM_OTHER": 1, "WRONG_CANDIDATE": 3}, "yesno": {"ABSTAIN": 9}}, "clarify_replies": 98, "confirm_rows": 32, "creative_turns": 10, "creative_turns_with_writes": 0, "day1_saved_facts": 18, "day1_saved_facts_kept_at_end": 18, "distinct_replies": 66, "facts_saved": 33, "facts_total": 131, "most_common_reply_count": 49, "ms_median": 730.0, "ms_p90": 1001.9, "new_triples": 34, "new_triples_owner_value_unsupported": 0, "nosave_turns_with_writes": 0, "user_rows": 194}
{"arm": "330a_cre", "asks": {"ALL": {"ABSTAIN": 44, "CONFIRM_OTHER": 8, "RIGHT": 11, "RIGHT_CONFIRM": 5, "WRONG_CANDIDATE": 3}, "edit": {"ABSTAIN": 3, "CONFIRM_OTHER": 3, "RIGHT_CONFIRM": 3, "WRONG_CANDIDATE": 1}, "never_told": {"RIGHT": 10}, "one_hop": {"ABSTAIN": 12, "RIGHT": 1, "RIGHT_CONFIRM": 2, "WRONG_CANDIDATE": 1}, "partial": {"ABSTAIN": 4, "CONFIRM_OTHER": 1}, "reversal": {"ABSTAIN": 9, "CONFIRM_OTHER": 1}, "two_hop": {"ABSTAIN": 8, "CONFIRM_OTHER": 2, "WRONG_CANDIDATE": 1}, "yesno": {"ABSTAIN": 8, "CONFIRM_OTHER": 1}}, "clarify_replies": 91, "confirm_rows": 53, "creative_turns": 10, "creative_turns_with_writes": 0, "day1_saved_facts": 32, "day1_saved_facts_kept_at_end": 32, "distinct_replies": 81, "facts_saved": 49, "facts_total": 131, "most_common_reply_count": 46, "ms_median": 744.8, "ms_p90": 1150.6, "new_triples": 52, "new_triples_owner_value_unsupported": 2, "nosave_turns_with_writes": 0, "user_rows": 194}
{"arm": "330a_chat", "asks": {"ALL": {"ABSTAIN": 38, "CONFIRM_OTHER": 8, "RIGHT": 12, "RIGHT_CONFIRM": 5, "WRONG_CANDIDATE": 8}, "edit": {"ABSTAIN": 3, "CONFIRM_OTHER": 3, "RIGHT_CONFIRM": 3, "WRONG_CANDIDATE": 1}, "never_told": {"RIGHT": 10}, "one_hop": {"ABSTAIN": 11, "RIGHT": 1, "RIGHT_CONFIRM": 2, "WRONG_CANDIDATE": 2}, "partial": {"ABSTAIN": 4, "CONFIRM_OTHER": 1}, "reversal": {"ABSTAIN": 8, "CONFIRM_OTHER": 1, "WRONG_CANDIDATE": 1}, "two_hop": {"ABSTAIN": 7, "CONFIRM_OTHER": 2, "WRONG_CANDIDATE": 2}, "yesno": {"ABSTAIN": 5, "CONFIRM_OTHER": 1, "RIGHT": 1, "WRONG_CANDIDATE": 2}}, "clarify_replies": 16, "confirm_rows": 53, "creative_turns": 10, "creative_turns_with_writes": 0, "day1_saved_facts": 32, "day1_saved_facts_kept_at_end": 32, "distinct_replies": 148, "facts_saved": 49, "facts_total": 131, "most_common_reply_count": 29, "ms_median": 934.0, "ms_p90": 1156.3, "new_triples": 52, "new_triples_owner_value_unsupported": 2, "nosave_turns_with_writes": 0, "user_rows": 194}
{"arm": "twin", "asks": {"ALL": {"ABSTAIN": 14, "RIGHT": 13, "WRONG_CANDIDATE": 44}, "edit": {"ABSTAIN": 2, "RIGHT": 2, "WRONG_CANDIDATE": 6}, "never_told": {"RIGHT": 4, "WRONG_CANDIDATE": 6}, "one_hop": {"ABSTAIN": 5, "RIGHT": 4, "WRONG_CANDIDATE": 7}, "partial": {"ABSTAIN": 1, "WRONG_CANDIDATE": 4}, "reversal": {"ABSTAIN": 3, "RIGHT": 2, "WRONG_CANDIDATE": 5}, "two_hop": {"ABSTAIN": 3, "RIGHT": 1, "WRONG_CANDIDATE": 7}, "yesno": {"WRONG_CANDIDATE": 9}}, "clarify_replies": 0, "confirm_rows": 0, "creative_turns": 10, "creative_turns_with_writes": 0, "day1_saved_facts": 0, "day1_saved_facts_kept_at_end": 0, "distinct_replies": 157, "facts_saved": 0, "facts_total": 131, "most_common_reply_count": 16, "ms_median": 1363.7, "ms_p90": 1379.5, "new_triples": 0, "new_triples_owner_value_unsupported": 0, "nosave_turns_with_writes": 0, "user_rows": 194}

## Arm 330a_chat: new triples with owner_value_supported=false (2 of 52)

1. [Kim, partner, Thea] <- nearest truth fact (Vaughn, fiancee, Thea)
   (same value Thea; relation fiancee ~= partner; owner differs; life e2e-dev-06 turn 13,
   confirm_answer row).
2. [Wyatt, allergy, talking] <- nearest truth facts tie: (Wyatt, pet, Slinky) and
   (Wyatt, age, 16) (same owner Wyatt; no relation or value match on either;
   life e2e-dev-08 turn 12, confirm_answer row).

## Deviations (2, both environment-only, 0 code edits)

1. The kit's `pip install -q "transformers>=5"` on the image's torch 2.4.0 made
   transformers v5 refuse torch (needs >= 2.5): the first launch failed all 5 arms in
   2-3 s each with ImportError, 0 rows written, scorer exited 1 (no files).
2. Upgrading torch 2.4.0 -> 2.14.0+cu130 then broke the old torchvision
   (RuntimeError: torchvision::nms does not exist) and torchaudio (.so load OSError):
   the second launch failed the same fast way. Upgrading torchvision to 0.29.0+cu130
   and torchaudio to match fixed it; the third launch ran 5/5 arms + scorer clean
   (walls above). No month-end file was edited anywhere.

## What it means (plain high-school English)

- The rehearsal the Windows machine could not start now runs end to end on Linux:
  5/5 arms finished, 194 user turns each, scorer lines above. This says the harness,
  the reader, and the DEV bank work together; it says nothing about the registered
  TEST-ONLY panel.
- G and 330a score identically; the creative/chat layers add saves (33 -> 49 facts)
  and 2 unsupported triples each; the twin saves nothing (0 facts) as built.

## What it doesn't mean

- It doesn't mean the agent passes anything registered: this is DEV data with
  mechanical counts only; the blind judges never ran here.
- It doesn't mean the Windows failure is fixed: the Windows blockers (Unix-only
  `resource` import, missing MiniLM snapshot) were sidestepped by renting Linux,
  not repaired.
