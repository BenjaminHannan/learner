# RESULTS-rent 0.2d-r (2026-09-26, label claude-monthend-02dr)

Registered run 0.2d-r: one arm X' on bank D with the lis-319 reader weights.
Code run, never edited. Bank D and arm rows never opened; only runner/scorer read them.

## R0 (Mac, before renting)
```
READER-SHA-MISMATCH: /Users/ben-hannan/premonition-models/lis301-merged/model.safetensors has sha256 b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890, expected e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76
```
Exit 1. Refusal confirmed; rental proceeded.

## Setup (S1-S6, rent-rt02d substitutions with this task's label/budget)
- S1 code tree: `git archive origin/builder-outbox | gzip -1 | ssh R 'mkdir -p ~/tree && tar -xz -C ~/tree'` 14:49:47Z-14:55:12Z; `git archive origin/main | gzip -1 | ssh R 'tar -xz -C ~/tree'` to 15:00:33Z. Nothing staged on the Mac. self122_head.pt scp'd from Mac checkout (sha256 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25, match).
- S2 kit C: torch 2.8.0+cu128, cuda True. pip transformers>=5 safetensors huggingface_hub accelerate numpy ok. Snapshot downloads: BASE = /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc (commit 87179e5c1f455ef22e6223592d2d61351b525bfc, matches expected); all-MiniLM-L6-v2 1110a243fdf4706b3f48f1d95db1a4f5529b4d41. route122 check returned a D8 routing (no raise).
- S3 sleep base checkpoint: `python -B scripts/fable_reasoner44.py --stage base --seed 4102 --out /tmp/r44` 13.9 s, copied to artifacts/fable-reasoner44-20260921/runs/base-seed4102.pt (sha256 1dfd95f5e6917cb5a5a73a408456555e27f4706a5bfae752cd0b0b632db63c86).
- S4 reader: DEPOT source (Director's depot REPORT.md on origin/builder-outbox, READY). `vastai copy 52755827:/root/reader319 52763487:/root/reader319` initiated 14:49:43Z; copy nested one level (flattened on rental); `/root/reader319/model.safetensors` sha256 e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76 MATCH, verified 15:01Z (~12 min incl. flatten+verify). Depot instance 52755827 only read, never stopped/changed. Mac fallback not used.
- S5 adapter: streamed BensPC -> rental through the Mac, no copy kept: adapter02c.pt sha256 a33211dc9bdb4e26bc7161b62147cb4dfc04fb605ba1aecbb26948f86e7936f5 MATCH, adapter02c.json beside it with matching adapter_sha256.
- S6 seals (from ~/tree): SEAL-code.sha256.txt 347 OK / 0 FAILED; SEAL-02dr.sha256.txt 3 OK; bankD SEAL.sha256.txt 3 OK. `claude_readersha_wrap.py --selftest` 9/9. arm_G.jsonl (481218 B) and arm_T.jsonl (231877 B) present from builder-outbox, never opened.

## Step 1 X' (registered, launched ONCE, PID 877)
First two output lines:
```
readersha: reader weights sha256 e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76 match READER_SHA
sleepcheck: logging every sleep to artifacts/claude-e2e02dr-20260926/run/sleep_X.jsonl; stop on missing checkpoint = True
```
Rows/lives written per arm: X' 816 rows, 40 lives (0.2c's X wrote 953 rows, 40 lives). Tr 658 rows, 40 lives.
Wall: X' ~15:06-15:20Z (~14 min).

