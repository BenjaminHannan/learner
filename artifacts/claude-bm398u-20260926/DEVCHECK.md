# bm-398u DEVCHECK: the reranker on code-made chats, which sets TOP_K (written 2026-09-26 19:50 UTC)

Run before sealing, on code-made chats only (artifacts/claude-bm398e-20260926/inputs/made.json, sha256
c19c82b3…b137). No LoCoMo line was scored. Command: `claude_bm398u_rerank.py devcheck --made … --limit 60`
(plain MiniCPM5-1B, CPU fp32, 912 s).

For each of the first 60 questions with evidence, the pool was the question's evidence turns plus random other turns
of the same chat, up to 20, in a seeded order (random.Random(3998)). The 1B scored every turn by
sum log P(question | turn).

| k | any evidence turn in the top k | all evidence turns in the top k | chance, one evidence turn |
|---|---|---|---|
| 3 | 60 of 60 | 58 of 60 | 15% |
| 5 | 60 of 60 | 59 of 60 | 25% |
| 8 | 60 of 60 | 60 of 60 | 40% |

An evidence turn was ranked first on 59 of 60.

**TOP_K by the PLAN's rule** (the smallest of 3, 5 and 8 whose all-evidence count is at least 90% of k = 8's, so at
least 54): **TOP_K = 3**.

Caveats:
- This pool is much easier than a store's top 20. The other turns are random turns of the chat, not near-misses
  picked by a retriever, and the code-made chats use plain wording. So this check shows the scorer points the right
  way. It does not predict how well it ranks store B's lines on LoCoMo.
- The code-made chats were built from Claude-written sentence patterns. They are used here only to set one number,
  not to train anything.
- A first devcheck run (top 5 only) was stopped by exact PID before it printed anything, so the report could cover
  k = 3, 5 and 8. Its output was never seen.
