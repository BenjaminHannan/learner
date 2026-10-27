# 0.2d gates, ADDENDUM-21: K1 creative row fixed. Written 2026-09-26 16:55 UTC, before any run

- Panel: artifacts/claude-crepanel02d-20260926/creative/items.jsonl (Creative answers in chat, sealed 9ffe2e08f,
  TEST-ONLY, never run or read). Its sha256 is 503bcd525a3629adaf8830bdfe2deea6a873e56b5a887590b7710d683d450535, which Month-end
  checked. It has 100 items: 35 idea items with a lead-in, 35 without, and 30 uses_facts items.
- Scorer: scripts/claude_k1rival_score.py (6fdf00563), sealed with the runner, twin recipe and judge brief
  (SEAL-scoring.sha256.txt).
- K1 is a no-harm row. PASS against each of T (MiniCPM5-1B), Q (Qwen3.5-2B) and L (LFM2.5-1.2B) requires two things:
  the build is not "behind" on useful replies (one-sided exact sign test in the rival's favour, p <= 0.05), and it has
  made-up replies <= the rival's + 3.
- Reported, not claimed: "ahead", and the 60% useful line.
- The talker's creative path is k1a (ADDENDUM-15).
