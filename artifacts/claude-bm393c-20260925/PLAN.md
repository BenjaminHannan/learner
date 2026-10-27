# bm-393c PLAN: one change to how the store ranks rows (benchmarks thread, 2026-09-25, before running)

bm-393b (RESULTS.md there) showed the store's MiniLM ranking 5 points below bm-393's (51.3% vs 56.3% any@10), and the
only difference in that path was the row text. The one change: scripts/claude_ep382_store_v2.py ranks rows by
'<speaker> said, "<text>"' (bm-390's turn format) instead of "<speaker>: <text>". Stored text, queries, k, fusion,
data and scoring are bm-393b's sealed code (scripts/claude_bm393c_store_recall.py swaps only the store module).
$0 CPU, counts only, labelled "after using LoCoMo for development"; nothing trained on LoCoMo.
Self-test with version 2: EP382-SELFTEST PASS.

Predictions (written before the run):
- C1: minilm recall_any@10 (categories 1-4) is at least 54.3% (within 2 points of bm-393's 56.3%).
- C2: fused recall_any@10 is at least 64.0% (bm-393b: 62.9%).
Use: if C2 holds, version 2 is the store for ep-382's GPU test and for month-end's join; if not, version 1 stays.
This is the last retrieval change tried on LoCoMo before the GPU test, to avoid tuning the store to LoCoMo.
