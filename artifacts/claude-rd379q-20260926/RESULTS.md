# rd-379q RESULTS (lane Q, question notes) — 2026-09-26

Lane Q verdict: FAIL (Q1, Q2, Q3 all fail; proved-wrong clause holds: question notes score below heard-only).
Development measurement on LoCoMo PRACTICE, label "after using LoCoMo for development". Counts and turn positions only; no LoCoMo question, answer, turn or note text. (Smoke dialogs are made up; their outputs are shown.)
Sanity: store A's counts equal rd-378L's A exactly (all categories, all modes) — the run is comparable with rd-378L's B.

## Marks (fused mode, questions of categories 1-4, n=759; "B" in notes_recall.json is Q)

| Mark | Bar | A | Q | Diff (points) | Result |
|---|---|---|---|---|---|
| Q1 | Q any@10 >= A + 5 | 496/759 = 65.3% | 431/759 = 56.8% | -8.5 | FAIL |
| Q2 | no category 1-4 more than 3 below A on any@10 | — | c1 -7.1, c2 -16.7, c3 -6.8, c4 -6.2 | worst -16.7 | FAIL |
| Q3 | Q anyT@10 >= A anyT@10 + 5 | 496/759 = 65.3% | 437/759 = 57.6% | -7.7 | FAIL |
| proved-wrong | Q any@10 <= A + 1 | — | 56.8% vs 66.3% | — | proved wrong holds |
| proved-wrong (anyT) | Q anyT@10 <= A anyT@10 + 1 | — | 57.6% vs 66.3% | — | proved wrong holds |

Next per the registered rules (Q fails): if rd-378L passes, run 4b (cut-only fact writer); rd-378L's lane W passed, so 4b is planned.

## Full fused tables per category (count / questions, percent to one decimal)

