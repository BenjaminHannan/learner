# rd-378u RESULTS (2026-09-26, Trustworthy notes thread)

Registered question: does the notes gain hold on the five unseen LoCoMo chats
(5-9), through the store the build would use (store v4 recall() defaults)?
Verdict: PASS (U1 and U2 pass; proved-wrong clause not triggered).

Counts only. No LoCoMo question, answer, turn or note text is quoted anywhere
in this file.

## Marks (any@10, categories 1-4, n=772)

| Mark | Bar | A | B | Diff (points) | Result |
|---|---|---|---|---|---|
| U1 | B any@10 >= A any@10 + 5 | 489 (63.3%) | 585 (75.8%) | +12.4 | PASS |
| U2 | no category 1-4 more than 3 points below A | -- | c1 +7.9, c2 +10.4, c3 +22.2, c4 +13.7 | worst +7.9 | PASS |
| proved-wrong | B any@10 <= A + 1 point | 63.3% (+1 = 64.3%) | 75.8% | -- | not triggered |

## Full A table per category (any@5 / any@10 / any@20; all@5 / all@10 / all@20)

| Arm | Cat | questions | any@5 | any@10 | any@20 | all@5 | all@10 | all@20 |
|---|---|---|---|---|---|---|---|---|
| A | 1 | 140 | 67 (47.9%) | 85 (60.7%) | 102 (72.9%) | 10 (7.1%) | 17 (12.1%) | 22 (15.7%) |
| A | 2 | 164 | 94 (57.3%) | 109 (66.5%) | 117 (71.3%) | 80 (48.8%) | 93 (56.7%) | 106 (64.6%) |
| A | 3 | 45 | 16 (35.6%) | 18 (40.0%) | 27 (60.0%) | 9 (20.0%) | 10 (22.2%) | 15 (33.3%) |
| A | 4 | 423 | 233 (55.1%) | 277 (65.5%) | 323 (76.4%) | 221 (52.2%) | 265 (62.6%) | 312 (73.8%) |
| A | 1-4 | 772 | 410 (53.1%) | 489 (63.3%) | 569 (73.7%) | 320 (41.5%) | 385 (49.9%) | 455 (58.9%) |

## Full B table per category

| Arm | Cat | questions | any@5 | any@10 | any@20 | all@5 | all@10 | all@20 |
|---|---|---|---|---|---|---|---|---|
| B | 1 | 140 | 79 (56.4%) | 96 (68.6%) | 109 (77.9%) | 13 (9.3%) | 24 (17.1%) | 30 (21.4%) |
| B | 2 | 164 | 112 (68.3%) | 126 (76.8%) | 136 (82.9%) | 97 (59.1%) | 113 (68.9%) | 120 (73.2%) |
| B | 3 | 45 | 22 (48.9%) | 28 (62.2%) | 29 (64.4%) | 13 (28.9%) | 15 (33.3%) | 17 (37.8%) |
| B | 4 | 423 | 300 (70.9%) | 335 (79.2%) | 372 (87.9%) | 286 (67.6%) | 326 (77.1%) | 367 (86.8%) |
| B | 1-4 | 772 | 513 (66.5%) | 585 (75.8%) | 646 (83.7%) | 409 (53.0%) | 478 (61.9%) | 534 (69.2%) |

## Lines shown and lines reached through a note (@10)

| Arm | lines@10 | via_note@10 |
|---|---|---|
| A:1-4 | 7720 | 0 |
| B:1-4 | 7720 | 6297 |
| A:1 | 1400 | 0 |
| B:1 | 1400 | 1142 |
| A:2 | 1640 | 0 |
| B:2 | 1640 | 1422 |
| A:3 | 450 | 0 |
| B:3 | 450 | 353 |
| A:4 | 4230 | 0 |
| B:4 | 4230 | 3380 |

Both arms show the same number of lines (raw lines only, one per turn), as
designed. 6297 of B's 7720 shown lines were reached through a note.

## Notes / turns / unparsed

- dialogs convs 5-9 turns: 3122
- notes written: 2866 (0.918 notes per turn)
- unparsed turns: 16
- notes59.jsonl rows: 3122, line-unparsed: 0

## Write timing (notes59.jsonl "ms" field, ms)

- median: 319.2
- p90: 595.8
- min: 53.7
- max: 1138.4

## Step JSON lines (verbatim)

