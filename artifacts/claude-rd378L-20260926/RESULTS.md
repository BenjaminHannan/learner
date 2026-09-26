# rd-378L RESULTS (lane W, retry of rent-rd378L) — 2026-09-26

Lane W verdict: PASS (L1, L2, L3 all pass; proved-wrong clause not triggered).
Development measurement on LoCoMo PRACTICE, label "after using LoCoMo for development". Counts and turn positions only; no question, answer, turn or note text.

## Marks (fused mode, questions of categories 1-4, n=759)

| Mark | Bar | A | B | Diff (points) | Result |
|---|---|---|---|---|---|
| L1 | B any@10 >= A + 5 | 496/759 = 65.3% | 583/759 = 76.8% | +11.5 | PASS |
| L2 | no category 1-4 more than 3 below A on any@10 | — | c1 +17.7, c2 +5.8, c3 +18.2, c4 +10.8 | worst +5.8 | PASS |
| L3 | B anyT@10 >= A anyT@10 + 5 | 496/759 = 65.3% | 577/759 = 76.0% | +10.7 | PASS |
| proved-wrong | B any@10 <= A + 1 | — | 76.8% vs 66.3% | — | not proved wrong |
| proved-wrong (anyT) | B anyT@10 <= A anyT@10 + 1 | — | 76.0% vs 66.3% | — | not proved wrong |

## Full fused tables per category (count / questions, percent to one decimal)

Store A (heard only):

| cat | n | any@5 | any@10 | any@20 | all@10 | anyT@10 | bm25 any@10 | bm25 anyT@10 | turns@10 (mean) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 141 | 61 (43.3%) | 77 (54.6%) | 96 (68.1%) | 19 (13.5%) | 77 (54.6%) | 59 (41.8%) | 59 (41.8%) | 1410 (10.00) |
| 2 | 156 | 109 (69.9%) | 125 (80.1%) | 135 (86.5%) | 118 (75.6%) | 125 (80.1%) | 112 (71.8%) | 112 (71.8%) | 1560 (10.00) |
| 3 | 44 | 12 (27.3%) | 16 (36.4%) | 24 (54.5%) | 9 (20.5%) | 16 (36.4%) | 15 (34.1%) | 15 (34.1%) | 440 (10.00) |
| 4 | 418 | 241 (57.7%) | 278 (66.5%) | 318 (76.1%) | 272 (65.1%) | 278 (66.5%) | 253 (60.5%) | 253 (60.5%) | 4180 (10.00) |
| 1-4 | 759 | 423 (55.7%) | 496 (65.3%) | 573 (75.5%) | 418 (55.1%) | 496 (65.3%) | 439 (57.8%) | 439 (57.8%) | 7590 (10.00) |

Store B (heard + fact notes):

| cat | n | any@5 | any@10 | any@20 | all@10 | anyT@10 | bm25 any@10 | bm25 anyT@10 | turns@10 (mean) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 141 | 78 (55.3%) | 102 (72.3%) | 120 (85.1%) | 24 (17.0%) | 101 (71.6%) | 78 (55.3%) | 77 (54.6%) | 1482 (10.51) |
| 2 | 156 | 124 (79.5%) | 134 (85.9%) | 143 (91.7%) | 127 (81.4%) | 134 (85.9%) | 120 (76.9%) | 121 (77.6%) | 1549 (9.93) |
| 3 | 44 | 19 (43.2%) | 24 (54.5%) | 28 (63.6%) | 13 (29.5%) | 24 (54.5%) | 14 (31.8%) | 15 (34.1%) | 431 (9.80) |
| 4 | 418 | 277 (66.3%) | 323 (77.3%) | 350 (83.7%) | 318 (76.1%) | 318 (76.1%) | 303 (72.5%) | 303 (72.5%) | 4104 (9.82) |
| 1-4 | 759 | 498 (65.6%) | 583 (76.8%) | 641 (84.5%) | 482 (63.5%) | 577 (76.0%) | 515 (67.9%) | 516 (68.0%) | 7566 (9.97) |

Mean fused turns@10: A 10.00, B 9.97.

## Notes

- turns: 2760, notes: 2556 (0.926/turn), unparsed: 33.
- write ms (ms field of notes.jsonl, 2760 rows): median 346.2, p90 635.2.
- rows with no note (empty or unparsed): 898.

## Writer

