# y1r addendum 2: bm-398u's reranker as a bar (Answering-from-memory thread, DRAFT 2026-09-27 00:33 UTC, for review before sealing; no y1r run has happened)

**Why:** bm-398u (main d8078eda4, artifacts/claude-bm398u-20260926/RESULTS.md) is the first measured picker to compare
with. On rd-378L's 759 questions the plain 1B, picking its own top 3 of store B's 20 lines by log P(question | line),
answered 236 right against 207 for store B's own top 3 (a PASS at that cut) and 264 for all 20 lines (a FAIL against
today's store). The Thread manager (00:33 UTC) asked that any picker this thread builds must beat the 1B's own
reranking at the same cut.

**What that means for y1r as sealed:**
- y1r works at the 20-line budget (PLAN.md; ADDENDUM-1 keeps k at 20). At a cut of 20, the 1B's rerank of a store's 20
  lines is the same set of lines in another order, so its finding counts equal the store's (bm-398u: 639 any, 541 all
  for both). At 20, arm U is already that bar for finding. The stage 1 and stage 2 marks do not change.
- The bar bites below 20. y1r registers no claim at a cut below 20. If y1r's retriever is ever used at a smaller cut
  (bm-398v proposes K = 8), that use needs its own sealed plan, and its mark is to beat the 1B's own reranking at that
  cut on blind right answers.

**Added, report only (no mark, no decision):** the finding counts ADDENDUM-1 already asks for (arms U, R and C on the
759 questions: the rows of rd-378L's ranked_turns.jsonl, sha256 2792906c…97d4, whose qids match the harness's
"conv-NN#i") are written at every cut the harness already scores (5, 10 and 20; any and all), next to bm-398u's
rows for store B's top k and the 1B's own top k at the same cuts. No code changes: they are counted from
store_recall_per_question.jsonl, which the sealed harness already writes.
- These rows are across stores. Store B is rd-378L's notes-assisted fused ranking; arms U, R and C use store v2's fused
  ranking over raw turns. So the table is a finding, and any comparison in it is suggested, not shown.

**Not added, open for the reviewer:** a same-budget answer bar at 20 (the 1B picking 20 lines out of arm U's top 40,
against arm R's 20). It needs new 1B scoring, belongs with Benchmarks' reranker script, and would only matter if stage
1 passes. Proposed as a follow-up then, not now.
