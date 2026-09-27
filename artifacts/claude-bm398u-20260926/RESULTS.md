# bm-398u RESULTS: the plain 1B reranks its lines before answering (benchmarks thread, written 2026-09-27 00:24 UTC)

**Verdict on the registered claim: PASS.** Given the same number of lines (3), the plain 1B answered right more often
when it picked the lines itself (BU, 236 of 759, blind) than when it took store B's own top 3 (BF, 207). That is
+29 right answers, 86 gained and 57 lost (two-sided exact McNemar p = 0.019), with no rise in wrong answers and no
category hurt.

**Against today's store: FAIL.** The same 1B answering from all 20 of store B's lines (BN) got 264. BU is 28 below it
(72 gained, 100 lost, p = 0.039), and wrong answers are 21 higher. So the reranker picks better lines than the
store's order, but keeping only 3 lines loses more than it gains. It is not a better memory path than today's.

Registered and sealed before any BF or BU reply existed (PLAN.md, DEVCHECK.md, ad75632eb). Every LoCoMo number is
"after using LoCoMo for development". Nothing was trained. Counts only.

## Marks
| Mark | Needed | Got | Result |
|---|---|---|---|
| U1: better lines | BU A ≥ BF A + 15, gained > lost, McNemar p < 0.05 | +29, 86 gained, 57 lost, p = 0.019 | holds |
| U2: no harm | BU D ≤ BF D + 8 | 332 against 366 | holds |
| U3: no category hurt | each category drops at most max(3, 3%) | 1: +5; 2: +4; 3: −3 (allowed 3); 4: +23 | holds |
| **PASS** | U1, U2 and U3 | | **PASS** |
| Proved wrong | BU A ≤ BF A | +29 | no |
| V1: better than today's store | BU A ≥ BN A + 15, gained > lost, p < 0.05 | −28, 72 gained, 100 lost | FAIL |
| V2: no harm against the store | BU D ≤ BN D + 8 | 332 against 311 | FAIL |

## Blind check (759 questions, categories 1-4, conversations 0-4; judges see the evidence lines)
| Arm | Lines shown | A right | B | C partly | D wrong | E don't know |
|---|---|---|---|---|---|---|
| BN: store B's first 20 | 20 | 264 | 20 | 148 | 311 | 16 |
| BF: store B's first 3 | 3 | 207 | 8 | 150 | 366 | 28 |
| BU: the 1B's own top 3 of the 20 | 3 | 236 | 8 | 155 | 332 | 28 |

- BU − BF: +29 (95% interval by conversation, report only, +0.5 to +8.4 points).
- BU − BN: −28 (−6.8 to +0.7 points). BF − BN (report only): −57, 64 gained, 121 lost (p = 0.00003).
- Right answers by category (BN, BF, BU): 1: 23, 11, 16 of 141; 2: 18, 21, 25 of 156; 3: 9, 10, 7 of 44;
  4: 214, 165, 188 of 418.
- BF-to-BU table: A→A 150, A→B 2, A→C 17, A→D 35, A→E 3, B→A 3, B→B 3, B→C 1, B→D 1, C→A 20, C→B 1, C→C 90,
  C→D 35, C→E 4, D→A 55, D→B 2, D→C 45, D→D 252, D→E 12, E→A 8, E→C 2, E→D 9, E→E 9.
- BN-to-BU table: A→A 164, A→B 4, A→C 28, A→D 60, A→E 8, B→A 8, B→B 1, B→C 4, B→D 7, C→A 22, C→C 76, C→D 49,
  C→E 1, D→A 40, D→B 3, D→C 45, D→D 214, D→E 9, E→A 2, E→C 2, E→D 2, E→E 10.
- 449 pairs of arms gave byte-identical replies (BN=BF 100, BN=BU 125, BF=BU 224). Their judges agreed on 421 of
  449. The relabel judge agreed with the main labels on 56 of 60.
- The BN replies are bm-398n's, unchanged (sha256 49ddb6d9…a3f7). Judged again here by other judges, they got 264
  right, against 269 in bm-398n. That 5-answer gap is one measure of judge-to-judge noise.
- An independent recount (a separate agent with its own script, reading only the key, the labels and a question →
  category list) agrees on every count above: the label counts, all three comparisons with their p values, the
  category rows, every flag, both tables and both agreements. Treating identical replies as one answer changed 25
  labels.

## Where the gain and the loss come from (report only)
Finding: questions with an evidence turn (any, all) among the lines shown.

