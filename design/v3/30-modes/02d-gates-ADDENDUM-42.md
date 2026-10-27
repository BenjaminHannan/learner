# 0.2d gates, ADDENDUM-42: no trained retriever in 0.2d; the store keeps its frozen ranking. Written Sun Sep 27 11:51:30 UTC 2026, before any run

Month-end. Additive only. No 0.2d code is sealed and nothing has run.

- y1r (Answering from memory; artifacts/claude-y1r-20260926/run/RESULTS.md, 184c59930): stage 1 FAIL, proved wrong as
  registered for its recipe and store. A MiniLM retriever trained on 874 practice pairs, in store v2's fused ranking
  (BM25, k 20), found every evidence line on 961 of 1,531 LoCoMo questions (categories 1-4) against 946 untrained
  (+1.0 point; +10 needed). LoCoMo numbers are after using LoCoMo for development.
- Why it applies: 0.2d's store v4 ranks with v2's ranking unchanged (scripts/claude_ep382_store_v4.py:11).
- Decision: 0.2d keeps the untrained fused ranking (RECALL_MODE02D "fused", frozen MiniLM). No code or mark changes.
