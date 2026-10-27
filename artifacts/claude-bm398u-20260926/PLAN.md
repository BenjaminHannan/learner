# bm-398u PLAN: the plain 1B reranks its lines before answering (benchmarks thread, first written 2026-09-26 19:28 UTC, revised 19:34 UTC after the Thread manager's review)

Registered and sealed before bm-398n's result is read, before any BF or BU reply exists, and before the reranker has
scored any LoCoMo line. The only run before sealing is a check on code-made chats (devcheck), which sets TOP_K by
the rule below; its counts are in DEVCHECK.md. Every LoCoMo number is "after using LoCoMo for development". Nothing
is trained. Counts only.

## Why ("obvious fix first", Thread manager 19:24 UTC after Ben's 19:20 message)
- The textbook fix for long-chat questions with a small model is retrieve, rerank, read. Here is where each part
  stands:
  - Hybrid retrieval (BM25 fused with MiniLM) was tested. Blind, the store's top 20 lines got 88 of 297 right,
    against 109 for the whole chat (bm-398d, 56c71354c).
  - Fact notes (the LoCoMo paper's observations) improve finding (rd-378L, rd-378u). Whether they improve answers is
    bm-398n, still running.
  - A reranker that reads each line with the question has not been tested.
- bm-398d: with only the right lines, the plain 1B is right on 137 of 297, about Qwen3.5-2B on the whole chat
  (138). With the right lines plus distractors it drops to 119. Fewer, better lines is the lever.
- Brain first (a textbook-level guess): recognition comes before recall. A cue is checked against candidate
  memories ("does this fit what I'm being asked?"), and only the ones that fit are brought back in full.

## Arms (all three answer from store B's lines, laid out and prompted the same way; only which lines differ)
- **BN** (from bm-398n, unchanged): the plain MiniCPM5-1B answers each of rd-378L's 759 questions from store B's
  first 20 distinct turns (notes-assisted fused ranking), in chat order under their session dates, with bm-390's
  prompt. Its replies are checked to be bm-398n's (same 759 questions, same 20 turns each). Their sha256 goes in
  score.json.
- **BF:** store B's own fused order, cut to its first TOP_K turns.
- **BU:** the same 20 turns. Before answering, the same 1B scores each turn as sum log P(question | turn), where the
  turn is shown with its session date under UPR_USER ("…Write a question that this message answers."), system
  "You are a helpful assistant.", thinking off. This is UPR (Sachan et al. 2022). Only the TOP_K best-scored turns
  go to the 1B (ties to store B's order).
- For every arm the answer step is the same: bm-390's system and QA prompt, 50 new tokens, greedy, CPU fp32.
- **The one change for the registered claim is BU against BF:** the same number of lines, so only the ranking
  differs. BU against BN is the "against today's store" row, with its own mark.
- No training and no new model. Nothing hand-written decides anything; the model's own likelihood picks the lines.
- **TOP_K** is fixed by this rule before the check runs, on code-made chats only, never LoCoMo. The check pools each
  question's evidence turns with random other turns of the same chat, up to 20. TOP_K is the smallest of 3, 5 and 8
  whose all-evidence count is at least 90% of the count for 8. Fewer lines means fewer distractors (bm-398d:
  137 → 119 with distractors), so take the smallest k that loses little.
- **Set by the check (DEVCHECK.md, 19:50 UTC): TOP_K = 3.** On 60 code-made questions, all evidence was in the
  reranker's top 3 for 58, top 5 for 59, and top 8 for 60.
- Already known from the turn lists, computed before sealing with no reply: an evidence turn is among store B's 20
  for 639 of 759 questions (all evidence for 541), among its fused top 5 for 495 (all for 408), and among its fused
  top 3 (BF's lines) for 438 (all for 367).
- Script: scripts/claude_bm398u_rerank.py (selftest 16/16).

## Blind check
- bm-398d's rubric: INSTRUCTIONS.md copied unchanged, so judges see the evidence lines. The labels are A right, B
  right plus a conflicting answer, C partly right, D wrong, E says it doesn't know.
- Latin square with three groups (group g holds arm ARMS[(n + g) % 3] of question n), random.Random(3997), 50-item
  batches. That is 3 × 759 items: 48 batches, 16 per group. X1 = the first 60 questions as group L0 holds them, for a relabel
  judge who judges no group.
- 12 main Opus judges (about 4 batches each, never two groups) and 1 relabel judge, in private folders outside the
  repository. Then an independent recount from the key and labels only.
- Byte-identical replies of two arms are one answer. Every arm in such a set takes the label of the member in the
  lowest-numbered group, and the pair is a tie.

## Marks (fixed now; coded in verdict())
- **U1 (the reranker picks better lines):** BU's A-count ≥ BF's + 15 of 759, with more gained than lost and a
  two-sided exact McNemar p < 0.05.
- **U2 (no harm):** BU's D (wrong) count ≤ BF's D + 8. E ("doesn't know") may rise; it is reported.
- **U3 (no category hurt):** in each of categories 1-4, BU's A-count is at most max(3, 3% of the category) below BF's.
- **PASS** = U1, U2 and U3. Anything else is a registered FAIL.
- **Proved wrong:** BU's A-count ≤ BF's. The model's own ranking would then pick no better than the store's order.
- **Against today's store (its own mark):** V1 = BU's A ≥ BN's + 15, gained > lost, McNemar p < 0.05. V2 = BU's
  D ≤ BN's D + 8. "Better than today's store" is claimed only if V1 and V2 both hold.
- **Report only:**
  - BF against BN (cutting to TOP_K lines without reranking);
  - F1 with the sealed bm-390 scorer, abstentions and confident-wrong counts;
  - finding: questions with an evidence turn (any, all) among store B's 20, BF's lines and BU's lines;
  - A by category, gained and lost, the BF-by-BU and BN-by-BU label tables;
  - relabel agreement, agreement on identical pairs, the conversation bootstrap.

## Predictions
First stated for TOP_K = 5 (19:34 UTC), then restated at 19:50 UTC for TOP_K = 3 once the check set it, before
sealing and before any LoCoMo line was scored. With 3 lines, BF is weaker than a 5-line cut, so the gain over BF
can be larger. Meanwhile BU has fewer chances to hold the evidence, so beating BN (20 lines) is harder.
- P1 (40%): U1 passes. Point guess: BU − BF = +15. (At TOP_K 5: 35%, +12.)
- P2 (80%): U2 holds.
- P3 (35%): PASS.
- P4 (75%): not proved wrong.
- P5 (75%): BU's lines hold an evidence turn for more questions than BF's 438 (report only).
- P6 (30%): V1 and V2 hold (BU beats today's store). (At TOP_K 5: 40%.)

## What it leads to
- **PASS:** reranking by the model's own reading is the next memory-path change. It goes to Answering from memory
  and Month-end as one change. The learned picker (398p draft, and Answering from memory's y1r) must then beat it.
- **FAIL, not proved wrong:** check the finding counts. If BU finds more than BF but answers no better, the loss is
  in reading, not ranking.
- **Proved wrong:** the plain 1B can't pick its own lines this way. Line choice then waits for a learned picker,
  trained on GLM data.

## Run and files
- CPU in this container, $0. It starts after bm-398n's run ends. 759 questions, 20 line scores and two answers each.
- Repository: RESULTS.md, score.json, the judge key and labels, DEVCHECK.md. Replies, scores and judge folders stay
  in the scratchpad.