- Route: rebuild on the rental from the BensPC adapter (no fallback needed).
- Adapter: streamed BensPC C:/Users/benja/rd378/tree/WORK/nrun/adapter -> rental ~/w/adapter through the Mac, no Mac copy kept; sha256 matched BensPC file for file (adapter_config.json 7043dc9d…, adapter_model.safetensors 7742e6b3…, chat_template.jinja d8db3ff4…, README.md 9255a264…, tokenizer.json 3e065a55…, tokenizer_config.json 5b46a8a8…).
- Merged model.safetensors sha256: dbcc8db5a5840d839fe049f720bdfeacf094deb78f2652984c28c53f8c388510 (matches the registered writer hash).

## JSON lines

- W1: {"sha256": "dbcc8db5a5840d839fe049f720bdfeacf094deb78f2652984c28c53f8c388510", "match": true, "torch": "2.11.0+cu128", "transformers": "5.17.0", "peft": "0.21.0", "gpu": "NVIDIA GeForce RTX 5090"}
- W2: wrote notes for 2760 turns on cuda
- W3: {"notes": {"turns": 2760, "unparsed": 33, "notes": 2556}, "A:1-4": {"questions": 759, "fused_any@5": 423, "fused_any@10": 496, "fused_any@20": 573, "fused_all@5": 348, "fused_all@10": 418, "fused_all@20": 479, "fused_anyT@5": 423, "fused_anyT@10": 496, "fused_anyT@20": 573, "fused_turns@5": 3795, "fused_turns@10": 7590, "fused_turns@20": 15180, "bm25_any@5": 377, "bm25_any@10": 439, "bm25_any@20": 509, "bm25_all@5": 316, "bm25_all@10": 364, "bm25_all@20": 430, "bm25_anyT@5": 377, "bm25_anyT@10": 439, "bm25_anyT@20": 509, "bm25_turns@5": 3795, "bm25_turns@10": 7590, "bm25_turns@20": 15180}, "B:1-4": {"questions": 759, "fused_any@5": 498, "fused_any@10": 583, "fused_any@20": 641, "fused_all@5": 415, "fused_all@10": 482, "fused_all@20": 542, "fused_anyT@5": 495, "fused_anyT@10": 577, "fused_anyT@20": 639, "fused_turns@5": 3848, "fused_turns@10": 7566, "fused_turns@20": 14817, "bm25_any@5": 440, "bm25_any@10": 515, "bm25_any@20": 564, "bm25_all@5": 369, "bm25_all@10": 426, "bm25_all@20": 475, "bm25_anyT@5": 437, "bm25_anyT@10": 516, "bm25_anyT@20": 569, "bm25_turns@5": 3642, "bm25_turns@10": 7243, "bm25_turns@20": 14386}}

## Provenance

- COMMIT: cd91474c676364c3e4d0ccfa6faf2542d447eb1c
- Import check: 2.11.0+cu128 5.17.0 0.21.0 NVIDIA GeForce RTX 5090 torchvision None
- Seals: SEAL-E 14/14 OK, SEAL-D 13/13 OK, SEAL-C 4/4 OK. Selftests: RD378L-SELFTEST PASS, RD379Q-SELFTEST PASS, RD379Q-V3-SELFTEST PASS, RD378L-REBUILD-SELFTEST PASS.
- DATA: locomo10.json sha256 79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4 (MMLU part of fetch failed without pyarrow, as expected; irrelevant). dialogs: {"turns": 2760}.
- GPU: NVIDIA GeForce RTX 5090. Instance id: 52770443 (label claude-notes-rd378Lb, shared with lane Q).
- Hours: ~0.93 (created 15:30 UTC, destroyed ~16:26 UTC 2026-09-26). dph: $0.5037. Dollars (whole task, both lanes, one rental): ~$0.47.
- Budget: $1.30; spent ~$0.47. No BUDGET-STOP. Rentals used: 1 of 4.
- Wall time per step (UTC 2026-09-26, approx): boot 15:30-15:33; TREE+ADAPTER ~15:33-15:35; SETUP ~15:35-15:38; import check + downloads ~15:38-15:43; seals + selftests ~15:43-15:44; fetch + dialogs ~15:44-15:46; W1 rebuild ~15:46-15:48; W2 write ~15:48-16:05 (~17 min); W3 score ~16:09-16:12; copyback + destroy ~16:23-16:26.

## File hashes (rental = Mac)

- notes_recall.json: 074225fb03d536e978a3e7a1efc5a693d63de3e9e4fea23a91b40e07563eecd4
- ranked_turns.jsonl: 2792906c947485d6042cbc37a8e84c4987094c4f3b3c94c3298934a2154d97d4
- private (never pushed): b_dialogs.jsonl 82b56b44…, notes.jsonl 6d31c19f…, notes_recall_per_question.jsonl 0341d1dc… (first try's dialogs.jsonl kept; new dialogs saved with b_ prefix)
