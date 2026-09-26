# bm-riv smoke 1: what it showed (Benchmarks thread, written 2026-09-26 16:23 UTC)

The rental report is on builder-outbox: artifacts/claude-bmriv-smoke-20260926/RESULTS-rent.md.
- It ran on an RTX 4090 and stopped at the $0.27 money rule after $0.261.
- The first rental never accepted SSH, which cost $0.065.
- plain1b and qwen2b finished all 30 items.
- lfm12b kept 10 rows, and each of the three thinking-on shards kept 6.
- No code error.

## The finding: the 512-token cap cuts off every rival
Every model works through these puzzles step by step, even with thinking off, and runs out of tokens before
writing a final grid.

| Arm | Rows | Hit the cap | Thinking closed |
|---|---|---|---|
| plain1b (512) | 30 | 25 | - |
| qwen2b (512) | 30 | 30 | - |
| lfm12b (512) | 10 | 10 | - |
| qwen2b_think (4,096) | 18 | 17 | 2 |

- A rough line count, not the scorer, looked for any reply containing a filled grid (as many lines of digits as the
  puzzle has rows, with no blanks). plain1b had 9 of 30, qwen2b 5 of 30 and lfm12b 3 of 10.
- 16 of 18 thinking-on replies are empty, because the thinking never closed within 4,096 tokens.
- A 512-token cap would score the rivals on where they were cut off, not on what they can do. The headline
  comparison with same-size models has to let them finish.

## What changes (decided here; undoable; nothing was sealed)
- Recommended to Sleep research for rsn-358b3 and to Month-end for row A:
  - 4,096 new tokens for every arm with thinking off;
  - 16,384 for the report-only Qwen arm with thinking on;
  - hit_max counts reported beside every score.
- Smoke 2 (handoff/queue/rent-bmrivsmoke2.md) runs the three thinking-off arms at 4,096 on 8 of the 30 items
  (--shard 1/4: sizes 5, 6, 5, 6, 7, 7, 5, 6). It gives Sleep research whole replies with final answers to
  check its parser against. The thinking-on arm is not rerun: once thinking closes, its reply is parsed the same way.
- Speed seen: one process ran about 24 tokens a second with four sharing the 4090, so about 96 a second in all.