## Step 2 score (registered, ~1 min, 15:22:27Z)
Scorer printed JSON lines (mechanical counts only, per arm and per ask type):
```
{"arm": "X", "asks": {"ALL": {"ABSTAIN": 99, "CONFIRM_OTHER": 27, "RIGHT": 77, "RIGHT_CONFIRM": 23, "WRONG_CANDIDATE": 18}, "edit": {"ABSTAIN": 14, "CONFIRM_OTHER": 3, "RIGHT": 4, "RIGHT_CONFIRM": 1, "WRONG_CANDIDATE": 8}, "never_told": {"CONFIRM_OTHER": 1, "RIGHT": 35}, "one_hop": {"ABSTAIN": 22, "CONFIRM_OTHER": 3, "RIGHT": 26, "RIGHT_CONFIRM": 15, "WRONG_CANDIDATE": 2}, "partial": {"ABSTAIN": 11, "CONFIRM_OTHER": 2}, "reversal": {"ABSTAIN": 28, "CONFIRM_OTHER": 3, "RIGHT": 2, "RIGHT_CONFIRM": 1, "WRONG_CANDIDATE": 1}, "two_hop": {"ABSTAIN": 18, "CONFIRM_OTHER": 9, "RIGHT": 2, "RIGHT_CONFIRM": 6, "WRONG_CANDIDATE": 4}, "yesno": {"ABSTAIN": 6, "CONFIRM_OTHER": 6, "RIGHT": 8, "WRONG_CANDIDATE": 3}}, "clarify_replies": 20, "confirm_rows": 158, "creative_turns": 36, "creative_turns_with_writes": 0, "day1_saved_facts": 160, "day1_saved_facts_kept_at_end": 158, "distinct_replies": 490, "facts_saved": 264, "facts_total": 369, "most_common_reply_count": 18, "ms_median": 955.5, "ms_p90": 1800.5, "new_triples": 276, "new_triples_owner_value_unsupported": 12, "nosave_turns_with_writes": 0, "user_rows": 658}
{"arm": "G", "asks": {"ALL": {"ABSTAIN": 109, "CONFIRM_OTHER": 41, "RIGHT": 53, "RIGHT_CONFIRM": 24, "WRONG_CANDIDATE": 17}, "edit": {"ABSTAIN": 11, "CONFIRM_OTHER": 6, "RIGHT": 3, "RIGHT_CONFIRM": 1, "WRONG_CANDIDATE": 9}, "never_told": {"CONFIRM_OTHER": 3, "RIGHT": 33}, "one_hop": {"ABSTAIN": 28, "CONFIRM_OTHER": 6, "RIGHT": 13, "RIGHT_CONFIRM": 19, "WRONG_CANDIDATE": 2}, "partial": {"ABSTAIN": 11, "CONFIRM_OTHER": 2}, "reversal": {"ABSTAIN": 30, "CONFIRM_OTHER": 2, "RIGHT_CONFIRM": 2, "WRONG_CANDIDATE": 1}, "two_hop": {"ABSTAIN": 20, "CONFIRM_OTHER": 13, "RIGHT": 1, "RIGHT_CONFIRM": 2, "WRONG_CANDIDATE": 3}, "yesno": {"ABSTAIN": 9, "CONFIRM_OTHER": 9, "RIGHT": 3, "WRONG_CANDIDATE": 2}}, "clarify_replies": 25, "confirm_rows": 202, "creative_turns": 36, "creative_turns_with_writes": 0, "day1_saved_facts": 143, "day1_saved_facts_kept_at_end": 141, "distinct_replies": 468, "facts_saved": 219, "facts_total": 369, "most_common_reply_count": 19, "ms_median": 1515.5, "ms_p90": 2491.7, "new_triples": 237, "new_triples_owner_value_unsupported": 18, "nosave_turns_with_writes": 0, "user_rows": 658}
{"arm": "T", "asks": {"ALL": {"ABSTAIN": 42, "RIGHT": 28, "WRONG_CANDIDATE": 174}, "edit": {"ABSTAIN": 8, "RIGHT": 3, "WRONG_CANDIDATE": 19}, "never_told": {"RIGHT": 12, "WRONG_CANDIDATE": 24}, "one_hop": {"ABSTAIN": 14, "RIGHT": 8, "WRONG_CANDIDATE": 46}, "partial": {"ABSTAIN": 1, "RIGHT": 1, "WRONG_CANDIDATE": 11}, "reversal": {"ABSTAIN": 8, "RIGHT": 2, "WRONG_CANDIDATE": 25}, "two_hop": {"ABSTAIN": 6, "RIGHT": 2, "WRONG_CANDIDATE": 31}, "yesno": {"ABSTAIN": 5, "WRONG_CANDIDATE": 18}}, "clarify_replies": 0, "confirm_rows": 0, "creative_turns": 36, "creative_turns_with_writes": 0, "day1_saved_facts": 0, "day1_saved_facts_kept_at_end": 0, "distinct_replies": 312, "facts_saved": 0, "facts_total": 369, "most_common_reply_count": 41, "ms_median": 906.5, "ms_p90": 1318.6, "new_triples": 0, "new_triples_owner_value_unsupported": 0, "nosave_turns_with_writes": 0, "user_rows": 658}
```
ms median/p90: X 955.5/1800.5, G 1515.5/2491.7, T 906.5/1318.6.

