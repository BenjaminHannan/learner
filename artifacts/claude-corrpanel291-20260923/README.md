# corrpanel291 — blind panel for exp 291 (TEST-ONLY, category level only)

No items are quoted in this file.

Folder: `artifacts/claude-corrpanel291-20260923/`
Files: `panel.jsonl` (96), `base138nb.jsonl` (96, same ids/order),
`make_panel.py`, `run_base.py`, `score_panel.py`, `README.md`, `SEAL.sha256.txt`.

Base: 138nb = `scripts/claude_loop138nb_agent.py` with
`artifacts/claude-merge138nb-20260923/loop138nb-config.json`
(copies already identical to `origin/builder-outbox`; loop build,
fresh work dir per dialog, setup then turn then followup in one session).
CPU only, one process at a time.

Panel fields (10): id, family, setup, turn, followup, stated_facts,
expect_gone, expect_store, gold_followup, note.
Base fields (10): id, setup_replies, stored_after_setup, turn_reply,
stored_after_turn, followup_reply, stored_after_followup,
base_right, base_wrong_value, base_false_claim.

Scoring (same in `run_base.py` and `score_panel.py`, triples
case-insensitive): store_ok = expect_store subset of stored_after_turn
and no expect_gone present and no junk writes; followup_ok = gold parts
present (or no gone-value when gold null); wrong_value = gone value in
followup (whole word); followup_write = stored_after_followup differs;
false_claim = a still-stored value appears in turn_reply together with
a removal/change claim (don't have / do not have / removed / updated /
deleted / changed). right = store_ok and followup_ok and no followup
write and not false_claim. Control additionally requires byte-identical
replies to the sealed base file (checked by the scorer when the sealed
base is present).

Families (96 total): verb_denial 8, possessive_denial 8,
contextual_denial 8, contextual_correction 8, explicit_correction 8,
tail_denial 8, opener_teach 8, opener_correction 8,
unstored_denial 6, ambiguous 6, question_trap 8, control 12.
Relations cover 10 distinct relations. Cause families each contain at
least 2 fully-lowercase turns and a majority of novel wordings.
All names are fictional, 1-4 words, written by hand.

Base 138nb results per family (right / wrong_value / false_claim / junk):
- verb_denial: 0 / 8 / 0 / 0
- possessive_denial: 2 / 6 / 1 / 0
- contextual_denial: 0 / 8 / 0 / 0
- contextual_correction: 0 / 8 / 0 / 0
- explicit_correction: 0 / 5 / 0 / 2
- tail_denial: 0 / 6 / 3 / 0
- opener_teach: 0 / 0 / 0 / 7
- opener_correction: 0 / 7 / 0 / 0
- unstored_denial: 6 / 0 / 0 / 0
- ambiguous: 6 / 0 / 0 / 0
- question_trap: 8 / 0 / 0 / 0
- control: 12 / 0 / 0 / 0
- TOTAL: 34 / 48 / 4 / 9, followup writes 0.

Acceptance: stated_facts equals stored_after_setup on all 96 items;
contextual items show exactly one stored value in the last setup reply
(16/16); ambiguous items show 2+ values or no stated fact (6/6);
control 12/12 base_right true. Cause families were not filtered by base
result; figures above are reported as observed.