Store A (heard only — identical to rd-378L's A):

| cat | n | any@5 | any@10 | any@20 | all@10 | anyT@10 | bm25 any@10 | bm25 anyT@10 | turns@10 (mean) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 141 | 61 (43.3%) | 77 (54.6%) | 96 (68.1%) | 19 (13.5%) | 77 (54.6%) | 59 (41.8%) | 59 (41.8%) | 1410 (10.00) |
| 2 | 156 | 109 (69.9%) | 125 (80.1%) | 135 (86.5%) | 118 (75.6%) | 125 (80.1%) | 112 (71.8%) | 112 (71.8%) | 1560 (10.00) |
| 3 | 44 | 12 (27.3%) | 16 (36.4%) | 24 (54.5%) | 9 (20.5%) | 16 (36.4%) | 15 (34.1%) | 15 (34.1%) | 440 (10.00) |
| 4 | 418 | 241 (57.7%) | 278 (66.5%) | 318 (76.1%) | 272 (65.1%) | 278 (66.5%) | 253 (60.5%) | 253 (60.5%) | 4180 (10.00) |
| 1-4 | 759 | 423 (55.7%) | 496 (65.3%) | 573 (75.5%) | 418 (55.1%) | 496 (65.3%) | 439 (57.8%) | 439 (57.8%) | 7590 (10.00) |

Store Q (heard + question notes):

| cat | n | any@5 | any@10 | any@20 | all@10 | anyT@10 | bm25 any@10 | bm25 anyT@10 | turns@10 (mean) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 141 | 50 (35.5%) | 67 (47.5%) | 92 (65.2%) | 7 (5.0%) | 68 (48.2%) | 50 (35.5%) | 51 (36.2%) | 1298 (9.21) |
| 2 | 156 | 77 (49.4%) | 99 (63.5%) | 119 (76.3%) | 92 (59.0%) | 100 (64.1%) | 92 (59.0%) | 92 (59.0%) | 1423 (9.12) |
| 3 | 44 | 10 (22.7%) | 13 (29.5%) | 24 (54.5%) | 4 (9.1%) | 14 (31.8%) | 13 (29.5%) | 13 (29.5%) | 393 (8.93) |
| 4 | 418 | 195 (46.7%) | 252 (60.3%) | 305 (73.0%) | 247 (59.1%) | 255 (61.0%) | 231 (55.3%) | 237 (56.7%) | 3738 (8.94) |
| 1-4 | 759 | 332 (43.7%) | 431 (56.8%) | 540 (71.1%) | 350 (46.1%) | 437 (57.6%) | 386 (50.9%) | 393 (51.8%) | 6852 (9.03) |

Mean fused turns@10: A 10.00, Q 9.03.

## Questions

- turns: 2760, questions written: 8265 (2.995/turn), unparsed: 0.
- turns with no question (empty notes list): 1.
- write ms (ms field of q_notes.jsonl, 2760 rows): median 358.8, p90 513.5.

## Smoke (fictional dialogs, 4 rows — questions and ms)

- t0, ms 3945.8: "What did you enjoy most about moving to Oakvale last weekend?" / "How did you feel about the new environment?" / "What did you do to make the transition smoother?"
- t1, ms 450.6: "What is the name of the beagle named Pip?" / "How long has the beagle Pip been a pet?" / "What is the name of the person who adopted Pip?"
- t2, ms 798.6: "What is the name of the beagle named Pip?" / "How did you decide to adopt a beagle named Pip?" / "What is the name of the library where you are starting your new job?"
- t3, ms 795.3: "What did you learn about moving to Oakvale last weekend?" / "Did you adopt a beagle named Pip?" / "How did you start your job at the Oakvale library?"
- All 4 rows have questions: smoke PASS.

## JSON lines

- Q1: wrote questions for 4 turns
- Q2: wrote questions for 2760 turns
- Q3: {"notes": {"turns": 2760, "unparsed": 0, "notes": 8265}, "A:1-4": {"questions": 759, "fused_any@5": 423, "fused_any@10": 496, "fused_any@20": 573, "fused_all@5": 348, "fused_all@10": 418, "fused_all@20": 479, "fused_anyT@5": 423, "fused_anyT@10": 496, "fused_anyT@20": 573, "fused_turns@5": 3795, "fused_turns@10": 7590, "fused_turns@20": 15180, "bm25_any@5": 377, "bm25_any@10": 439, "bm25_any@20": 509, "bm25_all@5": 316, "bm25_all@10": 364, "bm25_all@20": 430, "bm25_anyT@5": 377, "bm25_anyT@10": 439, "bm25_anyT@20": 509, "bm25_turns@5": 3795, "bm25_turns@10": 7590, "bm25_turns@20": 15180}, "B:1-4": {"questions": 759, "fused_any@5": 332, "fused_any@10": 431, "fused_any@20": 540, "fused_all@5": 273, "fused_all@10": 350, "fused_all@20": 442, "fused_anyT@5": 344, "fused_anyT@10": 437, "fused_anyT@20": 562, "fused_turns@5": 3550, "fused_turns@10": 6852, "fused_turns@20": 13279, "bm25_any@5": 304, "bm25_any@10": 386, "bm25_any@20": 485, "bm25_all@5": 252, "bm25_all@10": 323, "bm25_all@20": 405, "bm25_anyT@5": 309, "bm25_anyT@10": 393, "bm25_anyT@20": 491, "bm25_turns@5": 3644, "bm25_turns@10": 7140, "bm25_turns@20": 13962}}
- Q4 (v3 rescore of question notes): {"notes": {"turns": 2760, "unparsed": 0, "notes": 8265}, "A:1-4": {"questions": 759, "fused_any@5": 440, "fused_any@10": 520, "fused_any@20": 584, "fused_all@5": 365, "fused_all@10": 437, "fused_all@20": 491, "fused_anyT@5": 440, "fused_anyT@10": 520, "fused_anyT@20": 584, "fused_turns@5": 3795, "fused_turns@10": 7590, "fused_turns@20": 15180, "bm25_any@5": 377, "bm25_any@10": 442, "bm25_any@20": 508, "bm25_all@5": 316, "bm25_all@10": 366, "bm25_all@20": 429, "bm25_anyT@5": 377, "bm25_anyT@10": 442, "bm25_anyT@20": 508, "bm25_turns@5": 3795, "bm25_turns@10": 7590, "bm25_turns@20": 15180}, "B:1-4": {"questions": 759, "fused_any@5": 363, "fused_any@10": 468, "fused_any@20": 561, "fused_all@5": 294, "fused_all@10": 385, "fused_all@20": 459, "fused_anyT@5": 374, "fused_anyT@10": 482, "fused_anyT@20": 582, "fused_turns@5": 3519, "fused_turns@10": 6816, "fused_turns@20": 13158, "bm25_any@5": 311, "bm25_any@10": 395, "bm25_any@20": 488, "bm25_all@5": 258, "bm25_all@10": 330, "bm25_all@20": 405, "bm25_anyT@5": 314, "bm25_anyT@10": 399, "bm25_anyT@20": 493, "bm25_turns@5": 3641, "bm25_turns@10": 7128, "bm25_turns@20": 13943}}
- Q4 (v3 rescore of fact notes): {"notes": {"turns": 2760, "unparsed": 33, "notes": 2556}, "A:1-4": {"questions": 759, "fused_any@5": 440, "fused_any@10": 520, "fused_any@20": 584, "fused_all@5": 365, "fused_all@10": 437, "fused_all@20": 491, "fused_anyT@5": 440, "fused_anyT@10": 520, "fused_anyT@20": 584, "fused_turns@5": 3795, "fused_turns@10": 7590, "fused_turns@20": 15180, "bm25_any@5": 377, "bm25_any@10": 442, "bm25_any@20": 508, "bm25_all@5": 316, "bm25_all@10": 366, "bm25_all@20": 429, "bm25_anyT@5": 377, "bm25_anyT@10": 442, "bm25_anyT@20": 508, "bm25_turns@5": 3795, "bm25_turns@10": 7590, "bm25_turns@20": 15180}, "B:1-4": {"questions": 759, "fused_any@5": 511, "fused_any@10": 578, "fused_any@20": 650, "fused_all@5": 426, "fused_all@10": 481, "fused_all@20": 554, "fused_anyT@5": 507, "fused_anyT@10": 581, "fused_anyT@20": 649, "fused_turns@5": 3721, "fused_turns@10": 7247, "fused_turns@20": 14263, "bm25_any@5": 441, "bm25_any@10": 515, "bm25_any@20": 567, "bm25_all@5": 369, "bm25_all@10": 427, "bm25_all@20": 477, "bm25_anyT@5": 438, "bm25_anyT@10": 520, "bm25_anyT@20": 571, "bm25_turns@5": 3628, "bm25_turns@10": 7217, "bm25_turns@20": 14333}}

## Report-only v3 rescore (fused; overall and per category)

| store | any@10 overall | anyT@10 overall | c1 any@10 / anyT@10 | c2 any@10 / anyT@10 | c3 any@10 / anyT@10 | c4 any@10 / anyT@10 |
|---|---|---|---|---|---|---|
| v3 A (heard) | 520/759 = 68.5% | 520/759 = 68.5% | 83 (58.9%) / 83 (58.9%) | 127 (81.4%) / 127 (81.4%) | 18 (40.9%) / 18 (40.9%) | 292 (69.9%) / 292 (69.9%) |
| v3 Q (questions) | 468/759 = 61.7% | 482/759 = 63.5% | 70 (49.6%) / 73 (51.8%) | 114 (73.1%) / 116 (74.4%) | 18 (40.9%) / 19 (43.2%) | 266 (63.6%) / 274 (65.6%) |
| v3 fact-notes B | 578/759 = 76.2% | 581/759 = 76.5% | 98 (69.5%) / 98 (69.5%) | 134 (85.9%) / 135 (86.5%) | 22 (50.0%) / 24 (54.5%) | 324 (77.5%) / 324 (77.5%) |

Reading: on v3, Q anyT@10 (482) is below v3 A + 2 (522), and Q failed on v1 anyway; fact notes hold their gain on v3 (B anyT@10 581 vs A 520, +8.0 points).

## Q next to rd-378L's B (fused any@10 overall)

- A heard-only: 496/759 = 65.3%
- Q question notes: 431/759 = 56.8%
- B fact notes: 583/759 = 76.8%

## Provenance

- COMMIT: cd91474c676364c3e4d0ccfa6faf2542d447eb1c
- Import check: 2.11.0+cu128 5.17.0 0.21.0 NVIDIA GeForce RTX 5090 torchvision None
- Seals: SEAL-B 13/13 OK, SEAL 9/9 OK (plus SEAL-E/D/C for the shared scorer). Selftests: RD378L-SELFTEST PASS, RD379Q-SELFTEST PASS, RD379Q-V3-SELFTEST PASS, RD378L-REBUILD-SELFTEST PASS.
- DATA: locomo10.json sha256 79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4. dialogs: {"turns": 2760}.
- GPU: NVIDIA GeForce RTX 5090. Instance id: 52770443 (label claude-notes-rd378Lb, shared with lane W).
- Hours: ~0.93 (shared rental). dph: $0.5037. (Shared-rental dollar total is in the rd-378L file: ~$0.47.)
- Wall time per step (UTC 2026-09-26, approx): Q1 smoke ~15:48 (~1 min); Q2 write ~15:50-16:09 (~19 min); Q3 score ~16:14-16:18; Q4 rescores ~16:19-16:23.

## File hashes (rental = Mac)

- notes_recall.json: e1646215492c75103b65cc14e6f5f02f8055b1f72f23648e7d4d09bc286e2b17
- ranked_turns.jsonl: b4fb1379e3a32bbeced9b0e28e25c628e7990254b1181b7dfae89f44fc4ef467
- notes_recall_v3.json: 6aa57f772d525dbdbc6ef87a86c84533f6eded0d0745ac56763a5728f034e5bc
- notes_recall_v3_facts.json: 498793b7be97e1fb3d14085e7e084e931f4d31c450dc45429a2652ca18a4bcec
- private (never pushed): q_notes.jsonl b45ee32c…, notes_recall_per_question.jsonl b22f803b…, notes_recall_per_question_v3.jsonl 0cb3a1a2…, notes_recall_per_question_v3_facts.jsonl 050725f7…, smoke_q.jsonl a03ff76e…