| k lines | the 1B's own top k | store B's top k |
|---|---|---|
| 3 (BU, BF) | 492, 405 | 438, 367 |
| 5 | 539, 448 | 495, 408 |
| 8 | 582, 487 | 550, 460 |
| 10 | 601, 504 | 577, 476 |
| 20 (BN) | 639, 541 | 639, 541 |

Only k = 3 was answered. The other rows come from the scores the run saved, with no new replies.

Split by whose lines held an evidence turn. The split was chosen after seeing the labels, so it is suggested only:

| Evidence among the lines of | Questions | Right: first arm | Right: second arm |
|---|---|---|---|
| BU only (BU vs BF) | 118 | BU 43 | BF 4 |
| BF only | 64 | BU 7 | BF 31 |
| both | 374 | BU 161 | BF 153 |
| neither | 203 | BU 25 | BF 19 |
| BN only (BU vs BN) | 147 | BU 18 | BN 61 |
| both | 492 | BU 204 | BN 186 |
| neither | 120 | BU 14 | BN 17 |

- Suggested reading: when the 3 reranked lines hold the evidence, the 1B does better than with all 20 (204 against
  186 on the same 492 questions), which fits bm-398d (fewer distractors, more right). The whole loss against BN is
  the 147 questions where the evidence was among the 20 but the reranker left it out of its 3 (61 → 18). Untested.

## Word overlap and other counts (report only)
- F1, categories 1-4, sealed bm-390 scorer: BN 32.01, BF 28.29, BU 30.79.
- Abstentions: 15, 20, 20. Confident-wrong: 240, 303, 264. Half-right: 230, 207, 229.
- Reranking cost about 13 seconds a question on this CPU (median), on top of answering.

## Predictions
| Prediction | Held? |
|---|---|
| P1 (40%): U1 passes. Point guess +15 | yes (+29) |
| P2 (80%): U2 holds | yes |
| P3 (35%): PASS | yes |
| P4 (75%): not proved wrong | yes |
| P5 (75%): BU's lines hold evidence for more than BF's 438 (report only) | yes (492) |
| P6 (30%): V1 and V2 hold (BU beats today's store) | no |

## What it leads to
- The registered claim holds: the plain 1B reading each line with the question ranks lines better than the store's
  fixed recipe. Picking lines by the model's own reading is worth keeping.
- The PLAN's PASS branch said reranking goes to Answering from memory and Month-end as the next memory-path change.
  It should not go in as tested: with 3 lines it answers worse than today's 20-line store (V1 and V2 fail). What
  carries is the ranking, not the cut to 3.
- The cut was set by the devcheck on code-made chats, where the evidence was in the top 3 for 58 of 60. On LoCoMo the
  reranked top 3 held evidence for 492 of the 639 questions whose evidence was among the 20. DEVCHECK.md warned that
  its pool was easier. Lesson: a cut chosen on easy made-up chats was too tight for real ones.
- Suggested next test (one change, not yet written): the same reranker with a larger cut, fixed before any reply,
  against the 20-line store, on LoCoMo conversations 5-9, ~~whose answers have never been judged~~ where no
  store-B, notes or reranker answers have been judged. It would ask whether fewer, better lines can beat all 20 once
  the cut keeps most of the evidence. [Correction, 2026-09-27 00:26 UTC: 150 of bm-398d's 297 blind questions came
  from conversations 5-9, in other arms (whole chat, right lines, a store's top 20), and F1 was scored on all ten.]
- The learned picker (398p draft, Answering from memory's y1r) now has a bar: it must beat the plain 1B's own
  reranking at the same cut.

## Deviations and disclosures
- score.json names two finding rows "store_B_fused_top5" and "reranked_top5". They hold the top TOP_K = 3 lines
  (the key names were written before the devcheck set TOP_K). The counts are for 3 lines.
- One judge wrote its one-off format-check script in the parent judge folder instead of its own, ran it on its own
  labels only, and deleted it. The parent folder also holds the key. Re-running prep reproduced key.json
  byte-for-byte (sha256 b1cbb463…) and every judge's batch files matched, so nothing there was changed.
- Judges ruled some date and list edge cases differently (for example, the chat session's date given for "last
  week": C for some judges, D for others). Each group holds each arm for a third of the questions, so these rulings
  add noise but favour no arm by design.
- The run took 13,255 s on CPU (4 threads, niced), after bm-398n's run ended, as the PLAN says.
- Replies, scores, judge folders and the recount's own script stay in the scratchpad (they hold benchmark text or
  read from it).

## Files
- score.json (F1 and finding), jscore.json (the blind check, from `claude_bm398u_rerank.py jscore`),
  judge/key.json (item → question id and arm, and which arms' replies were identical), judge/labels/*.jsonl (item
  and label only).