- step 5 dialogs: {"turns": 3122}
- step 6 writer: {"sha256": "dbcc8db5a5840d839fe049f720bdfeacf094deb78f2652984c28c53f8c388510", "match": true, "torch": "2.11.0+cu128", "transformers": "5.17.0", "peft": "0.21.0", "gpu": "NVIDIA GeForce RTX 5090"}
- step 8 score: {"notes": {"turns": 3122, "unparsed": 16, "notes": 2866}, "A:1-4": {"questions": 772, "any@5": 410, "any@10": 489, "any@20": 569, "all@5": 320, "all@10": 385, "all@20": 455, "lines@10": 7720, "via_note@10": 0}, "B:1-4": {"questions": 772, "any@5": 513, "any@10": 585, "any@20": 646, "all@5": 409, "all@10": 478, "all@20": 534, "lines@10": 7720, "via_note@10": 6297}}

## Environment

- import-check line: 2.11.0+cu128 5.17.0 0.21.0 NVIDIA GeForce RTX 5090 torchvision None
- COMMIT: c4f1bfca91fec9c299e18b10c0fd501ce54bb56b
- BASE: /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
- MiniLM path: /root/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41 (exact match)
- writer route: rebuild on the rental (adapter streamed BensPC -> rental through the Mac, no Mac copy kept; rental sha256sum matched BensPC file for file); merged model.safetensors sha256 dbcc8db5a5840d839fe049f720bdfeacf094deb78f2652984c28c53f8c388510 (exit 0, match true). Mac fallback not used.
- SEAL.sha256.txt: 13/13 OK
- selftests: RD378U-SELFTEST PASS, EP382-V4-SELFTEST PASS, RD378L-SELFTEST PASS, RD378L-REBUILD-SELFTEST PASS
- DATA: fetch MMLU/GSM8K part failed without pyarrow (does not matter); DATA/locomo10.json sha256 79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4 (match)

## Money and machine

- GPU: NVIDIA GeForce RTX 5090
- instance id: 52779987 (label claude-notes-rd378u); rentals used: 1 of 3
- window: 2026-09-26 16:38:31Z (create) to 17:24:54Z (destroyed, confirmed gone) = 0.773h
- dph: 0.5037; dollars: ~$0.39 of $0.80 budget (kill line $0.72 never reached)
- credit balance number at gate: 7.912477276269769

## Wall time per step (UTC 2026-09-26)

- rent create -> running: 16:38:31 -> ~16:41 (~2.5 min)
- TREE: 16:41:15 -> 16:41:27 (~0.2 min)
- ADAPTER: 16:41:49 -> 16:43:35 (~1.8 min, 6 files, ~100 MB)
- SETUP (torch 2.11.0 cu128 + uninstall torchvision/torchaudio + transformers/peft/etc): 16:43:44 -> ~16:46 (~2.5 min)
- import check + HF downloads: ~16:47 -> 16:48 (~1 min + ~27 s MiniCPM + ~3 s MiniLM cached path)
- SEALS + 4 selftests: ~16:48 -> 16:54
- DATA fetch + dialogs 5-9: ~16:50 -> 16:54 (fetch log) + dialogs line
- WRITER rebuild: 16:54:50 -> ~16:56 (~1.5 min)
- WRITE: 16:57:02 -> 17:13:28 (~16.4 min, 3122 turns)
- SCORE: 17:17:16 -> 17:20:01 (~2.7 min)
- copy back (5 files, sha256 verified both ends) + destroy + confirm: 17:20 -> 17:24:54

## Copy-back hashes (rental and Mac identical, checked BEFORE destroy)

- notes_confirm.json: 106168baa6fe68743317a305e08d3dd6d3935b81f791fd29d841ec7fa0cbd029
- ranked_turns.jsonl (1544 lines, turn positions only): 785c9c9adf26071b83716d53465c03663e96f99a517348f4a98f03b792d9ff5e
- dialogs59.jsonl (kept in ~/rd378u-private/, outside git): 1e5d4d3d0a98d8fe4753c90926374debb8efc0f15a927a6297ffe785c80ec109
- notes59.jsonl (kept in ~/rd378u-private/, outside git): 62d09febf987939db43fc45053f790b90bd7dd522eedd6644176cca602679854
- per_question.jsonl (1544 lines, kept in ~/rd378u-private/, outside git): 17b38f33912063b5ac818fff9d319551b9f4805e36cfdfa2d4ed1ade2bd05f8e

## What this means (plain reading, counts only)

On five chats no notes decision had used, the notes arm found an evidence
line in the top 10 for 96 more questions out of 772 than the heard-only arm
(585 vs 489), with the same number of lines shown, and gained in every
category (smallest gain +7.9 points in category 1). The proved-wrong bar
(B at most A + 1 point) is far from met. Per PASSMARKS.md this is a PASS:
store v4 is offered to Month-end for the joined build with these numbers.
