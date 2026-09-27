# y1r addendum 2: bm-398u's reranker as a bar (Answering-from-memory thread, drafted 2026-09-27 00:29 UTC, fixed after the Thread manager's review and sealed 00:35 UTC; no y1r run has happened)

**Why:** bm-398u (main d8078eda4, artifacts/claude-bm398u-20260926/RESULTS.md) is the first measured picker to compare
with. On rd-378L's 759 questions the plain 1B, picking its own top 3 of store B's 20 lines by log P(question | line),
answered 236 right against 207 for store B's own top 3 (a PASS at that cut) and 264 for all 20 of store B's lines
(a FAIL against store B's 20). The Thread manager (message received 00:27 UTC) asked that any picker this thread builds must beat the 1B's own
reranking at the same cut.

**What that means for y1r as sealed:**
- y1r works at the 20-line budget (PLAN.md; ADDENDUM-1 keeps k at 20). At a cut of 20 this bar is empty: the 1B's
  rerank of a store's 20 lines is the same 20 lines in another order, so it finds exactly what the store finds and
  gives the same context (bm-398u: 639 any, 541 all for both). It adds nothing beyond arm U, which y1r already has to
  beat. The stage 1 and stage 2 marks do not change.
- The bar bites below 20. y1r registers no claim at a cut below 20. If y1r's retriever is ever used at a cut below 20
  (bm-398v proposes K = 8), that use needs its own sealed plan, and it passes only if both hold, fixed now:
  - it beats the 1B's own reranking at that cut: blind right answers (label A) at least +15, gained > lost, two-sided
    exact McNemar p < 0.05;
  - it beats all 20 lines of the same store on the same questions: right answers at least +15, gained > lost,
    McNemar p < 0.05 (bm-398u's V1 form). bm-398u showed a 3-line picker can beat its store's top 3 and still lose
    to all 20 (236 against 264), so beating the reranker alone is not enough.

**Added, report only (no mark, no decision):** the finding counts ADDENDUM-1 already asks for (arms U, R and C on the
759 questions: the rows of rd-378L's ranked_turns.jsonl, sha256 2792906c…97d4, whose qids match the harness's
"conv-NN#i") are written at every cut the harness already scores (5, 10 and 20; any and all), next to bm-398u's
rows for store B's top k and the 1B's own top k at the same cuts. No code changes: they are counted from
store_recall_per_question.jsonl, which the sealed harness already writes.
- These rows are across stores. Store B is rd-378L's notes-assisted fused ranking; arms U, R and C use store v2's fused
  ranking over raw turns. So the table is a finding, and any comparison in it is suggested, not shown.
- Store B is a reference, not a store in any build: its notes come from the rd-378 writer, which is out of every build
  (Ben, 16:39 UTC; bm-398v PLAN.md). It is used here only because bm-398u's rows are on it.

**Not added (the review left it as a follow-up):** a same-budget answer bar at 20 (the 1B picking 20 lines out of arm U's top 40,
against arm R's 20). It needs new 1B scoring, belongs with Benchmarks' reranker script, and would only matter if stage
1 passes. Proposed as a follow-up then, not now.
