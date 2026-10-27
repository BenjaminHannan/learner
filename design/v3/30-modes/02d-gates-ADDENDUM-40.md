# 0.2d gates, ADDENDUM-40: no line reranker in 0.2d; the store's 20 lines stay. Written Sun Sep 27 07:25:51 UTC 2026, before any run

Month-end. Additive only. No 0.2d code is sealed and nothing has run.

- bm-398v (Benchmarks, artifacts/claude-bm398v-20260927/RESULTS.md, df149a5b8): FAIL and proved wrong. The plain 1B
  answering from its own top 8 of store B's 20 lines got 256 of 772 LoCoMo questions right against 264 from all 20
  (60 gained, 68 lost, p 0.54), with 18 more wrong answers. bm-398u's top-3 rerank also lost to all 20 (236 vs 264 of
  759; artifacts/claude-bm398u-20260926/RESULTS.md).
- Decision: 0.2d adds no reranking step. K02D stays 20 (scripts/claude_e2e02d.py), as already written. This confirms
  the draft; it changes no code and no mark.
- Scope: these are LoCoMo results after using LoCoMo for development, on the plain 1B, not on the 0.2d build.
