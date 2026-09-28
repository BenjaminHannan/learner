---
name: month-end-02c-result
description: 0.2c registered run (09-26) verified FAIL; what passed/failed, the reader-weights error, and lessons for later joined runs
metadata:
  type: project
---
0.2c ran on BensPC 06:56-10:47 UTC 09-26 (006k). VERIFIED FAIL 11:05 UTC (main 408b60595, artifacts/claude-e2e02c-20260926/VERIFY-02c.md).
- PASS: sleep L1-L6 (TEST lucky 74->192, greedy 5->12, lost 10 of 201 general, exact reload, activation 10/10), C2 grammar 92.3/93.0%, H2 wrong saves 34 vs 36, K2 0 vs 0.
- FAIL: Q1 think numeric 10 vs 12; Q2 10 vs 11; Y1 45 vs 44 of 195; ME1 3 vs 4; H3 "don't know" 18 vs 33 of 36; H1 8 vs 5; H4; C1 30-30; K1 18/50 vs T 21; S1 made-up user facts 26 vs 16. H5/H6 not measured. Chat-path puzzles 0 before and after sleep.
- MY ERROR (D1): bank D X and the DEV gate X got --model READER (lis-301 weights) with lis-319 code; wrong weights load WITHOUT error. Fix: scripts/claude_readersha_wrap.py (READER_SHA) on every reader launch; 0.2d-r reruns those rows. ADDENDUM-D1-dev.md records the dev part.
- S1 cause (Making things up, counts): extra made-up claims all in 1B chat replies; only difference = sleep adapter on for ALL 1B calls -> 0.2d plan: adapter only on the puzzle route (mu-402 tests it).
- Lessons: each blind judge gets a private folder (judges 1+2 shared scratch -> contaminated); Windows needs claude_winnl2_wrap.py; job files need bare `DISK: <GB>` + kit streaming step.
- lis-319 load facts: sha e688e1b2...6a76; BensPC C:/Users/benja/lis319/work/run/merged; Mac ~/premonition-models/lis319-merged; Director depot 52755827:/root/reader319; T=0.995; Reader319 + build_prompt_hist last 6 pairs; greedy, stop "<END>", max_new 200.
- bm-398d (Benchmarks): LoCoMo losses are both finding and reading (right lines 137/297 vs whole chat 109; Qwen 138); answer-level check scripts/claude_bm398d_evidence.py.
Open duties and live jobs: [[month-end-open-duties]]. Road map [[month-end-results]].
