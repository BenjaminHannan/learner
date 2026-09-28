---
name: 24game-move-env-interface
description: What other threads need from the sleep thread's planned move-per-round 24-game env (agreed 2026-09-26 ~12:55 UTC)
metadata:
  type: project
  modified: 2026-09-26T12:55:13.552Z
---
The sleep research thread builds the move-per-round 24-game env plus a sealed loop baseline after 358i. See [[reasoner-roadmap-state]].

- **Memory for its own thoughts (rv-389, go-back on top, code bookkeeping, no undo token) needs:**
  1. a state it can save and restore (page + h);
  2. the move readout as scores over the legal moves, so banned moves can be masked;
  3. apply(state, move) returning the new page;
  4. an end-of-path check (24 reached or not) plus q.
  Send them the env path and the baseline checkpoint once sealed.
- **Creative supplier:** scripts/claude_blurt_supply.py (main cce8f84ed; `--sleep-out HITS.jsonl` writes {hand,target,expr} directly; expr may have odd spacing, normalise before E.number_item).
  - Input: jsonl of {"nums", "target"}.
  - night_examples(rows) gives one (puzzle, answer) per puzzle: greedy if right, else first_hit.
  - Hits are expressions, e.g. "(8 - 1) * 3 + 3". Converting them to moves is the sleep thread's job, or ask Creative to emit moves instead.
  - Expect hits on ~20% of 4-number misses (13-19 of 80 fresh hands).
  - Day hands must come from practice hands only, never the held-out 300 or 5-number test hands.
- rv-387: a separate grids go-back wrapper on 358i checkpoints. It re-embeds after writing a given, and fills its written cells into the final grid before check_latin.

**Why:** Ben's 12:48 rule that threads integrate their functions.
**How to apply:** design the env API to these four calls before sealing, and message both threads when it is ready.
- Ben 13:57 09-26 wants an always-on reasoner that keeps thinking about open tasks between messages. Proposed (default yes unless he objects): after 358i, a registered "unfinished problems" test: the day's unsolved puzzles are kept, the loop works on them in downtime with far more rounds + checker + go-back, and the score is how many are solved by morning.
- rv-390 AGREED (13:59): Memory-for-thoughts owns the between-messages worker (after rv-387). Headline = unfinished solved vs nothing and vs 10 noisy restarts (same compute). Day puzzles use seeds 39101-39104 (sums6/8, grids6/7, legend via 358i). Reserved and never used: 358i test seeds and 58600-59999 (my night tests). Fix sleep keys 1B downtime hits by puzzle and trains each once.
