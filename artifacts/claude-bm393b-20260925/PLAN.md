# bm-393b PLAN: the ep-382 store's recall() on LoCoMo practice (benchmarks thread, 2026-09-25, before running)

What: scripts/claude_bm393b_store_recall.py runs the new store (scripts/claude_ep382_store.py, interface
design/v3/30-modes/382-memory-store-interface.md) the way an agent would use it: every LoCoMo turn remembered as a
"heard" row (word for word, speaker, position, session date as said_at), then recall(bare question, k=20) in three
modes: fused (MiniLM + BM25, reciprocal rank fusion, constant 60), minilm, bm25. Evidence found = an evidence turn's
position in the top k. $0 CPU, no language model, counts only, labelled "after using LoCoMo for development";
nothing trained on LoCoMo. Self-test first (ids, reload, append-only, sources, before, modes): EP382-SELFTEST PASS.

Differences from bm-393 (so the numbers are not identical): rows are "speaker: text" instead of bm-390's
'speaker said, "text"'; BM25 here indexes the speaker name too; the query is always the bare question.

Predictions (written before the run):
- S1: fused recall_any@10 on categories 1-4 is at least 62%.
- S2: fused is higher than both minilm and bm25 on recall_any@10 and on recall_all@10 (categories 1-4).
- S3: the store's minilm recall_any@10 is within 3 points of bm-393's MiniLM (56.3%).
Use: if S1 and S2 hold, recall() keeps fused as its default and ep-382's GPU test (plain 1B answering from
recall()'s top 10 vs Rb's 25.06) uses it; if fused is not better, the default becomes minilm (the interface's text).
