# bm-398v PLAN: can the 1B's own top 8 lines beat reading all 20? (benchmarks thread, written 2026-09-27 00:30 UTC)

Registered and sealed before any reply on conversations 5-9 exists. Nothing is trained. Counts only. Every LoCoMo
number is "after using LoCoMo for development": conversations 0-4 were used by bm-398n and bm-398u, and 150 of
bm-398d's 297 blind questions came from conversations 5-9 (whole chat, right lines, a store's top 20). No store-B,
notes or reranker answer has been judged on conversations 5-9.

## Why
- bm-398u (d8078eda4, recount agrees): the plain 1B scoring each of store B's 20 lines by log P(question | line)
  and keeping its top 3 answered right on 236 of 759, against 207 for store B's own top 3 (p 0.019). But all 20
  lines gave 264: the cut to 3 lost more than the better ranking gained.
- Suggested only (split chosen after the labels): where both the 3 reranked lines and the 20 held evidence (492
  questions), 3 lines did better (204 against 186). The loss was the 147 questions whose evidence the reranker left
  out of its 3.
- The cut of 3 came from a check on code-made chats that was too easy (evidence in the top 3 for 58 of 60). This
  test widens the cut so it keeps most of the evidence, and asks the question that matters for the memory path:
  do fewer, model-picked lines beat all 20?
- Brain first (a textbook-level guess): recognition checks many candidates quickly, and only the ones that fit are
  brought back in full. The open question is how many to bring back.

## The one change
- **BN:** the plain MiniCPM5-1B answers each of rd-378u's 772 questions (LoCoMo conversations 5-9, categories 1-4,
  with evidence) from store B's first 20 distinct turns, in chat order under their session dates, with bm-390's
  prompt. The turns come from rd-378u's ranked_turns.jsonl (f4edf55ac, sha256 785c9c9a…ff5e, pinned in the
  script). Its turn numbers match this harness: rd-378u's any@5/10/20 counts for stores A and B were reproduced
  exactly before sealing.
- **BU:** the same 20 turns. The same 1B scores each with bm-398u's scorer, unchanged. Only the TOP_K best (ties to
  store B's order) go to the 1B, laid out and prompted exactly as BN.
- **The registered claim is BU against BN.** Only which lines the 1B reads differs.
- **TOP_K = 8**, set by a rule on conversations 0-4 only, from bm-398u's saved scores (no new reply). The rule is
  the smallest k in 5, 8 and 10 whose reranked any@k is at least 90% of the 20 lines' any@20. The counts were 539,
  582 and 601 against 639, and 90% is 575.2, so k = 8. `claude_bm398v_rerank8.py kcheck` re-derives it. This rule was
  written after bm-398u's labels were seen.
- Store B's notes come from the rd-378 writer, which is out of every build (Ben, 16:39 UTC) because it learned from
  Claude-written notes. That is fine here, since nothing is trained and the reranker sits on top of any store. It
  keeps BN comparable with bm-398n and bm-398u. A store A run would be a separate test.
- Script: scripts/claude_bm398v_rerank8.py (selftest 11/11). A 2-question smoke on conversations 0-4 only (`--dev`)
  ran end to end. Its 2 BN replies were byte-identical to bm-398n's for the same questions.

## Blind check
- bm-398d's rubric: INSTRUCTIONS.md copied unchanged, so judges see the evidence lines. The labels are A right, B
  right plus a conflicting answer, C partly right, D wrong, E says it doesn't know.
- Latin square with two groups: group g holds arm ARMS[(n + g) % 2] of question n. random.Random(3999), 50-item
  batches: 16 per group. X1 = the first 60 questions as group L0 holds them, for a relabel judge who judges no group.
- 8 main Opus judges (4 batches each, one group each) and 1 relabel judge, in private folders outside the
  repository. Then an independent recount from the key and labels only.
- Byte-identical BN and BU replies are one answer. Both arms take group L0's label, and the question is a tie.

## Marks (fixed now; coded in verdict())
- **W1 (more right answers):** BU's A-count ≥ BN's + 15 of 772, with more gained than lost and a two-sided exact
  McNemar p < 0.05.
- **W2 (no harm):** BU's D (wrong) count ≤ BN's D + 8. E ("doesn't know") may rise; it is reported.
- **W3 (no category hurt):** in each of categories 1-4, BU's A-count is at most max(3, 3% of the category) below
  BN's.
- **PASS** = W1, W2 and W3. Anything else is a registered FAIL.
- **Proved wrong:** BU's A-count ≤ BN's. Then even a cut that keeps about 90% of the finds does not beat all 20.
- **Report only:**
  - F1 with the sealed bm-390 scorer, abstentions, confident-wrong counts;
  - evidence in the lines shown (any, all) for BN and BU;
  - a split fixed now: questions whose evidence reached BU's 8 ("both"), reached only BN's 20 ("BN only"), or
    neither, with each arm's A-count in each;
  - A by category, gained and lost, the BN-by-BU label table;
  - relabel agreement, agreement on identical pairs, the conversation bootstrap.

## Predictions
- P1 (20%): W1 passes. Point guess: BU − BN = +3. The reasoning: on 0-4, 3 lines gained about 18 on the questions
  both found and lost about 43 on the ones only the 20 found. At 8 lines, fewer questions are missed (about 57 of
  639 on 0-4), but the gain from fewer distractors is also smaller.
- P2 (70%): W2 holds.
- P3 (15%): PASS.
- P4 (50%): not proved wrong.
- P5 (60%): BU's 8 lines hold evidence for at least 90% of the questions whose evidence is in the 20 (report only).

## What it leads to
- **PASS:** the model's own reranking with an 8-line cut goes to Answering from memory and Month-end as one
  memory-path change, and the learned picker (398p, y1r) must beat it.
- **FAIL, not proved wrong:** the plain reranker is not enough at this size. Line choice waits for a learned picker
  trained on GLM data, and the gap to Qwen stays in reading.
- **Proved wrong:** with this 1B, cutting lines costs more than distractors do. The next plain fix to test is the
  reader itself: training on reading with distractors, from GLM-worded chats with code-checked answers.

## Run and files
- CPU in this container, $0. About 25 seconds a question (smoke), so about 5.5 hours for 772.
- Repository: RESULTS.md, score.json, the judge key and labels. Replies, scores and judge folders stay in the
  scratchpad.