## Step 3 machine check Tr (REPORT-ONLY, spend $0.35 < $0.65 so run, PID 1055, ~15:23-15:29Z ~6 min; score-machine ~1 min)
Scorer printed JSON line (mechanical counts only):
```
{"arm": "Tr", "asks": {"ALL": {"ABSTAIN": 52, "RIGHT": 23, "WRONG_CANDIDATE": 169}, "edit": {"ABSTAIN": 8, "WRONG_CANDIDATE": 22}, "never_told": {"RIGHT": 13, "WRONG_CANDIDATE": 23}, "one_hop": {"ABSTAIN": 17, "RIGHT": 5, "WRONG_CANDIDATE": 46}, "partial": {"ABSTAIN": 5, "WRONG_CANDIDATE": 8}, "reversal": {"ABSTAIN": 9, "RIGHT": 2, "WRONG_CANDIDATE": 24}, "two_hop": {"ABSTAIN": 9, "RIGHT": 3, "WRONG_CANDIDATE": 27}, "yesno": {"ABSTAIN": 4, "WRONG_CANDIDATE": 19}}, "clarify_replies": 0, "confirm_rows": 0, "creative_turns": 36, "creative_turns_with_writes": 0, "day1_saved_facts": 0, "day1_saved_facts_kept_at_end": 0, "distinct_replies": 311, "facts_saved": 0, "facts_total": 369, "most_common_reply_count": 38, "ms_median": 473.2, "ms_p90": 718.5, "new_triples": 0, "new_triples_owner_value_unsupported": 0, "nosave_turns_with_writes": 0, "user_rows": 658}
```
ms median/p90: Tr 473.2/718.5.
Raw Tr-vs-0.2c-T RIGHT diffs per ask type (for VERIFY-02dr's addendum-3 rule; no verdict claimed here): never_told 13 vs 12 (diff 1); edit 0 vs 3 (diff 3); ALL 23 vs 28 (diff 5); one_hop 5 vs 8 (diff 3); partial 0 vs 1 (diff 1); reversal 2 vs 2 (diff 0); two_hop 3 vs 2 (diff 1); yesno 0 vs 0 (diff 0).
Tr scored on its own in score-machine/, never mixed into the registered score.

## Rental/money
GPU NVIDIA GeForce RTX 5090. Instance 52763487 (offer 49024471, image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime, disk 80). Rented 14:42:02Z, destroyed ~15:33:30Z: 0.86 h x dph $0.5037 = ~$0.43 of $0.80 budget (1 rental of max 4). Credit at gate 7.88. Post-destroy 0 claude-monthend-02dr live (confirmed via `vastai show instances`). Copy-back 24 files sha256-verified identical both ends before destroy. No weights pushed.

## Deviations (all minor except noted)
1. X' wrote 816 rows vs 0.2c X's 953 rows (40 lives both) - reported, unexplained.
2. ep382_X.jsonl never written (EP382_LOG set, wrapper produced no file).
3. sleep_Tr.jsonl never written (SLEEPCHECK_LOG set, twin produced no file).
4. SSH launch commands timed out client-side (60-120 s) while the server-side process started; each registered process launched ONCE (ps checked empty before every launch; PIDs 877, 1010-score, 1055).
5. vastai copy nested the reader one level (/root/reader319/reader319); flattened on rental, sha re-verified MATCH.
6. Actual dph $0.5037 vs offer-list estimate $0.469 (billing incl. storage).
7. No code edits, no TEST-ONLY panel opened, no judge/arm/bank rows opened, no reply quoted.
