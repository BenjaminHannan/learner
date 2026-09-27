# bm-398v RESULTS: the 1B's own top 8 lines against all 20 (benchmarks thread, written 2026-09-27 05:24 UTC)

**Verdict: FAIL, and proved wrong.** On LoCoMo conversations 5-9, the plain 1B answered right on 256 of 772
questions from its own top 8 of store B's 20 lines (BU), and on 264 from all 20 (BN), blind. That is 8 fewer right
answers (60 gained, 68 lost, p = 0.54), and 18 more wrong ones. Cutting to the lines the model itself ranks best did
not beat reading all 20, even with a cut that kept about 90% of the found evidence. It is registered as sealed
(PLAN.md 7058498ab, AMEND-1.md 67f2bb2d9) and does not change. Every LoCoMo number is "after using LoCoMo for
development". Counts only.

## Marks
| Mark | Needed | Got | Result |
|---|---|---|---|
| W1: more right answers | BU A ≥ BN A + 15, gained > lost, McNemar p < 0.05 | −8, 60 gained, 68 lost, p = 0.536 | FAIL |
| W2: no harm | BU D ≤ BN D + 8 | 334 against 316 (+18) | FAIL |
| W3: no category hurt | drops of at most 4, 5, 3, 13 (AMEND-1) | 1: −4; 2: +2; 3: 0; 4: −6 | holds |
| Proved wrong | BU A ≤ BN A | 256 ≤ 264 | yes |

## Blind check (772 questions, categories 1-4, conversations 5-9; judges see the evidence lines)
| Arm | Lines shown | A right | B | C partly | D wrong | E don't know |
|---|---|---|---|---|---|---|
| BN: store B's first 20 | 20 | 264 | 26 | 137 | 316 | 29 |
| BU: the 1B's own top 8 of the 20 | 8 | 256 | 19 | 132 | 334 | 31 |

- BU − BN: −8 right answers (95% interval by conversation, report only, −3.1 to +2.1 points).
- Right answers by category (BN → BU): 1: 29 → 25 of 140; 2: 14 → 16 of 164; 3: 13 → 13 of 45; 4: 208 → 202 of 423.
- The BN-to-BU table: A→A 196, A→B 6, A→C 14, A→D 45, A→E 3, B→A 12, B→B 9, B→D 3, B→E 2, C→A 14, C→B 1,
  C→C 86, C→D 32, C→E 4, D→A 31, D→B 2, D→C 30, D→D 243, D→E 10, E→A 3, E→B 1, E→C 2, E→D 11, E→E 12.
- 220 of 772 questions got byte-identical replies from both arms. Their two judges agreed on 211 of 220. The relabel
  judge agreed with the main labels on 59 of 60.
- An independent recount (a separate agent with its own script, reading only the key, the labels and a question →
  category list) agrees on every count above, the McNemar p, the category rows, the split, every flag, the table
  and both agreements.

## Where it was lost (the split fixed in the PLAN, report only)
| Evidence among the lines of | Questions | BN right | BU right |
|---|---|---|---|
| both (BU's 8 and BN's 20) | 579 | 226 | 231 |
| BN's 20 only | 67 | 22 | 6 |
| neither | 126 | 16 | 19 |

- Where the 8 lines held the evidence, fewer lines helped by 5 answers. Where the reranker left the evidence out, 16
  were lost. The loss outweighs the gain.
- bm-398u (conversations 0-4, 3 lines) showed the same pattern, in a split chosen after its labels: +18 where both
  held the evidence, −43 where only the 20 did. Here, with a wider cut, both sides shrank, and the balance is still
  negative.

## Word overlap and other counts (report only)
- F1, categories 1-4, sealed bm-390 scorer: BN 31.27, BU 30.76 (−0.51).
- Abstentions 23 → 24; confident-wrong 230 → 254; half-right 211 → 222.
- Evidence in the lines shown (any, all): BN 646, 534; BU 579, 473. BU's 8 lines held evidence for 89.6% of the
  questions whose evidence was among the 20.

## Predictions
| Prediction | Held? |
|---|---|
| P1 (20%): W1 passes. Point guess +3 | no (−8) |
| P2 (70%): W2 holds | no (+18 wrong) |
| P3 (15%): PASS | no |
| P4 (50%): not proved wrong | no |
| P5 (60%): BU's 8 hold evidence for at least 90% of what the 20 find (report only) | no (89.6%) |

## What it leads to
- Per the PLAN, proved wrong: with this 1B, cutting lines costs more than the distractors do. The plain reranker
  stops here. bm-398u's finding stands (the model's own reading ranks lines better than the store's recipe), but
  no cut of store B's 20 has beaten all 20.
- For problem #4 ("past-chat answers are too long and right less often than Qwen"), the plain fixes tested so far
  have not closed the gap: shortening (bm-397t, bm-398r, bm-398e), a date tool (bm-398c), notes (bm-398n) and
  reranking (bm-398u, bm-398v). bm-398d showed the 1B with only the right lines matches Qwen (137 against 138 of 297),
  while distractors cost it (119). Since picking fewer lines loses evidence, what is left is the reader: getting
  the 1B to read 20 lines as well as it reads the right ones.
- The textbook fix for that is training the reader on questions whose context mixes the right lines with
  distractors (RAFT, Zhang et al. 2024). Here it needs GLM-worded chats and questions with code-checked answers
  (Ben, 16:39 UTC), trained on BensPC or a rental (a rental needs Ben's yes on a plan). It is not written yet.
- A learned picker (398p, y1r) remains the other route. To beat all 20 lines it would have to keep the evidence
  more often than the plain reranker's 89.6% at 8 lines.

## Deviations and disclosures
- The run started at 00:31 UTC, before the Thread manager's review arrived. AMEND-1 (00:34 UTC, before any reply
  was read) fixed the plan's wording and the scope of a PASS; it changed no step of the run.
- Two judges' closing reports quoted a few words of item text as examples of their rulings (generic category
  words, a few answer details, and one gold-answer phrase with its session date). That put those words into the builder's context. They
  are not repeated here and changed no label, since all labels were already written.
- Judges ruled some edge cases differently (for example, the chat session's date given for "a few days before":
  C for some, D for others; a city for a country: A for some, C for others). Each group holds each arm for half the
  questions, so these rulings add noise but favour no arm by design.
- Re-running prep reproduced key.json and every judge's batch files byte-for-byte after judging. Judges saved their
  format-check scripts inside their own folders.
- The run took 17,260 s on CPU (4 threads, niced). Replies, scores, judge folders and the recount's own script stay
  in the scratchpad (they hold benchmark text or read from it).

## Files
- score.json (F1, finding and split counts), jscore.json (the blind check, from `claude_bm398v_rerank8.py jscore`),
  judge/key.json (item → question id and arm, identical replies, the split), judge/labels/*.jsonl (item and label
  only).
